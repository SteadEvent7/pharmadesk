from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from app.services.auth_service import AuthenticatedUser
from app.services.pharmacy_service import pharmacy_service
from app.ui.widgets import TreeSection
from app.utils.currency import format_currency
from tkcalendar import DateEntry


class BillingView(ttk.Frame):
    def __init__(self, parent: tk.Misc, current_user: AuthenticatedUser) -> None:
        super().__init__(parent, padding=18)
        self.current_user = current_user
        self.selected_sale_id: int | None = None
        self.search_var = tk.StringVar()
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.use_start_var = tk.BooleanVar(value=False)
        self.use_end_var = tk.BooleanVar(value=False)

        toolbar = ttk.Frame(self, style="Card.TFrame", padding=16)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Archives de facturation", style="Section.TLabel").pack(side="left")
        actions = ttk.Frame(toolbar, style="Card.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="Imprimer", style="Secondary.TButton", command=self.print_selected).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Exporter PDF", style="Secondary.TButton", command=self.export_pdf).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Exporter texte", style="Secondary.TButton", command=self.export_selected).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Exporter toutes les factures", style="Primary.TButton", command=self.export_all).pack(side="right")

        search_bar = ttk.Frame(self, style="Card.TFrame", padding=16)
        search_bar.pack(fill="x", pady=(14, 0))
        ttk.Label(search_bar, text="Numero ou date", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(search_bar, textvariable=self.search_var).grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Checkbutton(search_bar, text="Du", variable=self.use_start_var).grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.start_date_picker = DateEntry(search_bar, textvariable=self.start_date_var, width=12, date_pattern="yyyy-mm-dd", locale="en_US")
        self.start_date_picker.grid(row=0, column=3, sticky="w", padx=8)
        ttk.Checkbutton(search_bar, text="Au", variable=self.use_end_var).grid(row=0, column=4, sticky="w")
        self.end_date_picker = DateEntry(search_bar, textvariable=self.end_date_var, width=12, date_pattern="yyyy-mm-dd", locale="en_US")
        self.end_date_picker.grid(row=0, column=5, sticky="w", padx=8)
        ttk.Button(search_bar, text="Rechercher", style="Primary.TButton", command=self.refresh).grid(row=0, column=6, sticky="e")
        ttk.Button(search_bar, text="Reinitialiser", style="Secondary.TButton", command=self.reset_search).grid(row=0, column=7, sticky="e", padx=(8, 0))
        search_bar.columnconfigure(1, weight=1)

        self.start_date_var.set("")
        self.end_date_var.set("")

        content = ttk.Frame(self)
        content.pack(fill="both", expand=True, pady=(14, 0))
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        left = ttk.Frame(content, style="Card.TFrame", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(left, text="Historique des factures", style="Section.TLabel").pack(anchor="w")
        self.invoice_table = TreeSection(
            left,
            ["id", "sale_number", "sale_date", "payment_method", "total_amount", "seller_name"],
            ["ID", "Numero", "Date", "Paiement", "Total", "Caissier"],
        )
        self.invoice_table.pack(fill="both", expand=True, pady=(10, 0))
        self.invoice_table.tree.column("id", width=60, anchor="center")
        self.invoice_table.tree.column("sale_number", width=130)
        self.invoice_table.tree.column("sale_date", width=160)
        self.invoice_table.tree.column("payment_method", width=120)
        self.invoice_table.tree.column("total_amount", width=110, anchor="e")
        self.invoice_table.tree.column("seller_name", width=140)
        self.invoice_table.tree.bind("<<TreeviewSelect>>", self._on_invoice_selected)

        right = ttk.Frame(content, style="Card.TFrame", padding=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(right, text="Details de la facture", style="Section.TLabel").pack(anchor="w")
        self.items_table = TreeSection(
            right,
            ["medicine_name", "quantity", "unit_price", "line_total"],
            ["Produit", "Quantite", "Prix U.", "Sous-total"],
        )
        self.items_table.pack(fill="both", expand=True, pady=(10, 0))
        self.items_table.tree.column("medicine_name", width=220)
        self.items_table.tree.column("quantity", width=90, anchor="center")
        self.items_table.tree.column("unit_price", width=100, anchor="e")
        self.items_table.tree.column("line_total", width=110, anchor="e")

        preview_card = ttk.Frame(self, style="Card.TFrame", padding=14)
        preview_card.pack(fill="both", expand=False, pady=(14, 0))
        ttk.Label(preview_card, text="Apercu texte", style="Section.TLabel").pack(anchor="w")
        self.preview = tk.Text(preview_card, height=10, wrap="word", font=("Consolas", 10))
        self.preview.pack(fill="both", expand=True, pady=(10, 0))
        self.preview.configure(state="disabled")
        self.refresh()

    def refresh(self) -> None:
        self.invoice_table.clear()
        if not self._validate_date_filters():
            return
        invoices = pharmacy_service.search_invoices(
            self.search_var.get(),
            self.start_date_var.get() if self.use_start_var.get() else "",
            self.end_date_var.get() if self.use_end_var.get() else "",
        )
        for invoice in invoices:
            self.invoice_table.tree.insert(
                "",
                "end",
                iid=str(invoice["id"]),
                values=(
                    invoice["id"],
                    invoice["sale_number"],
                    invoice["sale_date"],
                    invoice["payment_method"],
                    format_currency(float(invoice["total_amount"])),
                    invoice.get("seller_name") or "-",
                ),
            )
        self.items_table.clear()
        self._set_preview("")
        self.selected_sale_id = None

    def _on_invoice_selected(self, _event=None) -> None:
        selection = self.invoice_table.tree.selection()
        if not selection:
            return
        self.selected_sale_id = int(selection[0])
        self.items_table.clear()
        for item in pharmacy_service.get_invoice_items(self.selected_sale_id):
            self.items_table.tree.insert(
                "",
                "end",
                values=(
                    item["medicine_name"],
                    item["quantity"],
                    format_currency(float(item["unit_price"])),
                    format_currency(float(item["line_total"])),
                ),
            )
        self._set_preview(pharmacy_service.build_invoice_from_sale(self.selected_sale_id))

    def _set_preview(self, content: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", content)
        self.preview.configure(state="disabled")

    def export_all(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Exporter les factures",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="factures.csv",
        )
        if not path:
            return
        if not self._validate_date_filters():
            return
        exported = pharmacy_service.export_invoices_csv(
            path,
            self.search_var.get(),
            self.start_date_var.get() if self.use_start_var.get() else "",
            self.end_date_var.get() if self.use_end_var.get() else "",
        )
        pharmacy_service.record_audit(self.current_user.id, "exporter", "factures", f"Export CSV des factures vers {exported}")
        messagebox.showinfo("Facturation", f"Export realise: {exported}")

    def export_selected(self) -> None:
        if not self.selected_sale_id:
            messagebox.showwarning("Facturation", "Selectionnez une facture.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter la facture",
            defaultextension=".txt",
            filetypes=[("Texte", "*.txt")],
            initialfile=f"facture_{self.selected_sale_id}.txt",
        )
        if not path:
            return
        exported = pharmacy_service.export_invoice_text(self.selected_sale_id, path)
        pharmacy_service.record_audit(self.current_user.id, "exporter", "facture", f"Export texte facture {self.selected_sale_id} vers {exported}", self.selected_sale_id)
        messagebox.showinfo("Facturation", f"Facture exportee: {exported}")

    def export_pdf(self) -> None:
        if not self.selected_sale_id:
            messagebox.showwarning("Facturation", "Selectionnez une facture.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter la facture en PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"facture_{self.selected_sale_id}.pdf",
        )
        if not path:
            return
        exported = pharmacy_service.export_invoice_pdf(self.selected_sale_id, path)
        pharmacy_service.record_audit(self.current_user.id, "exporter", "facture", f"Export PDF facture {self.selected_sale_id} vers {exported}", self.selected_sale_id)
        messagebox.showinfo("Facturation", f"Facture PDF exportee: {exported}")

    def print_selected(self) -> None:
        if not self.selected_sale_id:
            messagebox.showwarning("Facturation", "Selectionnez une facture.")
            return
        printed = pharmacy_service.print_invoice(self.selected_sale_id)
        pharmacy_service.record_audit(self.current_user.id, "imprimer", "facture", f"Impression facture {self.selected_sale_id} via {printed}", self.selected_sale_id)
        messagebox.showinfo("Facturation", f"Impression envoyee via: {printed}")

    def reset_search(self) -> None:
        self.search_var.set("")
        self.use_start_var.set(False)
        self.use_end_var.set(False)
        self.start_date_picker.set_date(datetime.today())
        self.end_date_picker.set_date(datetime.today())
        self.refresh()

    def _validate_date_filters(self) -> bool:
        start_value = self.start_date_var.get().strip() if self.use_start_var.get() else ""
        end_value = self.end_date_var.get().strip() if self.use_end_var.get() else ""
        try:
            start_date = datetime.strptime(start_value, "%Y-%m-%d") if start_value else None
            end_date = datetime.strptime(end_value, "%Y-%m-%d") if end_value else None
        except ValueError:
            messagebox.showerror("Facturation", "Les dates doivent etre au format AAAA-MM-JJ.")
            return False
        if start_date and end_date and start_date > end_date:
            messagebox.showerror("Facturation", "La date de debut doit etre anterieure ou egale a la date de fin.")
            return False
        return True