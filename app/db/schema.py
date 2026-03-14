from __future__ import annotations

from datetime import date

from app.config import CONFIG
from app.db.connection import db


SQLITE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        must_change_password INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        email TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        purchase_price REAL NOT NULL,
        sale_price REAL NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        expiration_date TEXT NOT NULL,
        supplier_id INTEGER,
        description TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        movement_type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        reason TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_number TEXT NOT NULL UNIQUE,
        sale_date TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        total_amount REAL NOT NULL,
        seller_id INTEGER,
        FOREIGN KEY (seller_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id),
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS maintenance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT NOT NULL,
        source_path TEXT,
        target_path TEXT,
        safety_backup_path TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """,
]


MYSQL_SCHEMA = [
    statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INTEGER PRIMARY KEY AUTO_INCREMENT")
    .replace("TEXT", "VARCHAR(255)")
    .replace("REAL", "DECIMAL(10,2)")
    .replace("created_at VARCHAR(255)", "created_at DATETIME")
    .replace("sale_date VARCHAR(255)", "sale_date DATETIME")
    .replace("expiration_date VARCHAR(255)", "expiration_date DATE")
    for statement in SQLITE_SCHEMA
]


def initialize_database(progress_callback=None) -> None:
    schema = MYSQL_SCHEMA if db.engine == "mysql" else SQLITE_SCHEMA
    total_steps = len(schema) + 4
    for index, statement in enumerate(schema, start=1):
        db.execute(statement)
        if callable(progress_callback):
            progress_callback(index / total_steps)
    ensure_users_schema()
    if callable(progress_callback):
        progress_callback((len(schema) + 1) / total_steps)
    ensure_sales_schema()
    if callable(progress_callback):
        progress_callback((len(schema) + 2) / total_steps)
    seed_default_admin()
    if callable(progress_callback):
        progress_callback((len(schema) + 3) / total_steps)
    clear_non_admin_password_change_flags()
    if callable(progress_callback):
        progress_callback(1.0)


def _get_table_columns(table_name: str) -> set[str]:
    if db.engine == "mysql":
        columns = db.fetch_all(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            """,
            (CONFIG.mysql_database, table_name),
        )
        return {column["COLUMN_NAME"] for column in columns}

    columns = db.fetch_all(f"PRAGMA table_info({table_name})")
    return {column["name"] for column in columns}


def ensure_users_schema() -> None:
    column_names = _get_table_columns("users")

    if "must_change_password" not in column_names:
        db.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")


def ensure_sales_schema() -> None:
    column_names = _get_table_columns("sales")

    if "subtotal_amount" not in column_names:
        db.execute("ALTER TABLE sales ADD COLUMN subtotal_amount REAL NOT NULL DEFAULT 0")
    if "tax_amount" not in column_names:
        db.execute("ALTER TABLE sales ADD COLUMN tax_amount REAL NOT NULL DEFAULT 0")
    if "received_amount" not in column_names:
        db.execute("ALTER TABLE sales ADD COLUMN received_amount REAL")
    if "change_amount" not in column_names:
        db.execute("ALTER TABLE sales ADD COLUMN change_amount REAL NOT NULL DEFAULT 0")

    db.execute("UPDATE sales SET subtotal_amount = total_amount WHERE subtotal_amount = 0 AND total_amount <> 0")
    db.execute("UPDATE sales SET tax_amount = 0 WHERE tax_amount IS NULL")
    db.execute("UPDATE sales SET change_amount = 0 WHERE change_amount IS NULL")


def seed_default_admin() -> None:
    from app.services.auth_service import DEFAULT_DELIVERED_PASSWORD, DEFAULT_DELIVERED_USERNAME, hash_password

    existing = db.fetch_one("SELECT id FROM users WHERE username = ?", (DEFAULT_DELIVERED_USERNAME,))
    if existing:
        db.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ? AND password = ?",
            (DEFAULT_DELIVERED_USERNAME, hash_password(DEFAULT_DELIVERED_PASSWORD)),
        )
        return

    db.execute(
        """
        INSERT INTO users (full_name, username, password, role, is_active, must_change_password, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Administrateur",
            DEFAULT_DELIVERED_USERNAME,
            hash_password(DEFAULT_DELIVERED_PASSWORD),
            "administrateur",
            1,
            1,
            date.today().isoformat(),
        ),
    )


def clear_non_admin_password_change_flags() -> None:
    from app.services.auth_service import DEFAULT_DELIVERED_USERNAME

    db.execute(
        "UPDATE users SET must_change_password = 0 WHERE username <> ? AND must_change_password <> 0",
        (DEFAULT_DELIVERED_USERNAME,),
    )