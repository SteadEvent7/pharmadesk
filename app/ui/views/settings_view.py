from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.services.auth_service import AuthenticatedUser
from app.config import CONFIG
from app.services.backup_service import backup_service
from app.services.pharmacy_service import pharmacy_service
from app.services.update_service import UpdateCheckResult, UpdateManifest, update_service
from app.ui.widgets import TreeSection
from app.utils.currency import AFRICAN_CURRENCIES


class SettingsView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser, on_settings_changed=None) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        self.is_admin = current_user.role == "administrateur"
        self.on_settings_changed = on_settings_changed
        self.pending_manifest: UpdateManifest | None = None
        self.downloaded_installer_path: str | None = None
        self.summary_vars: dict[str, tk.StringVar] = {}
        self.auto_update_var = tk.BooleanVar(value=CONFIG.auto_check_updates)
        self.update_status_var = tk.StringVar(value="Aucune verification effectuee.")
        self.update_progress_var = tk.DoubleVar(value=0.0)
        summary = ttk.Frame(self, style="Card.TFrame", padding=20)
        summary.pack(fill="x")
        ttk.Label(summary, text="Configuration generale", style="Section.TLabel").pack(anchor="w")

        entries = [
            ("db_engine", "Moteur base de donnees", CONFIG.db_engine),
            ("sqlite_path", "SQLite", CONFIG.sqlite_path),
            ("mysql_host", "MySQL hote", f"{CONFIG.mysql_host}:{CONFIG.mysql_port}"),
            ("mysql_database", "MySQL base", CONFIG.mysql_database),
            ("low_stock", "Seuil stock faible", str(CONFIG.low_stock_threshold)),
            ("github", "GitHub Release", f"{CONFIG.github_owner}/{CONFIG.github_repo}"),
            ("manifest", "Manifest distant", CONFIG.update_manifest_url or "Derive du depot GitHub"),
            ("auto_update", "Verification auto", "Oui" if CONFIG.auto_check_updates else "Non"),
            ("currency", "Devise active", CONFIG.currency_code),
        ]

        grid = ttk.Frame(summary, style="Card.TFrame")
        grid.pack(fill="x", pady=(14, 0))
        for index, (key, label, value) in enumerate(entries):
            row = ttk.Frame(grid, style="Card.TFrame")
            row.grid(row=index, column=0, sticky="ew", pady=4)
            ttk.Label(row, text=label, style="Subtitle.TLabel", width=24).pack(side="left")
            self.summary_vars[key] = tk.StringVar(value=value)
            ttk.Label(row, textvariable=self.summary_vars[key]).pack(side="left")
        grid.columnconfigure(0, weight=1)

        update_card = ttk.Frame(self, style="Card.TFrame", padding=20)
        update_card.pack(fill="x", pady=(14, 0))
        ttk.Label(update_card, text="Mises a jour distantes", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            update_card,
            text="Verifiez manuellement les nouvelles versions publiees sur GitHub et preparez l'installation depuis cet ecran.",
            style="Subtitle.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

        update_actions = ttk.Frame(update_card, style="Card.TFrame")
        update_actions.pack(fill="x", pady=(14, 0))
        self.update_button = ttk.Button(
            update_actions,
            text="Verifier les mises a jour maintenant",
            style="Primary.TButton",
            command=self.check_updates,
        )
        self.update_button.pack(side="left")
        self.install_update_button = ttk.Button(
            update_actions,
            text="Installer la mise a jour telechargee",
            style="Secondary.TButton",
            command=self.install_downloaded_update,
        )
        self.install_update_button.pack(side="left", padx=8)

        ttk.Label(update_card, textvariable=self.update_status_var, style="Subtitle.TLabel").pack(anchor="w", pady=(12, 0))
        self.update_progress = ttk.Progressbar(update_card, variable=self.update_progress_var, maximum=100)
        self.update_progress.pack(fill="x", pady=(10, 0))

        ttk.Label(update_card, text="Notes de version distantes", style="Section.TLabel").pack(anchor="w", pady=(14, 6))
        self.update_notes = tk.Text(
            update_card,
            height=6,
            wrap="word",
            relief="flat",
            bg="#f8fafc",
            fg="#0f172a",
            padx=10,
            pady=10,
            font=("Segoe UI", 9),
        )
        self.update_notes.pack(fill="x")
        self.update_notes.insert("1.0", "Les notes de version apparaitront ici apres verification du manifest distant.\nJournal: data/logs/update.log")
        self.update_notes.configure(state="disabled")

        currency_card = ttk.Frame(self, style="Card.TFrame", padding=20)
        currency_card.pack(fill="x", pady=(14, 0))
        ttk.Label(currency_card, text="Devise", style="Section.TLabel").pack(anchor="w")
        ttk.Label(currency_card, text="Choisissez la devise d'affichage des montants.", style="Subtitle.TLabel").pack(anchor="w", pady=(10, 0))
        self.currency_options = {details["label"]: code for code, details in AFRICAN_CURRENCIES.items()}
        current_label = AFRICAN_CURRENCIES.get(CONFIG.currency_code, AFRICAN_CURRENCIES["XOF"])["label"]
        self.currency_label_var = tk.StringVar(value=current_label)
        row = ttk.Frame(currency_card, style="Card.TFrame")
        row.pack(fill="x", pady=(12, 0))
        self.currency_combo = ttk.Combobox(row, textvariable=self.currency_label_var, values=list(self.currency_options.keys()), state="readonly", width=34)
        self.currency_combo.pack(side="left")
        self.apply_currency_button = ttk.Button(row, text="Appliquer", style="Primary.TButton", command=self.save_currency)
        self.apply_currency_button.pack(side="left", padx=10)

        help_card = ttk.Frame(self, style="Card.TFrame", padding=20)
        help_card.pack(fill="x", pady=(14, 0))
        ttk.Label(help_card, text="Maintenance et mises a jour", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            help_card,
            text=(
                "Le fichier config.json permet de basculer entre SQLite et MySQL. "
                "Pour une exploitation multi-postes, renseignez les parametres MySQL puis redemarrez l'application. "
                "Le module de mise a jour distante lit un manifest JSON, telecharge l'installateur en arriere-plan puis le lance avec elevation Windows."
            ),
            style="Subtitle.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

        auto_row = ttk.Frame(help_card, style="Card.TFrame")
        auto_row.pack(fill="x", pady=(14, 0))
        self.auto_check_button = ttk.Checkbutton(
            auto_row,
            text="Verifier automatiquement les mises a jour au demarrage",
            variable=self.auto_update_var,
            command=self.toggle_auto_updates,
        )
        self.auto_check_button.pack(side="left")

        buttons = ttk.Frame(help_card, style="Card.TFrame")
        buttons.pack(fill="x", pady=(14, 0))
        self.backup_button = ttk.Button(buttons, text="Sauvegarder SQLite", style="Primary.TButton", command=self.backup_data)
        self.backup_button.pack(side="left", padx=(0, 8))
        self.restore_button = ttk.Button(buttons, text="Restaurer SQLite", style="Secondary.TButton", command=self.restore_data)
        self.restore_button.pack(side="left")

        ttk.Label(self, text="Historique sauvegardes et restaurations", style="Section.TLabel").pack(anchor="w", pady=(18, 8))
        self.maintenance_table = TreeSection(
            self,
            ["created_at", "user_name", "event_type", "source_path", "target_path", "safety_backup_path"],
            ["Date", "Utilisateur", "Type", "Source", "Destination", "Copie secours"],
        )
        self.maintenance_table.pack(fill="both", expand=True)

        if not self.is_admin:
            ttk.Label(
                help_card,
                text="Certaines actions sont reservees a l'administrateur.",
                style="Subtitle.TLabel",
            ).pack(anchor="w", pady=(12, 0))
            self.currency_combo.state(["disabled"])
            self.apply_currency_button.state(["disabled"])
            self.auto_check_button.state(["disabled"])
            self.update_button.state(["disabled"])
            self.install_update_button.state(["disabled"])
            self.backup_button.state(["disabled"])
            self.restore_button.state(["disabled"])
        else:
            self.install_update_button.state(["disabled"])

    def save_currency(self) -> None:
        if not self.is_admin:
            messagebox.showerror("Parametres", "Seul l'administrateur peut changer la devise.")
            return
        selected_label = self.currency_label_var.get().strip()
        code = self.currency_options.get(selected_label)
        if not code:
            messagebox.showwarning("Parametres", "Selectionnez une devise valide.")
            return
        CONFIG.currency_code = code
        CONFIG.save()
        pharmacy_service.record_audit(self.current_user.id, "modifier", "parametre", f"Devise changee vers {code}")
        self.refresh()
        messagebox.showinfo("Parametres", "Devise enregistree.")
        if callable(self.on_settings_changed):
            self.on_settings_changed()

    def check_updates(self) -> None:
        if not self.is_admin:
            messagebox.showerror("Parametres", "Seul l'administrateur peut lancer les mises a jour.")
            return
        self.update_progress_var.set(0)
        self.update_status_var.set("Verification du manifest distant en cours...")
        self.update_button.state(["disabled"])
        update_service.check_for_updates_async(self, lambda result: self.present_update_result(result, ask_to_download=True, silent=False))

    def toggle_auto_updates(self) -> None:
        if not self.is_admin:
            self.auto_update_var.set(CONFIG.auto_check_updates)
            messagebox.showerror("Parametres", "Seul l'administrateur peut modifier la verification automatique.")
            return
        CONFIG.auto_check_updates = bool(self.auto_update_var.get())
        CONFIG.save()
        pharmacy_service.record_audit(
            self.current_user.id,
            "modifier",
            "parametre",
            f"Verification auto des mises a jour: {'activee' if CONFIG.auto_check_updates else 'desactivee'}",
        )
        self.refresh()
        self.update_status_var.set("Preference de verification automatique enregistree.")

    def present_update_result(self, result: UpdateCheckResult, ask_to_download: bool = True, silent: bool = False) -> None:
        self.update_button.state(["!disabled"])
        self.pending_manifest = result.manifest
        self.downloaded_installer_path = None
        self.install_update_button.state(["disabled"])
        self.update_progress_var.set(0)

        if result.manifest is not None:
            self._set_update_notes(result.manifest)
        if result.available and result.manifest is not None:
            self.update_status_var.set(
                f"Nouvelle version detectee: {result.manifest.display_version}. Pret pour telechargement asynchrone."
            )
            if ask_to_download and messagebox.askyesno(
                "Mise a jour disponible",
                f"{result.message}\n\nSouhaitez-vous telecharger l'installateur maintenant ?",
            ):
                self.start_manifest_download(result.manifest, prompt_install=True)
            return

        self.update_status_var.set(result.message)
        if result.error:
            self._set_update_notes(None, f"Erreur: {result.message}\nConsultez data/logs/update.log pour le detail.")
            if not silent:
                messagebox.showwarning("Mise a jour", result.message)
        elif not silent:
            messagebox.showinfo("Mise a jour", result.message)

    def start_manifest_download(self, manifest: UpdateManifest | None = None, prompt_install: bool = True) -> None:
        if not self.is_admin:
            messagebox.showerror("Mise a jour", "Seul l'administrateur peut telecharger une mise a jour.")
            return
        manifest_to_download = manifest or self.pending_manifest
        if manifest_to_download is None:
            messagebox.showwarning("Mise a jour", "Aucune mise a jour distante n'est prete au telechargement.")
            return
        self.update_status_var.set(f"Telechargement lance pour {manifest_to_download.display_version}...")
        self.update_progress_var.set(0)
        self.update_button.state(["disabled"])
        self.install_update_button.state(["disabled"])
        started = update_service.download_update_async(
            self,
            manifest_to_download,
            self._handle_update_download_progress,
            lambda success, message, path, ask_install=prompt_install: self._handle_update_download_complete(
                success,
                message,
                path,
                ask_install,
            ),
        )
        if not started:
            self.update_button.state(["!disabled"])
            self.update_status_var.set("Un telechargement de mise a jour est deja en cours.")
            messagebox.showinfo("Mise a jour", "Un telechargement est deja en cours.")

    def _handle_update_download_progress(self, downloaded: int, total: int, message: str) -> None:
        if total > 0:
            progress = min((downloaded / total) * 100, 100)
            self.update_progress_var.set(progress)
            self.update_status_var.set(f"{message}... {progress:.0f}%")
            return
        self.update_status_var.set(f"{message}...")

    def _handle_update_download_complete(self, success: bool, message: str, path: str | None, ask_install: bool) -> None:
        self.update_button.state(["!disabled"])
        if not success:
            self.update_progress_var.set(0)
            self.update_status_var.set(message)
            messagebox.showerror("Mise a jour", message)
            return

        self.downloaded_installer_path = path
        self.update_progress_var.set(100)
        self.update_status_var.set(message)
        self.install_update_button.state(["!disabled"])
        pharmacy_service.record_audit(
            self.current_user.id,
            "telecharger",
            "mise_a_jour",
            f"Installateur telecharge: {path}",
        )
        if ask_install and messagebox.askyesno(
            "Installer maintenant",
            "Le telechargement est termine. Voulez-vous fermer l'application et lancer l'installateur ?",
        ):
            self.install_downloaded_update()

    def install_downloaded_update(self) -> None:
        if not self.is_admin:
            messagebox.showerror("Mise a jour", "Seul l'administrateur peut installer une mise a jour.")
            return
        if not self.downloaded_installer_path:
            messagebox.showwarning("Mise a jour", "Aucun installateur n'a encore ete telecharge.")
            return
        success, message = update_service.schedule_installer_launch(self.downloaded_installer_path)
        if not success:
            messagebox.showerror("Mise a jour", message)
            return
        pharmacy_service.record_audit(
            self.current_user.id,
            "installer",
            "mise_a_jour",
            f"Installateur lance: {self.downloaded_installer_path}",
        )
        messagebox.showinfo("Mise a jour", message)
        self.winfo_toplevel().after(200, self.winfo_toplevel().destroy)

    def _set_update_notes(self, manifest: UpdateManifest | None, fallback_text: str | None = None) -> None:
        if manifest is not None:
            lines = [f"Version distante: {manifest.display_version}"]
            if manifest.published_at:
                lines.append(f"Publication: {manifest.published_at}")
            lines.append(f"Installateur: {manifest.installer_name}")
            lines.append("")
            lines.append(manifest.notes or "Aucune note de version fournie.")
            content = "\n".join(lines)
        else:
            content = fallback_text or "Aucune information de version disponible."
        self.update_notes.configure(state="normal")
        self.update_notes.delete("1.0", "end")
        self.update_notes.insert("1.0", content)
        self.update_notes.configure(state="disabled")

    def backup_data(self) -> None:
        if not self.is_admin:
            messagebox.showerror("Parametres", "Seul l'administrateur peut sauvegarder ou restaurer la base.")
            return
        try:
            backup_path = backup_service.create_sqlite_backup(self.current_user.id)
        except FileNotFoundError as error:
            messagebox.showerror("Sauvegarde", str(error))
            return
        pharmacy_service.record_audit(self.current_user.id, "sauvegarder", "base", f"Sauvegarde creee: {backup_path}")
        messagebox.showinfo("Sauvegarde", f"Sauvegarde creee: {backup_path}")
        self.refresh()

    def restore_data(self) -> None:
        if not self.is_admin:
            messagebox.showerror("Parametres", "Seul l'administrateur peut sauvegarder ou restaurer la base.")
            return
        path = filedialog.askopenfilename(
            title="Restaurer une sauvegarde SQLite",
            filetypes=[("Base SQLite", "*.db"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno("Restauration", "La restauration remplacera la base actuelle. Continuer ?"):
            return
        try:
            restored, safety_backup = backup_service.restore_sqlite_backup(path, self.current_user.id)
        except FileNotFoundError as error:
            messagebox.showerror("Restauration", str(error))
            return
        details = f"Base restauree: {restored}"
        if safety_backup is not None:
            details += f"\nCopie de secours creee: {safety_backup}"
        pharmacy_service.record_audit(self.current_user.id, "restaurer", "base", details)
        messagebox.showinfo("Restauration", details)
        self.refresh()
        if callable(self.on_settings_changed):
            self.on_settings_changed()

    def refresh(self) -> None:
        self.summary_vars["db_engine"].set(CONFIG.db_engine)
        self.summary_vars["sqlite_path"].set(CONFIG.sqlite_path)
        self.summary_vars["mysql_host"].set(f"{CONFIG.mysql_host}:{CONFIG.mysql_port}")
        self.summary_vars["mysql_database"].set(CONFIG.mysql_database)
        self.summary_vars["low_stock"].set(str(CONFIG.low_stock_threshold))
        self.summary_vars["github"].set(f"{CONFIG.github_owner}/{CONFIG.github_repo}")
        self.summary_vars["manifest"].set(CONFIG.update_manifest_url or "Derive du depot GitHub")
        self.summary_vars["auto_update"].set("Oui" if CONFIG.auto_check_updates else "Non")
        self.summary_vars["currency"].set(CONFIG.currency_code)
        self.auto_update_var.set(CONFIG.auto_check_updates)
        self.maintenance_table.clear()
        for event in backup_service.list_maintenance_logs():
            self.maintenance_table.tree.insert(
                "",
                "end",
                values=(
                    event["created_at"],
                    event.get("user_name") or "-",
                    event["event_type"],
                    event.get("source_path") or "-",
                    event.get("target_path") or "-",
                    event.get("safety_backup_path") or "-",
                ),
            )