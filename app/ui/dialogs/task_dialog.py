"""
Quick Task Dialog (Focus MIT)
"""
import tkinter as tk


class QuickTaskDialog(tk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app.root)
        self.withdraw()
        self.app = master_app
        self.title("🎯 Mục Tiêu Quan Trọng Trong Ngày (Focus MIT)")
        self.attributes("-topmost", True)
        self.configure(bg="#11141c")
        self.resizable(False, False)

        w, h = 460, 220
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        f = tk.Frame(self, bg="#11141c", padx=16, pady=14)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="🎯 TASK QUAN TRỌNG NHẤT HÔM NAY", font=("Segoe UI", 11, "bold"), bg="#11141c", fg="#38BDF8").pack(anchor="w", pady=(0, 4))
        tk.Label(f, text="Giữ 1 mục tiêu duy nhất hiển thị cạnh đồng hồ để chống xao nhãng.", font=("Segoe UI", 8), bg="#11141c", fg="#94A3B8").pack(anchor="w", pady=(0, 10))

        self.ent_task = tk.Entry(f, font=("Segoe UI", 10), bg="#1e2430", fg="#F8FAFC", insertbackground="#fff", relief="flat", highlightthickness=1, highlightbackground="#334155")
        self.ent_task.pack(fill="x", pady=(0, 8), ipady=4)
        curr_task = self.app.config.get("focus_task", {}).get("text", "")
        self.ent_task.insert(0, curr_task)
        self.ent_task.focus_set()

        self.var_enable = tk.BooleanVar(value=self.app.config.get("focus_task", {}).get("enabled", True))
        chk = tk.Checkbutton(
            f,
            text="Hiển thị Task này trên đồng hồ",
            variable=self.var_enable,
            font=("Segoe UI", 9),
            bg="#11141c",
            fg="#FCD34D",
            selectcolor="#1e2430",
            activebackground="#11141c",
            activeforeground="#FCD34D"
        )
        chk.pack(anchor="w", pady=(0, 10))

        btn_box = tk.Frame(f, bg="#11141c")
        btn_box.pack(fill="x")

        btn_save = tk.Button(
            btn_box,
            text="💾 Lưu Task",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.save_task
        )
        btn_save.pack(side="left", padx=(0, 6))

        btn_clear = tk.Button(
            btn_box,
            text="🗑️ Xóa / Hoàn thành",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.clear_task
        )
        btn_clear.pack(side="left")

        self.bind("<Return>", lambda e: self.save_task())
        self.bind("<Escape>", lambda e: self.destroy())
        self.deiconify()

    def save_task(self):
        txt = self.ent_task.get().strip()
        self.app.config.setdefault("focus_task", {})
        self.app.config["focus_task"]["text"] = txt
        self.app.config["focus_task"]["enabled"] = self.var_enable.get() and bool(txt)
        self.app.save_config()
        self.app.update_extra_info_visibility()
        self.destroy()

    def clear_task(self):
        self.app.config.setdefault("focus_task", {})
        self.app.config["focus_task"]["text"] = ""
        self.app.config["focus_task"]["enabled"] = False
        self.app.save_config()
        self.app.update_extra_info_visibility()
        self.destroy()
