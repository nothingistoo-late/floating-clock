"""
YouTube Player Service (mpv nhúng qua HWND)

- Phát TRỰC TUYẾN bằng mpv + yt-dlp: chỉ đệm trong RAM (--cache-on-disk=no), không ghi file video xuống ổ.
- mpv vẽ thẳng vào một khung Tk (--wid=<hwnd>) nên video nằm "thật" trong cửa sổ của app.
- Điều khiển (pause / resume / volume) qua JSON IPC named pipe của mpv.
- Process mpv được gắn vào Job Object "kill on close": app thoát / crash thì mpv tự tắt theo, không kêu mồ côi.
"""
import collections
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import urllib.parse

from app.config import APP_DIR, BUNDLE_DIR
from app.core.win32_utils import assign_process_to_kill_job
from app.services.ytdlp_updater import YtDlpUpdater

_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_LIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{2,80}$")
LOOP_MODES = ("off", "one", "all")   # tắt / lặp 1 video / lặp cả danh sách
_YT_HOSTS = ("youtube.com", "music.youtube.com", "youtube-nocookie.com")


CREATE_NO_WINDOW = 0x08000000


def _parse_start_seconds(raw):
    """'90' / '90s' / '1m30s' / '1h2m3s' → số giây (int), lỗi → 0."""
    if not raw:
        return 0
    s = str(raw).strip().lower()
    if s.isdigit():
        return int(s)
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?", s)
    if not m:
        return 0
    h, mi, sec = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + sec


def parse_youtube_url(raw):
    """
    Nhận link YouTube dạng bất kỳ (watch, youtu.be, shorts, live, embed, music, playlist, ID trần)
    → dict {"id", "list", "url", "start"} hoặc None nếu không phải link YouTube hợp lệ.
    - "list" khác rỗng = phát cả danh sách (playlist thường PL..., Mix RD..., ...).
    - "id" rỗng = link playlist thuần (youtube.com/playlist?list=...).
    """
    s = str(raw or "").strip()
    if not s:
        return None
    if _YT_ID_RE.match(s):
        return {"id": s, "list": "", "url": f"https://www.youtube.com/watch?v={s}", "start": 0}

    if not re.match(r"^https?://", s, re.I):
        s = "https://" + s
    try:
        u = urllib.parse.urlparse(s)
    except Exception:
        return None

    host = (u.hostname or "").lower()
    for pfx in ("www.", "m."):
        if host.startswith(pfx):
            host = host[len(pfx):]
    q = urllib.parse.parse_qs(u.query)
    parts = [p for p in u.path.split("/") if p]

    vid = ""
    if host == "youtu.be" and parts:
        vid = parts[0]
    elif host in _YT_HOSTS:
        if u.path == "/watch":
            vid = (q.get("v") or [""])[0]
        elif len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
            vid = parts[1]

    list_id = (q.get("list") or [""])[0].strip()
    if not _LIST_ID_RE.match(list_id):
        list_id = ""
    # Mix "liked videos" (LL) / "watch later" (WL) là danh sách riêng tư cần đăng nhập → bỏ qua
    if list_id in ("LL", "WL"):
        list_id = ""

    has_vid = bool(_YT_ID_RE.match(vid or ""))
    if not has_vid and not list_id:
        return None
    start = _parse_start_seconds((q.get("t") or q.get("start") or [""])[0]) if has_vid else 0

    if list_id and has_vid:
        url = f"https://www.youtube.com/watch?v={vid}&list={list_id}"
    elif list_id:
        url = f"https://www.youtube.com/playlist?list={list_id}"
    else:
        url = f"https://www.youtube.com/watch?v={vid}"
    return {"id": vid if has_vid else "", "list": list_id, "url": url, "start": start}


def find_bundled_binary(exe_name):
    """Tìm exe đi kèm app (app/bin, bin) rồi tới PATH hệ thống. Không thấy → None."""
    candidates = [
        os.path.join(APP_DIR, "app", "bin", exe_name),
        os.path.join(APP_DIR, "bin", exe_name),
        os.path.join(BUNDLE_DIR, "app", "bin", exe_name),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    found = shutil.which(exe_name)
    return os.path.abspath(found) if found else None


QUALITY_HEIGHTS = {"1080": 1080, "720": 720, "480": 480, "360": 360}
SPEED_PRESETS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]


def build_ytdl_format(quality="720"):
    """Chuỗi chọn định dạng cho yt-dlp theo chất lượng (tránh AV1 vì máy văn phòng hay không decode phần cứng)."""
    h = QUALITY_HEIGHTS.get(str(quality), 720)
    return f"bestvideo[height<=?{h}][vcodec!^=av01]+bestaudio/best[height<=?{h}]/best"


# Gán lại chuột trong khung video cho giống YouTube (thanh OSC của mpv đã tắt, dùng thanh điều khiển riêng)
_MPV_KEYBINDS = [
    ("MBTN_LEFT", "cycle pause"),          # click video = dừng / phát
    ("MBTN_LEFT_DBL", "ignore"),           # không bật fullscreen (đang nhúng trong đồng hồ)
    ("MBTN_RIGHT", "ignore"),
    ("WHEEL_UP", "add volume 5"),          # lăn chuột trên video = chỉnh âm lượng
    ("WHEEL_DOWN", "add volume -5"),
    ("f", "ignore"),
]

# Các property đọc định kỳ cho thanh điều khiển: (tên mpv, khóa trong self.status)
_STATUS_PROPS = [
    ("media-title", "title"),
    ("playlist-pos", "playlist_pos"),
    ("playlist-count", "playlist_count"),
    ("eof-reached", "eof"),
    ("pause", "paused"),
    ("time-pos", "time_pos"),
    ("duration", "duration"),
    ("volume", "volume"),
    ("mute", "mute"),
    ("speed", "speed"),
]


class YouTubePlayer:
    """Quản lý 1 process mpv phát video YouTube nhúng vào HWND cho trước."""

    POLL_INTERVAL = 0.5

    def __init__(self):
        self.proc = None
        self.current = None          # dict từ parse_youtube_url
        self.paused = False
        self.pipe_name = ""
        # Trạng thái đọc từ mpv định kỳ (luồng nền) — xem _STATUS_PROPS
        self.status = {}
        self._generation = 0
        self._req_id = 0
        # Cơ chế "start" tạm: mở video ở giây X (link ?t=, đổi chất lượng giữa chừng) rồi trả start về none
        # để video sau trong danh sách không bị nhảy theo. "idle" | "wait_none" | "wait_value"
        self._start_reset_state = "idle"
        self._start_reset_since = 0.0
        self._output_tail = collections.deque(maxlen=30)
        self._cmd_queue = queue.Queue()
        self._cmd_thread = threading.Thread(target=self._cmd_worker, daemon=True, name="FC_MpvIPC")
        self._cmd_thread.start()

    # ---------------- Trạng thái ----------------
    @staticmethod
    def mpv_path():
        return find_bundled_binary("mpv.exe")

    def is_available(self):
        return bool(self.mpv_path())

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def last_error_text(self):
        """Vài dòng lỗi cuối cùng mpv/yt-dlp in ra (để báo cho người dùng)."""
        lines = [ln for ln in self._output_tail if ln.strip()]
        return "\n".join(lines[-6:])

    # ---------------- Điều khiển ----------------
    def play(self, url_info, wid, volume=70, start_paused=False, loop="off", quality="720", speed=1.0):
        """
        Khởi chạy mpv nhúng vào HWND `wid`. Raise FileNotFoundError nếu chưa có mpv.exe.
        loop: "off" (hết thì dừng ở khung cuối) | "one" (lặp video hiện tại) | "all" (lặp cả danh sách)
        """
        self.stop()
        mpv = self.mpv_path()
        if not mpv:
            raise FileNotFoundError(
                "Chưa có mpv.exe — chép mpv.exe vào thư mục app\\bin (cạnh yt-dlp.exe) "
                "hoặc cài mpv vào PATH rồi thử lại (◕‿◕)"
            )

        self.pipe_name = rf"\\.\pipe\floatingclock-mpv-{os.getpid()}"
        vol = max(0, min(100, int(volume)))
        args = [
            mpv,
            f"--wid={int(wid)}",
            "--no-config",                 # không bị config mpv riêng của máy can thiệp
            f"--input-ipc-server={self.pipe_name}",
            "--force-window=immediate",
            "--keep-open=yes",             # hết video thì dừng ở khung cuối, không tự thoát
            "--osc=no",                    # dùng thanh điều khiển riêng của app (luôn hiện, kiểu YouTube)
            "--hwdec=auto-safe",
            f"--volume={vol}",
            f"--speed={self._clamp_speed(speed)}",
            # Chỉ đệm trong RAM, KHÔNG ghi video xuống ổ đĩa
            "--cache=yes",
            "--cache-on-disk=no",
            "--demuxer-max-bytes=64MiB",
            "--demuxer-max-back-bytes=16MiB",
            "--ytdl=yes",
            f"--ytdl-format={build_ytdl_format(quality)}",
            "--msg-level=all=error",
            "--cursor-autohide=1500",
        ]
        if start_paused:
            args.append("--pause")
        if url_info.get("list"):
            # Mặc định mpv chỉ lấy 1 video của link watch?v=..&list=.. → ép yt-dlp lấy cả danh sách
            args.append("--ytdl-raw-options=yes-playlist=")
        args.extend(self._loop_args(loop))
        if url_info.get("start"):
            args.append(f"--start={int(url_info['start'])}")
        # Ưu tiên bản yt-dlp đã được cập nhật (xem ytdlp_updater.py), không có thì dùng bản đi kèm app
        ytdlp = YtDlpUpdater().resolve_path()
        if ytdlp:
            args.append(f"--script-opts=ytdl_hook-ytdl_path={ytdlp}")
        args.append(url_info["url"])

        self._output_tail.clear()
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )
        try:
            assign_process_to_kill_job(int(self.proc._handle))
        except Exception:
            pass
        threading.Thread(target=self._drain_output, args=(self.proc,), daemon=True, name="FC_MpvLog").start()
        self.current = url_info
        self.paused = bool(start_paused)
        self.status = {}
        # Link có ?t= → sau khi video đầu tiên mở xong thì trả start về none
        self._start_reset_state = "wait_value" if url_info.get("start") else "idle"
        self._start_reset_since = time.time()
        for key, cmd in _MPV_KEYBINDS:
            self._cmd_queue.put(["keybind", key, cmd])
        self._generation += 1
        threading.Thread(
            target=self._status_poller, args=(self.proc, self._generation, url_info),
            daemon=True, name="FC_MpvStatus"
        ).start()

    def pause(self):
        # Gửi lệnh vô điều kiện (set_property là idempotent) — người dùng có thể đã
        # click vào video để dừng / phát nên cờ nội bộ không đáng tin tuyệt đối
        if self.is_running():
            self.paused = True
            self._cmd_queue.put(["set_property", "pause", True])

    def resume(self):
        if self.is_running():
            self.paused = False
            self._cmd_queue.put(["set_property", "pause", False])

    def next(self):
        """Video kế tiếp trong danh sách."""
        if self.is_running():
            self._cmd_queue.put(["playlist-next", "force"])
            self._cmd_queue.put(["set_property", "pause", False])

    def prev(self):
        """Video trước trong danh sách."""
        if self.is_running():
            self._cmd_queue.put(["playlist-prev", "force"])
            self._cmd_queue.put(["set_property", "pause", False])

    def replay(self):
        """Xem lại video hiện tại từ đầu (dùng khi đã xem hết và đang đứng ở khung cuối)."""
        if self.is_running():
            self._cmd_queue.put(["seek", 0, "absolute"])
            self._cmd_queue.put(["set_property", "pause", False])

    def seek_to(self, seconds):
        """Tua tới giây thứ `seconds` của video hiện tại."""
        if self.is_running():
            self._cmd_queue.put(["seek", max(0.0, float(seconds)), "absolute"])

    def set_loop(self, mode):
        """Đổi chế độ lặp ngay khi đang phát."""
        if not self.is_running():
            return
        mode = mode if mode in LOOP_MODES else "off"
        self._cmd_queue.put(["set_property", "loop-file", "inf" if mode == "one" else "no"])
        self._cmd_queue.put(["set_property", "loop-playlist", "inf" if mode == "all" else "no"])

    @staticmethod
    def _loop_args(mode):
        if mode == "one":
            return ["--loop-file=inf"]
        if mode == "all":
            return ["--loop-playlist=inf"]
        return []

    def set_volume(self, volume):
        if self.is_running():
            self._cmd_queue.put(["set_property", "volume", max(0, min(100, int(volume)))])

    def set_mute(self, muted):
        if self.is_running():
            self._cmd_queue.put(["set_property", "mute", bool(muted)])

    @staticmethod
    def _clamp_speed(speed):
        try:
            return max(0.25, min(4.0, float(speed)))
        except Exception:
            return 1.0

    def set_speed(self, speed):
        if self.is_running():
            self._cmd_queue.put(["set_property", "speed", self._clamp_speed(speed)])

    def set_quality(self, quality):
        """
        Đổi chất lượng giữa chừng: đặt định dạng mới rồi mở lại video hiện tại ĐÚNG vị trí đang xem
        (giữ nguyên danh sách phát, tốc độ, âm lượng).
        """
        if not self.is_running():
            return
        self._cmd_queue.put(["set_property", "ytdl-format", build_ytdl_format(quality)])
        pos = self.status.get("time_pos")
        if isinstance(pos, (int, float)) and pos > 1 and not self.status.get("eof"):
            self._cmd_queue.put(["set_property", "start", f"{pos:.1f}"])
            self._start_reset_state = "wait_none"
            self._start_reset_since = time.time()
        self._cmd_queue.put(["playlist-play-index", "current"])

    def stop(self):
        """Tắt hẳn mpv (không chặn UI lâu)."""
        proc = self.proc
        self.proc = None
        self.current = None
        self.paused = False
        self.status = {}
        self._generation += 1   # luồng đọc trạng thái cũ tự dừng
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=1.0)
        except Exception:
            pass

    # ---------------- Nội bộ ----------------
    def _drain_output(self, proc):
        """Đọc output của mpv liên tục (tránh đầy buffer) và giữ vài dòng cuối để báo lỗi."""
        try:
            for raw in iter(proc.stdout.readline, b""):
                try:
                    self._output_tail.append(raw.decode("utf-8", "replace").rstrip())
                except Exception:
                    pass
        except Exception:
            pass

    def _query_many(self, props, timeout=3.0):
        """
        Đọc nhiều property của mpv qua 1 kết nối IPC (gọi từ luồng nền, KHÔNG gọi trên luồng Tk).
        Trả dict {prop: value}; property chưa có (vd: time-pos lúc đang tải) → None.
        """
        if not props:
            return {}
        base = self._req_id + 1
        self._req_id += len(props)
        lines = [
            json.dumps({"command": ["get_property", p], "request_id": base + i})
            for i, p in enumerate(props)
        ]
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        results = {}
        try:
            with open(self.pipe_name, "r+b", buffering=0) as pipe:
                pipe.write(payload)
                buf = b""
                deadline = time.time() + timeout
                while len(results) < len(props) and time.time() < deadline:
                    chunk = pipe.read(65536)
                    if not chunk:
                        break
                    buf += chunk
                    *done, buf = buf.split(b"\n")
                    for line in done:
                        try:
                            msg = json.loads(line)
                        except Exception:
                            continue
                        rid = msg.get("request_id")
                        if isinstance(rid, int) and base <= rid < base + len(props):
                            ok = msg.get("error") == "success"
                            results[props[rid - base]] = msg.get("data") if ok else None
        except OSError:
            pass
        return results

    def _query(self, prop, timeout=3.0):
        return self._query_many([prop], timeout=timeout).get(prop)

    def _status_poller(self, proc, generation, url_info):
        """
        Mỗi ~0.5s đọc trạng thái mpv cho thanh điều khiển / tiêu đề / menu.
        - Link watch?v=X&list=Y: yt-dlp trả cả danh sách từ đầu → tự nhảy tới đúng video X một lần.
        - Trả option "start" về none sau khi video mở xong đúng vị trí (xem set_quality / ?t=).
        """
        want_id = url_info.get("id") if url_info.get("list") else ""
        jumped = not want_id
        started = time.time()
        names = [p for p, _ in _STATUS_PROPS]
        while proc.poll() is None and generation == self._generation:
            raw = self._query_many(names)
            if generation != self._generation:
                break
            if raw:
                st = {key: raw.get(prop) for prop, key in _STATUS_PROPS}
                st["eof"] = bool(st.get("eof"))
                st["paused"] = bool(st.get("paused"))
                st["mute"] = bool(st.get("mute"))
                self.status = st
                self._advance_start_reset(st)

                count = st.get("playlist_count") or 0
                if not jumped and count > 1:
                    jumped = True
                    items = self._query("playlist", timeout=5.0) or []
                    for idx, item in enumerate(items):
                        if want_id in str(item.get("filename", "")):
                            if idx != st.get("playlist_pos"):
                                self._cmd_queue.put(["set_property", "playlist-pos", idx])
                            break
                elif not jumped and time.time() - started > 90:
                    jumped = True  # danh sách không mở rộng được → thôi
            time.sleep(self.POLL_INTERVAL)

    def _advance_start_reset(self, st):
        """time-pos: có → mất (đang mở lại) → có lại = video mới đã mở đúng vị trí → start = none."""
        state = self._start_reset_state
        if state == "idle":
            return
        has_pos = isinstance(st.get("time_pos"), (int, float))
        if state == "wait_none" and not has_pos:
            self._start_reset_state = "wait_value"
        elif state == "wait_value" and has_pos:
            self._start_reset_state = "idle"
            self._cmd_queue.put(["set_property", "start", "none"])
        elif time.time() - self._start_reset_since > 40:
            self._start_reset_state = "idle"
            self._cmd_queue.put(["set_property", "start", "none"])

    def _cmd_worker(self):
        """Gửi lệnh IPC tuần tự trên luồng riêng — mở pipe có thể chờ, không được chặn Tk."""
        while True:
            cmd = self._cmd_queue.get()
            payload = (json.dumps({"command": cmd}) + "\n").encode("utf-8")
            # mpv vừa khởi động có thể chưa tạo pipe → thử lại trong ~3s
            for _ in range(30):
                if not self.is_running():
                    break
                try:
                    with open(self.pipe_name, "r+b", buffering=0) as pipe:
                        pipe.write(payload)
                    break
                except OSError:
                    time.sleep(0.1)
