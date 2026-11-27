"""
Network helpers — tạo SSL context CÓ kiểm tra chứng chỉ cho mọi request HTTPS.

Không dùng ssl._create_unverified_context(): nó cho phép kẻ đứng giữa (MITM, Wi-Fi công cộng...)
đọc trộm API key hoặc giả mạo phản hồi GitHub/thời tiết.
"""
import ssl

_cached_ctx = None


def create_secure_ssl_context():
    """
    Trả SSL context có verify chứng chỉ + hostname.
    - Ưu tiên bundle của certifi nếu có cài (ổn định trên bản PyInstaller).
    - Không có certifi → ssl.create_default_context() (Windows tự nạp kho chứng chỉ hệ thống).
    """
    global _cached_ctx
    if _cached_ctx is not None:
        return _cached_ctx
    ctx = None
    try:
        import certifi  # type: ignore
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = None
    if ctx is None:
        ctx = ssl.create_default_context()
    _cached_ctx = ctx
    return ctx
