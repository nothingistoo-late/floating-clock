"""
Salary calculation and Payday Countdown Engine
Hỗ trợ tăng ca (OT session), BHXH NLĐ ước lượng, gross/net trên đồng hồ.
"""
import calendar
from datetime import datetime, timedelta
from app.messages import SALARY_TEXTS


def get_payday_countdown_info(now, payday_day=5):
    """
    Tính số ngày đếm ngược đến ngày nhận lương tiếp theo.
    Xử lý an toàn cho mọi ngày trong tháng (28, 29, 30, 31) không bị crash ValueError.
    """
    year = now.year
    month = now.month
    try:
        max_days_current = calendar.monthrange(year, month)[1]
        target_day = min(max(1, int(payday_day)), max_days_current)
        target_payday = datetime(year, month, target_day, 9, 0, 0)

        # Cùng ngày nhận lương → còn 0 ngày (tránh ceil buổi sáng ra 1)
        if now.date() == target_payday.date():
            return 0, target_payday.strftime("%d/%m/%Y")

        if now > target_payday:
            if month == 12:
                next_year = year + 1
                next_month = 1
            else:
                next_year = year
                next_month = month + 1
            max_days_next = calendar.monthrange(next_year, next_month)[1]
            target_day_next = min(max(1, int(payday_day)), max_days_next)
            target_payday = datetime(next_year, next_month, target_day_next, 9, 0, 0)

        diff_days = (target_payday.date() - now.date()).days
        return max(0, int(diff_days)), target_payday.strftime("%d/%m/%Y")
    except Exception:
        return 0, ""


def is_holiday_date(now, config):
    """Kiểm tra hôm nay có khớp holidays (month/day) trong config không."""
    try:
        holidays = config.get("holidays") or []
        for h in holidays:
            if int(h.get("month", 0)) == now.month and int(h.get("day", 0)) == now.day:
                return True, h.get("name", "Ngày lễ")
    except Exception:
        pass
    return False, ""


def resolve_ot_multiplier(now, config):
    """
    Chọn hệ số OT theo ngày: lễ > CN > ngày thường.
    Trả (multiplier, kind_label).
    """
    sal = config.get("salary", {})
    is_hol, hol_name = is_holiday_date(now, config)
    if is_hol:
        return float(sal.get("ot_multiplier_holiday", 3.0)), f"Ngày lễ ({hol_name})" if hol_name else "Ngày lễ"
    if now.weekday() == 6:
        return float(sal.get("ot_multiplier_sunday", 2.0)), "Chủ nhật"
    return float(sal.get("ot_multiplier_weekday", 1.5)), "Ngày thường"


def _normalize_ot_time_str(raw):
    """Chuẩn hóa 'HH:MM' / 'HH:MM:SS' → 'HH:MM:SS' hoặc None."""
    if not raw:
        return None
    s = str(raw).strip()
    parts = s.split(":")
    try:
        if len(parts) == 2:
            h, m = int(parts[0]), int(parts[1])
            return f"{h:02d}:{m:02d}:00"
        if len(parts) >= 3:
            h, m, sec = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{h:02d}:{m:02d}:{sec:02d}"
    except Exception:
        return None
    return None


def reset_ot_session_if_needed(config, now):
    """
    Sang ngày mới → xóa ot_start. Trả True nếu đã sửa config (caller nên save).
    """
    sal = config.setdefault("salary", {})
    today = now.strftime("%Y-%m-%d")
    ot_date = sal.get("ot_date", "") or ""
    if ot_date and ot_date != today:
        sal["ot_start"] = None
        sal["ot_date"] = ""
        return True
    return False


def set_ot_start(config, start_time_str, now=None):
    """Lưu phiên OT hôm nay. start_time_str: HH:MM hoặc HH:MM:SS."""
    now = now or datetime.now()
    norm = _normalize_ot_time_str(start_time_str)
    if not norm:
        raise ValueError("Giờ bắt đầu tăng ca không hợp lệ (HH:MM)")
    sal = config.setdefault("salary", {})
    sal["ot_start"] = norm
    sal["ot_date"] = now.strftime("%Y-%m-%d")
    return norm


def clear_ot_session(config):
    """Dừng phiên tăng ca."""
    sal = config.setdefault("salary", {})
    sal["ot_start"] = None
    sal["ot_date"] = ""


def _fmt_vnd(amount):
    return f"{int(amount):,} đ".replace(",", ".")


def calculate_salary_info(now, config, get_today_departure_func):
    """
    Tính toán chi tiết tiền lương realtime (theo ngày & lũy kế tháng / chu kỳ nhận lương).
    Gồm OT (nếu đã bấm bắt đầu tăng ca) và BHXH ước lượng.
    """
    sal_cfg = config.get("salary", {})
    if not sal_cfg.get("enabled", False):
        return {}

    # Reset OT sang ngày mới (in-memory; caller có thể save nếu cần)
    reset_ot_session_if_needed(config, now)
    sal_cfg = config.get("salary", {})

    monthly = float(sal_cfg.get("monthly", 15000000))
    work_days = max(1, int(sal_cfg.get("work_days", 22)))
    work_hours = max(1.0, float(sal_cfg.get("work_hours", 8.0)))

    daily_rate = monthly / work_days if work_days > 0 else 0.0
    hourly_rate = daily_rate / work_hours if work_hours > 0 else 0.0

    work_cfg = config.get("work_departure", {
        "start_time": "08:30",
        "mon_fri_time": "17:45",
        "sat_time": "16:00",
        "lunch_start": "12:00",
        "lunch_end": "13:15"
    })
    today_str = now.strftime("%Y-%m-%d")
    st_str = work_cfg.get("start_time", "08:30") + ":00"
    dep_time, _ = get_today_departure_func(now)
    ls_str = work_cfg.get("lunch_start", "12:00") + ":00"
    le_str = work_cfg.get("lunch_end", "13:15") + ":00"

    daily_earned = 0.0
    worked_hours = 0.0
    today_scheduled_hours = work_hours
    is_lunch = False
    try:
        dt_start = datetime.strptime(f"{today_str} {st_str}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        dt_start = datetime.strptime(f"{today_str} 08:30:00", "%Y-%m-%d %H:%M:%S")
    try:
        # dep_time có thể đã có giây
        dep_norm = dep_time if len(str(dep_time).split(":")) >= 3 else f"{dep_time}:00"
        dt_end = datetime.strptime(f"{today_str} {dep_norm}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        dt_end = datetime.strptime(f"{today_str} 17:45:00", "%Y-%m-%d %H:%M:%S")

    try:
        dt_lunch_start = datetime.strptime(f"{today_str} {ls_str}", "%Y-%m-%d %H:%M:%S")
        dt_lunch_end = datetime.strptime(f"{today_str} {le_str}", "%Y-%m-%d %H:%M:%S")

        if dt_start < dt_lunch_start < dt_lunch_end < dt_end:
            today_scheduled_sec = (dt_lunch_start - dt_start).total_seconds() + (dt_end - dt_lunch_end).total_seconds()
        elif dt_start < dt_lunch_start <= dt_end <= dt_lunch_end:
            today_scheduled_sec = (dt_lunch_start - dt_start).total_seconds()
        else:
            today_scheduled_sec = max(0.0, (dt_end - dt_start).total_seconds())

        if today_scheduled_sec <= 0:
            today_scheduled_sec = work_hours * 3600.0

        today_scheduled_hours = max(0.5, today_scheduled_sec / 3600.0)
        today_hourly_rate = daily_rate / today_scheduled_hours if today_scheduled_hours > 0 else hourly_rate

        if now <= dt_start:
            daily_earned = 0.0
            worked_hours = 0.0
        elif now >= dt_end:
            worked_hours = today_scheduled_hours
            daily_earned = daily_rate
        else:
            if dt_start < dt_lunch_start < dt_lunch_end < dt_end:
                if now < dt_lunch_start:
                    worked_sec = (now - dt_start).total_seconds()
                elif dt_lunch_start <= now < dt_lunch_end:
                    is_lunch = True
                    worked_sec = (dt_lunch_start - dt_start).total_seconds()
                else:
                    morning_sec = (dt_lunch_start - dt_start).total_seconds()
                    afternoon_sec = (now - dt_lunch_end).total_seconds()
                    worked_sec = morning_sec + afternoon_sec
            else:
                total_window_sec = (dt_end - dt_start).total_seconds()
                ratio = (now - dt_start).total_seconds() / max(1.0, total_window_sec)
                worked_sec = ratio * today_scheduled_sec

            worked_sec = max(0.0, min(today_scheduled_sec, worked_sec))
            worked_hours = worked_sec / 3600.0
            daily_earned = min(daily_rate, worked_hours * today_hourly_rate)
    except Exception:
        daily_earned = 0.0
        worked_hours = 0.0
        today_scheduled_hours = work_hours
        today_hourly_rate = hourly_rate

    # Tính lũy kế tháng tới hôm qua
    cycle_mode = sal_cfg.get("calc_cycle", "calendar_month")
    payday_day = config.get("payday_day", 5)
    past_work_days = 0
    cycle_label = f"Tháng {now.month}"

    if cycle_mode == "payday_cycle":
        try:
            if now.day >= payday_day:
                max_d = calendar.monthrange(now.year, now.month)[1]
                dt_c_start = datetime(now.year, now.month, min(payday_day, max_d)).date()
            else:
                if now.month == 1:
                    prev_y = now.year - 1
                    prev_m = 12
                else:
                    prev_y = now.year
                    prev_m = now.month - 1
                max_d = calendar.monthrange(prev_y, prev_m)[1]
                dt_c_start = datetime(prev_y, prev_m, min(payday_day, max_d)).date()

            cur_d = dt_c_start
            yesterday = now.date() - timedelta(days=1)
            while cur_d <= yesterday:
                w_day = cur_d.weekday()
                if work_days >= 24:
                    if w_day <= 5:
                        past_work_days += 1
                else:
                    if w_day <= 4:
                        past_work_days += 1
                cur_d += timedelta(days=1)
            cycle_label = f"Kỳ {dt_c_start.strftime('%d/%m')}"
        except Exception:
            cycle_label = "Kỳ Lương"
    else:
        cur_year = now.year
        cur_month = now.month
        for day in range(1, now.day):
            try:
                dt_d = datetime(cur_year, cur_month, day)
                w_day = dt_d.weekday()
                if work_days >= 24:
                    if w_day <= 5:
                        past_work_days += 1
                else:
                    if w_day <= 4:
                        past_work_days += 1
            except Exception:
                pass
        cycle_label = f"Tháng {now.month}"

    is_weekend = (now.weekday() == 6) or (now.weekday() == 5 and work_days <= 22)
    if is_weekend:
        daily_earned = 0.0
        worked_hours = 0.0

    # --- Tăng ca (OT session) ---
    ot_start_raw = sal_cfg.get("ot_start")
    ot_date = sal_cfg.get("ot_date", "") or ""
    ot_active = False
    ot_earned = 0.0
    ot_hours = 0.0
    ot_start_display = ""
    ot_mult, ot_kind = resolve_ot_multiplier(now, config)

    if ot_date == today_str and ot_start_raw:
        norm_ot = _normalize_ot_time_str(ot_start_raw)
        if norm_ot:
            try:
                dt_ot = datetime.strptime(f"{today_str} {norm_ot}", "%Y-%m-%d %H:%M:%S")
                ot_sec = max(0.0, (now - dt_ot).total_seconds())
                ot_hours = ot_sec / 3600.0
                ot_earned = ot_hours * hourly_rate * ot_mult
                ot_active = True
                ot_start_display = norm_ot[:5]
            except Exception:
                pass

    # Nút OT: sau tan làm (ngày làm) HOẶC cuối tuần/lễ (có thể OT cả ngày)
    # Theo plan: show khi now >= dt_end; cuối tuần vẫn cho bấm nếu đã hết “ca” (dt_end)
    show_ot_button = bool(sal_cfg.get("enabled", False)) and (now >= dt_end)

    daily_gross = daily_earned + ot_earned
    # Tháng: past đầy đủ + gross hôm nay (không cap cứng bỏ OT — cap soft bằng monthly*1.5 nếu cần)
    month_base = past_work_days * daily_rate
    month_gross = month_base + daily_gross

    # --- BHXH NLĐ ước lượng ---
    deduct_bhxh = bool(sal_cfg.get("deduct_bhxh", False))
    bhxh_base = float(sal_cfg.get("bhxh_base") or 0)
    if bhxh_base <= 0:
        bhxh_base = monthly
    bhxh_rate_pct = float(sal_cfg.get("bhxh_rate_pct", 10.5))
    bhxh_month_full = bhxh_base * (bhxh_rate_pct / 100.0) if deduct_bhxh else 0.0

    progress = 0.0
    if monthly > 0:
        progress = max(0.0, min(1.0, month_gross / monthly))
    bhxh_month = bhxh_month_full * progress if deduct_bhxh else 0.0
    # Phần BHXH quy cho hôm nay theo tỷ lệ gross ngày / gross tháng
    if deduct_bhxh and month_gross > 0:
        bhxh_daily = bhxh_month * (daily_gross / month_gross)
    else:
        bhxh_daily = 0.0

    daily_net = daily_gross - bhxh_daily
    month_net = month_gross - bhxh_month

    clock_display = sal_cfg.get("clock_display", "gross")
    if clock_display not in ("gross", "net"):
        clock_display = "gross"
    if not deduct_bhxh:
        # net = gross khi tắt trừ
        daily_net = daily_gross
        month_net = month_gross

    daily_show = daily_net if clock_display == "net" else daily_gross
    month_show = month_net if clock_display == "net" else month_gross
    pct_month = (month_show / monthly) * 100.0 if monthly > 0 else 0.0

    is_hidden = sal_cfg.get("hidden", False)
    ot_tag = f" • +OT×{ot_mult:g}" if ot_active and ot_earned > 0 else ""

    if is_hidden:
        daily_str = SALARY_TEXTS["hidden_daily"]
        month_str = SALARY_TEXTS["hidden_month"].format(cycle_label=cycle_label)
    elif is_weekend and not ot_active:
        daily_str = SALARY_TEXTS["weekend"]
        month_str = f"📅 {cycle_label}: {_fmt_vnd(month_show)} ({pct_month:.1f}%)"
    elif now < dt_start and not ot_active:
        daily_str = SALARY_TEXTS["before_work"].format(start_time=st_str[:5])
        month_str = f"📅 {cycle_label}: {_fmt_vnd(month_show)} ({pct_month:.1f}%)"
    elif is_lunch and not ot_active:
        pct_day = (worked_hours / today_scheduled_hours) * 100.0 if today_scheduled_hours > 0 else 0.0
        lunch_txt = SALARY_TEXTS["lunch_break"]
        daily_str = f"💸 Ngày: {_fmt_vnd(daily_show)} ({pct_day:.1f}%) • {lunch_txt}"
        month_str = f"📅 {cycle_label}: {_fmt_vnd(month_show)} ({pct_month:.1f}%)"
    elif now >= dt_end:
        pct_day = 100.0 if not is_weekend else 0.0
        after_txt = SALARY_TEXTS["after_work"]
        if ot_active:
            daily_str = f"💸 Ngày: {_fmt_vnd(daily_show)}{ot_tag} • OT {ot_hours:.2f}h"
        else:
            daily_str = f"💸 Ngày: {_fmt_vnd(daily_show)} ({pct_day:.0f}%) • {after_txt}"
        month_str = f"📅 {cycle_label}: {_fmt_vnd(month_show)} ({pct_month:.1f}%)"
    else:
        pct_day = (worked_hours / today_scheduled_hours) * 100.0 if today_scheduled_hours > 0 else 0.0
        daily_str = f"💸 Ngày: {_fmt_vnd(daily_show)} ({pct_day:.1f}%) • {worked_hours:.2f}h / {today_scheduled_hours:g}h{ot_tag}"
        month_str = f"📅 {cycle_label}: {_fmt_vnd(month_show)} ({pct_month:.1f}%)"

    return {
        "daily_earned": daily_earned,
        "daily_gross": daily_gross,
        "daily_net": daily_net,
        "month_earned": month_show,  # tương thích code cũ
        "month_gross": month_gross,
        "month_net": month_net,
        "daily_str": daily_str,
        "month_str": month_str,
        "worked_hours": worked_hours,
        "today_scheduled_hours": today_scheduled_hours,
        "show_daily": sal_cfg.get("show_daily", True),
        "show_monthly": sal_cfg.get("show_monthly", True),
        "hidden": is_hidden,
        "hourly_rate": hourly_rate,
        "daily_rate": daily_rate,
        "monthly": monthly,
        "past_work_days": past_work_days,
        "cycle_label": cycle_label,
        "clock_display": clock_display,
        "deduct_bhxh": deduct_bhxh,
        "bhxh_base": bhxh_base,
        "bhxh_rate_pct": bhxh_rate_pct,
        "bhxh_daily": bhxh_daily,
        "bhxh_month": bhxh_month,
        "bhxh_month_full": bhxh_month_full,
        "ot_active": ot_active,
        "ot_earned": ot_earned,
        "ot_hours": ot_hours,
        "ot_start_display": ot_start_display,
        "ot_multiplier_used": ot_mult,
        "ot_kind": ot_kind,
        "show_ot_button": show_ot_button,
        "dt_end_display": dt_end.strftime("%H:%M"),
        "is_weekend": is_weekend,
        "after_work": now >= dt_end,
    }
