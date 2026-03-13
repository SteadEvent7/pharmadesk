from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.auth_service import AuthenticatedUser
from app.services.pharmacy_service import pharmacy_service
from app.ui.widgets import LabeledCombobox, LabeledEntry, TreeSection


class UsersView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        self.selected_id: int | None = None
        self.full_name_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.role_var = tk.StringVar(value="pharmacien")
        self.active_var = tk.StringVar(value="Oui")

        form = ttk.Frame(self, style="Card.TFrame", padding=16)
        form.pack(fill="x")
        ttk.Label(form, text="Utilisateur", style="Section.TLabel").grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 12))
        LabeledEntry(form, "Nom complet", self.full_name_var).grid(row=1, column=0, sticky="ew", padx=6)
        LabeledEntry(form, "Nom d'utilisateur", self.username_var).grid(row=1, column=1, sticky="ew", padx=6)
        LabeledEntry(form, "Mot de passe", self.password_var, show="*").grid(row=1, column=2, sticky="ew", padx=6)
        LabeledCombobox(form, "Role", self.role_var, ["administrateur", "pharmacien", "caissier"]).grid(row=1, column=3, sticky="ew", padx=6)
        LabeledCombobox(form, "Actif", self.active_var, ["Oui", "Non"]).grid(row=1, column=4, sticky="ew", padx=6)
        for column in range(5):
            form.columnconfigure(column, weight=1)

        actions = ttk.Frame(form, style="Card.TFrame")
        actions.grid(row=2, column=0, columnspan=5, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Nouveau", style="Secondary.TButton", command=self.reset_form).pack(side="left", padx=4)
        ttk.Button(actions, text="Enregistrer", style="Primary.TButton", command=self.save_user).pack(side="left", padx=4)
        ttk.Button(actions, text="Supprimer", style="Secondary.TButton", command=self.delete_user).pack(side="left", padx=4)

        self.table = TreeSection(
            self,
            ["id", "full_name", "username", "role", "is_active", "created_at"],
            ["ID", "Nom", "Utilisateur", "Role", "Actif", "Creation"],
        )
        self.table.pack(fill="both", expand=True, pady=(12, 0))
        self.table.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.refresh()

    def refresh(self) -> None:
        self.table.clear()
        for user in pharmacy_service.list_users():
            self.table.tree.insert(
                "",
                "end",
                iid=str(user["id"]),
                values=(
                    user["id"],
                    user["full_name"],
                    user["username"],
                    user["role"],
                    "Oui" if int(user["is_active"]) else "Non",
                    user["created_at"],
                ),
            )

    def reset_form(self) -> None:
        self.selected_id = None
        for variable in (self.full_name_var, self.username_var, self.password_var):
            variable.set("")
        self.role_var.set("pharmacien")
        self.active_var.set("Oui")

    def _on_select(self, _event=None) -> None:
        selected = self.table.tree.selection()
        if not selected:
            return
        self.selected_id = int(selected[0])
        values = self.table.tree.item(selected[0], "values")
        self.full_name_var.set(values[1])
        self.username_var.set(values[2])
        self.password_var.set("")
        self.role_var.set(values[3])
        self.active_var.set(values[4])

    def save_user(self) -> None:
        if not self.full_name_var.get().strip() or not self.username_var.get().strip():
            messagebox.showwarning("Utilisateur", "Nom et identifiant sont obligatoires.")
            return
        if not self.selected_id and not self.password_var.get().strip():
            messagebox.showwarning("Utilisateur", "Le mot de passe est obligatoire a la creation.")
            return
        pharmacy_service.save_user(
            self.selected_id,
            {
                "full_name": self.full_name_var.get().strip(),
                "username": self.username_var.get().strip(),
                "password": self.password_var.get().strip(),
                "role": self.role_var.get().strip(),
                "is_active": 1 if self.active_var.get() == "Oui" else 0,
            },
            self.current_user.id,
        )
        self.refresh()
        self.reset_form()

    def delete_user(self) -> None:
        if not self.selected_id:
            return
        if not messagebox.askyesno("Suppression", "Supprimer cet utilisateur ?"):
            return
        pharmacy_service.delete_user(self.selected_id, self.current_user.id)
        self.refresh()
        self.reset_form()