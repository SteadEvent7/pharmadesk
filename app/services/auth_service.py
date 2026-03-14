from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.db.connection import db


DEFAULT_DELIVERED_USERNAME = "admin"
DEFAULT_DELIVERED_PASSWORD = "admin123"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class AuthenticatedUser:
    id: int
    full_name: str
    username: str
    role: str
    requires_password_change: bool = False


class AuthService:
    def login(self, username: str, password: str) -> AuthenticatedUser | None:
        record = db.fetch_one(
            """
            SELECT id, full_name, username, role, must_change_password AS requires_password_change
            FROM users
            WHERE username = ? AND password = ? AND is_active = 1
            """,
            (username, hash_password(password)),
        )
        if not record:
            return None
        record["requires_password_change"] = bool(record.get("requires_password_change")) and record.get("username") == DEFAULT_DELIVERED_USERNAME
        return AuthenticatedUser(**record)

    def change_password(self, user_id: int, new_password: str) -> None:
        db.execute(
            """
            UPDATE users
            SET password = ?, must_change_password = 0
            WHERE id = ?
            """,
            (hash_password(new_password), user_id),
        )


auth_service = AuthService()