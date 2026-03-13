from __future__ import annotations

import tkinter as tk
from datetime import datetime
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
        self.total_var = tk.StringVar(value=format_currency(0))
        self.invoice_text = tk.StringVar()
        self.cart: list[dict[str, float | int | str]] = []
        self.medicine_map: dict[str, dict[str, float | int | str]] = {}

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

        footer = ttk.Frame(self, style="Card.TFrame", padding=16)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, text="Total", style="Section.TLabel").pack(side="left")
        ttk.Label(footer, textvariable=self.total_var, font=("Segoe UI Semibold", 16)).pack(side="left", padx=(12, 0))
        ttk.Button(footer, text="Finaliser la vente", style="Primary.TButton", command=self.checkout).pack(side="right")
        ttk.Button(footer, text="Vider", style="Secondary.TButton", command=self.clear_cart).pack(side="right", padx=8)

        self.refresh()

    def refresh(self) -> None:
        medicines = [item for item in pharmacy_service.list_medicines() if int(item["quantity"]) > 0]
        self.medicine_map = {item["name"]: item for item in medicines}
        self.medicine_input.combobox.configure(values=list(self.medicine_map.keys()))

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

    def _render_cart(self) -> None:
        self.cart_table.clear()
        total = 0.0
        for item in self.cart:
            total += float(item["line_total"])
            self.cart_table.tree.insert(
                "",
                "end",
                values=(
                    item["name"],
                    item["quantity"],
                    f"{float(item['unit_price']):.2f}",
                    f"{float(item['line_total']):.2f}",
                ),
            )
        self.total_var.set(format_currency(total))

    def clear_cart(self) -> None:
        self.cart.clear()
        self._render_cart()

    def checkout(self) -> None:
        if not self.cart:
            messagebox.showwarning("Vente", "Le panier est vide.")
            return
        sale_number = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        pharmacy_service.create_sale(sale_number, self.payment_var.get(), self.current_user.id, self.cart)
        invoice = pharmacy_service.build_invoice(
            sale_number,
            self.current_user.full_name,
            self.payment_var.get(),
            self.cart,
        )
        self.clear_cart()
        self.refresh()
        self.on_sale_created()
        self._show_invoice(invoice)

    def _show_invoice(self, content: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Facture")
        dialog.geometry("480x420")
        text = tk.Text(dialog, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", content)
        text.configure(state="disabled")