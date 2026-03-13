from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.auth_service import AuthenticatedUser
from app.services.pharmacy_service import pharmacy_service
from app.ui.widgets import LabeledEntry, TreeSection


class SuppliersView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser, on_data_changed) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        self.on_data_changed = on_data_changed
        self.selected_id: int | None = None
        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self.email_var = tk.StringVar()

        form = ttk.Frame(self, style="Card.TFrame", padding=16)
        form.pack(fill="x")
        ttk.Label(form, text="Fournisseur", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))
        fields = [
            ("Nom", self.name_var),
            ("Telephone", self.phone_var),
            ("Adresse", self.address_var),
            ("Email", self.email_var),
        ]
        for index, (label, variable) in enumerate(fields):
            widget = LabeledEntry(form, label, variable)
            widget.grid(row=1, column=index, sticky="ew", padx=6)
            form.columnconfigure(index, weight=1)

        actions = ttk.Frame(form, style="Card.TFrame")
        actions.grid(row=2, column=0, columnspan=4, sticky="e", pady=(14, 0))
        ttk.Button(actions, text="Nouveau", style="Secondary.TButton", command=self.reset_form).pack(side="left", padx=4)
        ttk.Button(actions, text="Enregistrer", style="Primary.TButton", command=self.save_supplier).pack(side="left", padx=4)
        ttk.Button(actions, text="Supprimer", style="Secondary.TButton", command=self.delete_supplier).pack(side="left", padx=4)

        ttk.Label(self, text="Liste des fournisseurs", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.table = TreeSection(self, ["id", "name", "phone", "address", "email"], ["ID", "Nom", "Telephone", "Adresse", "Email"])
        self.table.pack(fill="both", expand=True)
        self.table.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.refresh()

    def refresh(self) -> None:
        self.table.clear()
        for supplier in pharmacy_service.list_suppliers():
            self.table.tree.insert(
                "",
                "end",
                iid=str(supplier["id"]),
                values=(supplier["id"], supplier["name"], supplier["phone"], supplier["address"], supplier["email"]),
            )

    def reset_form(self) -> None:
        self.selected_id = None
        for variable in (self.name_var, self.phone_var, self.address_var, self.email_var):
            variable.set("")

    def _on_select(self, _event=None) -> None:
        selected = self.table.tree.selection()
        if not selected:
            return
        self.selected_id = int(selected[0])
        values = self.table.tree.item(selected[0], "values")
        self.name_var.set(values[1])
        self.phone_var.set(values[2])
        self.address_var.set(values[3])
        self.email_var.set(values[4])

    def save_supplier(self) -> None:
        if not self.name_var.get().strip():
            messagebox.showwarning("Fournisseur", "Le nom est obligatoire.")
            return
        pharmacy_service.save_supplier(
            self.selected_id,
            {
                "name": self.name_var.get().strip(),
                "phone": self.phone_var.get().strip(),
                "address": self.address_var.get().strip(),
                "email": self.email_var.get().strip(),
            },
            self.current_user.id,
        )
        self.refresh()
        self.reset_form()
        self.on_data_changed()

    def delete_supplier(self) -> None:
        if not self.selected_id:
            return
        if not messagebox.askyesno("Suppression", "Supprimer ce fournisseur ?"):
            return
        pharmacy_service.delete_supplier(self.selected_id, self.current_user.id)
        self.refresh()
        self.reset_form()
        self.on_data_changed()