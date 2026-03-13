from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class PlaceholderView(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, message: str) -> None:
        super().__init__(parent, padding=18)
        card = ttk.Frame(self, style="Card.TFrame", padding=24)
        card.pack(fill="both", expand=True)
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor="w")
        ttk.Label(card, text=message, style="Subtitle.TLabel", wraplength=760, justify="left").pack(anchor="w", pady=(10, 0))