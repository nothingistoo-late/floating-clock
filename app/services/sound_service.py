"""
Audio and Sound Managers (Alarms, Chimes, and Focus Ambient / Stream Media)
"""
import math
import os
import random
import struct
import subprocess
import threading
import time
import wave
import winsound
from app.config import APP_DIR, BUNDLE_DIR


class SoundManager:
    """Quản lý các loại âm thanh báo chuông, đếm ngược, nhắc uống nước"""
    def __init__(self):
        self._ringing = False
        self._thread = None
        self.sound_enabled = True

    def is_ringing(self):
        return self._ringing

    def stop_alarm(self):
        self._ringing = False

    def play_alarm_loop(self, message="Báo thức"):
        if not self.sound_enabled:
            return
        self.stop_alarm()
        self._ringing = True

        def _worker():
            melody = [
                (1046, 120), (1318, 120), (1568, 120), (2093, 220),
                (1568, 120), (2093, 300), (0, 150),
                (1046, 120), (1318, 120), (1568, 120), (2093, 220),
                (2349, 150), (2093, 400), (0, 300)
            ]
            while self._ringing:
                for freq, dur in melody:
                    if not self._ringing:
                        break
                    if freq == 0:
                        time.sleep(dur / 1000.0)
                    else:
                        try:
                            winsound.Beep(freq, dur)
                        except Exception:
                            pass
                time.sleep(0.2)

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def play_timer_chime(self):
        if not self.sound_enabled:
            return
        def _worker():
            notes = [(880, 150), (1175, 150), (1318, 150), (1760, 350)]
            for f, d in notes:
                try:
                    winsound.Beep(f, d)
                except Exception:
                    pass
        threading.Thread(target=_worker, daemon=True).start()

    def play_water_chime(self):
        if not self.sound_enabled:
            return
        def _worker():
            notes = [(1318, 180), (1760, 300)]
            for f, d in notes:
                try:
                    winsound.Beep(f, d)
                except Exception:
                    pass
        threading.Thread(target=_worker, daemon=True).start()

    def play_pomo_break(self):
        if not self.sound_enabled:
            return
        def _worker():
            notes = [(1046, 150), (1318, 150), (1568, 250), (1318, 150), (1568, 350)]
            for f, d in notes:
                try:
                    winsound.Beep(f, d)
                except Exception:
                    pass
        threading.Thread(target=_worker, daemon=True).start()

    def play_tick(self):
        if not self.sound_enabled:
            return
        def _worker():
            try:
                winsound.Beep(1200, 40)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()


class FocusSoundManager:
    """
    Quản lý âm thanh tập trung chất lượng cao & phát luồng nhạc trực tuyến từ URL
    (Hỗ trợ YouTube, TikTok, SoundCloud, Đài Lofi Radio và Direct Stream)
    """
    SOUND_TYPES = {
        "rain": {
            "name": "Mưa rào êm dịu (Rainfall)",
            "icon": "🌧️",
            "type": "synth_rain"
        },
        "ocean": {
            "name": "Sóng biển dạt dào (Ocean Waves)",
            "icon": "🌊",
            "type": "synth_ocean"
        },
        "cafe": {
            "name": "Quán cà phê chill (Cafe Ambient)",
            "icon": "☕",
            "type": "synth_cafe"
        },
        "night_forest": {
            "name": "Rừng đêm tĩnh lặng & Tiếng dế",
            "icon": "🌲",
            "type": "synth_forest"
        },
        "lofi_beats": {
            "name": "Lofi Chill Radio (Live 24/7)",
            "icon": "🎧",
            "url": "https://stream.zeno.fm/f3wvbbqmdg8uv",
            "type": "stream"
        },
        "lofi_piano": {
            "name": "Lofi Piano Thư Giãn (Live 24/7)",
            "icon": "🎹",
            "url": "https://stream.zeno.fm/0r0xa792kwzuv",
            "type": "stream"
        },
        "custom": {
            "name": "Phát từ Link tùy chỉnh (YouTube / TikTok / Stream)",
            "icon": "🔗",
            "type": "custom"
        },
    }

    def __init__(self, config):
        self.config = config
        self.is_playing = False
        self.current_sound_type = config.get("focus_sound", {}).get("sound_type", "rain")
        self.current_title = ""
        self.status_message = "Chưa phát"
        self.volume = config.get("focus_sound", {}).get("volume", 50)
        self.custom_url = config.get("focus_sound", {}).get("custom_url", "")
        
        self.sounds_dir = os.path.join(APP_DIR, "app", "assets", "sounds")
        os.makedirs(self.sounds_dir, exist_ok=True)
        
        self.bin_dir = os.path.join(BUNDLE_DIR, "app", "bin")
        if not os.path.exists(os.path.join(self.bin_dir, "yt-dlp.exe")):
            self.bin_dir = os.path.join(APP_DIR, "app", "bin")
        self.yt_dlp_path = os.path.join(self.bin_dir, "yt-dlp.exe")
        
        self.worker_script = os.path.join(BUNDLE_DIR, "app", "scripts", "audio_worker.ps1")
        if not os.path.exists(self.worker_script):
            self.worker_script = os.path.join(APP_DIR, "app", "scripts", "audio_worker.ps1")
        
        self._worker_proc = None
        self._lock = threading.Lock()
        self._play_token = 0

    @property
    def current_sound(self):
        return self.current_sound_type

    @current_sound.setter
    def current_sound(self, val):
        self.current_sound_type = val

    def _ensure_worker(self):
        """Khởi động tiến trình worker phát nhạc ngầm nếu chưa chạy"""
        if self._worker_proc is not None and self._worker_proc.poll() is None:
            return True
        try:
            self._worker_proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", self.worker_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            # Đọc dòng READY
            line = self._worker_proc.stdout.readline()
            self._send_cmd(f"volume {self.volume}")
            return True
        except Exception:
            self._worker_proc = None
            return False

    def _send_cmd(self, cmd_str):
        """Gửi lệnh điều khiển đến audio worker"""
        try:
            if self._worker_proc and self._worker_proc.stdin:
                self._worker_proc.stdin.write(cmd_str + "\n")
                self._worker_proc.stdin.flush()
                # Đọc phản hồi
                resp = self._worker_proc.stdout.readline().strip()
                return resp
        except Exception:
            pass
        return None

    def generate_synth_wav(self, sound_type="rain", duration_sec=8, sample_rate=44100):
        """Tạo file WAV chất lượng cao, êm dịu, không bị rè kim loại"""
        target_file = os.path.join(self.sounds_dir, f"{sound_type}.wav")
        if os.path.exists(target_file) and os.path.getsize(target_file) > 10000:
            return target_file

        num_samples = int(duration_sec * sample_rate)
        try:
            with wave.open(target_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)

                raw_data = bytearray()
                lp1, lp2 = 0.0, 0.0

                if sound_type == "rain":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        lp1 = (lp1 * 0.96) + (white * 0.04)
                        lp2 = (lp2 * 0.92) + (lp1 * 0.08)
                        splash = random.uniform(0.1, 0.35) if random.random() < 0.0008 else 0.0
                        val = max(-0.85, min(0.85, lp2 * 2.6 + splash))
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                elif sound_type == "ocean":
                    period = 6.0
                    for i in range(num_samples):
                        t = i / sample_rate
                        swell = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(2 * math.pi * t / period))
                        white = random.uniform(-1.0, 1.0)
                        lp1 = (lp1 * 0.98) + (white * 0.02)
                        lp2 = (lp2 * 0.94) + (lp1 * 0.06)
                        val = max(-0.85, min(0.85, lp2 * swell * 3.2))
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                elif sound_type == "cafe":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        lp1 = (lp1 * 0.95) + (white * 0.05)
                        lp2 = (lp2 * 0.90) + (lp1 * 0.10)
                        t = i / sample_rate
                        # Thêm chút âm sắc ấm áp nhẹ nhàng của hợp âm Lofi
                        harm = 0.08 * math.sin(2 * math.pi * 220.0 * t) + 0.05 * math.sin(2 * math.pi * 330.0 * t)
                        val = max(-0.8, min(0.8, lp2 * 1.5 + harm))
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                elif sound_type == "night_forest":
                    for i in range(num_samples):
                        t = i / sample_rate
                        white = random.uniform(-1.0, 1.0)
                        lp1 = (lp1 * 0.985) + (white * 0.015)
                        # Tiếng dế đêm nhịp nhàng
                        cricket = 0.0
                        if int(t * 4) % 2 == 0:
                            cricket = 0.12 * math.sin(2 * math.pi * 4500.0 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 30.0 * t))
                        val = max(-0.8, min(0.8, lp1 * 1.8 + cricket))
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                else:
                    for i in range(num_samples):
                        white = random.uniform(-0.3, 0.3)
                        raw_data.extend(struct.pack('<h', int(white * 32767)))

                wf.writeframes(raw_data)
            return target_file
        except Exception:
            return None

    def _resolve_media_url(self, raw_url):
        """
        Trích xuất link audio stream trực tiếp và tiêu đề từ URL video (YouTube, TikTok, v.v.)
        """
        raw_url = (raw_url or "").strip()
        if not raw_url:
            return None, "Link trống"

        # Nếu là link stream trực tiếp hoặc file audio
        if any(raw_url.lower().endswith(ext) for ext in [".mp3", ".wav", ".aac", ".m4a", ".ogg"]) or "stream.zeno.fm" in raw_url or "iloveradio" in raw_url:
            return raw_url, "Direct Audio Stream"

        # Nếu có yt-dlp, dùng yt-dlp để extract stream URL cho YouTube, TikTok, SoundCloud, v.v.
        if os.path.exists(self.yt_dlp_path):
            try:
                cmd = [
                    self.yt_dlp_path,
                    "-g",
                    "-f", "bestaudio/best",
                    "--get-title",
                    "--no-playlist",
                    "--no-warnings",
                    raw_url
                ]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
                if len(lines) >= 2:
                    title = lines[0]
                    stream_url = lines[1]
                    return stream_url, title
                elif len(lines) == 1:
                    return lines[0], "Online Media Track"
            except Exception:
                pass

        # Fallback dùng trực tiếp URL nếu không resolve được
        return raw_url, "Online Audio Link"

    def play(self, sound_type=None, custom_url=None, callback=None):
        """Bắt đầu phát âm thanh tập trung hoặc luồng nhạc từ URL"""
        if sound_type:
            self.current_sound_type = sound_type
        if custom_url is not None:
            self.custom_url = custom_url

        self._play_token += 1
        current_token = self._play_token

        def _async_worker():
            with self._lock:
                if current_token != self._play_token:
                    return

                if not self._ensure_worker():
                    self.status_message = "Lỗi khởi tạo Audio Player"
                    if callback:
                        callback(False, self.status_message)
                    return

                stype = self.current_sound_type
                s_info = self.SOUND_TYPES.get(stype, {})
                target_url = None
                display_title = s_info.get("name", "Âm thanh tập trung")
                is_loop = False

                if stype == "custom" or self.custom_url:
                    self.status_message = "⏳ Đang trích xuất luồng âm thanh..."
                    if callback:
                        callback(None, self.status_message)
                    url_to_fetch = self.custom_url if self.custom_url else s_info.get("url", "")
                    resolved_url, title = self._resolve_media_url(url_to_fetch)
                    if resolved_url:
                        target_url = resolved_url
                        display_title = title
                        is_loop = False
                    else:
                        self.status_message = "Không thể phát link này"
                        if callback:
                            callback(False, self.status_message)
                        return

                elif s_info.get("type") == "stream":
                    target_url = s_info.get("url")
                    display_title = s_info.get("name")
                    is_loop = False

                else:
                    # Các âm thanh tự nhiên tổng hợp (Rain, Ocean, Cafe, Forest)
                    self.status_message = f"Đang chuẩn bị {display_title}..."
                    target_url = self.generate_synth_wav(stype)
                    is_loop = True

                if current_token != self._play_token:
                    return

                if target_url:
                    self._send_cmd(f"volume {self.volume}")
                    self._send_cmd(f"loop {1 if is_loop else 0}")
                    self._send_cmd(f"play {target_url}")
                    self.is_playing = True
                    self.current_title = display_title
                    self.status_message = f"Đang phát: {display_title}"
                    if callback:
                        callback(True, self.status_message)
                else:
                    self.is_playing = False
                    self.status_message = "Không tìm thấy file/luồng âm thanh"
                    if callback:
                        callback(False, self.status_message)

        threading.Thread(target=_async_worker, daemon=True).start()
        return True

    def stop(self):
        """Dừng phát âm thanh nền"""
        self._play_token += 1
        with self._lock:
            self._send_cmd("stop")
            self.is_playing = False
            self.status_message = "Đã dừng"

    def pause(self):
        self._send_cmd("pause")
        self.is_playing = False
        self.status_message = "Tạm dừng"

    def resume(self):
        self._send_cmd("resume")
        self.is_playing = True
        self.status_message = f"Đang phát: {self.current_title}"

    def set_volume(self, vol):
        """Thiết lập âm lượng (0 - 100)"""
        try:
            self.volume = max(0, min(100, int(vol)))
            self._send_cmd(f"volume {self.volume}")
            self.config.setdefault("focus_sound", {})["volume"] = self.volume
        except Exception:
            pass

    def toggle(self, sound_type=None, custom_url=None, callback=None):
        """Bật / Tắt âm thanh tập trung"""
        if self.is_playing:
            self.stop()
            if callback:
                callback(False, "Đã dừng")
            return False
        else:
            return self.play(sound_type, custom_url, callback)


# Global singleton instance for chimes/alarm
sound_mgr = SoundManager()
