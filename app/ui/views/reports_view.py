from __future__ import annotations

import subprocess
import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from app.services.auth_service import AuthenticatedUser
from app.services.pharmacy_service import pharmacy_service
from app.ui.widgets import TreeSection
from app.utils.currency import format_currency


class ReportsView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        intro = ttk.Frame(self, style="Card.TFrame", padding=16)
        intro.pack(fill="x")
        ttk.Label(intro, text="Rapports", style="Section.TLabel").pack(anchor="w")
        ttk.Label(intro, text="Suivi des ventes journalieres et alertes critiques de stock.", style="Subtitle.TLabel").pack(anchor="w", pady=(8, 0))
        ttk.Button(intro, text="Imprimer le rapport", style="Primary.TButton", command=self.print_report).pack(anchor="e", pady=(10, 0))

        ttk.Label(self, text="Rapport des ventes par jour", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.sales_table = TreeSection(self, ["date", "total"], ["Date", "Total"])
        self.sales_table.pack(fill="both", expand=True)

        ttk.Label(self, text="Alertes critiques", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.alerts_table = TreeSection(self, ["name", "quantity", "expiration_date", "status"], ["Medicament", "Stock", "Expiration", "Alerte"])
        self.alerts_table.pack(fill="both", expand=True)

        ttk.Label(self, text="Journal d'audit", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.audit_table = TreeSection(
            self,
            ["created_at", "user_name", "action", "entity_type", "details"],
            ["Date", "Utilisateur", "Action", "Cible", "Details"],
        )
        self.audit_table.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self) -> None:
        self.sales_table.clear()
        for row in pharmacy_service.get_sales_report():
            self.sales_table.tree.insert("", "end", values=(row["date"], format_currency(float(row["total"]))))

        self.alerts_table.clear()
        alerts = pharmacy_service.get_stock_alerts()
        for label, items in (("Stock faible", alerts["low_stock"]), ("Expire", alerts["expired"]), ("Expire bientot", alerts["expiring_soon"])):
            for item in items:
                self.alerts_table.tree.insert(
                    "",
                    "end",
                    values=(item["name"], item["quantity"], item["expiration_date"], label),
                )

        self.audit_table.clear()
        for entry in pharmacy_service.list_audit_logs(100):
            self.audit_table.tree.insert(
                "",
                "end",
                values=(
                    entry["created_at"],
                    entry.get("user_name") or "-",
                    entry["action"],
                    entry["entity_type"],
                    entry.get("details") or "",
                ),
            )

    def print_report(self) -> None:
        output = Path(tempfile.gettempdir()) / "pharmadesk_report_print.txt"
        output.write_text(self._build_report_text(), encoding="utf-8")
        subprocess.run(["notepad.exe", "/p", str(output)], check=False)
        pharmacy_service.record_audit(self.current_user.id, "imprimer", "rapport", f"Impression du rapport via {output}")

    def _build_report_text(self) -> str:
        lines = ["PHARMADESK - RAPPORT", "=" * 48, "Ventes par jour", "-"]
        sales_report = pharmacy_service.get_sales_report()
        if not sales_report:
            lines.append("Aucune vente enregistree.")
        else:
            for row in sales_report:
                lines.append(f"{row['date']} : {format_currency(float(row['total']))}")

        lines.extend(["", "Alertes critiques", "-"])
        alerts = pharmacy_service.get_stock_alerts()
        has_alert = False
        for label, items in (("Stock faible", alerts["low_stock"]), ("Expire", alerts["expired"]), ("Expire bientot", alerts["expiring_soon"])):
            for item in items:
                has_alert = True
                lines.append(f"[{label}] {item['name']} | stock={item['quantity']} | expiration={item['expiration_date']}")
        if not has_alert:
            lines.append("Aucune alerte critique.")
        lines.extend(["", "Journal d'audit recent", "-"])
        for entry in pharmacy_service.list_audit_logs(20):
            lines.append(
                f"{entry['created_at']} | {(entry.get('user_name') or '-')} | {entry['action']} | {entry['entity_type']} | {(entry.get('details') or '')}"
            )
        return "\n".join(lines)

