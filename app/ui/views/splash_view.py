from __future__ import annotations

import tkinter as tk
from app.ui.theme import current_colors, mix_colors, shift_color


class SplashView(tk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        colors = current_colors()
        super().__init__(parent, bg=colors["shell_topbar"])
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Initialisation en cours")
        self.step_var = tk.StringVar(value="Preparation de l'application")
        self.tip_var = tk.StringVar(value="Astuce: exportez vos rapports en PDF et Excel pour l'audit.")

        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        colors = current_colors()
        header_bg = mix_colors(colors["shell_topbar"], colors["shell_sidebar"], 0.2)
        header = tk.Frame(self, bg=header_bg, height=150)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Gestion Magasin POS",
            bg=header_bg,
            fg=colors["shell_sidebar_text"],
            font=("Segoe UI Semibold", 28),
        ).pack(pady=(48, 10))
        tk.Label(
            header,
            textvariable=self.status_var,
            bg=header_bg,
            fg=mix_colors(colors["shell_sidebar_text"], colors["panel_alt"], 0.35),
            font=("Segoe UI", 15),
        ).pack()

    def _build_body(self) -> None:
        colors = current_colors()
        body_bg = mix_colors(colors["shell_topbar"], colors["primary"], 0.28)
        body = tk.Frame(self, bg=body_bg)
        body.pack(fill="both", expand=True)

        self.background_canvas = tk.Canvas(body, bg=body_bg, highlightthickness=0)
        self.background_canvas.pack(fill="both", expand=True)
        self.background_canvas.bind("<Configure>", self._draw_background)

        self.title_text = self.background_canvas.create_text(
            480,
            130,
            text="Progression du demarrage",
            fill=mix_colors(colors["shell_sidebar_text"], colors["panel_alt"], 0.3),
            font=("Segoe UI Semibold", 24),
        )
        self.step_text = self.background_canvas.create_text(
            480,
            280,
            text=self.step_var.get(),
            fill=colors["shell_sidebar_text"],
            font=("Segoe UI Semibold", 20),
        )
        self.tip_text = self.background_canvas.create_text(
            480,
            330,
            text=self.tip_var.get(),
            fill=mix_colors(colors["panel_alt"], colors["shell_sidebar_text"], 0.55),
            font=("Segoe UI", 12),
        )

        self.bar_bg = self.background_canvas.create_rectangle(120, 390, 840, 430, fill=shift_color(colors["shell_sidebar"], -8), width=0)
        self.bar_fill = self.background_canvas.create_rectangle(120, 390, 120, 430, fill=colors["accent"], width=0)
        self.percent_text = self.background_canvas.create_text(
            480,
            450,
            text="0%",
            fill=colors["shell_sidebar_text"],
            font=("Segoe UI Semibold", 26),
        )

    def _draw_background(self, event: tk.Event) -> None:
        colors = current_colors()
        canvas = self.background_canvas
        width = event.width
        height = event.height
        canvas.delete("bg")
        canvas.create_oval(-220, 180, 220, height + 120, fill=mix_colors(colors["shell_sidebar"], colors["primary"], 0.25), outline="", tags="bg")
        canvas.create_oval(width - 340, 230, width + 120, height + 180, fill=mix_colors(colors["shell_topbar"], colors["primary_dark"], 0.25), outline="", tags="bg")
        canvas.create_oval(width / 2 - 160, 20, width / 2 + 160, 300, fill=mix_colors(colors["primary"], colors["shell_topbar"], 0.12), outline="", tags="bg")
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