from __future__ import annotations

import tkinter as tk
from app import APP_NAME
from app.ui.branding import load_brand_logo
from app.ui.theme import current_colors, mix_colors, shift_color


class SplashView(tk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        colors = current_colors()
        super().__init__(parent, bg=colors["bg"])
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Initialisation en cours")
        self.step_var = tk.StringVar(value="Preparation de l'application")
        self.tip_var = tk.StringVar(value="Astuce: exportez vos rapports en PDF et Excel pour l'audit.")
        self.background_canvas: tk.Canvas | None = None
        self.logo_image = load_brand_logo((220, 96))
        self.logo_image_item: int | None = None
        self.app_label: int | None = None
        self.left_title_text: int | None = None
        self.left_subtitle_text: int | None = None
        self.badge_text: int | None = None
        self.title_text: int | None = None
        self.status_text: int | None = None
        self.step_text: int | None = None
        self.tip_text: int | None = None
        self.progress_label_text: int | None = None
        self.footer_text: int | None = None
        self.bar_bg: int | None = None
        self.bar_fill: int | None = None
        self.percent_text: int | None = None

        self._build_canvas()

    def _build_canvas(self) -> None:
        colors = current_colors()
        self.background_canvas = tk.Canvas(self, bg=colors["bg"], highlightthickness=0, bd=0)
        self.background_canvas.pack(fill="both", expand=True)
        self.background_canvas.bind("<Configure>", self._draw_background)

        self.app_label = self.background_canvas.create_text(
            480,
            170,
            text=APP_NAME,
            fill=colors["shell_sidebar_text"],
            font=("Segoe UI Semibold", 16),
            anchor="nw",
        )
        if self.logo_image is not None:
            self.logo_image_item = self.background_canvas.create_image(480, 170, image=self.logo_image, anchor="nw")
            self.background_canvas.itemconfigure(self.app_label, state="hidden")
        self.left_title_text = self.background_canvas.create_text(
            170,
            220,
            text="Chargement\nintelligent",
            fill=colors["shell_sidebar_text"],
            font=("Segoe UI Semibold", 24),
            width=200,
            anchor="nw",
        )
        self.left_subtitle_text = self.background_canvas.create_text(
            170,
            330,
            text="Le poste prepare la base, l'interface et les controles pour ouvrir votre espace de gestion dans de bonnes conditions.",
            fill=mix_colors(colors["shell_sidebar_text"], colors["panel_alt"], 0.48),
            font=("Segoe UI", 10),
            width=210,
            anchor="nw",
        )
        self.badge_text = self.background_canvas.create_text(
            480,
            170,
            text="Demarrage securise",
            fill=colors["primary_dark"],
            font=("Segoe UI Semibold", 9),
        )
        self.title_text = self.background_canvas.create_text(
            480,
            220,
            text="Ouverture de l'application",
            fill=colors["text"],
            font=("Segoe UI Semibold", 23),
            anchor="nw",
        )
        self.status_text = self.background_canvas.create_text(
            480,
            264,
            text=self.status_var.get(),
            fill=colors["muted"],
            font=("Segoe UI", 11),
            anchor="nw",
        )
        self.step_text = self.background_canvas.create_text(
            480,
            344,
            text=self.step_var.get(),
            fill=colors["text"],
            font=("Segoe UI Semibold", 17),
            width=360,
            anchor="nw",
        )
        self.progress_label_text = self.background_canvas.create_text(
            480,
            418,
            text="Progression",
            fill=colors["muted"],
            font=("Segoe UI Semibold", 9),
            anchor="nw",
        )
        self.tip_text = self.background_canvas.create_text(
            480,
            510,
            text=self.tip_var.get(),
            fill=colors["muted"],
            font=("Segoe UI", 10),
            width=360,
            anchor="nw",
        )
        self.footer_text = self.background_canvas.create_text(
            480,
            590,
            text="Base   •   Interface   •   Controles   •   Journalisation",
            fill=mix_colors(colors["muted"], colors["panel_alt"], 0.12),
            font=("Segoe UI", 9),
            anchor="nw",
        )

        self.bar_bg = self.background_canvas.create_rectangle(120, 470, 840, 490, fill=mix_colors(colors["panel_alt"], colors["border"], 0.35), outline="")
        self.bar_fill = self.background_canvas.create_rectangle(120, 470, 120, 490, fill=colors["primary"], outline="")
        self.percent_text = self.background_canvas.create_text(
            480,
            420,
            text="0%",
            fill=colors["primary_dark"],
            font=("Segoe UI Semibold", 20),
            anchor="ne",
        )

    def _draw_background(self, event: tk.Event) -> None:
        colors = current_colors()
        canvas = self.background_canvas
        if canvas is None:
            return
        width = event.width
        height = event.height
        canvas.configure(bg=colors["bg"])
        canvas.delete("bg")

        top_band = mix_colors(colors["bg"], colors["panel_alt"], 0.48)
        bottom_band = mix_colors(colors["bg"], colors["panel_alt"], 0.16)
        panel_fill = mix_colors(colors["panel"], colors["panel_alt"], 0.08)
        left_panel_fill = mix_colors(colors["shell_sidebar"], colors["primary_dark"], 0.18)
        badge_fill = mix_colors(colors["panel_alt"], colors["bg"], 0.25)

        canvas.create_rectangle(0, 0, width, height * 0.42, fill=top_band, outline="", tags="bg")
        canvas.create_rectangle(0, height * 0.42, width, height, fill=bottom_band, outline="", tags="bg")
        canvas.create_oval(-width * 0.16, height * 0.06, width * 0.36, height * 0.82, fill=mix_colors(colors["primary"], colors["panel_alt"], 0.58), outline="", tags="bg")
        canvas.create_oval(width * 0.7, -height * 0.12, width * 1.14, height * 0.48, fill=mix_colors(colors["accent"], colors["panel_alt"], 0.78), outline="", tags="bg")
        canvas.create_oval(width * 0.55, height * 0.42, width * 1.06, height * 1.06, fill=mix_colors(colors["primary_dark"], colors["bg"], 0.83), outline="", tags="bg")
        canvas.create_oval(width * 0.08, height * 0.58, width * 0.46, height * 1.08, fill=mix_colors(colors["ok"], colors["bg"], 0.86), outline="", tags="bg")

        card_width = min(max(width * 0.78, 840), 940)
        card_height = min(max(height * 0.72, 404), 430)
        left = (width - card_width) / 2
        top = max((height - card_height) / 2 - 4, 54)
        right = left + card_width
        bottom = top + card_height
        split_x = left + (card_width * 0.31)

        canvas.create_rectangle(left, top, right, bottom, fill=panel_fill, outline=colors["border"], width=1, tags="bg")
        canvas.create_rectangle(left, top, split_x, bottom, fill=left_panel_fill, outline="", tags="bg")
        canvas.create_rectangle(split_x, top, split_x + 1, bottom, fill=mix_colors(colors["border"], colors["panel_alt"], 0.2), outline="", tags="bg")
        canvas.create_oval(left + 24, top + 24, left + 92, top + 92, fill=mix_colors(colors["shell_sidebar_text"], left_panel_fill, 0.08), outline="", tags="bg")
        canvas.create_arc(left + 18, top + 52, split_x - 22, bottom - 26, start=36, extent=248, style="arc", outline=mix_colors(colors["accent"], colors["primary"], 0.42), width=12, tags="bg")
        canvas.create_arc(left + 46, top + 82, split_x + 8, bottom - 34, start=28, extent=238, style="arc", outline=mix_colors(colors["primary"], colors["shell_topbar"], 0.16), width=7, tags="bg")
        canvas.create_rectangle(split_x + 28, top + 24, split_x + 154, top + 52, fill=badge_fill, outline="", tags="bg")
        canvas.tag_lower("bg")
        self._reposition_content(width, height, left, top, right, bottom, split_x)

    def _reposition_content(
        self,
        width: float,
        height: float | None = None,
        left: float | None = None,
        top: float | None = None,
        right: float | None = None,
        bottom: float | None = None,
        split_x: float | None = None,
    ) -> None:
        canvas = self.background_canvas
        if canvas is None:
            return
        if height is None:
            height = max(canvas.winfo_height(), 576)
        if left is None or top is None or right is None or bottom is None:
            card_width = min(max(width * 0.78, 840), 940)
            card_height = min(max(height * 0.72, 404), 430)
            left = (width - card_width) / 2
            top = max((height - card_height) / 2 - 4, 54)
            right = left + card_width
            bottom = top + card_height
        if split_x is None:
            split_x = left + ((right - left) * 0.31)

        right_left = split_x + 28
        bar_left = right_left
        bar_right = right - 34
        bar_top = top + 274
        bar_bottom = bar_top + 20
        progress_x = bar_left + ((bar_right - bar_left) * (self.progress_var.get() / 100))

        canvas.coords(self.app_label, left + 34, top + 34)
        if self.logo_image_item is not None:
            canvas.coords(self.logo_image_item, right_left, top + 20)
        canvas.coords(self.left_title_text, left + 34, top + 98)
        canvas.coords(self.left_subtitle_text, left + 34, top + 208)
        canvas.coords(self.badge_text, split_x + 92, top + 38)
        canvas.coords(self.title_text, right_left, top + (104 if self.logo_image_item is not None else 82))
        canvas.coords(self.status_text, right_left, top + (144 if self.logo_image_item is not None else 120))
        canvas.coords(self.step_text, right_left, top + 188)
        canvas.coords(self.progress_label_text, right_left, top + 246)
        canvas.coords(self.bar_bg, bar_left, bar_top, bar_right, bar_bottom)
        canvas.coords(self.bar_fill, bar_left, bar_top, progress_x, bar_bottom)
        canvas.coords(self.percent_text, right - 34, top + 246)
        canvas.coords(self.tip_text, right_left, top + 324)
        canvas.coords(self.footer_text, right_left, bottom - 34)

    def update_progress(self, percent: int, status: str, step: str, tip: str | None = None) -> None:
        if not self.winfo_exists() or self.background_canvas is None:
            return
        self.progress_var.set(percent)
        self.status_var.set(status)
        self.step_var.set(step)
        if tip:
            self.tip_var.set(tip)
        if not self.background_canvas.winfo_exists():
            return
        self.background_canvas.itemconfigure(self.status_text, text=self.status_var.get())
        self.background_canvas.itemconfigure(self.step_text, text=self.step_var.get())
        self.background_canvas.itemconfigure(self.tip_text, text=self.tip_var.get())
        self.background_canvas.itemconfigure(self.percent_text, text=f"{percent}%")
        width = max(self.background_canvas.winfo_width(), 1024)
        height = max(self.background_canvas.winfo_height(), 576)
        self._reposition_content(width, height)
        self.update_idletasks()