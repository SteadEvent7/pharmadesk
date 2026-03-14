from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app import APP_NAME, APP_VERSION
from app.config import CONFIG
from app.db.schema import initialize_database
from app.services.auth_service import AuthenticatedUser
from app.services.update_service import UpdateCheckResult, update_service
from app.services.pharmacy_service import pharmacy_service
from app.ui.branding import load_brand_logo
from app.ui.theme import COLORS, apply_theme
from app.ui.views.billing_view import BillingView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.force_password_change_view import ForcePasswordChangeView
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
        self._set_window_geometry(1024, 576, resizable=False)
        self.current_user: AuthenticatedUser | None = None
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self.nav_buttons: dict[str, tk.Button] = {}
        self.views: dict[str, ttk.Frame] = {}
        self.current_view_key: str | None = None
        self.alert_count_var = tk.StringVar(value="0")
        self.topbar_logo_image = None
        self._startup_update_check_scheduled = False
        self._startup_queue: queue.Queue[tuple[str, int, float, str, str, str]] = queue.Queue()
        self._startup_current_index = 0
        self.show_splash()

    def show_splash(self) -> None:
        self.root.overrideredirect(True)
        self._set_window_geometry(1024, 576, resizable=False)
        self._clear_container()
        self.splash_view = SplashView(self.container)
        self.splash_view.pack(fill="both", expand=True)
        self.startup_steps = [
            (6, 14, "Initialisation en cours", "Chargement des composants du poste", "Astuce: les droits d'acces dependent du role connecte.", self._startup_noop, False, False),
            (14, 62, "Progression du demarrage", "Initialisation de la base de donnees", "Astuce: pensez a sauvegarder avant toute restauration.", initialize_database, True, True),
            (62, 74, "Progression du demarrage", "Preparation des services de mise a jour", "Astuce: exportez vos rapports en PDF et Excel pour l'audit.", self._startup_noop, False, False),
            (74, 86, "Progression du demarrage", "Configuration de l'interface", "Astuce: choisissez la devise depuis Parametres.", self._apply_runtime_theme, False, False),
            (86, 96, "Progression du demarrage", "Securisation du poste et des modules", "Astuce: les mouvements de stock sont journalises automatiquement.", self._startup_noop, False, False),
            (96, 100, "Demarrage termine", "Ouverture de l'ecran de connexion", "", self._finish_startup, False, False),
        ]
        self._startup_current_index = 0
        self.splash_view.update_progress(4, "Initialisation en cours", "Preparation du poste", "Chargement des ressources de base...")
        self.root.after(80, self._poll_startup_queue)
        self.root.after(120, lambda: self._run_startup_step(0))

    def _startup_noop(self) -> None:
        return

    def _apply_runtime_theme(self) -> None:
        apply_theme(self.root)

    def _finish_startup(self) -> None:
        self.root.overrideredirect(False)
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self._set_window_geometry(1400, 860, min_width=1180, min_height=760, resizable=True)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass
        self.show_login()

    def _set_window_geometry(
        self,
        width: int,
        height: int,
        min_width: int | None = None,
        min_height: int | None = None,
        resizable: bool = True,
    ) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max((screen_width - width) // 2, 40)
        y = max((screen_height - height) // 2, 40)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        if min_width is None:
            min_width = width
        if min_height is None:
            min_height = height
        self.root.minsize(min_width, min_height)
        self.root.resizable(resizable, resizable)

    def _run_startup_step(self, index: int) -> None:
        if index >= len(self.startup_steps):
            return
        self._startup_current_index = index
        start_percent, end_percent, status, step, tip, callback, threaded, supports_progress = self.startup_steps[index]
        self.splash_view.update_progress(start_percent, status, step, tip)

        if threaded:
            self._run_threaded_startup_step(index, start_percent, end_percent, status, step, tip, callback, supports_progress)
            return

        try:
            callback()
        except Exception as error:
            self._handle_startup_error(step, error)
            return

        self.splash_view.update_progress(end_percent, status, step, tip)
        self.root.after(40, lambda: self._run_startup_step(index + 1))

    def _run_threaded_startup_step(self, index: int, start_percent: int, end_percent: int, status: str, step: str, tip: str, callback, supports_progress: bool) -> None:
        def progress_callback(progress: float) -> None:
            bounded = max(0.0, min(1.0, progress))
            current_percent = start_percent + ((end_percent - start_percent) * bounded)
            self._startup_queue.put(("progress", index, current_percent, status, step, tip))

        def worker() -> None:
            try:
                if supports_progress:
                    callback(progress_callback=progress_callback)
                else:
                    callback()
            except Exception as error:
                self._startup_queue.put(("error", index, 0, status, step, str(error)))
                return
            self._startup_queue.put(("complete", index, float(end_percent), status, step, tip))

        threading.Thread(target=worker, daemon=True, name=f"startup-step-{index}").start()

    def _poll_startup_queue(self) -> None:
        if not hasattr(self, "splash_view") or not self.splash_view.winfo_exists():
            return
        while True:
            try:
                event_type, step_index, percent, status, step, payload = self._startup_queue.get_nowait()
            except queue.Empty:
                break

            if step_index != self._startup_current_index:
                continue

            if event_type == "progress":
                self.splash_view.update_progress(int(percent), status, step, payload)
            elif event_type == "complete":
                self.splash_view.update_progress(int(percent), status, step, payload)
                self.root.after(40, lambda next_index=step_index + 1: self._run_startup_step(next_index))
            elif event_type == "error":
                self._handle_startup_error(step, RuntimeError(payload))

        if self.container.winfo_exists() and hasattr(self, "splash_view") and self.splash_view.winfo_exists():
            self.root.after(80, self._poll_startup_queue)

    def _handle_startup_error(self, step: str, error: Exception) -> None:
        messagebox.showerror("Demarrage", f"Erreur pendant l'etape '{step}': {error}")

    def show_login(self) -> None:
        self._startup_update_check_scheduled = False
        self.current_user = None
        self._clear_container()
        login_view = LoginView(self.container, self.on_login_success)
        login_view.pack(fill="both", expand=True)

    def on_login_success(self, user: AuthenticatedUser) -> None:
        self.current_user = user
        if user.requires_password_change:
            self.show_force_password_change()
            return
        self.show_main_shell()

    def show_force_password_change(self) -> None:
        self._clear_container()
        if not self.current_user:
            self.show_login()
            return
        force_view = ForcePasswordChangeView(
            self.container,
            self.current_user,
            on_success=self._on_forced_password_changed,
            on_cancel=self.show_login,
        )
        force_view.pack(fill="both", expand=True)

    def _on_forced_password_changed(self, user: AuthenticatedUser) -> None:
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
        self.topbar_logo_image = load_brand_logo((110, 34))
        if self.topbar_logo_image is not None:
            tk.Label(left, image=self.topbar_logo_image, bg=COLORS["shell_topbar"]).pack(side="left", padx=(14, 8))
        tk.Label(left, text="   PharmaDesk  •  Point de Vente", bg=COLORS["shell_topbar"], fg=COLORS["shell_sidebar_text"], font=("Segoe UI Semibold", 13)).pack(side="left", padx=14)

        right = tk.Frame(topbar, bg=COLORS["shell_topbar"])
        right.pack(side="right", fill="y", padx=12)
        alert_wrap = tk.Frame(right, bg=COLORS["shell_topbar"])
        alert_wrap.pack(side="left", padx=(0, 14))
        tk.Button(
            alert_wrap,
            text="🔔",
            command=self.show_alert_center,
            bg=COLORS["shell_topbar"],
            fg=COLORS["shell_sidebar_text"],
            activebackground=COLORS["shell_topbar"],
            activeforeground=COLORS["shell_sidebar_text"],
            relief="flat",
            borderwidth=0,
            padx=6,
            pady=4,
            font=("Segoe UI Symbol", 14),
        ).pack(side="left")
        tk.Label(
            alert_wrap,
            textvariable=self.alert_count_var,
            bg=COLORS["danger"],
            fg="#ffffff",
            font=("Segoe UI Semibold", 8),
            padx=6,
            pady=2,
        ).pack(side="left", padx=(0, 2))
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
        self._refresh_alert_badge()

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
        self._refresh_alert_badge()

    def _refresh_alert_badge(self) -> None:
        notifications = pharmacy_service.get_alert_notifications()
        self.alert_count_var.set(str(len(notifications)))

    def show_alert_center(self) -> None:
        notifications = pharmacy_service.get_alert_notifications()
        self._refresh_alert_badge()

        dialog = tk.Toplevel(self.root)
        dialog.title("Centre d'alertes")
        dialog.geometry("720x460")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)

        frame = ttk.Frame(dialog, padding=16, style="Card.TFrame")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Alertes produit", style="Section.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Expiration, produits expires et seuils de stock faibles.", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 12))

        columns = ["label", "medicine", "stock", "expiration", "severity"]
        headings = ["Alerte", "Produit", "Stock", "Expiration", "Niveau"]
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        for column, heading, width, anchor in (
            ("label", "Alerte", 170, "w"),
            ("medicine", "Produit", 220, "w"),
            ("stock", "Stock", 80, "center"),
            ("expiration", "Expiration", 120, "center"),
            ("severity", "Niveau", 100, "center"),
        ):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor=anchor)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for item in notifications:
            tree.insert(
                "",
                "end",
                values=(
                    item["label"],
                    item["medicine_name"],
                    item["quantity"],
                    item["expiration_date"],
                    item["severity"].title(),
                ),
            )

        if not notifications:
            tree.insert("", "end", values=("Aucune alerte", "-", "-", "-", "Normal"))

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