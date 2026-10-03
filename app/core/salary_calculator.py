"""
Salary calculation and Payday Countdown Engine
"""
import calendar
import math
from datetime import datetime, timedelta


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

        diff_days = (target_payday - now).total_seconds() / 86400.0
        days_int = int(math.ceil(diff_days))
        return days_int, target_payday.strftime("%d/%m/%Y")
    except Exception:
        return 0, ""


def calculate_salary_info(now, config, get_today_departure_func):
    """
    Tính toán chi tiết tiền lương realtime (theo ngày & lũy kế tháng / chu kỳ nhận lương).
    """
    sal_cfg = config.get("salary", {})
    if not sal_cfg.get("enabled", False):
        return {}

    monthly = float(sal_cfg.get("monthly", 15000000))
    work_days = max(1, int(sal_cfg.get("work_days", 22)))
    work_hours = max(1.0, float(sal_cfg.get("work_hours", 8.0)))

    # Đơn giá lương theo ngày và theo giờ
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
    is_lunch = False

    try:
        dt_start = datetime.strptime(f"{today_str} {st_str}", "%Y-%m-%d %H:%M:%S")
        dt_end = datetime.strptime(f"{today_str} {dep_time}", "%Y-%m-%d %H:%M:%S")
        dt_lunch_start = datetime.strptime(f"{today_str} {ls_str}", "%Y-%m-%d %H:%M:%S")
        dt_lunch_end = datetime.strptime(f"{today_str} {le_str}", "%Y-%m-%d %H:%M:%S")

        if now <= dt_start:
            daily_earned = 0.0
            worked_hours = 0.0
        elif now >= dt_end:
            worked_hours = work_hours
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
                worked_sec = ratio * (work_hours * 3600.0)

            worked_sec = max(0.0, min(work_hours * 3600.0, worked_sec))
            worked_hours = worked_sec / 3600.0
            daily_earned = worked_hours * hourly_rate
    except Exception:
        daily_earned = 0.0
        worked_hours = 0.0

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

    month_earned = min(monthly, (past_work_days * daily_rate) + daily_earned)
    pct_month = (month_earned / monthly) * 100.0 if monthly > 0 else 0.0

    is_weekend = (now.weekday() == 6) or (now.weekday() == 5 and work_days <= 22)
    is_hidden = sal_cfg.get("hidden", False)

    if is_hidden:
        daily_str = "💸 Ngày: •••••• đ"
        month_str = f"📅 {cycle_label}: •••••• đ"
    elif is_weekend:
        daily_str = "💸 Ngày: Nghỉ cuối tuần 🌴"
        month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
    elif now < dt_start:
        daily_str = f"💸 Ngày: Chuẩn bị làm việc ({st_str[:5]}) ☕"
        month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
    elif is_lunch:
        pct_day = (worked_hours / work_hours) * 100.0 if work_hours > 0 else 0.0
        daily_str = f"💸 Ngày: {int(daily_earned):,} đ ({pct_day:.1f}%) • 🍱 Giờ nghỉ trưa"
        month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
    elif now >= dt_end:
        pct_day = 100.0
        daily_str = f"💸 Ngày: {int(daily_earned):,} đ ({pct_day:.0f}%) • Đã tan làm 🎉"
        month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")
    else:
        pct_day = (worked_hours / work_hours) * 100.0 if work_hours > 0 else 0.0
        daily_str = f"💸 Ngày: {int(daily_earned):,} đ ({pct_day:.1f}%) • {worked_hours:.2f}h / {work_hours:g}h"
        month_str = f"📅 {cycle_label}: {int(month_earned):,} đ ({pct_month:.1f}%)".replace(",", ".")

    daily_str = daily_str.replace(",", ".")

    return {
        "daily_earned": daily_earned,
        "month_earned": month_earned,
        "daily_str": daily_str,
        "month_str": month_str,
        "worked_hours": worked_hours,
        "show_daily": sal_cfg.get("show_daily", True),
        "show_monthly": sal_cfg.get("show_monthly", True),
        "hidden": is_hidden
    }
