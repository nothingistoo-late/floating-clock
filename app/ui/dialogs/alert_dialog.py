"""
Alert Notification Dialog (Alarm, Timer, and Target Time triggers)
"""
import tkinter as tk
from app.services.sound_service import sound_mgr


class AlertNotificationDialog(tk.Toplevel):
    def __init__(self, master, title_text, message_text, on_dismiss=None, on_snooze=None, on_restart=None):
        super().__init__(master)
        self.withdraw()
        self.title(title_text)
        self.attributes("-topmost", True)
        self.configure(bg="#151922")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.dismiss)

        self.on_dismiss = on_dismiss
        self.on_snooze = on_snooze
        self.on_restart = on_restart
        self.flash_timer = None
        self.flash_state = False

        w, h = 440, 250
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        container = tk.Frame(self, bg="#151922", padx=20, pady=16)
        container.pack(fill="both", expand=True)

        lbl_icon = tk.Label(container, text="🔔 ⏰ 🔔", font=("Segoe UI Emoji", 24), bg="#151922", fg="#F59E0B")
        lbl_icon.pack(pady=(0, 6))

        self.lbl_msg = tk.Label(
            container,
            text=message_text,
            font=("Segoe UI", 12, "bold"),
            bg="#151922",
            fg="#F8FAFC",
            wraplength=400,
            justify="center"
        )
        self.lbl_msg.pack(pady=(0, 16))

        btn_frame = tk.Frame(container, bg="#151922")
        btn_frame.pack(fill="x", side="bottom")

        btn_dismiss = tk.Button(
            btn_frame,
            text="🔕 Tắt chuông",
            font=("Segoe UI", 10, "bold"),
            bg="#EF4444",
            fg="#FFFFFF",
            activebackground="#DC2626",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.dismiss
        )
        btn_dismiss.pack(side="left", expand=True, fill="x", padx=4)

        if on_snooze:
            btn_snooze = tk.Button(
                btn_frame,
                text="💤 Báo lại 5p",
                font=("Segoe UI", 10, "bold"),
                bg="#3B82F6",
                fg="#FFFFFF",
                activebackground="#2563EB",
                activeforeground="#FFFFFF",
                relief="flat",
                padx=10,
                pady=8,
                cursor="hand2",
                command=self.snooze
            )
            btn_snooze.pack(side="left", expand=True, fill="x", padx=4)

        if on_restart:
            btn_restart = tk.Button(
                btn_frame,
                text="🔄 Lặp lại",
                font=("Segoe UI", 10, "bold"),
                bg="#10B981",
                fg="#FFFFFF",
                activebackground="#059669",
                activeforeground="#FFFFFF",
                relief="flat",
                padx=10,
                pady=8,
                cursor="hand2",
                command=self.restart
            )
            btn_restart.pack(side="left", expand=True, fill="x", padx=4)

        self.bind("<Escape>", lambda e: self.dismiss())
        self.bind("<Return>", lambda e: self.dismiss())
        self.bind("<space>", lambda e: self.dismiss())

        self.deiconify()

        # Start visual flash effect
        self._flash()

    def _flash(self):
        try:
            self.flash_state = not self.flash_state
            fg = "#EF4444" if self.flash_state else "#F59E0B"
            if self.winfo_exists():
                self.lbl_msg.configure(fg=fg)
                self.flash_timer = self.after(400, self._flash)
        except Exception:
            pass

    def _cleanup_timer(self):
        if self.flash_timer is not None:
            try:
                self.after_cancel(self.flash_timer)
            except Exception:
                pass
            self.flash_timer = None

    def dismiss(self):
        sound_mgr.stop_alarm()
        self._cleanup_timer()
        if self.on_dismiss:
            try:
                self.on_dismiss()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass

    def snooze(self):
        sound_mgr.stop_alarm()
        self._cleanup_timer()
        if self.on_snooze:
            try:
                self.on_snooze()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass

    def restart(self):
        sound_mgr.stop_alarm()
        self._cleanup_timer()
        if self.on_restart:
            try:
                self.on_restart()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
