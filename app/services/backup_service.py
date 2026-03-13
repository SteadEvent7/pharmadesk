from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.config import CONFIG, DATA_DIR
from app.db.connection import db


class BackupService:
    def _record_maintenance_event(
        self,
        user_id: int | None,
        event_type: str,
        source_path: str | None,
        target_path: str | None,
        safety_backup_path: str | None = None,
    ) -> None:
        db.execute(
            """
            INSERT INTO maintenance_logs (user_id, event_type, source_path, target_path, safety_backup_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, event_type, source_path, target_path, safety_backup_path, datetime.now().isoformat(timespec="seconds")),
        )

    def list_maintenance_logs(self, limit: int = 100) -> list[dict[str, object]]:
        return db.fetch_all(
            """
            SELECT maintenance_logs.id, maintenance_logs.event_type, maintenance_logs.source_path,
                   maintenance_logs.target_path, maintenance_logs.safety_backup_path, maintenance_logs.created_at,
                   users.full_name AS user_name
            FROM maintenance_logs
            LEFT JOIN users ON users.id = maintenance_logs.user_id
            ORDER BY maintenance_logs.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def create_sqlite_backup(self, user_id: int | None = None) -> Path:
        source = Path(CONFIG.sqlite_path)
        if not source.exists():
            raise FileNotFoundError("La base SQLite n'existe pas encore.")
        backup_dir = DATA_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"pharmacy_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(source, backup_path)
        self._record_maintenance_event(user_id, "backup", str(source), str(backup_path))
        return backup_path

    def create_pre_restore_backup(self) -> Path:
        source = Path(CONFIG.sqlite_path)
        if not source.exists():
            raise FileNotFoundError("La base SQLite actuelle est introuvable.")
        backup_dir = DATA_DIR / "backups" / "pre_restore"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"pharmacy_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(source, backup_path)
        return backup_path

    def restore_sqlite_backup(self, backup_file: str, user_id: int | None = None) -> tuple[Path, Path | None]:
        source = Path(backup_file)
        if not source.exists():
            raise FileNotFoundError("Le fichier de sauvegarde est introuvable.")
        destination = Path(CONFIG.sqlite_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        safety_backup: Path | None = None
        if destination.exists():
            safety_backup = self.create_pre_restore_backup()
        shutil.copy2(source, destination)
        self._record_maintenance_event(
            user_id,
            "restore",
            str(source),
            str(destination),
            str(safety_backup) if safety_backup is not None else None,
        )
        return destination, safety_backup


backup_service = BackupService()