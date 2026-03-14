from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

from app.services.auth_service import AuthenticatedUser
from app.services.pharmacy_service import pharmacy_service
from app.ui.widgets import LabeledCombobox, LabeledEntry, TreeSection
from app.utils.currency import format_currency


class SalesView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser, on_sale_created) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        self.on_sale_created = on_sale_created
        self.medicine_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.payment_var = tk.StringVar(value="Especes")
        self.subtotal_var = tk.StringVar(value=format_currency(0))
        self.tax_var = tk.StringVar(value=format_currency(0))
        self.total_var = tk.StringVar(value=format_currency(0))
        self.received_amount_var = tk.StringVar()
        self.received_display_var = tk.StringVar(value=format_currency(0))
        self.change_var = tk.StringVar(value=format_currency(0))
        self.change_status_var = tk.StringVar(value="Monnaie a rendre")
        self.recent_invoice_var = tk.StringVar()
        self.invoice_text = tk.StringVar()
        self.cart: list[dict[str, float | int | str]] = []
        self.medicine_map: dict[str, dict[str, float | int | str]] = {}
        self.recent_invoice_map: dict[str, int] = {}

        self.received_amount_var.trace_add("write", lambda *_args: self._update_payment_summary())
        self.payment_var.trace_add("write", lambda *_args: self._update_payment_summary())

        top = ttk.Frame(self, style="Card.TFrame", padding=16)
        top.pack(fill="x")
        ttk.Label(top, text="Point de vente", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))
        self.medicine_input = LabeledCombobox(top, "Medicament", self.medicine_var, [])
        self.medicine_input.grid(row=1, column=0, sticky="ew", padx=6)
        quantity_input = LabeledEntry(top, "Quantite", self.quantity_var)
        quantity_input.grid(row=1, column=1, sticky="ew", padx=6)
        payment_input = LabeledCombobox(top, "Paiement", self.payment_var, ["Especes", "Carte", "Mobile Money"])
        payment_input.grid(row=1, column=2, sticky="ew", padx=6)
        ttk.Button(top, text="Ajouter au panier", style="Primary.TButton", command=self.add_to_cart).grid(row=1, column=3, sticky="e", padx=6, pady=(18, 0))
        for column in range(4):
            top.columnconfigure(column, weight=1)

        ttk.Label(self, text="Panier", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.cart_table = TreeSection(
            self,
            ["name", "quantity", "unit_price", "line_total"],
            ["Medicament", "Quantite", "Prix unitaire", "Sous-total"],
        )
        self.cart_table.pack(fill="both", expand=True)

        self.cart_table.tree.configure(height=9)

        footer = ttk.Frame(self, style="Card.TFrame", padding=14)
        footer.pack(fill="x", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=0)

        summary = ttk.Frame(footer, style="Card.TFrame")
        summary.grid(row=0, column=0, sticky="ew")
        ttk.Label(summary, text="Total HT", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.subtotal_var, font=("Segoe UI Semibold", 12)).grid(row=0, column=1, sticky="w", padx=(8, 14))
        ttk.Label(summary, text="Taxe", style="Subtitle.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Label(summary, textvariable=self.tax_var, font=("Segoe UI Semibold", 12)).grid(row=0, column=3, sticky="w", padx=(8, 14))
        ttk.Label(summary, text="Total final", style="Section.TLabel").grid(row=0, column=4, sticky="w")
        ttk.Label(summary, textvariable=self.total_var, font=("Segoe UI Semibold", 16)).grid(row=0, column=5, sticky="w", padx=(10, 0))
        ttk.Label(summary, text="Montant recu", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(summary, textvariable=self.received_amount_var, width=14).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(summary, text="Encaisse", style="Subtitle.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Label(summary, textvariable=self.received_display_var, font=("Segoe UI Semibold", 12)).grid(row=1, column=3, sticky="w", padx=(8, 14), pady=(8, 0))
        ttk.Label(summary, textvariable=self.change_status_var, style="Subtitle.TLabel").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Label(summary, textvariable=self.change_var, font=("Segoe UI Semibold", 12)).grid(row=1, column=5, sticky="w", padx=(8, 0), pady=(8, 0))
        for column in range(6):
            summary.columnconfigure(column, weight=0)
        summary.columnconfigure(6, weight=1)

        actions = ttk.Frame(footer, style="Card.TFrame")
        actions.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(16, 0))
        ttk.Button(actions, text="Vider", style="Secondary.TButton", command=self.clear_cart).pack(side="top", fill="x")
        ttk.Button(actions, text="Finaliser la vente", style="Primary.TButton", command=self.checkout).pack(side="top", fill="x", pady=(8, 0))

        recent_frame = ttk.Frame(footer, style="Card.TFrame")
        recent_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        recent_frame.columnconfigure(1, weight=1)
        ttk.Label(recent_frame, text="Facture recente", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w")
        self.recent_invoice_combo = ttk.Combobox(recent_frame, textvariable=self.recent_invoice_var, state="readonly")
        self.recent_invoice_combo.grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Button(recent_frame, text="Reimprimer", style="Secondary.TButton", command=self.reprint_recent_invoice).grid(row=0, column=2, sticky="e")

        self.refresh()

    def refresh(self) -> None:
        medicines = [item for item in pharmacy_service.list_medicines() if int(item["quantity"]) > 0]
        self.medicine_map = {item["name"]: item for item in medicines}
        self.medicine_input.combobox.configure(values=list(self.medicine_map.keys()))
        self._refresh_recent_invoices()

    def _refresh_recent_invoices(self) -> None:
        recent_invoices = pharmacy_service.get_recent_invoices()
        values: list[str] = []
        self.recent_invoice_map.clear()
        for invoice in recent_invoices:
            label = f"{invoice['sale_number']}  |  {invoice['sale_date'][:16]}  |  {format_currency(float(invoice['total_amount']))}"
            values.append(label)
            self.recent_invoice_map[label] = int(invoice["id"])
        self.recent_invoice_combo.configure(values=values)
        self.recent_invoice_var.set(values[0] if values else "")

    def add_to_cart(self) -> None:
        medicine = self.medicine_map.get(self.medicine_var.get().strip())
        if not medicine:
            messagebox.showwarning("Vente", "Selectionnez un medicament en stock.")
            return
        try:
            quantity = int(self.quantity_var.get())
        except ValueError:
            messagebox.showerror("Vente", "Quantite invalide.")
            return
        if quantity <= 0 or quantity > int(medicine["quantity"]):
            messagebox.showerror("Vente", "Quantite demandee indisponible.")
            return

        alerts = self._collect_medicine_alerts(medicine)
        if alerts and not messagebox.askyesno("Alerte vente", "\n\n".join(alerts) + "\n\nVoulez-vous continuer ?"):
            return

        unit_price = float(medicine["sale_price"])
        line_total = unit_price * quantity
        self.cart.append(
            {
                "medicine_id": int(medicine["id"]),
                "name": str(medicine["name"]),
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )
        self._render_cart()

    def _collect_medicine_alerts(self, medicine: dict[str, float | int | str]) -> list[str]:
        alerts: list[str] = []
        purchase_price = float(medicine["purchase_price"])
        sale_price = float(medicine["sale_price"])
        if sale_price < purchase_price:
            alerts.append(
                f"Le prix de vente de {medicine['name']} est inferieur au prix d'achat ({format_currency(sale_price)} < {format_currency(purchase_price)})."
            )

        expiration_date = date.fromisoformat(str(medicine["expiration_date"]))
        remaining_days = (expiration_date - date.today()).days
        if remaining_days < 0:
            alerts.append(f"Le produit {medicine['name']} est deja perime depuis le {expiration_date.isoformat()}.")
        elif expiration_date <= date.today() + timedelta(days=pharmacy_service.EXPIRING_SOON_DAYS):
            alerts.append(
                f"Le produit {medicine['name']} expire bientot ({expiration_date.isoformat()}, dans {remaining_days} jour(s))."
            )
        return alerts

    def _render_cart(self) -> None:
        self.cart_table.clear()
        totals = pharmacy_service.calculate_sale_totals(self.cart)
        for item in self.cart:
            self.cart_table.tree.insert(
                "",
                "end",
                values=(
                    item["name"],
                    item["quantity"],
                    format_currency(float(item["unit_price"])),
                    format_currency(float(item["line_total"])),
                ),
            )
        self.subtotal_var.set(format_currency(totals["subtotal"]))
        self.tax_var.set(format_currency(totals["tax_amount"]))
        self.total_var.set(format_currency(totals["total"]))
        self._update_payment_summary()

    def clear_cart(self) -> None:
        self.cart.clear()
        self.received_amount_var.set("")
        self._render_cart()

    def _parse_amount(self, raw_value: str) -> float | None:
        value = raw_value.strip().replace(" ", "").replace(",", ".")
        if not value:
            return 0.0
        try:
            amount = float(value)
        except ValueError:
            return None
        if amount < 0:
            return None
        return amount

    def _current_total(self) -> float:
        return pharmacy_service.calculate_sale_totals(self.cart)["total"]

    def _update_payment_summary(self) -> None:
        totals = pharmacy_service.calculate_sale_totals(self.cart)
        total = totals["total"]
        if self.payment_var.get() != "Especes":
            self.received_display_var.set(format_currency(total))
            self.change_status_var.set("Monnaie a rendre")
            self.change_var.set("Non applicable")
            return

        amount_received = self._parse_amount(self.received_amount_var.get())
        if amount_received is None:
            self.received_display_var.set("-")
            self.change_status_var.set("Montant invalide")
            self.change_var.set("-")
            return

        self.received_display_var.set(format_currency(amount_received))
        difference = amount_received - total
        if difference >= 0:
            self.change_status_var.set("Monnaie a rendre")
            self.change_var.set(format_currency(difference))
            return

        self.change_status_var.set("Reste a payer")
        self.change_var.set(format_currency(abs(difference)))

    def checkout(self) -> None:
        if not self.cart:
            messagebox.showwarning("Vente", "Le panier est vide.")
            return
        total = self._current_total()
        amount_received: float | None = None
        if self.payment_var.get() == "Especes":
            amount_received = self._parse_amount(self.received_amount_var.get())
            if amount_received is None:
                messagebox.showerror("Vente", "Le montant recu est invalide.")
                return
            if amount_received < total:
                messagebox.showwarning("Vente", "Le montant recu est inferieur au total de la vente.")
                return
        sale_number = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        pharmacy_service.create_sale(sale_number, self.payment_var.get(), self.current_user.id, self.cart, received_amount=amount_received)
        invoice = pharmacy_service.build_invoice(
            sale_number,
            self.current_user.full_name,
            self.payment_var.get(),
            self.cart,
            received_amount=amount_received,
        )
        self.clear_cart()
        self.refresh()
        self.on_sale_created()
        self._show_invoice(invoice)

    def reprint_recent_invoice(self) -> None:
        sale_id = self.recent_invoice_map.get(self.recent_invoice_var.get())
        if not sale_id:
            messagebox.showwarning("Facturation", "Aucune facture recente disponible.")
            return
        printed = pharmacy_service.print_invoice(sale_id)
        pharmacy_service.record_audit(self.current_user.id, "imprimer", "facture", f"Reimpression rapide facture {sale_id} via {printed}", sale_id)
        messagebox.showinfo("Facturation", f"Impression envoyee via: {printed}")

    def _show_invoice(self, content: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Facture")
        dialog.geometry("480x420")
        text = tk.Text(dialog, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", content)
        text.configure(state="disabled")