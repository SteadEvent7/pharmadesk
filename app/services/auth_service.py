from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.db.connection import db


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class AuthenticatedUser:
    id: int
    full_name: str
    username: str
    role: str


class AuthService:
    def login(self, username: str, password: str) -> AuthenticatedUser | None:
        record = db.fetch_one(
            """
            SELECT id, full_name, username, role
            FROM users
            WHERE username = ? AND password = ? AND is_active = 1
            """,
            (username, hash_password(password)),
        )
        if not record:
            return None
        return AuthenticatedUser(**record)


auth_service = AuthService()