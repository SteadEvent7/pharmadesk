from __future__ import annotations

from tkinter import Tk, ttk


COLORS = {
    "bg": "#f4f7fb",
    "panel": "#ffffff",
    "primary": "#0f766e",
    "primary_dark": "#115e59",
    "accent": "#f59e0b",
    "text": "#0f172a",
    "muted": "#64748b",
    "danger": "#dc2626",
    "ok": "#16a34a",
}


def apply_theme(root: Tk) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=COLORS["bg"])

    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["panel"], relief="flat")
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 20), foreground=COLORS["text"])
    style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=COLORS["muted"])
    style.configure("Section.TLabel", font=("Segoe UI Semibold", 12), foreground=COLORS["text"])
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
        background="#e2e8f0",
        foreground=COLORS["text"],
        padding=(10, 8),
        borderwidth=0,
    )
    style.map("Secondary.TButton", background=[("active", "#cbd5e1")])
    style.configure("Treeview", rowheight=28, font=("Segoe UI", 9), fieldbackground="#ffffff")
    style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#dce7f5")
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI Semibold", 10))
    style.map("TNotebook.Tab", background=[("selected", COLORS["panel"])])
    return style