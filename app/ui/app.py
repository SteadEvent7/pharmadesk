from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app import APP_NAME, APP_VERSION
from app.config import CONFIG
from app.db.schema import initialize_database
from app.services.auth_service import AuthenticatedUser
from app.services.update_service import UpdateCheckResult, update_service
from app.ui.theme import COLORS, apply_theme
from app.ui.views.billing_view import BillingView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.login_view import LoginView
from app.ui.views.medicines_view import MedicinesView
from app.ui.views.reports_view import ReportsView
from app.ui.views.sales_view import SalesView
from app.ui.views.settings_view import SettingsView
from app.ui.views.splash_view import SplashView
from app.ui.views.stock_view import StockView
from app.ui.views.suppliers_view import SuppliersView
from app.ui.views.users_view import UsersView


class PharmacyApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - Initialisation")
        self.root.geometry("1280x720")
        self.root.minsize(1100, 680)
        self.current_user: AuthenticatedUser | None = None
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self.nav_buttons: dict[str, tk.Button] = {}
        self.views: dict[str, ttk.Frame] = {}
        self.current_view_key: str | None = None
        self._startup_update_check_scheduled = False
        self.show_splash()

    def show_splash(self) -> None:
        self._clear_container()
        self.splash_view = SplashView(self.container)
        self.splash_view.pack(fill="both", expand=True)
        self.startup_steps = [
            (14, "Initialisation en cours", "Chargement des composants du poste", "Astuce: les droits d'acces dependent du role connecte.", self._startup_noop),
            (36, "Progression du demarrage", "Initialisation de la base de donnees", "Astuce: pensez a sauvegarder avant toute restauration.", initialize_database),
            (57, "Progression du demarrage", "Recherche des mises a jour", "Astuce: exportez vos rapports en PDF et Excel pour l'audit.", self._startup_noop),
            (76, "Progression du demarrage", "Configuration de l'interface", "Astuce: choisissez la devise depuis Parametres.", self._apply_runtime_theme),
            (92, "Progression du demarrage", "Securisation du poste et des modules", "Astuce: les mouvements de stock sont journalises automatiquement.", self._startup_noop),
            (100, "Demarrage termine", "Ouverture de l'ecran de connexion", "", self._finish_startup),
        ]
        self.root.after(120, lambda: self._run_startup_step(0))

    def _startup_noop(self) -> None:
        return

    def _apply_runtime_theme(self) -> None:
        apply_theme(self.root)

    def _finish_startup(self) -> None:
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1400x860")
        self.root.minsize(1180, 760)
        self.show_login()

    def _run_startup_step(self, index: int) -> None:
        if index >= len(self.startup_steps):
            return
        percent, status, step, tip, callback = self.startup_steps[index]
        self.splash_view.update_progress(percent, status, step, tip)
        callback()
        self.root.after(260 if index < len(self.startup_steps) - 1 else 120, lambda: self._run_startup_step(index + 1))

    def show_login(self) -> None:
        self._startup_update_check_scheduled = False
        self._clear_container()
        login_view = LoginView(self.container, self.on_login_success)
        login_view.pack(fill="both", expand=True)

    def on_login_success(self, user: AuthenticatedUser) -> None:
        self.current_user = user
        self.show_main_shell()

    def show_main_shell(self) -> None:
        self._clear_container()
        if not self.current_user:
            messagebox.showerror("Erreur", "Aucun utilisateur connecte.")
            self.show_login()
            return

        shell = ttk.Frame(self.container)
        shell.pack(fill="both", expand=True)

        self._build_topbar(shell)

        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_workspace(body)
        self._create_views()
        self.show_view("dashboard")
        self._schedule_startup_update_check()

    def _build_topbar(self, parent: ttk.Frame) -> None:
        topbar = tk.Frame(parent, bg=COLORS["shell_topbar"], height=52)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        left = tk.Frame(topbar, bg=COLORS["shell_topbar"])
        left.pack(side="left", fill="y")
        tk.Label(left, text="   PharmaDesk  •  Point de Vente", bg=COLORS["shell_topbar"], fg=COLORS["shell_sidebar_text"], font=("Segoe UI Semibold", 13)).pack(side="left", padx=14)

        right = tk.Frame(topbar, bg=COLORS["shell_topbar"])
        right.pack(side="right", fill="y", padx=12)
        tk.Label(
            right,
            text=f"{self.current_user.full_name}  |  {self.current_user.role.title()}",
            bg=COLORS["shell_topbar"],
            fg=COLORS["shell_sidebar_text"],
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(0, 16))
        tk.Button(
            right,
            text="Deconnexion",
            command=self.show_login,
            bg=COLORS["shell_topbar_button"],
            fg=COLORS["shell_sidebar_text"],
            activebackground=COLORS["shell_topbar_button_active"],
            activeforeground=COLORS["shell_sidebar_text"],
            relief="flat",
            padx=14,
            pady=6,
            font=("Segoe UI Semibold", 9),
        ).pack(side="left")

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        self.sidebar = tk.Frame(parent, bg=COLORS["shell_sidebar"], width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(
            self.sidebar,
            text="Magasin POS",
            bg=COLORS["shell_sidebar"],
            fg=COLORS["shell_sidebar_text"],
            font=("Segoe UI Semibold", 14),
            anchor="w",
            padx=14,
            pady=16,
        ).pack(fill="x")

        sections = [
            (
                "VENTE",
                [
                    ("dashboard", "Tableau de bord"),
                    ("pos", "Point de vente"),
                    ("billing", "Facturation"),
                ],
            ),
            (
                "STOCK",
                [
                    ("products", "Produits"),
                    ("stock", "Stock"),
                    ("suppliers", "Fournisseurs"),
                ],
            ),
            (
                "PILOTAGE",
                [
                    ("reports", "Rapports"),
                    ("users", "Utilisateurs"),
                ],
            ),
        ]

        for title, items in sections:
            tk.Label(
                self.sidebar,
                text=title,
                bg=COLORS["shell_sidebar"],
                fg=COLORS["shell_sidebar_section"],
                font=("Segoe UI Semibold", 9),
                anchor="w",
                padx=12,
                pady=10,
            ).pack(fill="x")
            for key, label in items:
                if key in {"users", "reports"} and self.current_user.role != "administrateur":
                    continue
                self._add_nav_button(key, label)

        spacer = tk.Frame(self.sidebar, bg=COLORS["shell_sidebar"])
        spacer.pack(fill="both", expand=True)
        self._add_nav_button("settings", "Parametres")

    def _add_nav_button(self, key: str, label: str) -> None:
        button = tk.Button(
            self.sidebar,
            text=f"  {label}",
            command=lambda item=key: self.show_view(item),
            anchor="w",
            justify="left",
            relief="flat",
            borderwidth=0,
            bg=COLORS["shell_sidebar"],
            fg=COLORS["shell_sidebar_text"],
            activebackground=COLORS["shell_sidebar_active"],
            activeforeground=COLORS["shell_sidebar_text"],
            padx=18,
            pady=10,
            font=("Segoe UI Semibold", 10),
        )
        button.pack(fill="x")
        self.nav_buttons[key] = button

    def _build_workspace(self, parent: ttk.Frame) -> None:
        workspace = ttk.Frame(parent, padding=16)
        workspace.pack(side="left", fill="both", expand=True)

        self.page_header = ttk.Frame(workspace, style="Card.TFrame", padding=18)
        self.page_header.pack(fill="x")
        self.page_title_var = tk.StringVar()
        self.page_subtitle_var = tk.StringVar()
        ttk.Label(self.page_header, textvariable=self.page_title_var, style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.page_header, textvariable=self.page_subtitle_var, style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        self.content_host = ttk.Frame(workspace)
        self.content_host.pack(fill="both", expand=True, pady=(14, 0))

    def _create_views(self) -> None:
        self.nav_buttons = dict(self.nav_buttons)
        self.dashboard_view = DashboardView(self.content_host)
        self.medicines_view = MedicinesView(self.content_host, self.current_user, self.refresh_all)
        self.stock_view = StockView(self.content_host, self.current_user, self.refresh_all)
        self.sales_view = SalesView(self.content_host, self.current_user, self.refresh_all)
        self.billing_view = BillingView(self.content_host, self.current_user)
        self.suppliers_view = SuppliersView(self.content_host, self.current_user, self.refresh_all)
        self.reports_view = ReportsView(self.content_host, self.current_user) if self.current_user and self.current_user.role == "administrateur" else None
        self.settings_view = SettingsView(self.content_host, self.current_user, self.apply_user_preferences)

        self.users_view = UsersView(self.content_host, self.current_user) if self.current_user and self.current_user.role == "administrateur" else None
        self.views = {
            "dashboard": self.dashboard_view,
            "pos": self.sales_view,
            "billing": self.billing_view,
            "products": self.medicines_view,
            "stock": self.stock_view,
            "suppliers": self.suppliers_view,
            "settings": self.settings_view,
        }
        if self.reports_view is not None:
            self.views["reports"] = self.reports_view
        if self.users_view is not None:
            self.views["users"] = self.users_view

    def show_view(self, key: str) -> None:
        if key not in self.views:
            return
        if self.current_view_key and self.current_view_key in self.views:
            self.views[self.current_view_key].pack_forget()
        self.current_view_key = key
        self._set_active_nav(key)
        title, subtitle = self._page_metadata(key)
        self.page_title_var.set(title)
        self.page_subtitle_var.set(subtitle)
        view = self.views[key]
        view.pack(fill="both", expand=True)
        self._refresh_view_if_supported(view)

    def _set_active_nav(self, active_key: str) -> None:
        for key, button in self.nav_buttons.items():
            is_active = key == active_key
            button.configure(bg=COLORS["shell_sidebar_active"] if is_active else COLORS["shell_sidebar"])

    def _page_metadata(self, key: str) -> tuple[str, str]:
        metadata = {
            "dashboard": ("Pilotage en temps reel", "Indicateurs cles, ventes recentes et alertes stock."),
            "pos": ("Point de vente", "Encaissement rapide, panier et generation de facture."),
            "billing": ("Facturation", "Historique des factures, details et export des enregistrements."),
            "products": ("Produits", "Catalogue des medicaments et informations commerciales."),
            "stock": ("Stock", "Entrees, sorties, alertes de seuil et expiration."),
            "suppliers": ("Fournisseurs", "Carnet fournisseurs et coordonnees de contact."),
            "reports": ("Rapports", "Suivi journalier et alertes critiques."),
            "users": ("Utilisateurs", "Comptes d'acces et roles applicatifs."),
            "settings": ("Parametres", "Configuration generale de l'application et de la base."),
        }
        return metadata.get(key, ("Module", ""))

    def _refresh_view_if_supported(self, view: ttk.Frame) -> None:
        refresh_method = getattr(view, "refresh", None)
        if callable(refresh_method):
            refresh_method()

    def refresh_all(self) -> None:
        self.dashboard_view.refresh()
        self.medicines_view.refresh_suppliers()
        self.medicines_view.refresh()
        self.stock_view.refresh()
        self.sales_view.refresh()
        self.billing_view.refresh()
        self.suppliers_view.refresh()
        self.settings_view.refresh()
        if self.users_view is not None:
            self.users_view.refresh()
        if self.reports_view is not None:
            self.reports_view.refresh()

    def apply_user_preferences(self) -> None:
        active_view = self.current_view_key or "dashboard"
        self._apply_runtime_theme()
        if self.current_user is None:
            self.show_login()
            return
        self.show_main_shell()
        if active_view in self.views:
            self.show_view(active_view)

    def _schedule_startup_update_check(self) -> None:
        if not self.current_user or self.current_user.role != "administrateur":
            return
        if not CONFIG.auto_check_updates or self._startup_update_check_scheduled:
            return
        self._startup_update_check_scheduled = True
        self.root.after(900, lambda: update_service.check_for_updates_async(self.root, self._handle_startup_update_result, source="demarrage"))

    def _handle_startup_update_result(self, result: UpdateCheckResult) -> None:
        self.settings_view.present_update_result(result, ask_to_download=False, silent=True)
        if not result.available or result.manifest is None:
            return

        notes = result.manifest.notes.strip()
        prompt = f"{result.message}\n\nVersion locale: {update_service.local_display_version()}"
        if notes:
            prompt += f"\n\nNotes:\n{notes[:420]}"
        prompt += "\n\nVoulez-vous telecharger l'installateur maintenant ?"

        if messagebox.askyesno("Mise a jour disponible", prompt):
            self.show_view("settings")
            self.settings_view.start_manifest_download(result.manifest, prompt_install=True)

    def _clear_container(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def run(self) -> None:
        self.root.mainloop()