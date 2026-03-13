from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


APP_FOLDER_NAME = "PharmaDesk"
BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_storage_root() -> Path:
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_FOLDER_NAME
        return Path.home() / f".{APP_FOLDER_NAME.lower()}"
    return BASE_DIR


STORAGE_ROOT = _resolve_storage_root()
DATA_DIR = STORAGE_ROOT / "data"
CONFIG_PATH = STORAGE_ROOT / "config.json"


@dataclass(slots=True)
class AppConfig:
    db_engine: str = "sqlite"
    sqlite_path: str = str(DATA_DIR / "pharmacy.db")
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "pharmacy_db"
    low_stock_threshold: int = 10
    github_owner: str = "SteadEvent7"
    github_repo: str = "pharmadesk"
    auto_check_updates: bool = False
    update_manifest_url: str = ""
    update_download_dir: str = str(DATA_DIR / "updates")
    update_installer_args: str = "/CLOSEAPPLICATIONS /NORESTART"
    currency_code: str = "XOF"

    @classmethod
    def load(cls) -> "AppConfig":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            config = cls()
            CONFIG_PATH.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
            return config

        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return cls(**payload)

    def save(self) -> None:
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


CONFIG = AppConfig.load()