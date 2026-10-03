"""
Weather Manager (Open-Meteo Realtime Forecast)
"""
import json
import ssl
import threading
import time
import urllib.request
from app.constants import CITY_COORDINATES, WEATHER_CODE_MAP


class WeatherManager:
    """Quản lý tải thông tin thời tiết thời gian thực từ Open-Meteo API"""
    def __init__(self, config):
        self.config = config
        self.last_fetch_time = 0
        self.current_weather_str = ""
        self.current_data = {}
        self.is_fetching = False

    def fetch_weather(self, callback=None, dispatcher=None):
        """
        Tải thời tiết bất đồng bộ.
        dispatcher: hàm dispatch (thường là root.after(0, ...)) để callback chạy an toàn trên Tkinter main thread.
        """
        w_cfg = self.config.get("weather", {})
        if not w_cfg.get("enabled", True):
            return

        city = w_cfg.get("city_name", "Hà Nội")
        lat, lon = CITY_COORDINATES.get(city, (w_cfg.get("lat", 21.0285), w_cfg.get("lon", 105.8542)))

        def _worker():
            self.is_fetching = True
            try:
                try:
                    ctx = ssl._create_unverified_context()
                except Exception:
                    ctx = None
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                req = urllib.request.Request(url, headers={"User-Agent": "TopFloatingClock/2.1"})
                with urllib.request.urlopen(req, timeout=6, context=ctx) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    cw = data.get("current_weather", {})
                    temp = cw.get("temperature", 28.0)
                    w_code = cw.get("weathercode", 0)
                    wind = cw.get("windspeed", 0.0)

                    icon, desc = WEATHER_CODE_MAP.get(w_code, ("🌤️", "Thời tiết tốt"))
                    txt = f"{icon} {city}: {temp:.0f}°C • {desc}"

                    self.current_weather_str = txt
                    self.current_data = {
                        "city": city,
                        "temp": temp,
                        "wind": wind,
                        "icon": icon,
                        "desc": desc,
                        "time": cw.get("time", "")
                    }
                    self.last_fetch_time = time.time()
                    if callback:
                        if dispatcher:
                            dispatcher(lambda: callback(txt, self.current_data))
                        else:
                            callback(txt, self.current_data)
            except Exception:
                pass
            finally:
                self.is_fetching = False

        threading.Thread(target=_worker, daemon=True).start()
