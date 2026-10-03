"""
Audio and Sound Managers (Alarms, Chimes, and Focus Ambient Noise)
"""
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


class FocusSoundManager:
    """Quản lý và tổng hợp âm thanh nền tập trung (White Noise, Mưa, Sóng biển, v.v.)"""
    SOUND_TYPES = {
        "rain": {"name": "Mưa rào êm dịu (Rainfall)", "icon": "🌧️"},
        "ocean": {"name": "Sóng biển dạt dào (Ocean Waves)", "icon": "🌊"},
        "brown_noise": {"name": "Tiếng ồn nâu sâu lắng (Brown Noise)", "icon": "🧘"},
        "white_noise": {"name": "Tiếng ồn trắng tĩnh tâm (White Noise)", "icon": "📻"},
        "alpha_wave": {"name": "Sóng não Alpha 432Hz (Deep Focus)", "icon": "🧠"},
        "cafe": {"name": "Quán cà phê chill (Cafe Ambient)", "icon": "☕"},
    }

    def __init__(self, config):
        self.config = config
        self.is_playing = False
        self.current_sound_type = config.get("focus_sound", {}).get("sound_type", "rain")
        self.temp_sound_file = os.path.join(APP_DIR, "_ambient_loop.wav")

    @property
    def current_sound(self):
        return self.current_sound_type

    @current_sound.setter
    def current_sound(self, val):
        self.current_sound_type = val

    def generate_sound_wav(self, sound_type="rain", duration_sec=6, sample_rate=22050):
        num_samples = int(duration_sec * sample_rate)
        try:
            with wave.open(self.temp_sound_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)

                raw_data = bytearray()
                last_val = 0.0

                if sound_type == "rain":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.94) + (white * 0.06)
                        if random.random() < 0.003:
                            val = last_val * 0.7 + random.uniform(-0.6, 0.6) * 0.3
                        else:
                            val = last_val
                        val_c = max(-1.0, min(1.0, val * 1.2))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "ocean":
                    wave_period = 5.0
                    for i in range(num_samples):
                        t = i / sample_rate
                        surge = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * t / wave_period))
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.92) + (white * 0.08)
                        val_c = max(-1.0, min(1.0, last_val * surge * 1.5))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "brown_noise":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.985) + (white * 0.015)
                        val_c = max(-1.0, min(1.0, last_val * 2.5))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "white_noise":
                    for i in range(num_samples):
                        val = random.uniform(-0.25, 0.25)
                        raw_data.extend(struct.pack('<h', int(val * 32767)))

                elif sound_type == "alpha_wave":
                    for i in range(num_samples):
                        t = i / sample_rate
                        carrier = math.sin(2 * math.pi * 432.0 * t)
                        mod = 0.75 + 0.25 * math.sin(2 * math.pi * 10.0 * t)
                        val_c = carrier * mod * 0.2
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                elif sound_type == "cafe":
                    for i in range(num_samples):
                        white = random.uniform(-1.0, 1.0)
                        last_val = (last_val * 0.93) + (white * 0.07)
                        val = last_val * 0.6
                        if random.random() < 0.0006:
                            val += random.uniform(-0.8, 0.8)
                        val_c = max(-1.0, min(1.0, val))
                        raw_data.extend(struct.pack('<h', int(val_c * 32767)))

                wf.writeframes(raw_data)
            return True
        except Exception:
            return False

    def play(self, sound_type=None):
        if sound_type:
            self.current_sound_type = sound_type
        if self.generate_sound_wav(self.current_sound_type):
            try:
                winsound.PlaySound(self.temp_sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
                self.is_playing = True
                return True
            except Exception:
                pass
        return False

    def stop(self):
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        self.is_playing = False

    def toggle(self, sound_type=None):
        if self.is_playing:
            self.stop()
            return False
        else:
            return self.play(sound_type)


# Global singleton instance for chimes/alarm
sound_mgr = SoundManager()
