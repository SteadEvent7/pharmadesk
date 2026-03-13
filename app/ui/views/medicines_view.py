from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.auth_service import AuthenticatedUser
from app.services.pharmacy_service import pharmacy_service
from app.ui.widgets import LabeledCombobox, LabeledEntry, TreeSection
from tkcalendar import DateEntry


class MedicinesView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser, on_data_changed) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        self.is_admin = current_user.role == "administrateur"
        self.on_data_changed = on_data_changed
        self.selected_id: int | None = None
        self.search_var = tk.StringVar()
        self.code_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.purchase_var = tk.StringVar(value="0")
        self.sale_var = tk.StringVar(value="0")
        self.quantity_var = tk.StringVar(value="0")
        self.expiration_var = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.supplier_map: dict[str, int] = {}

        search_box = ttk.Frame(self, style="Card.TFrame", padding=12)
        search_box.pack(fill="x")
        ttk.Label(search_box, text="Recherche", style="Section.TLabel").pack(anchor="w")
        ttk.Entry(search_box, textvariable=self.search_var).pack(side="left", fill="x", expand=True, pady=(8, 0))
        ttk.Button(search_box, text="Chercher", style="Secondary.TButton", command=self.refresh).pack(side="left", padx=8, pady=(8, 0))

        form = ttk.Frame(self, style="Card.TFrame", padding=16)
        form.pack(fill="x", pady=12)
        ttk.Label(form, text="Medicament", style="Section.TLabel").grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 12))

        entries = [
            ("Code", self.code_var),
            ("Nom", self.name_var),
            ("Categorie", self.category_var),
            ("Prix achat", self.purchase_var),
            ("Prix vente", self.sale_var),
            ("Quantite", self.quantity_var),
            ("Description", self.description_var),
        ]
        for index, (label, variable) in enumerate(entries):
            widget = LabeledEntry(form, label, variable)
            widget.grid(row=1 + index // 4, column=index % 4, sticky="ew", padx=6, pady=4)
            form.columnconfigure(index % 4, weight=1)

        expiration_wrap = ttk.Frame(form)
        expiration_wrap.grid(row=2, column=2, sticky="ew", padx=6, pady=4)
        ttk.Label(expiration_wrap, text="Expiration").pack(anchor="w")
        self.expiration_picker = DateEntry(expiration_wrap, textvariable=self.expiration_var, width=18, date_pattern="yyyy-mm-dd", locale="en_US")
        self.expiration_picker.pack(fill="x", pady=(4, 0))

        self.supplier_input = LabeledCombobox(form, "Fournisseur", self.supplier_var, [])
        self.supplier_input.grid(row=3, column=0, sticky="ew", padx=6, pady=4)

        actions = ttk.Frame(form, style="Card.TFrame")
        actions.grid(row=3, column=1, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Nouveau", style="Secondary.TButton", command=self.reset_form).pack(side="left", padx=4)
        ttk.Button(actions, text="Enregistrer", style="Primary.TButton", command=self.save_medicine).pack(side="left", padx=4)
        self.delete_button = ttk.Button(actions, text="Supprimer", style="Secondary.TButton", command=self.delete_medicine)
        self.delete_button.pack(side="left", padx=4)
        if not self.is_admin:
            self.delete_button.state(["disabled"])

        self.table = TreeSection(
            self,
            ["id", "code", "name", "category", "sale_price", "quantity", "expiration_date", "supplier_name"],
            ["ID", "Code", "Nom", "Categorie", "Prix vente", "Stock", "Expiration", "Fournisseur"],
        )
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.refresh_suppliers()
        self.refresh()

    def refresh_suppliers(self) -> None:
        suppliers = pharmacy_service.list_suppliers()
        self.supplier_map = {supplier["name"]: int(supplier["id"]) for supplier in suppliers}
        self.supplier_input.combobox.configure(values=list(self.supplier_map.keys()))

    def refresh(self) -> None:
        self.table.clear()
        for medicine in pharmacy_service.list_medicines(self.search_var.get().strip()):
            self.table.tree.insert(
                "",
                "end",
                iid=str(medicine["id"]),
                values=(
                    medicine["id"],
                    medicine["code"],
                    medicine["name"],
                    medicine["category"],
                    f"{float(medicine['sale_price']):.2f}",
                    medicine["quantity"],
                    medicine["expiration_date"],
                    medicine.get("supplier_name") or "-",
                ),
            )

    def reset_form(self) -> None:
        self.selected_id = None
        for variable in (
            self.code_var,
            self.name_var,
            self.category_var,
            self.purchase_var,
            self.sale_var,
            self.quantity_var,
            self.expiration_var,
            self.supplier_var,
            self.description_var,
        ):
            variable.set("")
        self.purchase_var.set("0")
        self.sale_var.set("0")
        self.quantity_var.set("0")

    def _on_select(self, _event=None) -> None:
        selected = self.table.tree.selection()
        if not selected:
            return
        self.selected_id = int(selected[0])
        medicine = next(
            item for item in pharmacy_service.list_medicines() if int(item["id"]) == self.selected_id
        )
        self.code_var.set(medicine["code"])
        self.name_var.set(medicine["name"])
        self.category_var.set(medicine["category"])
        self.purchase_var.set(str(medicine["purchase_price"]))
        self.sale_var.set(str(medicine["sale_price"]))
        self.quantity_var.set(str(medicine["quantity"]))
        self.expiration_var.set(medicine["expiration_date"])
        self.supplier_var.set(medicine.get("supplier_name") or "")
        self.description_var.set(medicine.get("description") or "")

    def save_medicine(self) -> None:
        try:
            payload = {
                "code": self.code_var.get().strip(),
                "name": self.name_var.get().strip(),
                "category": self.category_var.get().strip(),
                "purchase_price": float(self.purchase_var.get() or 0),
                "sale_price": float(self.sale_var.get() or 0),
                "quantity": int(self.quantity_var.get() or 0),
                "expiration_date": self.expiration_var.get().strip(),
                "supplier_id": self.supplier_map.get(self.supplier_var.get().strip()),
                "description": self.description_var.get().strip(),
            }
        except ValueError:
            messagebox.showerror("Medicament", "Prix ou quantite invalides.")
            return
        if not payload["code"] or not payload["name"] or not payload["expiration_date"]:
            messagebox.showwarning("Medicament", "Code, nom et date d'expiration sont obligatoires.")
            return
        pharmacy_service.save_medicine(self.selected_id, payload, self.current_user.id)
        self.refresh()
        self.reset_form()
        self.on_data_changed()

    def delete_medicine(self) -> None:
        if not self.is_admin:
            messagebox.showerror("Medicament", "Seul l'administrateur peut supprimer un produit.")
            return
        if not self.selected_id:
            return
        if not messagebox.askyesno("Suppression", "Supprimer ce medicament ?"):
            return
        pharmacy_service.delete_medicine(self.selected_id, self.current_user.id)
        self.refresh()
        self.reset_form()
        self.on_data_changed()