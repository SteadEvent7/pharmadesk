from __future__ import annotations

import secrets
import string
import tkinter as tk
from tkinter import messagebox, ttk

from app import APP_NAME
from app.services.auth_service import AuthenticatedUser, DEFAULT_DELIVERED_PASSWORD, auth_service


class ForcePasswordChangeView(ttk.Frame):
    def __init__(self, parent: tk.Misc, user: AuthenticatedUser, on_success, on_cancel) -> None:
        super().__init__(parent, padding=24)
        self.user = user
        self.on_success = on_success
        self.on_cancel = on_cancel
        self.new_password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()

        layout = ttk.Frame(self)
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=1)
        layout.rowconfigure(0, weight=1)

        card = ttk.Frame(layout, style="Card.TFrame", padding=28)
        card.grid(row=0, column=0)
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Changement obligatoire du mot de passe", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text=(
                f"Le compte par defaut '{self.user.username}' doit etre securise avant la premiere utilisation de {APP_NAME}."
            ),
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 20))

        info = ttk.Label(
            card,
            text="Choisissez un nouveau mot de passe personnel pour continuer.",
            justify="left",
        )
        info.grid(row=2, column=0, sticky="w", pady=(0, 16))

        form = ttk.Frame(card, style="Card.TFrame")
        form.grid(row=3, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Nouveau mot de passe").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(form, text="Confirmer le mot de passe").grid(row=0, column=1, sticky="w")

        self.new_password_entry = ttk.Entry(form, textvariable=self.new_password_var, show="*")
        self.new_password_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(6, 0))
        self.confirm_password_entry = ttk.Entry(form, textvariable=self.confirm_password_var, show="*")
        self.confirm_password_entry.grid(row=1, column=1, sticky="ew", pady=(6, 0))

        helper_actions = ttk.Frame(card, style="Card.TFrame")
        helper_actions.grid(row=4, column=0, sticky="w", pady=(14, 0))
        ttk.Button(
            helper_actions,
            text="Generer automatiquement",
            style="Secondary.TButton",
            command=self._generate_password,
        ).pack(side="left")
        ttk.Label(
            helper_actions,
            text="Cree un mot de passe fort et remplit les deux champs.",
        ).pack(side="left", padx=(10, 0))

        tip = ttk.Label(
            card,
            text="Le nouveau mot de passe doit etre different du mot de passe par defaut et contenir au moins 6 caracteres.",
            wraplength=520,
            justify="left",
        )
        tip.grid(row=5, column=0, sticky="w", pady=(18, 18))

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=6, column=0, sticky="e")
        ttk.Button(actions, text="Retour a la connexion", style="Secondary.TButton", command=self.on_cancel).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Mettre a jour et continuer", style="Primary.TButton", command=self._submit).pack(side="left")

        self.new_password_entry.bind("<Return>", lambda _event: self._submit())
        self.confirm_password_entry.bind("<Return>", lambda _event: self._submit())
        self.after(100, self.new_password_entry.focus_set)

    def _generate_password(self) -> None:
        alphabet = string.ascii_letters + string.digits + "@#$%&*-_"
        while True:
            generated = "".join(secrets.choice(alphabet) for _ in range(12))
            if (
                any(character.islower() for character in generated)
                and any(character.isupper() for character in generated)
                and any(character.isdigit() for character in generated)
            ):
                break
        self.new_password_var.set(generated)
        self.confirm_password_var.set(generated)
        self.confirm_password_entry.focus_set()

    def _submit(self) -> None:
        new_password = self.new_password_var.get().strip()
        confirm_password = self.confirm_password_var.get().strip()

        if len(new_password) < 6:
            messagebox.showwarning("Mot de passe", "Le nouveau mot de passe doit contenir au moins 6 caracteres.")
            return
        if new_password == DEFAULT_DELIVERED_PASSWORD:
            messagebox.showwarning("Mot de passe", "Le mot de passe par defaut n'est pas autorise.")
            return
        if new_password != confirm_password:
            messagebox.showwarning("Mot de passe", "La confirmation du mot de passe ne correspond pas.")
            return

        auth_service.change_password(self.user.id, new_password)
        self.user.requires_password_change = False
        messagebox.showinfo("Securite", "Votre mot de passe a ete mis a jour. Vous pouvez maintenant utiliser l'application.")
        self.on_success(self.user)