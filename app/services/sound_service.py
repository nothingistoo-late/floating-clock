"""
Audio and Sound Managers (Alarms, Chimes, and Natural Focus Ambient Sounds)
Uses direct Native WinMM MCI Engine inside FloatingClock process.
"""
import ctypes
import math
import os
import random
import struct
import threading
import time
import wave
import winsound
from app.config import APP_DIR


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


import queue
from app.config import APP_DIR, BUNDLE_DIR


class FocusSoundManager:
    """
    Quản lý âm thanh tập trung chất lượng cao (Mưa rào, Sóng biển, Quán Cafe, Rừng đêm, Tiếng ồn trắng)
    Sử dụng luồng thực thi âm thanh chuyên dụng (Dedicated Audio Worker) để điều khiển Windows MCI,
    đảm bảo chuyển đổi tức thì giữa các âm thanh, không bị phát chồng chéo và dừng sạch sẽ 100%.
    """
    ALIAS = "FC_FOCUS_BGM"

    SOUND_TYPES = {
        "rain": {
            "name": "Mưa rào êm dịu (Rainfall)",
            "icon": "🌧️"
        },
        "ocean": {
            "name": "Sóng biển dạt dào (Ocean Waves)",
            "icon": "🌊"
        },
        "cafe": {
            "name": "Quán cà phê chill (Cafe Ambient)",
            "icon": "☕"
        },
        "night_forest": {
            "name": "Rừng đêm tĩnh lặng & Tiếng dế",
            "icon": "🌲"
        },
        "white_noise": {
            "name": "Tiếng ồn trắng (White Noise)",
            "icon": "📻"
        },
        "pink_noise": {
            "name": "Tiếng ồn hồng thư giãn (Pink Noise)",
            "icon": "🌸"
        }
    }

    def __init__(self, config):
        self.config = config
        self.is_playing = False
        self.current_sound_type = config.get("focus_sound", {}).get("sound_type", "rain")
        self.current_title = ""
        self.status_message = "Chưa phát"
        self.volume = config.get("focus_sound", {}).get("volume", 50)

        dir_candidates = [
            os.path.join(BUNDLE_DIR, "app", "assets", "sounds"),
            os.path.join(APP_DIR, "app", "assets", "sounds"),
            os.path.join(APP_DIR, "assets", "sounds"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sounds"),
        ]
        self.sounds_dir = next((d for d in dir_candidates if os.path.exists(d)), dir_candidates[0])
        try:
            os.makedirs(self.sounds_dir, exist_ok=True)
        except Exception:
            pass

        # Hàng đợi lệnh điều khiển âm thanh trên một luồng MCI chuyên biệt duy nhất
        self._cmd_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._audio_worker_loop, daemon=True, name="FC_AudioWorker")
        self._worker_thread.start()

    @property
    def current_sound(self):
        return self.current_sound_type

    @current_sound.setter
    def current_sound(self, val):
        self.current_sound_type = val

    def _mci_send(self, cmd_str):
        """Gửi lệnh trực tiếp đến Windows Multimedia Engine (WinMM) trên cùng luồng worker"""
        try:
            buf = ctypes.create_unicode_buffer(256)
            err = ctypes.windll.winmm.mciSendStringW(cmd_str, buf, 255, 0)
            return err, buf.value
        except Exception:
            return -1, ""

    def _apply_volume(self):
        """Áp dụng âm lượng qua MCI và Master Wave Volume"""
        try:
            mci_vol = int(max(0, min(100, self.volume)) * 10)
            self._mci_send(f"setaudio {self.ALIAS} volume to {mci_vol}")
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

                elif sound_type == "pink_noise":
                    b0, b1, b2, b3, b4, b5, b6 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    for _ in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        b0 = 0.99886 * b0 + white * 0.0555179
                        b1 = 0.99332 * b1 + white * 0.0750759
                        b2 = 0.96900 * b2 + white * 0.1538520
                        b3 = 0.86650 * b3 + white * 0.3104856
                        b4 = 0.55000 * b4 + white * 0.5329522
                        b5 = -0.7616 * b5 - white * 0.0168980
                        pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362
                        b6 = white * 0.115926
                        val = max(-0.8, min(0.8, pink * 0.12))
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                else:  # white_noise
                    for _ in range(num_samples):
                        white = random.uniform(-0.35, 0.35)
                        raw_data.extend(struct.pack('<h', int(white * 32767)))

                wf.writeframes(raw_data)
            return target_file
        except Exception:
            return None

    def _audio_worker_loop(self):
        """Vòng lặp xử lý lệnh âm thanh tập trung trên luồng đơn nhất định danh MCI"""
        while True:
            cmd, payload, callback = self._cmd_queue.get()
            try:
                if cmd == "stop":
                    # Dừng và đóng sạch sẽ thiết bị MCI hiện tại
                    try:
                        winsound.PlaySound(None, winsound.SND_PURGE)
                    except Exception:
                        pass
                    self._mci_send(f"stop {self.ALIAS}")
                    self._mci_send(f"close {self.ALIAS}")
                    self.is_playing = False
                    self.status_message = "Đã dừng"
                    if callback:
                        try:
                            callback(False, "Đã dừng")
                        except Exception:
                            pass

                elif cmd == "play":
                    stype = payload
                    # 1. Dừng âm thanh cũ hoàn toàn trước khi nạp âm thanh mới
                    try:
                        winsound.PlaySound(None, winsound.SND_PURGE)
                    except Exception:
                        pass
                    self._mci_send(f"stop {self.ALIAS}")
                    self._mci_send(f"close {self.ALIAS}")

                    s_info = self.SOUND_TYPES.get(stype, {})
                    display_title = s_info.get("name", "Âm thanh tập trung")
                    target_file = self.generate_synth_wav(stype)

                    if target_file and os.path.exists(target_file):
                        norm_p = os.path.abspath(target_file).replace("\\", "/")
                        err, _ = self._mci_send(f'open "{norm_p}" type mpegvideo alias {self.ALIAS}')
                        if err == 0:
                            self._mci_send(f"set {self.ALIAS} time format ms")
                            self._apply_volume()
                            self._mci_send(f"play {self.ALIAS} repeat")
                            self.is_playing = True
                            self.current_sound_type = stype
                            self.current_title = display_title
                            self.status_message = f"Đang phát: {display_title}"
                            if callback:
                                try:
                                    callback(True, self.status_message)
                                except Exception:
                                    pass
                            continue
                        else:
                            # Fallback winsound nếu hệ thống không cho phép mở mpegvideo
                            try:
                                winsound.PlaySound(target_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
                                self.is_playing = True
                                self.current_sound_type = stype
                                self.current_title = display_title
                                self.status_message = f"Đang phát: {display_title}"
                                if callback:
                                    try:
                                        callback(True, self.status_message)
                                    except Exception:
                                        pass
                                continue
                            except Exception:
                                pass

                    self.is_playing = False
                    self.status_message = "Không thể phát âm thanh"
                    if callback:
                        try:
                            callback(False, self.status_message)
                        except Exception:
                            pass

                elif cmd == "volume":
                    self.volume = payload
                    if self.is_playing:
                        self._apply_volume()

            except Exception:
                pass
            finally:
                self._cmd_queue.task_done()

    def play(self, sound_type=None, callback=None):
        """Bắt đầu phát hoặc chuyển đổi sang âm thanh tập trung mới"""
        if sound_type:
            self.current_sound_type = sound_type
        stype = self.current_sound_type
        s_info = self.SOUND_TYPES.get(stype, {})
        self.current_title = s_info.get("name", "Âm thanh tập trung")
        self.status_message = f"Đang tải: {self.current_title}..."
        self.is_playing = True

        # Đẩy lệnh vào worker queue để dừng âm thanh cũ và phát ngay âm thanh mới
        self._cmd_queue.put(("play", stype, callback))
        return True

    def stop(self, callback=None):
        """Dừng phát âm thanh nền ngay lập tức"""
        self.is_playing = False
        self.status_message = "Đã dừng"
        self._cmd_queue.put(("stop", None, callback))

    def set_volume(self, vol):
        """Thiết lập âm lượng (0 - 100)"""
        try:
            self.volume = max(0, min(100, int(vol)))
            self.config.setdefault("focus_sound", {})["volume"] = self.volume
            self._cmd_queue.put(("volume", self.volume, None))
        except Exception:
            pass

    def toggle(self, sound_type=None, callback=None):
        """Bật / Tắt âm thanh tập trung"""
        if self.is_playing:
            self.stop(callback)
            return False
        else:
            return self.play(sound_type, callback)


# Global singleton instance for chimes/alarm
sound_mgr = SoundManager()
