from __future__ import annotations

from datetime import date

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


def initialize_database() -> None:
    schema = MYSQL_SCHEMA if db.engine == "mysql" else SQLITE_SCHEMA
    for statement in schema:
        db.execute(statement)
    seed_default_admin()


def seed_default_admin() -> None:
    from app.services.auth_service import hash_password

    existing = db.fetch_one("SELECT id FROM users WHERE username = ?", ("admin",))
    if existing:
        return

    db.execute(
        """
        INSERT INTO users (full_name, username, password, role, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "Administrateur",
            "admin",
            hash_password("admin123"),
            "administrateur",
            1,
            date.today().isoformat(),
        ),
    )