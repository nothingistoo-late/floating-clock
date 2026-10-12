"""
GitHub Releases Auto-Update Service
Manages remote version checks, changelog retrieval, and release page redirection.
"""
import json
import re
import ssl
import threading
import urllib.request
import webbrowser

from app.constants import APP_VERSION, GITHUB_API_LATEST_RELEASE, GITHUB_RELEASES_URL


class UpdateManager:
    """Quản lý kiểm tra và thông báo phiên bản mới từ GitHub Releases"""

    def __init__(self, config=None):
        self.config = config or {}
        self.is_checking = False
        self.last_check_time = 0.0
        self.latest_release_info = None

    @staticmethod
    def parse_version(v_str):
        """Chuyển đổi chuỗi phiên bản (vd: 'v2.3.0', '2.4.1') thành tuple số để so sánh chính xác"""
        if not v_str:
            return (0, 0, 0)
        nums = re.findall(r"\d+", str(v_str))
        return tuple(map(int, nums)) if nums else (0, 0, 0)

    @classmethod
    def is_newer_version(cls, remote_tag, local_tag=APP_VERSION):
        """Kiểm tra xem phiên bản remote có mới hơn phiên bản hiện tại không"""
        return cls.parse_version(remote_tag) > cls.parse_version(local_tag)

    def check_for_updates(self, callback=None, dispatcher=None):
        """
        Kiểm tra bản cập nhật mới nhất từ GitHub Releases trên luồng ngầm (non-blocking).

        :param callback: fn(has_update: bool, update_info: dict, error: str)
        :param dispatcher: hàm điều phối callback về Main Thread Tkinter (vd: root.after)
        """
        if self.is_checking:
            return

        def _dispatch(has_update, update_info, err):
            self.is_checking = False
            if callback:
                if dispatcher:
                    dispatcher(lambda: callback(has_update, update_info, err))
                else:
                    callback(has_update, update_info, err)

        def _worker():
            self.is_checking = True
            try:
                try:
                    if hasattr(ssl, "_create_unverified_context"):
                        ctx = ssl._create_unverified_context()
                    else:
                        ctx = ssl.create_default_context()
                except Exception:
                    ctx = None

                req = urllib.request.Request(
                    GITHUB_API_LATEST_RELEASE,
                    headers={
                        "User-Agent": f"TopFloatingClock/{APP_VERSION}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                with urllib.request.urlopen(req, timeout=6, context=ctx) as res:
                    data = json.loads(res.read().decode("utf-8"))

                remote_tag = data.get("tag_name", "").strip()
                title = data.get("name", "").strip() or remote_tag
                body = data.get("body", "").strip()
                release_url = data.get("html_url", GITHUB_RELEASES_URL)
                published_at = data.get("published_at", "")

                update_info = {
                    "current_version": APP_VERSION,
                    "latest_version": remote_tag,
                    "title": title,
                    "changelog": body,
                    "release_url": release_url,
                    "published_at": published_at,
                    "assets": [
                        {
                            "name": a.get("name", ""),
                            "download_url": a.get("browser_download_url", ""),
                            "size": a.get("size", 0),
                        }
                        for a in data.get("assets", [])
                    ],
                }

                self.latest_release_info = update_info
                has_update = self.is_newer_version(remote_tag, APP_VERSION)
                _dispatch(has_update, update_info, None)

            except Exception as e:
                _dispatch(False, None, str(e))

        th = threading.Thread(target=_worker, daemon=True)
        th.start()

    @staticmethod
    def open_release_page(url=None):
        """Mở trang tải bản phát hành trên trình duyệt mặc định của hệ thống"""
        target = url or GITHUB_RELEASES_URL
        try:
            webbrowser.open(target)
            return True
        except Exception:
            return False
