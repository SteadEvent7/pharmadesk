from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import CONFIG

try:
    import mysql.connector  # type: ignore
except ImportError:  # pragma: no cover
    mysql = None


class DatabaseManager:
    def __init__(self) -> None:
        self.engine = CONFIG.db_engine.lower()
        self.sqlite_path = Path(CONFIG.sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    def _prepare_query(self, query: str) -> str:
        if self.engine == "mysql":
            return query.replace("?", "%s")
        return query

    @contextmanager
    def get_connection(self) -> Iterator[Any]:
        if self.engine == "mysql":
            if mysql is None:
                raise RuntimeError(
                    "Le connecteur MySQL n'est pas installe. Ajoutez mysql-connector-python."
                )
            connection = mysql.connector.connect(
                host=CONFIG.mysql_host,
                port=CONFIG.mysql_port,
                user=CONFIG.mysql_user,
                password=CONFIG.mysql_password,
                database=CONFIG.mysql_database,
            )
        else:
            connection = sqlite3.connect(self.sqlite_path)
            connection.row_factory = sqlite3.Row

        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(self._prepare_query(query), params)

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(self._prepare_query(query), params)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def execute_many(self, query: str, params_list: list[tuple[Any, ...]]) -> None:
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.executemany(self._prepare_query(query), params_list)


db = DatabaseManager()