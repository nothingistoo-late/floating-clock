"""
Weather Forecast Dialog
"""
import tkinter as tk
from tkinter import ttk
from app.constants import CITY_COORDINATES


class WeatherForecastDialog(tk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.withdraw()
        self.app = master_app
        self.title("🌦️ Dự Báo Thời Tiết (Open-Meteo Realtime)")
        self.attributes("-topmost", True)
        self.configure(bg="#0f172a")
        self.resizable(False, False)

        w, h = 460, 320
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        container = tk.Frame(self, bg="#0f172a", padx=16, pady=14)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="🌦️ THỜI TIẾT HIỆN TẠI & DỰ BÁO", font=("Segoe UI", 12, "bold"), bg="#0f172a", fg="#38BDF8").pack(anchor="w", pady=(0, 4))
        tk.Label(container, text="Dữ liệu thời gian thực từ trạm khí tượng thủy văn Open-Meteo", font=("Segoe UI", 8), bg="#0f172a", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        # City Selector Box
        sel_frame = tk.Frame(container, bg="#1e2430", padx=10, pady=8, relief="groove", bd=1)
        sel_frame.pack(fill="x", pady=(0, 12))

        tk.Label(sel_frame, text="Khu vực / Tỉnh thành:", font=("Segoe UI", 9, "bold"), bg="#1e2430", fg="#F8FAFC").pack(side="left", padx=(0, 6))

        cities = list(CITY_COORDINATES.keys())
        curr_city = self.app.config.get("weather", {}).get("city_name", "Hà Nội")
        self.cmb_city = ttk.Combobox(sel_frame, values=cities, state="readonly", width=16, font=("Segoe UI", 9))
        if curr_city in cities:
            self.cmb_city.current(cities.index(curr_city))
        else:
            self.cmb_city.current(0)
        self.cmb_city.pack(side="left", padx=(0, 6))

        btn_refresh = tk.Button(
            sel_frame,
            text="🔄 Cập nhật",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.update_weather_data
        )
        btn_refresh.pack(side="left")

        # Weather details display card
        self.card = tk.Frame(container, bg="#111827", padx=14, pady=12, relief="groove", bd=1)
        self.card.pack(fill="both", expand=True, pady=(0, 10))

        self.lbl_icon = tk.Label(self.card, text="☀️", font=("Segoe UI Emoji", 32), bg="#111827", fg="#F59E0B")
        self.lbl_icon.pack(side="left", padx=(6, 16))

        info_box = tk.Frame(self.card, bg="#111827")
        info_box.pack(side="left", fill="both", expand=True)

        self.lbl_temp = tk.Label(info_box, text="--°C", font=("Segoe UI", 20, "bold"), bg="#111827", fg="#F8FAFC")
        self.lbl_temp.pack(anchor="w")

        self.lbl_desc = tk.Label(info_box, text="Đang tải dữ liệu thời tiết...", font=("Segoe UI", 10), bg="#111827", fg="#38BDF8")
        self.lbl_desc.pack(anchor="w", pady=1)

        self.lbl_wind = tk.Label(info_box, text="Gió: -- km/h", font=("Segoe UI", 9), bg="#111827", fg="#94A3B8")
        self.lbl_wind.pack(anchor="w", pady=1)

        btn_close = tk.Button(
            container,
            text="Đóng (Esc)",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#FFFFFF",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.destroy
        )
        btn_close.pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())
        self.deiconify()
        self.update_weather_data()

    def update_weather_data(self):
        sel_city = self.cmb_city.get()
        self.app.config.setdefault("weather", {})
        self.app.config["weather"]["city_name"] = sel_city
        if sel_city in CITY_COORDINATES:
            lat, lon = CITY_COORDINATES[sel_city]
            self.app.config["weather"]["lat"] = lat
            self.app.config["weather"]["lon"] = lon
        self.app.save_config()

        def _on_fetched(txt, data):
            if not self.winfo_exists():
                return
            if data:
                self.lbl_icon.configure(text=data.get("icon", "🌤️"))
                self.lbl_temp.configure(text=f"{data.get('temp', 0):.1f}°C")
                self.lbl_desc.configure(text=f"{data.get('desc', '')} ({data.get('city', '')})")
                self.lbl_wind.configure(text=f"💨 Tốc độ gió: {data.get('wind', 0)} km/h")

        self.app.weather_mgr.fetch_weather(callback=_on_fetched, dispatcher=self.after_idle)
