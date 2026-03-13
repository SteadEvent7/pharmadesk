from __future__ import annotations

from tkinter import Tk, ttk

from app.config import CONFIG


THEMES: dict[str, dict[str, str]] = {
    "light": {
        "label": "Clair standard",
        "bg": "#f4f7fb",
        "panel": "#ffffff",
        "panel_alt": "#eef4fb",
        "primary": "#0f766e",
        "primary_dark": "#115e59",
        "accent": "#f59e0b",
        "text": "#0f172a",
        "muted": "#64748b",
        "danger": "#dc2626",
        "ok": "#16a34a",
        "border": "#d8e1eb",
        "button_secondary": "#e2e8f0",
        "button_secondary_active": "#cbd5e1",
        "tree_heading": "#dce7f5",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a",
        "shell_topbar": "#0b5cab",
        "shell_sidebar": "#124d95",
        "shell_sidebar_active": "#1f73d0",
        "shell_sidebar_text": "#ffffff",
        "shell_sidebar_section": "#d8e8ff",
        "shell_topbar_button": "#d94841",
        "shell_topbar_button_active": "#bf3b35",
        "stock_low_bg": "#fde68a",
        "stock_ok_bg": "#dcfce7",
        "stock_empty_bg": "#fecaca",
    },
    "comfort": {
        "label": "Confort visuel",
        "bg": "#eef2ea",
        "panel": "#f8f5eb",
        "panel_alt": "#e7ebdd",
        "primary": "#3b6b5c",
        "primary_dark": "#2f5649",
        "accent": "#c88b3a",
        "text": "#21302b",
        "muted": "#5f6d67",
        "danger": "#b04a3f",
        "ok": "#4f7d4a",
        "border": "#cfd6c4",
        "button_secondary": "#dfe5d6",
        "button_secondary_active": "#ced6c4",
        "tree_heading": "#d9e2d0",
        "input_bg": "#fbf8f0",
        "input_fg": "#21302b",
        "shell_topbar": "#567a6d",
        "shell_sidebar": "#5f7d70",
        "shell_sidebar_active": "#759788",
        "shell_sidebar_text": "#f7fbf6",
        "shell_sidebar_section": "#dbe8de",
        "shell_topbar_button": "#b85f53",
        "shell_topbar_button_active": "#9f4f45",
        "stock_low_bg": "#ead8a2",
        "stock_ok_bg": "#d8ebd6",
        "stock_empty_bg": "#eac3bf",
    },
    "dark_soft": {
        "label": "Sombre doux",
        "bg": "#11161c",
        "panel": "#1a222c",
        "panel_alt": "#212b36",
        "primary": "#2f8f83",
        "primary_dark": "#267469",
        "accent": "#d39a4a",
        "text": "#eef4f7",
        "muted": "#aab7c2",
        "danger": "#df6b64",
        "ok": "#6eb072",
        "border": "#2c3946",
        "button_secondary": "#26313d",
        "button_secondary_active": "#31404f",
        "tree_heading": "#22303c",
        "input_bg": "#111922",
        "input_fg": "#eef4f7",
        "shell_topbar": "#18364f",
        "shell_sidebar": "#1a2b3a",
        "shell_sidebar_active": "#23445f",
        "shell_sidebar_text": "#f4f8fb",
        "shell_sidebar_section": "#b8cde0",
        "shell_topbar_button": "#b44f49",
        "shell_topbar_button_active": "#933f3b",
        "stock_low_bg": "#5a4f2b",
        "stock_ok_bg": "#244233",
        "stock_empty_bg": "#5b2d31",
    },
}

COLORS = dict(THEMES["light"])


def get_theme_options() -> dict[str, str]:
    return {palette["label"]: code for code, palette in THEMES.items()}


def get_theme_label(theme_code: str) -> str:
    return THEMES.get(theme_code, THEMES["light"])["label"]


def current_colors() -> dict[str, str]:
    return COLORS


def mix_colors(left: str, right: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    left_rgb = _hex_to_rgb(left)
    right_rgb = _hex_to_rgb(right)
    mixed = tuple(int((left_channel * (1 - ratio)) + (right_channel * ratio)) for left_channel, right_channel in zip(left_rgb, right_rgb))
    return _rgb_to_hex(mixed)


def shift_color(color: str, delta: int) -> str:
    red, green, blue = _hex_to_rgb(color)
    shifted = (
        _clamp(red + delta),
        _clamp(green + delta),
        _clamp(blue + delta),
    )
    return _rgb_to_hex(shifted)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    clean = color.lstrip("#")
    if len(clean) != 6:
        raise ValueError(f"Couleur hex invalide: {color}")
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)


def _rgb_to_hex(color: tuple[int, int, int]) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def apply_theme(root: Tk) -> ttk.Style:
    selected_theme = THEMES.get(CONFIG.theme_code, THEMES["light"])
    COLORS.clear()
    COLORS.update(selected_theme)

    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=COLORS["bg"])

    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["panel"], relief="flat")
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 20), foreground=COLORS["text"])
    style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=COLORS["muted"])
    style.configure("Section.TLabel", font=("Segoe UI Semibold", 12), foreground=COLORS["text"])
    style.configure("TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI", 10))
    style.map("TCheckbutton", background=[("active", COLORS["panel"])])
    style.configure("TEntry", fieldbackground=COLORS["input_bg"], foreground=COLORS["input_fg"], bordercolor=COLORS["border"])
    style.configure("TCombobox", fieldbackground=COLORS["input_bg"], foreground=COLORS["input_fg"], bordercolor=COLORS["border"], arrowsize=14)
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["input_bg"])], foreground=[("readonly", COLORS["input_fg"])])
    style.configure(
        "Primary.TButton",
        background=COLORS["primary"],
        foreground="#ffffff",
        padding=(12, 8),
        borderwidth=0,
        focuscolor=COLORS["primary"],
    )
    style.map("Primary.TButton", background=[("active", COLORS["primary_dark"])])
    style.configure(
        "Secondary.TButton",
        background=COLORS["button_secondary"],
        foreground=COLORS["text"],
        padding=(10, 8),
        borderwidth=0,
    )
    style.map("Secondary.TButton", background=[("active", COLORS["button_secondary_active"])])
    style.configure("Treeview", rowheight=28, font=("Segoe UI", 9), fieldbackground=COLORS["input_bg"], background=COLORS["input_bg"], foreground=COLORS["text"])
    style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background=COLORS["tree_heading"], foreground=COLORS["text"])
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI Semibold", 10))
    style.map("TNotebook.Tab", background=[("selected", COLORS["panel"])])
    style.configure("Horizontal.TProgressbar", troughcolor=COLORS["panel_alt"], background=COLORS["primary"], bordercolor=COLORS["border"], lightcolor=COLORS["primary"], darkcolor=COLORS["primary"])
    return style