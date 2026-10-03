"""
Hydration and Posture Reminder Dialog
"""
import tkinter as tk
from app.messages import ALERT_MESSAGES


class HydrationReminderDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(ALERT_MESSAGES["hydration_title"])
        self.attributes("-topmost", True)
        self.configure(bg="#0f172a")
        self.resizable(False, False)

        w, h = 380, 200
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        container = tk.Frame(self, bg="#0f172a", padx=16, pady=14)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="💧 🤸 👁️", font=("Segoe UI Emoji", 24), bg="#0f172a", fg="#38BDF8").pack(pady=(0, 4))
        tk.Label(container, text=ALERT_MESSAGES["hydration_header"], font=("Segoe UI", 11, "bold"), bg="#0f172a", fg="#38BDF8").pack(pady=(0, 4))
        tk.Label(
            container,
            text=ALERT_MESSAGES["hydration_body"],
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94A3B8",
            wraplength=340,
            justify="center"
        ).pack(pady=(0, 12))

        btn = tk.Button(
            container,
            text=ALERT_MESSAGES["hydration_btn"],
            font=("Segoe UI", 10, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.destroy
        )
        btn.pack()

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<space>", lambda e: self.destroy())
