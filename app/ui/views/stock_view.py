from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.auth_service import AuthenticatedUser
from app.config import CONFIG
from app.services.pharmacy_service import pharmacy_service
from app.ui.theme import COLORS
from app.ui.widgets import LabeledCombobox, LabeledEntry, TreeSection


class StockView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser, on_data_changed) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        self.on_data_changed = on_data_changed
        self.medicine_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.reason_var = tk.StringVar()
        self.type_var = tk.StringVar(value="entree")
        self.medicine_map: dict[str, int] = {}

        form = ttk.Frame(self, style="Card.TFrame", padding=16)
        form.pack(fill="x")
        ttk.Label(form, text="Mouvement de stock", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))
        self.medicine_input = LabeledCombobox(form, "Medicament", self.medicine_var, [])
        self.medicine_input.grid(row=1, column=0, sticky="ew", padx=6)
        quantity_input = LabeledEntry(form, "Quantite", self.quantity_var)
        quantity_input.grid(row=1, column=1, sticky="ew", padx=6)
        reason_input = LabeledEntry(form, "Motif", self.reason_var)
        reason_input.grid(row=1, column=2, sticky="ew", padx=6)
        type_input = LabeledCombobox(form, "Type", self.type_var, ["entree", "sortie"])
        type_input.grid(row=1, column=3, sticky="ew", padx=6)
        for column in range(4):
            form.columnconfigure(column, weight=1)
        ttk.Button(form, text="Valider", style="Primary.TButton", command=self.apply_movement).grid(row=2, column=3, sticky="e", pady=(12, 0))

        ttk.Label(self, text="Etat du stock", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.inventory_table = TreeSection(
            self,
            ["code", "name", "category", "quantity", "expiration_date", "supplier_name"],
            ["Code", "Medicament", "Categorie", "Stock", "Expiration", "Fournisseur"],
        )
        self.inventory_table.pack(fill="both", expand=True)
        self.inventory_table.tree.column("code", width=110)
        self.inventory_table.tree.column("name", width=220)
        self.inventory_table.tree.column("category", width=140)
        self.inventory_table.tree.column("quantity", width=90, anchor="center")
        self.inventory_table.tree.column("expiration_date", width=120)
        self.inventory_table.tree.column("supplier_name", width=180)
        self.inventory_table.tree.tag_configure("stock_low", background=COLORS["stock_low_bg"], foreground=COLORS["text"])
        self.inventory_table.tree.tag_configure("stock_ok", background=COLORS["stock_ok_bg"], foreground=COLORS["text"])
        self.inventory_table.tree.tag_configure("stock_empty", background=COLORS["stock_empty_bg"], foreground=COLORS["text"])

        ttk.Label(self, text="Historique des mouvements", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.movements_table = TreeSection(
            self,
            ["created_at", "medicine_code", "medicine_name", "movement_type", "quantity", "reason"],
            ["Date", "Code", "Medicament", "Type", "Quantite", "Motif"],
        )
        self.movements_table.pack(fill="both", expand=True)

        ttk.Label(self, text="Alertes stock et expiration", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.alerts_table = TreeSection(
            self,
            ["name", "quantity", "expiration_date", "status"],
            ["Medicament", "Stock", "Expiration", "Alerte"],
        )
        self.alerts_table.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self) -> None:
        medicines = pharmacy_service.list_medicines()
        self.medicine_map = {item["name"]: int(item["id"]) for item in medicines}
        self.medicine_input.combobox.configure(values=list(self.medicine_map.keys()))

        self.inventory_table.clear()
        for medicine in medicines:
            quantity = int(medicine["quantity"])
            tag = "stock_empty" if quantity <= 0 else "stock_low" if quantity <= CONFIG.low_stock_threshold else "stock_ok"
            self.inventory_table.tree.insert(
                "",
                "end",
                iid=f"stock-{medicine['id']}",
                values=(
                    medicine["code"],
                    medicine["name"],
                    medicine["category"],
                    medicine["quantity"],
                    medicine["expiration_date"],
                    medicine.get("supplier_name") or "-",
                ),
                tags=(tag,),
            )

        self.movements_table.clear()
        for movement in pharmacy_service.get_stock_movements():
            self.movements_table.tree.insert(
                "",
                "end",
                values=(
                    movement["created_at"],
                    movement["medicine_code"],
                    movement["medicine_name"],
                    movement["movement_type"],
                    movement["quantity"],
                    movement.get("reason") or "-",
                ),
            )

        alerts = pharmacy_service.get_stock_alerts()
        rows = [(item, "Stock faible") for item in alerts["low_stock"]]
        rows.extend((item, "Expire") for item in alerts["expired"])
        rows.extend((item, "Expire bientot") for item in alerts["expiring_soon"])
        self.alerts_table.clear()
        seen: set[int] = set()
        for medicine, status in rows:
            if int(medicine["id"]) in seen:
                continue
            seen.add(int(medicine["id"]))
            self.alerts_table.tree.insert(
                "",
                "end",
                values=(medicine["name"], medicine["quantity"], medicine["expiration_date"], status),
            )

    def apply_movement(self) -> None:
        medicine_id = self.medicine_map.get(self.medicine_var.get().strip())
        if not medicine_id:
            messagebox.showwarning("Stock", "Selectionnez un medicament.")
            return
        try:
            quantity = int(self.quantity_var.get())
        except ValueError:
            messagebox.showerror("Stock", "Quantite invalide.")
            return
        try:
            pharmacy_service.adjust_stock(medicine_id, quantity, self.type_var.get(), self.reason_var.get().strip(), self.current_user.id)
        except ValueError as error:
            messagebox.showerror("Stock", str(error))
            return
        self.quantity_var.set("1")
        self.reason_var.set("")
        self.refresh()
        self.on_data_changed()