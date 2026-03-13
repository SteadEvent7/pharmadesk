from __future__ import annotations

import tkinter as tk
class SplashView(tk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg="#1658bd")
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Initialisation en cours")
        self.step_var = tk.StringVar(value="Preparation de l'application")
        self.tip_var = tk.StringVar(value="Astuce: exportez vos rapports en PDF et Excel pour l'audit.")

        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg="#124ba3", height=150)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Gestion Magasin POS",
            bg="#124ba3",
            fg="#ffffff",
            font=("Segoe UI Semibold", 28),
        ).pack(pady=(48, 10))
        tk.Label(
            header,
            textvariable=self.status_var,
            bg="#124ba3",
            fg="#cfe0ff",
            font=("Segoe UI", 15),
        ).pack()

    def _build_body(self) -> None:
        body = tk.Frame(self, bg="#1a5fd0")
        body.pack(fill="both", expand=True)

        self.background_canvas = tk.Canvas(body, bg="#1a5fd0", highlightthickness=0)
        self.background_canvas.pack(fill="both", expand=True)
        self.background_canvas.bind("<Configure>", self._draw_background)

        self.title_text = self.background_canvas.create_text(
            480,
            130,
            text="Progression du demarrage",
            fill="#e8f0ff",
            font=("Segoe UI Semibold", 24),
        )
        self.step_text = self.background_canvas.create_text(
            480,
            280,
            text=self.step_var.get(),
            fill="#ffffff",
            font=("Segoe UI Semibold", 20),
        )
        self.tip_text = self.background_canvas.create_text(
            480,
            330,
            text=self.tip_var.get(),
            fill="#8bb1ef",
            font=("Segoe UI", 12),
        )

        self.bar_bg = self.background_canvas.create_rectangle(120, 390, 840, 430, fill="#194ba0", width=0)
        self.bar_fill = self.background_canvas.create_rectangle(120, 390, 120, 430, fill="#efc93f", width=0)
        self.percent_text = self.background_canvas.create_text(
            480,
            450,
            text="0%",
            fill="#ffffff",
            font=("Segoe UI Semibold", 26),
        )

    def _draw_background(self, event: tk.Event) -> None:
        canvas = self.background_canvas
        width = event.width
        height = event.height
        canvas.delete("bg")
        canvas.create_oval(-220, 180, 220, height + 120, fill="#204fa9", outline="", tags="bg")
        canvas.create_oval(width - 340, 230, width + 120, height + 180, fill="#1d53ad", outline="", tags="bg")
        canvas.create_oval(width / 2 - 160, 20, width / 2 + 160, 300, fill="#1b58bf", outline="", tags="bg")
        canvas.tag_lower("bg")
        self._reposition_content(width)

    def _reposition_content(self, width: float) -> None:
        canvas = self.background_canvas
        center_x = width / 2
        canvas.coords(self.title_text, center_x, 130)
        canvas.coords(self.step_text, center_x, 280)
        canvas.coords(self.tip_text, center_x, 330)
        canvas.coords(self.bar_bg, center_x - 360, 390, center_x + 360, 430)
        progress_x = center_x - 360 + (720 * (self.progress_var.get() / 100))
        canvas.coords(self.bar_fill, center_x - 360, 390, progress_x, 430)
        canvas.coords(self.percent_text, center_x, 450)

    def update_progress(self, percent: int, status: str, step: str, tip: str | None = None) -> None:
        self.progress_var.set(percent)
        self.status_var.set(status)
        self.step_var.set(step)
        if tip:
            self.tip_var.set(tip)
        self.background_canvas.itemconfigure(self.step_text, text=self.step_var.get())
        self.background_canvas.itemconfigure(self.tip_text, text=self.tip_var.get())
        self.background_canvas.itemconfigure(self.percent_text, text=f"{percent}%")
        width = max(self.background_canvas.winfo_width(), 960)
        self._reposition_content(width)
        self.update_idletasks()