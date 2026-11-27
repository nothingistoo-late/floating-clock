"""
yt-dlp Updater — giữ yt-dlp (dùng để lấy link video YouTube) luôn mới.

YouTube đổi cách hoạt động khá thường xuyên → yt-dlp cũ sẽ hỏng sau vài tuần / vài tháng.
- Bản yt-dlp gói sẵn trong app chỉ là "bản khởi đầu": nó nằm trong exe / Program Files nên không ghi đè được.
- App chép nó ra thư mục người dùng ghi được (%LOCALAPPDATA%\\FloatingClock\\bin) rồi cập nhật bản đó
  bằng chính lệnh `yt-dlp -U` (yt-dlp tự tải từ GitHub chính chủ và kiểm tra checksum).
- Trình phát YouTube luôn ưu tiên dùng bản đã cập nhật này.
"""
import os
import re
import shutil
import subprocess
import threading

from app.config import APP_DIR, BUNDLE_DIR

CREATE_NO_WINDOW = 0x08000000
EXE_NAME = "yt-dlp.exe"


def default_managed_dir():
    base = os.environ.get("LOCALAPPDATA") or APP_DIR
    return os.path.join(base, "FloatingClock", "bin")


def parse_version(v):
    """'2026.08.19' / '2026.11.20.232045' → tuple số để so sánh; lỗi → ()."""
    return tuple(int(x) for x in re.findall(r"\d+", str(v or "")))


class YtDlpUpdater:
    """Quản lý bản yt-dlp ghi được + cập nhật nó (chạy nền, không chặn giao diện)."""

    def __init__(self, managed_dir=None):
        self.managed_dir = managed_dir or default_managed_dir()
        self.is_updating = False
        self._lock = threading.Lock()

    # ---------------- Đường dẫn ----------------
    @property
    def managed_path(self):
        return os.path.join(self.managed_dir, EXE_NAME)

    @staticmethod
    def bundled_path():
        """Bản yt-dlp đi kèm app (trong exe onefile / cạnh exe / bản dev)."""
        for path in (
            os.path.join(BUNDLE_DIR, "app", "bin", EXE_NAME),
            os.path.join(APP_DIR, "app", "bin", EXE_NAME),
            os.path.join(APP_DIR, "bin", EXE_NAME),
        ):
            if os.path.isfile(path):
                return os.path.abspath(path)
        found = shutil.which(EXE_NAME)
        return os.path.abspath(found) if found else None

    def resolve_path(self):
        """yt-dlp nên dùng để phát: bản đã cập nhật nếu có, không thì bản đi kèm. Không chạy process nào."""
        if os.path.isfile(self.managed_path):
            return self.managed_path
        return self.bundled_path()

    # ---------------- Phiên bản ----------------
    @staticmethod
    def get_version(path, timeout=60):
        """Chạy `yt-dlp --version` → '2026.08.19' hoặc None."""
        if not path or not os.path.isfile(path):
            return None
        try:
            res = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
            )
            out = (res.stdout or "").strip().splitlines()
            return out[-1].strip() if res.returncode == 0 and out else None
        except Exception:
            return None

    def ensure_managed_copy(self):
        """
        Đảm bảo có bản ghi được. Chép từ bản đi kèm nếu chưa có, hoặc nếu bản đi kèm MỚI hơn
        (người dùng vừa cài bản app mới có yt-dlp mới hơn). Trả đường dẫn hoặc None.
        """
        bundled = self.bundled_path()
        managed = self.managed_path
        if not os.path.isfile(managed):
            if not bundled:
                return None
            os.makedirs(self.managed_dir, exist_ok=True)
            shutil.copy2(bundled, managed)
            return managed
        if bundled and os.path.normcase(bundled) != os.path.normcase(managed):
            v_bundled = parse_version(self.get_version(bundled))
            v_managed = parse_version(self.get_version(managed))
            if v_bundled and v_bundled > v_managed:
                shutil.copy2(bundled, managed)
        return managed

    # ---------------- Cập nhật ----------------
    def update(self, timeout=240, on_progress=None):
        """
        Cập nhật yt-dlp lên bản mới nhất (chặn — gọi từ luồng nền).
        on_progress(text): báo từng bước bằng câu dễ hiểu (đọc trực tiếp output của `yt-dlp -U`).
        Trả dict: ok, updated, before, after, error.
        """
        def report(text):
            if on_progress:
                try:
                    on_progress(text)
                except Exception:
                    pass

        result = {"ok": False, "updated": False, "before": None, "after": None, "error": None}
        try:
            report("Đang chuẩn bị yt-dlp...")
            path = self.ensure_managed_copy()
            if not path:
                result["error"] = "Không tìm thấy yt-dlp.exe đi kèm app"
                return result
            result["before"] = self.get_version(path)
            report(f"Đang hỏi GitHub bản mới nhất (máy đang có {result['before'] or '?'})...")

            proc = subprocess.Popen(
                [path, "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                creationflags=CREATE_NO_WINDOW,
            )
            # Quá thời gian thì kill (readline bên dưới sẽ tự kết thúc theo)
            killed = {"timeout": False}

            def _kill_on_timeout():
                if proc.poll() is None:
                    killed["timeout"] = True
                    proc.kill()
            timer = threading.Timer(timeout, _kill_on_timeout)
            timer.start()
            lines = []
            try:
                for line in iter(proc.stdout.readline, ""):
                    line = line.strip()
                    if not line:
                        continue
                    lines.append(line)
                    msg = self._progress_text(line)
                    if msg:
                        report(msg)
                proc.wait()
            finally:
                timer.cancel()
            timed_out = killed["timeout"]

            result["after"] = self.get_version(path)
            result["updated"] = bool(
                result["after"] and parse_version(result["after"]) > parse_version(result["before"])
            )
            result["ok"] = proc.returncode == 0 and bool(result["after"])
            if not result["ok"]:
                if timed_out:
                    result["error"] = "Cập nhật yt-dlp quá lâu (mạng chậm?) — thử lại sau nhé"
                else:
                    result["error"] = "\n".join(lines[-4:]) or f"yt-dlp -U thoát với mã {proc.returncode}"
        except Exception as e:
            result["error"] = str(e)
        return result

    @staticmethod
    def _progress_text(line):
        """Đổi 1 dòng output của `yt-dlp -U` thành câu tiếng Việt (None = bỏ qua)."""
        low = line.lower()
        m = re.search(r"@([\d.]+)", line)
        ver = m.group(1) if m else ""
        if low.startswith("latest version"):
            return f"Bản mới nhất trên GitHub: {ver}" if ver else None
        if "is up to date" in low:
            return "Đã là bản mới nhất ✓"
        if low.startswith("updating to"):
            return f"Đang tải bản mới {ver}..." if ver else "Đang tải bản mới..."
        if low.startswith("updated yt-dlp"):
            return f"Đã cập nhật lên {ver} ✓" if ver else "Đã cập nhật ✓"
        if low.startswith("error"):
            return "Gặp lỗi khi cập nhật..."
        return None

    def update_async(self, callback=None, dispatcher=None, on_progress=None):
        """
        Chạy update() trên luồng nền; callback(result) và on_progress(text)
        được đưa về luồng Tk qua dispatcher.
        """
        with self._lock:
            if self.is_updating:
                return False
            self.is_updating = True

        def _to_ui(fn, *args):
            if dispatcher:
                dispatcher(lambda: fn(*args))
            else:
                fn(*args)

        def _progress(text):
            if on_progress:
                _to_ui(on_progress, text)

        def _worker():
            try:
                res = self.update(on_progress=_progress)
            finally:
                self.is_updating = False
            if callback:
                _to_ui(callback, res)

        threading.Thread(target=_worker, daemon=True, name="FC_YtDlpUpdate").start()
        return True
