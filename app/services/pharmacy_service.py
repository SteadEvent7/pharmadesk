from __future__ import annotations

import csv
import subprocess
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import CONFIG
from app.db.connection import db
from app.utils.currency import format_currency


class PharmacyService:
    DEFAULT_TAX_RATE = 0.0
    EXPIRING_SOON_DAYS = 30

    def record_audit(
        self,
        user_id: int | None,
        action: str,
        entity_type: str,
        details: str,
        entity_id: int | None = None,
    ) -> None:
        db.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, action, entity_type, entity_id, details, datetime.now().isoformat(timespec="seconds")),
        )

    def list_audit_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return db.fetch_all(
            """
            SELECT audit_logs.id, audit_logs.action, audit_logs.entity_type, audit_logs.entity_id,
                   audit_logs.details, audit_logs.created_at, users.full_name AS user_name
            FROM audit_logs
            LEFT JOIN users ON users.id = audit_logs.user_id
            ORDER BY audit_logs.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    @staticmethod
    def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
        month_index = (year * 12 + (month - 1)) + offset
        return month_index // 12, (month_index % 12) + 1

    def list_suppliers(self) -> list[dict[str, Any]]:
        return db.fetch_all("SELECT * FROM suppliers ORDER BY name")

    def save_supplier(self, supplier_id: int | None, data: dict[str, Any], actor_user_id: int | None = None) -> None:
        if supplier_id:
            db.execute(
                """
                UPDATE suppliers
                SET name = ?, phone = ?, address = ?, email = ?
                WHERE id = ?
                """,
                (data["name"], data["phone"], data["address"], data["email"], supplier_id),
            )
            self.record_audit(actor_user_id, "modifier", "fournisseur", f"Fournisseur modifie: {data['name']}", supplier_id)
            return
        db.execute(
            """
            INSERT INTO suppliers (name, phone, address, email, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (data["name"], data["phone"], data["address"], data["email"], date.today().isoformat()),
        )
        created = db.fetch_one("SELECT id FROM suppliers WHERE name = ? ORDER BY id DESC", (data["name"],))
        self.record_audit(actor_user_id, "ajouter", "fournisseur", f"Fournisseur cree: {data['name']}", created["id"] if created else None)

    def delete_supplier(self, supplier_id: int, actor_user_id: int | None = None) -> None:
        supplier = db.fetch_one("SELECT name FROM suppliers WHERE id = ?", (supplier_id,))
        db.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
        self.record_audit(actor_user_id, "supprimer", "fournisseur", f"Fournisseur supprime: {(supplier or {}).get('name', supplier_id)}", supplier_id)

    def list_medicines(self, search: str = "") -> list[dict[str, Any]]:
        if search:
            token = f"%{search}%"
            return db.fetch_all(
                """
                SELECT medicines.*, suppliers.name AS supplier_name
                FROM medicines
                LEFT JOIN suppliers ON suppliers.id = medicines.supplier_id
                WHERE medicines.name LIKE ? OR medicines.code LIKE ? OR medicines.category LIKE ?
                ORDER BY medicines.name
                """,
                (token, token, token),
            )
        return db.fetch_all(
            """
            SELECT medicines.*, suppliers.name AS supplier_name
            FROM medicines
            LEFT JOIN suppliers ON suppliers.id = medicines.supplier_id
            ORDER BY medicines.name
            """
        )

    def save_medicine(self, medicine_id: int | None, data: dict[str, Any], actor_user_id: int | None = None) -> None:
        params = (
            data["code"],
            data["name"],
            data["category"],
            data["purchase_price"],
            data["sale_price"],
            data["quantity"],
            data["expiration_date"],
            data["supplier_id"],
            data["description"],
        )
        if medicine_id:
            existing = db.fetch_one("SELECT quantity, name FROM medicines WHERE id = ?", (medicine_id,))
            db.execute(
                """
                UPDATE medicines
                SET code = ?, name = ?, category = ?, purchase_price = ?, sale_price = ?,
                    quantity = ?, expiration_date = ?, supplier_id = ?, description = ?
                WHERE id = ?
                """,
                params + (medicine_id,),
            )
            if existing is not None:
                previous_quantity = int(existing["quantity"])
                new_quantity = int(data["quantity"])
                if new_quantity != previous_quantity:
                    movement_type = "entree" if new_quantity > previous_quantity else "sortie"
                    db.execute(
                        """
                        INSERT INTO stock_movements (medicine_id, movement_type, quantity, reason, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            medicine_id,
                            movement_type,
                            abs(new_quantity - previous_quantity),
                            "Ajustement fiche produit",
                            datetime.now().isoformat(timespec="seconds"),
                        ),
                    )
            self.record_audit(actor_user_id, "modifier", "medicament", f"Medicament modifie: {data['name']}", medicine_id)
            return

        db.execute(
            """
            INSERT INTO medicines (
                code, name, category, purchase_price, sale_price, quantity,
                expiration_date, supplier_id, description, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            params + (date.today().isoformat(),),
        )
        created = db.fetch_one("SELECT id FROM medicines WHERE code = ?", (data["code"],))
        if created is not None and int(data["quantity"]) > 0:
            db.execute(
                """
                INSERT INTO stock_movements (medicine_id, movement_type, quantity, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created["id"],
                    "entree",
                    int(data["quantity"]),
                    "Stock initial produit",
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        self.record_audit(actor_user_id, "ajouter", "medicament", f"Medicament cree: {data['name']}", created["id"] if created else None)

    def delete_medicine(self, medicine_id: int, actor_user_id: int | None = None) -> None:
        medicine = db.fetch_one("SELECT name FROM medicines WHERE id = ?", (medicine_id,))
        db.execute("DELETE FROM medicines WHERE id = ?", (medicine_id,))
        self.record_audit(actor_user_id, "supprimer", "medicament", f"Medicament supprime: {(medicine or {}).get('name', medicine_id)}", medicine_id)

    def list_users(self) -> list[dict[str, Any]]:
        return db.fetch_all(
            "SELECT id, full_name, username, role, is_active, created_at FROM users ORDER BY full_name"
        )

    def verify_user_password(self, user_id: int, password: str, actor_user_id: int | None = None) -> bool:
        from app.services.auth_service import hash_password

        user = db.fetch_one("SELECT username FROM users WHERE id = ?", (user_id,))
        if not user:
            raise ValueError("Utilisateur introuvable")

        matched = db.fetch_one(
            "SELECT id FROM users WHERE id = ? AND password = ?",
            (user_id, hash_password(password)),
        ) is not None
        outcome = "succes" if matched else "echec"
        self.record_audit(
            actor_user_id,
            "verifier_mot_de_passe",
            "utilisateur",
            f"Verification de mot de passe {outcome} pour {user['username']}",
            user_id,
        )
        return matched

    def save_user(self, user_id: int | None, data: dict[str, Any], actor_user_id: int | None = None) -> None:
        from app.services.auth_service import hash_password

        if user_id:
            if data.get("password"):
                db.execute(
                    """
                    UPDATE users
                    SET full_name = ?, username = ?, password = ?, role = ?, is_active = ?
                    WHERE id = ?
                    """,
                    (
                        data["full_name"],
                        data["username"],
                        hash_password(data["password"]),
                        data["role"],
                        data["is_active"],
                        user_id,
                    ),
                )
            else:
                db.execute(
                    """
                    UPDATE users
                    SET full_name = ?, username = ?, role = ?, is_active = ?
                    WHERE id = ?
                    """,
                    (data["full_name"], data["username"], data["role"], data["is_active"], user_id),
                )
            self.record_audit(actor_user_id, "modifier", "utilisateur", f"Utilisateur modifie: {data['username']}", user_id)
            return

        db.execute(
            """
            INSERT INTO users (full_name, username, password, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["full_name"],
                data["username"],
                hash_password(data["password"]),
                data["role"],
                data["is_active"],
                date.today().isoformat(),
            ),
        )
        created = db.fetch_one("SELECT id FROM users WHERE username = ?", (data["username"],))
        self.record_audit(actor_user_id, "ajouter", "utilisateur", f"Utilisateur cree: {data['username']}", created["id"] if created else None)

    def delete_user(self, user_id: int, actor_user_id: int | None = None) -> None:
        user = db.fetch_one("SELECT username FROM users WHERE id = ?", (user_id,))
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.record_audit(actor_user_id, "supprimer", "utilisateur", f"Utilisateur supprime: {(user or {}).get('username', user_id)}", user_id)

    def adjust_stock(self, medicine_id: int, quantity: int, movement_type: str, reason: str, actor_user_id: int | None = None) -> None:
        medicine = db.fetch_one("SELECT quantity FROM medicines WHERE id = ?", (medicine_id,))
        if not medicine:
            raise ValueError("Medicament introuvable")

        current_quantity = int(medicine["quantity"])
        new_quantity = current_quantity + quantity if movement_type == "entree" else current_quantity - quantity
        if new_quantity < 0:
            raise ValueError("Stock insuffisant")

        db.execute("UPDATE medicines SET quantity = ? WHERE id = ?", (new_quantity, medicine_id))
        db.execute(
            """
            INSERT INTO stock_movements (medicine_id, movement_type, quantity, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (medicine_id, movement_type, quantity, reason, datetime.now().isoformat(timespec="seconds")),
        )
        self.record_audit(actor_user_id, movement_type, "stock", f"Mouvement stock {movement_type} sur medicament {medicine_id}, quantite={quantity}, motif={reason}", medicine_id)

    def get_stock_alerts(self) -> dict[str, list[dict[str, Any]]]:
        medicines = self.list_medicines()
        low_stock = [item for item in medicines if int(item["quantity"]) <= CONFIG.low_stock_threshold]
        today = date.today()
        expired = [item for item in medicines if date.fromisoformat(item["expiration_date"]) < today]
        expiring_soon = [
            item
            for item in medicines
            if today <= date.fromisoformat(item["expiration_date"]) <= today + timedelta(days=30)
        ]
        return {"low_stock": low_stock, "expired": expired, "expiring_soon": expiring_soon}

    def get_alert_notifications(self) -> list[dict[str, Any]]:
        alerts = self.get_stock_alerts()
        notifications: list[dict[str, Any]] = []
        seen: set[tuple[int, str]] = set()

        for category, label, severity in (
            ("expired", "Produit expire", "critique"),
            ("expiring_soon", "Expiration proche", "attention"),
            ("low_stock", "Stock faible", "attention"),
        ):
            for item in alerts[category]:
                key = (int(item["id"]), category)
                if key in seen:
                    continue
                seen.add(key)
                notifications.append(
                    {
                        "medicine_id": int(item["id"]),
                        "medicine_name": item["name"],
                        "category": category,
                        "label": label,
                        "severity": severity,
                        "quantity": int(item["quantity"]),
                        "expiration_date": item["expiration_date"],
                    }
                )
        return notifications

    def calculate_sale_totals(self, items: list[dict[str, Any]], tax_rate: float = DEFAULT_TAX_RATE) -> dict[str, float]:
        subtotal = round(sum(float(item["line_total"]) for item in items), 2)
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)
        return {"subtotal": subtotal, "tax_amount": tax_amount, "total": total}

    def get_recent_invoices(self, limit: int = 8) -> list[dict[str, Any]]:
        return db.fetch_all(
            """
            SELECT sales.id, sales.sale_number, sales.sale_date, sales.total_amount,
                   users.full_name AS seller_name
            FROM sales
            LEFT JOIN users ON users.id = sales.seller_id
            ORDER BY sales.sale_date DESC
            LIMIT ?
            """,
            (limit,),
        )

    def create_sale(
        self,
        sale_number: str,
        payment_method: str,
        seller_id: int,
        items: list[dict[str, Any]],
        received_amount: float | None = None,
        tax_rate: float = DEFAULT_TAX_RATE,
    ) -> int:
        totals = self.calculate_sale_totals(items, tax_rate)
        subtotal_amount = totals["subtotal"]
        tax_amount = totals["tax_amount"]
        total_amount = totals["total"]
        if received_amount is None:
            received_amount = total_amount
        change_amount = round(max(received_amount - total_amount, 0.0), 2)
        with db.get_connection() as connection:
            cursor = connection.cursor()
            placeholder = db._prepare_query
            cursor.execute(
                placeholder(
                    """
                INSERT INTO sales (
                    sale_number, sale_date, payment_method, total_amount,
                    subtotal_amount, tax_amount, received_amount, change_amount, seller_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ),
                (
                    sale_number,
                    datetime.now().isoformat(timespec="seconds"),
                    payment_method,
                    total_amount,
                    subtotal_amount,
                    tax_amount,
                    received_amount,
                    change_amount,
                    seller_id,
                ),
            )
            sale_id = cursor.lastrowid

            for item in items:
                cursor.execute(
                    placeholder(
                        """
                    INSERT INTO sale_items (sale_id, medicine_id, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ),
                    (
                        sale_id,
                        item["medicine_id"],
                        item["quantity"],
                        item["unit_price"],
                        item["line_total"],
                    ),
                )
                cursor.execute(
                    placeholder("UPDATE medicines SET quantity = quantity - ? WHERE id = ?"),
                    (item["quantity"], item["medicine_id"]),
                )
                cursor.execute(
                    placeholder(
                        """
                    INSERT INTO stock_movements (medicine_id, movement_type, quantity, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ),
                    (
                        item["medicine_id"],
                        "sortie",
                        item["quantity"],
                        f"Vente {sale_number}",
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
            self.record_audit(seller_id, "vente", "facture", f"Vente {sale_number} enregistree, montant={format_currency(total_amount)}", sale_id)
            return int(sale_id)

    def build_invoice(
        self,
        sale_number: str,
        cashier_name: str,
        payment_method: str,
        items: list[dict[str, Any]],
        received_amount: float | None = None,
        tax_rate: float = DEFAULT_TAX_RATE,
    ) -> str:
        totals = self.calculate_sale_totals(items, tax_rate)
        subtotal = totals["subtotal"]
        tax_amount = totals["tax_amount"]
        total = totals["total"]
        if received_amount is None:
            received_amount = total
        change_amount = max(received_amount - total, 0.0)
        lines = [
            "PHARMADESK",
            f"Facture: {sale_number}",
            f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Caissier: {cashier_name}",
            f"Paiement: {payment_method}",
            "-" * 42,
        ]
        for item in items:
            lines.append(
                f"{item['name']} x{item['quantity']} @ {format_currency(float(item['unit_price']))} = {format_currency(float(item['line_total']))}"
            )
        lines.extend(
            [
                "-" * 42,
                f"Total HT: {format_currency(subtotal)}",
                f"Taxe: {format_currency(tax_amount)}",
                f"Total final: {format_currency(total)}",
                f"Montant encaisse: {format_currency(received_amount)}",
                f"Monnaie rendue: {format_currency(change_amount)}",
                "Merci pour votre visite.",
            ]
        )
        return "\n".join(lines)

    def get_dashboard_metrics(self) -> dict[str, Any]:
        sales = db.fetch_all("SELECT sale_date, total_amount FROM sales ORDER BY sale_date DESC")
        medicines_count = db.fetch_one("SELECT COUNT(*) AS total FROM medicines") or {"total": 0}
        suppliers_count = db.fetch_one("SELECT COUNT(*) AS total FROM suppliers") or {"total": 0}
        users_count = db.fetch_one("SELECT COUNT(*) AS total FROM users") or {"total": 0}
        today = date.today().isoformat()
        today_sales_total = sum(float(item["total_amount"]) for item in sales if item["sale_date"].startswith(today))
        alerts = self.get_stock_alerts()
        return {
            "medicines_total": medicines_count["total"],
            "suppliers_total": suppliers_count["total"],
            "users_total": users_count["total"],
            "sales_total_today": round(today_sales_total, 2),
            "low_stock_total": len(alerts["low_stock"]),
            "expired_total": len(alerts["expired"]),
        }

    def get_sales_report(self) -> list[dict[str, Any]]:
        rows = db.fetch_all("SELECT sale_date, total_amount FROM sales ORDER BY sale_date")
        grouped: dict[str, float] = defaultdict(float)
        for row in rows:
            grouped[row["sale_date"][:10]] += float(row["total_amount"])
        return [{"date": key, "total": round(value, 2)} for key, value in grouped.items()]

    def get_sales_trend(self, period_months: int = 12) -> list[dict[str, Any]]:
        now = date.today()
        months: list[tuple[int, int]] = []
        for offset in range(-(period_months - 1), 1):
            months.append(self._shift_month(now.year, now.month, offset))

        grouped = {f"{year:04d}-{month:02d}": 0.0 for year, month in months}
        rows = db.fetch_all("SELECT sale_date, total_amount FROM sales ORDER BY sale_date")
        for row in rows:
            key = row["sale_date"][:7]
            if key in grouped:
                grouped[key] += float(row["total_amount"])

        result: list[dict[str, Any]] = []
        for year, month in months:
            key = f"{year:04d}-{month:02d}"
            result.append({"label": key[5:7], "total": round(grouped[key], 2), "period": key})
        return result

    def get_top_selling_products(self, period_months: int = 12, limit: int = 10) -> list[dict[str, Any]]:
        now = date.today()
        earliest_year, earliest_month = self._shift_month(now.year, now.month, -(period_months - 1))
        earliest_key = f"{earliest_year:04d}-{earliest_month:02d}"

        rows = db.fetch_all(
            """
            SELECT sales.sale_date, medicines.name AS medicine_name, sale_items.quantity
            FROM sale_items
            INNER JOIN sales ON sales.id = sale_items.sale_id
            INNER JOIN medicines ON medicines.id = sale_items.medicine_id
            ORDER BY sales.sale_date DESC
            """
        )
        ranking: dict[str, int] = defaultdict(int)
        for row in rows:
            if row["sale_date"][:7] < earliest_key:
                continue
            ranking[row["medicine_name"]] += int(row["quantity"])

        ordered = sorted(ranking.items(), key=lambda item: item[1], reverse=True)[:limit]
        return [{"name": name, "quantity": quantity} for name, quantity in ordered]

    def list_invoices(self) -> list[dict[str, Any]]:
        return self.search_invoices()

    def search_invoices(self, query: str = "", start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
        base_query = (
            """
            SELECT sales.id, sales.sale_number, sales.sale_date, sales.payment_method, sales.total_amount,
                   sales.subtotal_amount, sales.tax_amount, sales.received_amount, sales.change_amount,
                   users.full_name AS seller_name
            FROM sales
            LEFT JOIN users ON users.id = sales.seller_id
            """
        )
        clauses: list[str] = []
        params: list[str] = []

        if query.strip():
            token = f"%{query.strip()}%"
            clauses.append("(sales.sale_number LIKE ? OR sales.sale_date LIKE ?)")
            params.extend([token, token])

        if start_date.strip():
            clauses.append("substr(sales.sale_date, 1, 10) >= ?")
            params.append(start_date.strip())

        if end_date.strip():
            clauses.append("substr(sales.sale_date, 1, 10) <= ?")
            params.append(end_date.strip())

        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return db.fetch_all(base_query + where_clause + " ORDER BY sales.sale_date DESC", tuple(params))

    def get_invoice_items(self, sale_id: int) -> list[dict[str, Any]]:
        return db.fetch_all(
            """
            SELECT medicines.name AS medicine_name, sale_items.quantity, sale_items.unit_price, sale_items.line_total
            FROM sale_items
            INNER JOIN medicines ON medicines.id = sale_items.medicine_id
            WHERE sale_items.sale_id = ?
            ORDER BY sale_items.id ASC
            """,
            (sale_id,),
        )

    def build_invoice_from_sale(self, sale_id: int) -> str:
        invoice = db.fetch_one(
            """
             SELECT sales.sale_number, sales.sale_date, sales.payment_method, sales.total_amount,
                 sales.subtotal_amount, sales.tax_amount, sales.received_amount, sales.change_amount,
                   users.full_name AS seller_name
            FROM sales
            LEFT JOIN users ON users.id = sales.seller_id
            WHERE sales.id = ?
            """,
            (sale_id,),
        )
        if not invoice:
            raise ValueError("Facture introuvable")

        lines = [
            "PHARMADESK",
            f"Facture: {invoice['sale_number']}",
            f"Date: {invoice['sale_date']}",
            f"Caissier: {invoice.get('seller_name') or '-'}",
            f"Paiement: {invoice['payment_method']}",
            "-" * 42,
        ]
        for item in self.get_invoice_items(sale_id):
            lines.append(
                f"{item['medicine_name']} x{item['quantity']} @ {format_currency(float(item['unit_price']))} = {format_currency(float(item['line_total']))}"
            )
        received_amount = float(invoice["received_amount"]) if invoice.get("received_amount") is not None else float(invoice["total_amount"])
        lines.extend(
            [
                "-" * 42,
                f"Total HT: {format_currency(float(invoice.get('subtotal_amount') or invoice['total_amount']))}",
                f"Taxe: {format_currency(float(invoice.get('tax_amount') or 0))}",
                f"Total final: {format_currency(float(invoice['total_amount']))}",
                f"Montant encaisse: {format_currency(received_amount)}",
                f"Monnaie rendue: {format_currency(float(invoice.get('change_amount') or 0))}",
                "Merci pour votre visite.",
            ]
        )
        return "\n".join(lines)

    def export_invoices_csv(self, destination: str, query: str = "", start_date: str = "", end_date: str = "") -> Path:
        invoices = self.search_invoices(query, start_date, end_date)
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow([
                "numero_facture",
                "date",
                "mode_paiement",
                "caissier",
                "produit",
                "quantite",
                "prix_unitaire",
                "sous_total",
                "total_facture",
            ])
            for invoice in invoices:
                items = self.get_invoice_items(int(invoice["id"]))
                for item in items:
                    writer.writerow(
                        [
                            invoice["sale_number"],
                            invoice["sale_date"],
                            invoice["payment_method"],
                            invoice.get("seller_name") or "-",
                            item["medicine_name"],
                            item["quantity"],
                            f"{float(item['unit_price']):.2f}",
                            f"{float(item['line_total']):.2f}",
                            f"{float(invoice['total_amount']):.2f}",
                        ]
                    )
        return output

    def get_stock_movements(self, limit: int = 200) -> list[dict[str, Any]]:
        return db.fetch_all(
            """
            SELECT stock_movements.id, medicines.code AS medicine_code, medicines.name AS medicine_name,
                   stock_movements.movement_type, stock_movements.quantity, stock_movements.reason,
                   stock_movements.created_at
            FROM stock_movements
            INNER JOIN medicines ON medicines.id = stock_movements.medicine_id
            ORDER BY stock_movements.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def export_invoice_text(self, sale_id: int, destination: str) -> Path:
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.build_invoice_from_sale(sale_id), encoding="utf-8")
        return output

    def export_invoice_pdf(self, sale_id: int, destination: str) -> Path:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas

        invoice = db.fetch_one(
            """
             SELECT sales.sale_number, sales.sale_date, sales.payment_method, sales.total_amount,
                 sales.subtotal_amount, sales.tax_amount, sales.received_amount, sales.change_amount,
                   users.full_name AS seller_name
            FROM sales
            LEFT JOIN users ON users.id = sales.seller_id
            WHERE sales.id = ?
            """,
            (sale_id,),
        )
        if not invoice:
            raise ValueError("Facture introuvable")

        items = self.get_invoice_items(sale_id)
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)

        pdf = canvas.Canvas(str(output), pagesize=A4)
        width, height = A4
        x = 50
        y = height - 60

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(x, y, "PHARMADESK")
        y -= 28
        pdf.setFont("Helvetica", 11)
        pdf.drawString(x, y, f"Facture: {invoice['sale_number']}")
        y -= 18
        pdf.drawString(x, y, f"Date: {invoice['sale_date']}")
        y -= 18
        pdf.drawString(x, y, f"Caissier: {invoice.get('seller_name') or '-'}")
        y -= 18
        pdf.drawString(x, y, f"Paiement: {invoice['payment_method']}")
        y -= 28

        pdf.setFont("Helvetica-Bold", 10)
        headers = [(x, "Produit"), (320, "Qt"), (380, "Prix U."), (470, "Sous-total")]
        for x_pos, header in headers:
            pdf.drawString(x_pos, y, header)
        y -= 12
        pdf.line(x, y, width - 50, y)
        y -= 18
        pdf.setFont("Helvetica", 10)

        for item in items:
            if y < 80:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica", 10)
            pdf.drawString(x, y, str(item["medicine_name"])[:40])
            pdf.drawRightString(350, y, str(item["quantity"]))
            pdf.drawRightString(445, y, format_currency(float(item["unit_price"])))
            pdf.drawRightString(width - 50, y, format_currency(float(item["line_total"])))
            y -= 18

        y -= 8
        pdf.line(x, y, width - 50, y)
        y -= 22
        pdf.setFont("Helvetica", 11)
        received_amount = float(invoice["received_amount"]) if invoice.get("received_amount") is not None else float(invoice["total_amount"])
        summary_lines = [
            f"Total HT: {format_currency(float(invoice.get('subtotal_amount') or invoice['total_amount']))}",
            f"Taxe: {format_currency(float(invoice.get('tax_amount') or 0))}",
            f"Total final: {format_currency(float(invoice['total_amount']))}",
            f"Montant encaisse: {format_currency(received_amount)}",
            f"Monnaie rendue: {format_currency(float(invoice.get('change_amount') or 0))}",
        ]
        for line in summary_lines:
            text_width = stringWidth(line, "Helvetica", 11)
            pdf.drawString(width - 50 - text_width, y, line)
            y -= 16
        pdf.save()
        return output

    def print_invoice(self, sale_id: int) -> Path:
        output = Path(tempfile.gettempdir()) / "pharmadesk_print_invoice.txt"
        self.export_invoice_text(sale_id, str(output))
        subprocess.run(["notepad.exe", "/p", str(output)], check=False)
        return output

    def get_recent_sales(self) -> list[dict[str, Any]]:
        return db.fetch_all(
            """
            SELECT sales.id, sales.sale_number, sales.sale_date, sales.payment_method, sales.total_amount, users.full_name AS seller_name
            FROM sales
            LEFT JOIN users ON users.id = sales.seller_id
            ORDER BY sales.sale_date DESC
            LIMIT 20
            """
        )


pharmacy_service = PharmacyService()