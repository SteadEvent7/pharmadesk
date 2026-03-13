from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

from app.services.auth_service import auth_service


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
        self._card_size = (820, 500)
        self._intro_progress = 0.0
        self._ambient_phase = 0.0
        self._intro_job: str | None = None
        self._ambient_job: str | None = None

        self.background = tk.Canvas(self, highlightthickness=0, bd=0)
        self.background.pack(fill="both", expand=True)

        self.card = tk.Frame(self.background, bg="#f8fafc", bd=0, highlightthickness=0)
        self.card_window = self.background.create_window(0, 0, window=self.card, anchor="center")
        self._build_card()

        self.background.bind("<Configure>", self._on_resize)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.username_entry.bind("<Return>", lambda _event: self._login())
        self.password_entry.bind("<Return>", lambda _event: self._login())
        self.after(40, self._start_intro_animation)
        self.after(120, self.username_entry.focus_set)

    def _build_card(self) -> None:
        self.card.grid_columnconfigure(0, weight=11, minsize=350)
        self.card.grid_columnconfigure(1, weight=9, minsize=380)
        self.card.grid_rowconfigure(0, weight=1)

        self.art_panel = tk.Canvas(
            self.card,
            width=380,
            height=460,
            bg="#04131d",
            highlightthickness=0,
            bd=0,
        )
        self.art_panel.grid(row=0, column=0, sticky="nsew")

        form_panel = tk.Frame(self.card, bg="#f8fafc", padx=42, pady=38)
        form_panel.grid(row=0, column=1, sticky="nsew")
        form_panel.grid_columnconfigure(0, weight=1)

        badge = tk.Label(
            form_panel,
            text="PharmaDesk",
            bg="#dbeafe",
            fg="#0f3d63",
            font=("Segoe UI Semibold", 10),
            padx=12,
            pady=6,
        )
        badge.grid(row=0, column=0, sticky="w")

        title = tk.Label(
            form_panel,
            text="Connexion",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI Semibold", 27),
        )
        title.grid(row=1, column=0, sticky="w", pady=(28, 6))

        subtitle = tk.Label(
            form_panel,
            text="Acces securise a votre espace de gestion officinale.",
            bg="#f8fafc",
            fg="#64748b",
            justify="left",
            font=("Segoe UI", 10),
        )
        subtitle.grid(row=2, column=0, sticky="w", pady=(0, 22))

        username_block, self.username_entry = self._build_input(
            form_panel,
            "Nom d'utilisateur",
            self.username_var,
        )
        username_block.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        password_block, self.password_entry = self._build_input(
            form_panel,
            "Mot de passe",
            self.password_var,
            show="*",
        )
        password_block.grid(row=4, column=0, sticky="ew", pady=(0, 18))

        login_button = tk.Button(
            form_panel,
            text="Se connecter",
            command=self._login,
            bg="#0f172a",
            fg="#ffffff",
            activebackground="#0b1220",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=10,
            cursor="hand2",
        )
        login_button.grid(row=5, column=0, sticky="ew")

        helper = tk.Label(
            form_panel,
            text="Compte initial: admin / admin123",
            bg="#f8fafc",
            fg="#64748b",
            font=("Segoe UI", 9),
        )
        helper.grid(row=6, column=0, sticky="w", pady=(18, 10))

        security_note = tk.Label(
            form_panel,
            text="Roles geres: administrateur, pharmacien, caissier",
            bg="#f8fafc",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        )
        security_note.grid(row=7, column=0, sticky="w")

        self._draw_art_panel(380, 460)

    def _build_input(
        self,
        parent: tk.Misc,
        label: str,
        variable: tk.Variable,
        show: str | None = None,
    ) -> tuple[tk.Frame, tk.Entry]:
        wrapper = tk.Frame(parent, bg="#f8fafc")
        wrapper.grid_columnconfigure(0, weight=1)

        tk.Label(
            wrapper,
            text=label,
            bg="#f8fafc",
            fg="#334155",
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        field = tk.Frame(wrapper, bg="#ffffff", highlightthickness=1, highlightbackground="#dbe2ea")
        field.grid(row=1, column=0, sticky="ew")
        field.grid_columnconfigure(0, weight=1)

        entry = tk.Entry(
            field,
            textvariable=variable,
            show=show or "",
            relief="flat",
            bd=0,
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0f172a",
            font=("Segoe UI", 10),
        )
        entry.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
        return wrapper, entry

    def _on_resize(self, event: tk.Event) -> None:
        self._last_size = (event.width, event.height)
        self._draw_background(event.width, event.height)

        card_width = min(max(event.width - 120, 760), 940)
        card_height = min(max(event.height - 110, 470), 540)
        self._card_size = (card_width, card_height)
        self.background.itemconfigure(self.card_window, width=card_width, height=card_height)
        self._update_card_position()

        left_width = max(int(card_width * 0.46), 320)
        self.art_panel.configure(width=left_width, height=card_height)
        self._draw_art_panel(left_width, card_height)

    def _draw_background(self, width: int, height: int) -> None:
        for item in self._background_items:
            self.background.delete(item)
        self._background_items.clear()
        self._background_glow_items.clear()
        self._background_glow_specs.clear()

        self.background.configure(bg="#061017")
        stripes = [
            ("#0a6d84", 0.0, 0.22),
            ("#084b66", 0.22, 0.48),
            ("#052d43", 0.48, 0.76),
            ("#02070b", 0.76, 1.0),
        ]
        for color, start, end in stripes:
            item = self.background.create_rectangle(width * start, 0, width * end, height, fill=color, outline="")
            self._background_items.append(item)

        glow_specs = [
            (-0.1, 0.05, 0.52, 1.02, "#0b7285", 0.0),
            (0.58, -0.1, 1.25, 0.8, "#12364c", 1.3),
            (0.08, 0.68, 0.72, 1.22, "#145f5c", 2.1),
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
        for item in self._art_items:
            self.art_panel.delete(item)
        self._art_items.clear()

        base_layers = [
            (0, 0, width, height, "#03090d"),
            (0, height * 0.45, width, height, "#06131c"),
            (0, 0, width, height * 0.38, "#071b28"),
        ]
        for x1, y1, x2, y2, color in base_layers:
            item = self.art_panel.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            self._art_items.append(item)

        bubble_specs = [
            (-width * 0.25, -height * 0.08, width * 0.5, height * 0.42, "#127ea9"),
            (width * 0.18, height * 0.12, width * 1.05, height * 0.96, "#0f5f86"),
            (-width * 0.12, height * 0.42, width * 0.84, height * 1.12, "#1d8b9a"),
            (width * 0.42, -height * 0.04, width * 1.08, height * 0.48, "#0f172a"),
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
            fill="#0c4a6e",
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
            fill="#082f49",
            outline="",
            smooth=True,
        )
        self._art_items.append(wave_two)

        swirl_specs = [
            (width * 0.08, height * 0.18, width * 0.86, height * 1.02, "#38bdf8", 20),
            (width * 0.12, height * 0.14, width * 0.92, height * 0.94, "#0ea5e9", 12),
            (width * 0.2, height * 0.1, width * 0.98, height * 0.82, "#022c43", 28),
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
            fill="#d8f1fb",
            outline="",
        )
        self._art_items.append(highlight)
        self._art_highlight_item = highlight
        self._art_highlight_bounds = (0.08, 0.08, 0.26, 0.18)

        title = self.art_panel.create_text(
            width * 0.12,
            height * 0.62,
            anchor="nw",
            text="Connectez votre\npharmacie",
            fill="#f8fafc",
            font=("Segoe UI Semibold", 26),
        )
        self._art_items.append(title)

        subtitle = self.art_panel.create_text(
            width * 0.12,
            height * 0.79,
            anchor="nw",
            width=width * 0.68,
            text="Pilotez les ventes, le stock et les rapports depuis un espace fiable et centralise.",
            fill="#dbeafe",
            font=("Segoe UI", 11),
        )
        self._art_items.append(subtitle)

    def _ensure_shadow_items(self) -> None:
        if self._shadow_items:
            for item in self._shadow_items:
                self.background.tag_lower(item, self.card_window)
            return

        outer_shadow = self.background.create_rectangle(0, 0, 0, 0, fill="#020817", outline="")
        inner_shadow = self.background.create_rectangle(0, 0, 0, 0, fill="#082032", outline="")
        self._shadow_items = [outer_shadow, inner_shadow]
        for item in self._shadow_items:
            self.background.tag_lower(item, self.card_window)

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
        center_y = (height / 2) + y_offset

        self.background.coords(self.card_window, center_x, center_y)
        self.background.itemconfigure(self.card_window, width=display_width, height=display_height)

        self._ensure_shadow_items()
        shadow_offsets = [(30, 32, 0.34), (18, 18, 0.16)]
        for item, (dx, dy, spread) in zip(self._shadow_items, shadow_offsets):
            spread_x = display_width * spread
            spread_y = display_height * (spread * 0.58)
            self.background.coords(
                item,
                center_x - (display_width / 2) + dx - spread_x * 0.12,
                center_y - (display_height / 2) + dy - spread_y * 0.12,
                center_x + (display_width / 2) + dx + spread_x,
                center_y + (display_height / 2) + dy + spread_y,
            )
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