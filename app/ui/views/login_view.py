from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

from app import APP_NAME
from app.services.auth_service import auth_service
from app.ui.branding import load_brand_logo
from app.ui.theme import current_colors, mix_colors, shift_color


class LoginView(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_success) -> None:
        super().__init__(parent)
        self.on_success = on_success
        self.username_var = tk.StringVar(value="admin")
        self.password_var = tk.StringVar(value="admin123")
        self._background_items: list[int] = []
        self._art_items: list[int] = []
        self._shadow_items: list[int] = []
        self._background_glow_items: list[int] = []
        self._background_glow_specs: list[tuple[float, float, float, float, str, float]] = []
        self._art_highlight_item: int | None = None
        self._art_highlight_bounds: tuple[float, float, float, float] | None = None
        self._last_size = (0, 0)
        self._card_size = (780, 450)
        self._intro_progress = 0.0
        self._ambient_phase = 0.0
        self._intro_job: str | None = None
        self._ambient_job: str | None = None
        self.logo_image = load_brand_logo((210, 90))

        colors = current_colors()
        self.background = tk.Canvas(self, highlightthickness=0, bd=0, bg=colors["bg"])
        self.background.pack(fill="both", expand=True)

        self.card = tk.Frame(
            self.background,
            bg=colors["panel"],
            bd=0,
            highlightthickness=1,
            highlightbackground=colors["border"],
            highlightcolor=colors["border"],
        )
        self.card_window = self.background.create_window(0, 0, window=self.card, anchor="center")
        self._build_card()

        self.background.bind("<Configure>", self._on_resize)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.username_entry.bind("<Return>", lambda _event: self._login())
        self.password_entry.bind("<Return>", lambda _event: self._login())
        self.after(40, self._start_intro_animation)
        self.after(120, self.username_entry.focus_set)

    def _build_card(self) -> None:
        colors = current_colors()
        self.card.grid_columnconfigure(0, weight=10, minsize=320)
        self.card.grid_columnconfigure(1, weight=10, minsize=330)
        self.card.grid_rowconfigure(0, weight=1)

        self.card.configure(bg=colors["panel"])

        self.art_panel = tk.Canvas(
            self.card,
            width=340,
            height=430,
            bg=mix_colors(colors["shell_sidebar"], colors["primary_dark"], 0.28),
            highlightthickness=0,
            bd=0,
        )
        self.art_panel.grid(row=0, column=0, sticky="nsew")

        form_panel = tk.Frame(self.card, bg=colors["panel"], padx=30, pady=28)
        form_panel.grid(row=0, column=1, sticky="nsew")
        form_panel.grid_columnconfigure(0, weight=1)

        current_row = 0
        if self.logo_image is not None:
            tk.Label(form_panel, image=self.logo_image, bg=colors["panel"]).grid(row=current_row, column=0, sticky="w", pady=(0, 10))
            current_row += 1
        else:
            badge = tk.Label(
                form_panel,
                text=APP_NAME,
                bg=mix_colors(colors["panel_alt"], colors["bg"], 0.15),
                fg=colors["primary_dark"],
                font=("Segoe UI Semibold", 10),
                padx=12,
                pady=6,
            )
            badge.grid(row=current_row, column=0, sticky="w")
            current_row += 1

        title = tk.Label(
            form_panel,
            text="Connexion",
            bg=colors["panel"],
            fg=colors["text"],
            font=("Segoe UI Semibold", 23),
        )
        title.grid(row=current_row, column=0, sticky="w", pady=(12, 4))
        current_row += 1

        subtitle = tk.Label(
            form_panel,
            text="Acces securise a votre espace de gestion officinale.",
            bg=colors["panel"],
            fg=colors["muted"],
            justify="left",
            font=("Segoe UI", 9),
        )
        subtitle.grid(row=current_row, column=0, sticky="w", pady=(0, 14))
        current_row += 1

        username_block, self.username_entry = self._build_input(
            form_panel,
            "Nom d'utilisateur",
            self.username_var,
        )
        username_block.grid(row=current_row, column=0, sticky="ew", pady=(0, 10))
        current_row += 1

        password_block, self.password_entry = self._build_input(
            form_panel,
            "Mot de passe",
            self.password_var,
            show="*",
        )
        password_block.grid(row=current_row, column=0, sticky="ew", pady=(0, 12))
        current_row += 1

        login_button = tk.Button(
            form_panel,
            text="Se connecter",
            command=self._login,
            bg=colors["primary_dark"],
            fg=colors["shell_sidebar_text"],
            activebackground=colors["primary"],
            activeforeground=colors["shell_sidebar_text"],
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=10,
            cursor="hand2",
        )
        login_button.grid(row=current_row, column=0, sticky="ew")
        current_row += 1

        helper_card = tk.Frame(
            form_panel,
            bg=mix_colors(colors["panel_alt"], colors["bg"], 0.22),
            highlightthickness=1,
            highlightbackground=colors["border"],
            padx=12,
            pady=8,
        )
        helper_card.grid(row=current_row, column=0, sticky="ew", pady=(12, 0))

        helper = tk.Label(
            helper_card,
            text="Compte initial: admin / admin123",
            bg=mix_colors(colors["panel_alt"], colors["bg"], 0.22),
            fg=colors["muted"],
            font=("Segoe UI", 8),
        )
        helper.pack(anchor="w")

        security_note = tk.Label(
            helper_card,
            text="Roles geres: administrateur, pharmacien, caissier",
            bg=mix_colors(colors["panel_alt"], colors["bg"], 0.22),
            fg=mix_colors(colors["muted"], colors["panel"], 0.15),
            font=("Segoe UI", 8),
        )
        security_note.pack(anchor="w", pady=(4, 0))

        self._draw_art_panel(340, 430)

    def _build_input(
        self,
        parent: tk.Misc,
        label: str,
        variable: tk.Variable,
        show: str | None = None,
    ) -> tuple[tk.Frame, tk.Entry]:
        colors = current_colors()
        wrapper = tk.Frame(parent, bg=colors["panel"])
        wrapper.grid_columnconfigure(0, weight=1)

        tk.Label(
            wrapper,
            text=label,
            bg=colors["panel"],
            fg=mix_colors(colors["text"], colors["muted"], 0.45),
            font=("Segoe UI", 8),
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        field = tk.Frame(wrapper, bg=colors["input_bg"], highlightthickness=1, highlightbackground=colors["border"])
        field.grid(row=1, column=0, sticky="ew")
        field.grid_columnconfigure(0, weight=1)

        entry = tk.Entry(
            field,
            textvariable=variable,
            show=show or "",
            relief="flat",
            bd=0,
            bg=colors["input_bg"],
            fg=colors["input_fg"],
            insertbackground=colors["input_fg"],
            font=("Segoe UI", 10),
        )
        entry.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        return wrapper, entry

    def _on_resize(self, event: tk.Event) -> None:
        self._last_size = (event.width, event.height)
        self._draw_background(event.width, event.height)

        card_width = min(max(event.width - 120, 700), 900)
        card_height = min(max(event.height - 120, 430), 500)
        self._card_size = (card_width, card_height)
        self.background.itemconfigure(self.card_window, width=card_width, height=card_height)
        self._update_card_position()

        left_width = max(int(card_width * 0.42), 290)
        self.art_panel.configure(width=left_width, height=card_height)
        self._draw_art_panel(left_width, card_height)

    def _draw_background(self, width: int, height: int) -> None:
        colors = current_colors()
        for item in self._background_items:
            self.background.delete(item)
        self._background_items.clear()
        self._background_glow_items.clear()
        self._background_glow_specs.clear()

        self.background.configure(bg=colors["bg"])
        base_layers = [
            (0, 0, width, height * 0.44, mix_colors(colors["panel_alt"], colors["bg"], 0.55)),
            (0, height * 0.44, width, height, mix_colors(colors["bg"], colors["panel_alt"], 0.14)),
        ]
        for x1, y1, x2, y2, color in base_layers:
            item = self.background.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            self._background_items.append(item)

        background_shapes = [
            (-0.18, 0.08, 0.36, 0.92, mix_colors(colors["primary"], colors["panel_alt"], 0.58)),
            (0.64, -0.08, 1.12, 0.54, mix_colors(colors["accent"], colors["panel_alt"], 0.76)),
            (0.54, 0.44, 1.1, 1.06, mix_colors(colors["primary_dark"], colors["bg"], 0.82)),
        ]
        for x1, y1, x2, y2, color in background_shapes:
            item = self.background.create_oval(width * x1, height * y1, width * x2, height * y2, fill=color, outline="")
            self._background_items.append(item)

        sweep = self.background.create_polygon(
            0,
            height * 0.88,
            width * 0.18,
            height * 0.72,
            width * 0.42,
            height * 0.8,
            width * 0.62,
            height * 0.6,
            width,
            height * 0.7,
            width,
            height,
            0,
            height,
            fill=mix_colors(colors["panel_alt"], colors["bg"], 0.45),
            outline="",
            smooth=True,
        )
        self._background_items.append(sweep)

        glow_specs = [
            (-0.1, 0.04, 0.42, 0.92, mix_colors(colors["primary"], colors["panel_alt"], 0.42), 0.0),
            (0.66, 0.02, 1.12, 0.64, mix_colors(colors["accent"], colors["panel_alt"], 0.82), 1.3),
            (0.42, 0.56, 1.0, 1.08, mix_colors(colors["primary_dark"], colors["bg"], 0.76), 2.1),
        ]
        for x1, y1, x2, y2, color, phase in glow_specs:
            item = self.background.create_oval(
                width * x1,
                height * y1,
                width * x2,
                height * y2,
                fill=color,
                outline="",
            )
            self._background_items.append(item)
            self._background_glow_items.append(item)
            self._background_glow_specs.append((x1, y1, x2, y2, color, phase))

        self._ensure_shadow_items()
        self._update_card_position()

    def _draw_art_panel(self, width: int, height: int) -> None:
        colors = current_colors()
        for item in self._art_items:
            self.art_panel.delete(item)
        self._art_items.clear()

        base_layers = [
            (0, 0, width, height, shift_color(colors["shell_sidebar"], -30)),
            (0, height * 0.42, width, height, shift_color(colors["shell_sidebar"], -14)),
            (0, 0, width, height * 0.34, mix_colors(colors["shell_topbar"], colors["primary_dark"], 0.3)),
        ]
        for x1, y1, x2, y2, color in base_layers:
            item = self.art_panel.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            self._art_items.append(item)

        bubble_specs = [
            (-width * 0.25, -height * 0.08, width * 0.54, height * 0.42, mix_colors(colors["primary"], colors["shell_topbar"], 0.3)),
            (width * 0.22, height * 0.14, width * 1.05, height * 0.96, mix_colors(colors["primary_dark"], colors["shell_sidebar"], 0.38)),
            (-width * 0.12, height * 0.5, width * 0.82, height * 1.12, mix_colors(colors["ok"], colors["shell_sidebar"], 0.52)),
            (width * 0.44, -height * 0.04, width * 1.08, height * 0.5, shift_color(colors["shell_sidebar"], -30)),
        ]
        for x1, y1, x2, y2, color in bubble_specs:
            item = self.art_panel.create_oval(x1, y1, x2, y2, fill=color, outline="")
            self._art_items.append(item)

        wave_one = self.art_panel.create_polygon(
            0,
            height * 0.78,
            width * 0.18,
            height * 0.66,
            width * 0.36,
            height * 0.7,
            width * 0.52,
            height * 0.56,
            width * 0.76,
            height * 0.61,
            width,
            height * 0.48,
            width,
            height,
            0,
            height,
            fill=mix_colors(colors["primary_dark"], colors["shell_sidebar"], 0.62),
            outline="",
            smooth=True,
        )
        self._art_items.append(wave_one)

        wave_two = self.art_panel.create_polygon(
            0,
            height * 0.92,
            width * 0.16,
            height * 0.82,
            width * 0.3,
            height * 0.86,
            width * 0.52,
            height * 0.74,
            width * 0.72,
            height * 0.8,
            width,
            height * 0.68,
            width,
            height,
            0,
            height,
            fill=shift_color(colors["shell_sidebar"], -16),
            outline="",
            smooth=True,
        )
        self._art_items.append(wave_two)

        swirl_specs = [
            (width * 0.08, height * 0.18, width * 0.86, height * 1.02, mix_colors(colors["accent"], colors["primary"], 0.4), 20),
            (width * 0.12, height * 0.14, width * 0.92, height * 0.94, mix_colors(colors["primary"], colors["shell_topbar"], 0.15), 12),
            (width * 0.2, height * 0.1, width * 0.98, height * 0.82, shift_color(colors["shell_sidebar"], -36), 28),
        ]
        for x1, y1, x2, y2, color, size in swirl_specs:
            item = self.art_panel.create_arc(
                x1,
                y1,
                x2,
                y2,
                start=34,
                extent=245,
                style="arc",
                outline=color,
                width=size,
            )
            self._art_items.append(item)

        highlight = self.art_panel.create_oval(
            width * 0.08,
            height * 0.08,
            width * 0.26,
            height * 0.18,
            fill=mix_colors(colors["panel"], colors["shell_sidebar_text"], 0.35),
            outline="",
        )
        self._art_items.append(highlight)
        self._art_highlight_item = highlight
        self._art_highlight_bounds = (0.08, 0.08, 0.26, 0.18)

        title = self.art_panel.create_text(
            width * 0.12,
            height * 0.58,
            anchor="nw",
            text="Bienvenue dans\nvotre officine",
            fill=colors["shell_sidebar_text"],
            font=("Segoe UI Semibold", 26),
        )
        self._art_items.append(title)

        subtitle = self.art_panel.create_text(
            width * 0.12,
            height * 0.75,
            anchor="nw",
            width=width * 0.68,
            text="Retrouvez vos ventes, votre stock et vos controles quotidiens dans un espace plus lisible et plus stable.",
            fill=mix_colors(colors["shell_sidebar_text"], colors["panel_alt"], 0.4),
            font=("Segoe UI", 11),
        )
        self._art_items.append(subtitle)

    def _ensure_shadow_items(self) -> None:
        if not self._shadow_items:
            return
        for item in self._shadow_items:
            self.background.delete(item)
        self._shadow_items.clear()

    def _update_card_position(self) -> None:
        width, height = self._last_size
        if width <= 0 or height <= 0:
            return

        card_width, card_height = self._card_size
        progress = self._intro_progress
        y_offset = (1.0 - progress) * 34
        scale = 0.975 + (progress * 0.025)
        display_width = card_width * scale
        display_height = card_height * scale
        center_x = width / 2
        center_y = (height / 2) - 6 + y_offset

        self.background.coords(self.card_window, center_x, center_y)
        self.background.itemconfigure(self.card_window, width=display_width, height=display_height)
        self.background.tag_raise(self.card_window)

    def _start_intro_animation(self) -> None:
        toplevel = self.winfo_toplevel()
        try:
            toplevel.wm_attributes("-alpha", 0.9)
        except tk.TclError:
            pass
        self._intro_progress = 0.0
        self._animate_intro(0)

    def _animate_intro(self, step: int) -> None:
        steps = 16
        raw_progress = min(step / steps, 1.0)
        eased = 1 - pow(1 - raw_progress, 3)
        self._intro_progress = eased
        self._update_card_position()

        toplevel = self.winfo_toplevel()
        try:
            toplevel.wm_attributes("-alpha", 0.9 + (0.1 * eased))
        except tk.TclError:
            pass

        if step < steps:
            self._intro_job = self.after(22, lambda: self._animate_intro(step + 1))
            return

        self._intro_job = None
        try:
            toplevel.wm_attributes("-alpha", 1.0)
        except tk.TclError:
            pass
        self._start_ambient_animation()

    def _start_ambient_animation(self) -> None:
        if self._ambient_job is None:
            self._animate_ambient()

    def _animate_ambient(self) -> None:
        width, height = self._last_size
        if width <= 0 or height <= 0:
            self._ambient_job = self.after(70, self._animate_ambient)
            return

        self._ambient_phase += 0.08

        for item, (x1, y1, x2, y2, _color, phase) in zip(self._background_glow_items, self._background_glow_specs):
            drift_x = math.sin(self._ambient_phase + phase) * width * 0.018
            drift_y = math.cos((self._ambient_phase * 0.85) + phase) * height * 0.012
            self.background.coords(
                item,
                (width * x1) + drift_x,
                (height * y1) + drift_y,
                (width * x2) + drift_x,
                (height * y2) + drift_y,
            )

        if self._art_highlight_item and self._art_highlight_bounds:
            art_width = max(self.art_panel.winfo_width(), 1)
            art_height = max(self.art_panel.winfo_height(), 1)
            x1, y1, x2, y2 = self._art_highlight_bounds
            pulse = (math.sin(self._ambient_phase * 1.4) + 1) / 2
            expand_x = art_width * (0.012 + (pulse * 0.02))
            expand_y = art_height * (0.008 + (pulse * 0.015))
            self.art_panel.coords(
                self._art_highlight_item,
                (art_width * x1) - expand_x,
                (art_height * y1) - expand_y,
                (art_width * x2) + expand_x,
                (art_height * y2) + expand_y,
            )

        self._ambient_job = self.after(48, self._animate_ambient)

    def _on_destroy(self, _event: tk.Event) -> None:
        if not self.winfo_exists():
            return
        if self._intro_job is not None:
            self.after_cancel(self._intro_job)
            self._intro_job = None
        if self._ambient_job is not None:
            self.after_cancel(self._ambient_job)
            self._ambient_job = None

    def _login(self) -> None:
        user = auth_service.login(self.username_var.get().strip(), self.password_var.get().strip())
        if not user:
            messagebox.showerror("Connexion", "Identifiants invalides ou compte desactive.")
            return
        self.on_success(user)