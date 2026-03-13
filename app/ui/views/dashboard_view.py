from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.services.pharmacy_service import pharmacy_service
from app.ui.theme import COLORS
from app.ui.widgets import MetricCard, TreeSection
from app.utils.currency import format_currency


class DashboardView(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=18)
        self.period_var = tk.StringVar(value="12 mois")
        self.chart_data: list[dict[str, object]] = []
        self.metrics_frame = ttk.Frame(self)
        self.metrics_frame.pack(fill="x")

        controls = ttk.Frame(self, style="Card.TFrame", padding=12)
        controls.pack(fill="x", pady=(14, 0))
        ttk.Label(controls, text="Periode", style="Subtitle.TLabel").pack(side="left")
        self.period_combo = ttk.Combobox(
            controls,
            textvariable=self.period_var,
            state="readonly",
            values=["3 mois", "6 mois", "12 mois"],
        )
        self.period_combo.pack(side="left", padx=(10, 8))
        ttk.Button(controls, text="Actualiser", style="Primary.TButton", command=self.refresh).pack(side="left")

        lower_panel = ttk.Frame(self)
        lower_panel.pack(fill="both", expand=True, pady=(14, 0))
        lower_panel.columnconfigure(0, weight=3)
        lower_panel.columnconfigure(1, weight=2)
        lower_panel.rowconfigure(0, weight=1)

        trend_card = ttk.Frame(lower_panel, style="Card.TFrame", padding=16)
        trend_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(trend_card, text="Tendance des ventes", style="Section.TLabel").pack(anchor="w")
        ttk.Label(trend_card, text="Evolution mensuelle sur la periode selectionnee.", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 10))
        self.chart_canvas = tk.Canvas(trend_card, bg="#ffffff", highlightthickness=0, height=320)
        self.chart_canvas.pack(fill="both", expand=True)
        self.chart_canvas.bind("<Configure>", self._on_chart_resize)

        ranking_card = ttk.Frame(lower_panel, style="Card.TFrame", padding=16)
        ranking_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(ranking_card, text="Classement des ventes", style="Section.TLabel").pack(anchor="w")
        ttk.Label(ranking_card, text="Produits les plus vendus sur la periode.", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 10))
        self.ranking_section = TreeSection(
            ranking_card,
            ["name", "quantity"],
            ["Produit", "Quantite vendue"],
        )
        self.ranking_section.pack(fill="both", expand=True)
        self.ranking_section.tree.column("name", width=220)
        self.ranking_section.tree.column("quantity", width=120, anchor="center")
        self.refresh()

    def refresh(self) -> None:
        for child in self.metrics_frame.winfo_children():
            child.destroy()
        metrics = pharmacy_service.get_dashboard_metrics()
        cards = [
            ("Medicaments", str(metrics["medicines_total"]), COLORS["primary"]),
            ("Fournisseurs", str(metrics["suppliers_total"]), COLORS["accent"]),
            ("Utilisateurs", str(metrics["users_total"]), COLORS["ok"]),
            ("Ventes du jour", format_currency(float(metrics["sales_total_today"])), COLORS["primary_dark"]),
            ("Stock faible", str(metrics["low_stock_total"]), COLORS["danger"]),
            ("Expires", str(metrics["expired_total"]), COLORS["danger"]),
        ]
        for index, (title, value, color) in enumerate(cards):
            card = MetricCard(self.metrics_frame, title, value, color)
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=6, pady=6)
            self.metrics_frame.columnconfigure(index % 3, weight=1)

        months = int(self.period_var.get().split()[0])
        self.chart_data = pharmacy_service.get_sales_trend(months)
        self._draw_trend_chart()

        self.ranking_section.clear()
        for row in pharmacy_service.get_top_selling_products(months):
            self.ranking_section.tree.insert("", "end", values=(row["name"], row["quantity"]))

    def _on_chart_resize(self, _event: tk.Event) -> None:
        self._draw_trend_chart()

    def _draw_trend_chart(self) -> None:
        canvas = self.chart_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 260)
        left = 48
        right = width - 22
        top = 18
        bottom = height - 38

        canvas.create_line(left, top, left, bottom, fill="#c7d2e3", width=1)
        canvas.create_line(left, bottom, right, bottom, fill="#c7d2e3", width=1)

        if not self.chart_data:
            canvas.create_text(width / 2, height / 2, text="Aucune vente sur la periode.", fill="#64748b", font=("Segoe UI", 11))
            return

        max_total = max(float(item["total"]) for item in self.chart_data)
        if max_total <= 0:
            max_total = 1.0

        steps = 4
        for step in range(steps + 1):
            ratio = step / steps
            y = bottom - ((bottom - top) * ratio)
            value = max_total * ratio
            canvas.create_line(left, y, right, y, fill="#eef2f7", width=1)
            canvas.create_text(left - 10, y, text=f"{value:.0f}", fill="#94a3b8", font=("Segoe UI", 8))

        count = len(self.chart_data)
        x_gap = (right - left) / max(count - 1, 1)
        points: list[float] = []
        for index, item in enumerate(self.chart_data):
            total = float(item["total"])
            x = left + (index * x_gap)
            y = bottom - ((total / max_total) * (bottom - top))
            points.extend([x, y])
            canvas.create_text(x, bottom + 16, text=str(item["label"]), fill="#64748b", font=("Segoe UI", 9))
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#2f80ed", outline="#2f80ed")

        if len(points) >= 4:
            canvas.create_line(*points, fill="#2f80ed", width=3, smooth=True)
        elif len(points) == 2:
            x, y = points
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#2f80ed", outline="#2f80ed")