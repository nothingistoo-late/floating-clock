"""
Audio and Sound Managers (Alarms, Chimes, and Focus Ambient / Stream Media)
Uses direct Native WinMM MCI Engine inside FloatingClock process.
"""
import ctypes
import math
import os
import random
import struct
import subprocess
import threading
import time
import urllib.request
import ssl
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
    Quản lý âm thanh tập trung chất lượng cao & phát nhạc trực tuyến từ URL
    (Phát trực tiếp NATIVE trong tiến trình app qua Windows MCI - hiển thị đúng tên Floating Clock trong Volume Mixer)
    """
    ALIAS = "FC_FOCUS_BGM"

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
            "name": "Lofi Chill Radio (Live Stream)",
            "icon": "🎧",
            "url": "https://stream.zeno.fm/f3wvbbqmdg8uv",
            "type": "stream"
        },
        "lofi_piano": {
            "name": "Lofi Piano Thư Giãn (Live Stream)",
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

        self._lock = threading.Lock()
        self._play_token = 0
        self._current_loaded_file = None

    @property
    def current_sound(self):
        return self.current_sound_type

    @current_sound.setter
    def current_sound(self, val):
        self.current_sound_type = val

    def _mci_send(self, cmd_str):
        """Gửi lệnh trực tiếp đến Windows Multimedia Engine (WinMM)"""
        try:
            buf = ctypes.create_unicode_buffer(256)
            err = ctypes.windll.winmm.mciSendStringW(cmd_str, buf, 255, 0)
            return err, buf.value
        except Exception:
            return -1, ""

    def _apply_volume(self):
        """Áp dụng âm lượng qua MCI và Master Wave Volume"""
        try:
            # 1. MCI Volume (0 - 1000)
            mci_vol = int(max(0, min(100, self.volume)) * 10)
            self._mci_send(f"setaudio {self.ALIAS} volume to {mci_vol}")
            # 2. Master Wave Volume fallback (0x0000 - 0xFFFF)
            wave_vol = int((max(0, min(100, self.volume)) / 100.0) * 0xFFFF)
            ctypes.windll.winmm.waveOutSetVolume(0, (wave_vol << 16) | wave_vol)
        except Exception:
            pass

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
                        harm = 0.08 * math.sin(2 * math.pi * 220.0 * t) + 0.05 * math.sin(2 * math.pi * 330.0 * t)
                        val = max(-0.8, min(0.8, lp2 * 1.5 + harm))
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                elif sound_type == "night_forest":
                    for i in range(num_samples):
                        t = i / sample_rate
                        white = random.uniform(-1.0, 1.0)
                        lp1 = (lp1 * 0.985) + (white * 0.015)
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

    def _fetch_media_to_local_file(self, raw_url):
        """
        Tải nhanh bài hát từ YouTube / TikTok / Stream về file đệm để MCI phát trực tiếp
        """
        raw_url = (raw_url or "").strip()
        if not raw_url:
            return None, "Link trống"

        cache_base = os.path.join(self.sounds_dir, "_custom_audio")

        # 1. Nếu là link trực tiếp MP3 / Audio Stream
        if any(raw_url.lower().endswith(ext) for ext in [".mp3", ".wav", ".aac", ".m4a"]) or "stream.zeno.fm" in raw_url or "nightwaveplaza" in raw_url:
            try:
                target_file = cache_base + ".mp3"
                ctx = ssl._create_unverified_context()
                req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, context=ctx, timeout=8) as resp, open(target_file, "wb") as f:
                    f.write(resp.read(1024 * 1024)) # Đọc 1MB đệm đầu tiên
                if os.path.exists(target_file) and os.path.getsize(target_file) > 10000:
                    return target_file, "Online Audio Stream"
            except Exception:
                pass

        # 2. Nếu là link YouTube / TikTok / SoundCloud -> dùng yt-dlp tải audio track
        if os.path.exists(self.yt_dlp_path):
            try:
                # Xóa các file cache cũ
                for ext in [".mp3", ".m4a", ".webm", ".opus", ".wav"]:
                    old_f = cache_base + ext
                    if os.path.exists(old_f):
                        try:
                            os.remove(old_f)
                        except Exception:
                            pass

                # Lấy tiêu đề video
                cmd_title = [self.yt_dlp_path, "--get-title", "--no-playlist", "--no-warnings", raw_url]
                p_title = subprocess.run(cmd_title, capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                video_title = p_title.stdout.strip().splitlines()[0] if p_title.stdout.strip() else "Video Audio Track"

                # Tải audio stream
                out_tmpl = cache_base + ".%(ext)s"
                cmd_dl = [
                    self.yt_dlp_path,
                    "-f", "bestaudio/best",
                    "-o", out_tmpl,
                    "--no-playlist",
                    "--no-warnings",
                    raw_url
                ]
                subprocess.run(cmd_dl, capture_output=True, timeout=25, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

                # Tìm file vừa tải
                for ext in [".m4a", ".mp3", ".webm", ".opus", ".wav"]:
                    cand = cache_base + ext
                    if os.path.exists(cand) and os.path.getsize(cand) > 10000:
                        return cand, video_title
            except Exception:
                pass

        return None, "Không thể tải luồng âm thanh"

    def play(self, sound_type=None, custom_url=None, callback=None):
        """Bắt đầu phát âm thanh tập trung hoặc luồng nhạc từ URL trực tiếp qua WinMM"""
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

                # Dừng và đóng thiết bị âm thanh cũ
                self._mci_send(f"stop {self.ALIAS}")
                self._mci_send(f"close {self.ALIAS}")

                stype = self.current_sound_type
                s_info = self.SOUND_TYPES.get(stype, {})
                target_file = None
                display_title = s_info.get("name", "Âm thanh tập trung")

                if stype == "custom" or self.custom_url:
                    self.status_message = "⏳ Đang tải bài hát từ link..."
                    if callback:
                        callback(None, self.status_message)
                    url_to_fetch = self.custom_url if self.custom_url else s_info.get("url", "")
                    loaded_file, title = self._fetch_media_to_local_file(url_to_fetch)
                    if loaded_file:
                        target_file = loaded_file
                        display_title = title
                    else:
                        self.status_message = "Lỗi: Không thể phát link này"
                        if callback:
                            callback(False, self.status_message)
                        return

                elif s_info.get("type") == "stream":
                    self.status_message = f"⏳ Đang kết nối đài {display_title}..."
                    if callback:
                        callback(None, self.status_message)
                    loaded_file, _ = self._fetch_media_to_local_file(s_info.get("url"))
                    if loaded_file:
                        target_file = loaded_file
                    else:
                        # Fallback sang tiếng mưa tự nhiên nếu stream online gián đoạn
                        target_file = self.generate_synth_wav("rain")

                else:
                    # Âm thanh tự nhiên (Rain, Ocean, Cafe, Forest)
                    self.status_message = f"Đang phát {display_title}..."
                    target_file = self.generate_synth_wav(stype)

                if current_token != self._play_token:
                    return

                if target_file and os.path.exists(target_file):
                    target_path = os.path.abspath(target_file)
                    # Mở file với WinMM MCI
                    err_open, _ = self._mci_send(f'open "{target_path}" alias {self.ALIAS}')
                    if err_open == 0:
                        self._apply_volume()
                        # Phát lặp lại vô tận (repeat)
                        self._mci_send(f"play {self.ALIAS} repeat")
                        self.is_playing = True
                        self._current_loaded_file = target_path
                        self.current_title = display_title
                        self.status_message = f"Đang phát: {display_title}"
                        if callback:
                            callback(True, self.status_message)
                        return

                self.is_playing = False
                self.status_message = "Không thể phát âm thanh"
                if callback:
                    callback(False, self.status_message)

        threading.Thread(target=_async_worker, daemon=True).start()
        return True

    def stop(self):
        """Dừng phát âm thanh nền"""
        self._play_token += 1
        with self._lock:
            self._mci_send(f"stop {self.ALIAS}")
            self._mci_send(f"close {self.ALIAS}")
            self.is_playing = False
            self.status_message = "Đã dừng"

    def pause(self):
        self._mci_send(f"pause {self.ALIAS}")
        self.is_playing = False
        self.status_message = "Tạm dừng"

    def resume(self):
        self._mci_send(f"resume {self.ALIAS}")
        self.is_playing = True
        self.status_message = f"Đang phát: {self.current_title}"

    def set_volume(self, vol):
        """Thiết lập âm lượng (0 - 100)"""
        try:
            self.volume = max(0, min(100, int(vol)))
            self._apply_volume()
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
