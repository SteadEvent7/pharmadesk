from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.theme import COLORS


class MetricCard(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, value: str, color: str) -> None:
        super().__init__(parent, style="Card.TFrame", padding=16)
        stripe = tk.Frame(self, bg=color, width=6)
        stripe.pack(side="left", fill="y")
        content = ttk.Frame(self, style="Card.TFrame")
        content.pack(side="left", fill="both", expand=True, padx=(12, 0))
        ttk.Label(content, text=title, style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(content, text=value, font=("Segoe UI Semibold", 18), foreground=COLORS["text"]).pack(anchor="w", pady=(4, 0))


class LabeledEntry(ttk.Frame):
    def __init__(self, parent: tk.Misc, label: str, textvariable: tk.Variable, show: str | None = None) -> None:
        super().__init__(parent)
        ttk.Label(self, text=label).pack(anchor="w")
        entry = ttk.Entry(self, textvariable=textvariable, show=show or "")
        entry.pack(fill="x", pady=(4, 0))
        self.entry = entry


class LabeledCombobox(ttk.Frame):
    def __init__(self, parent: tk.Misc, label: str, textvariable: tk.Variable, values: list[str]) -> None:
        super().__init__(parent)
        ttk.Label(self, text=label).pack(anchor="w")
        combo = ttk.Combobox(self, textvariable=textvariable, values=values, state="readonly")
        combo.pack(fill="x", pady=(4, 0))
        self.combobox = combo


class TreeSection(ttk.Frame):
    def __init__(self, parent: tk.Misc, columns: list[str], headings: list[str]) -> None:
        super().__init__(parent, style="Card.TFrame", padding=12)
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for column, heading in zip(columns, headings):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=120, anchor="w")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def clear(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)