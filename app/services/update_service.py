from __future__ import annotations

import hashlib
import json
import logging
import queue
import ssl
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi

from app import APP_PATCH, APP_VERSION
from app.config import CONFIG, DATA_DIR


LOG_DIR = DATA_DIR / "logs"
HISTORY_PATH = DATA_DIR / "update_history.json"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("pharmadesk.update")
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "update.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


@dataclass(slots=True)
class UpdateManifest:
    version: str
    patch: int
    notes: str
    installer_url: str
    installer_name: str
    published_at: str = ""
    sha256: str = ""

    @property
    def display_version(self) -> str:
        return f"{self.version} (patch {self.patch})"


@dataclass(slots=True)
class UpdateCheckResult:
    available: bool
    message: str
    manifest: UpdateManifest | None = None
    error: str | None = None


class UpdateService:
    def __init__(self) -> None:
        self._download_lock = threading.Lock()
        self._download_active = False

    def local_display_version(self) -> str:
        return f"{APP_VERSION} (patch {APP_PATCH})"

    def get_manifest_url(self) -> str:
        configured_url = CONFIG.update_manifest_url.strip()
        if configured_url:
            return configured_url
        owner = CONFIG.github_owner.strip()
        repo = CONFIG.github_repo.strip()
        if owner and repo and owner != "your-org":
            return f"https://raw.githubusercontent.com/{owner}/{repo}/main/update.json"
        raise ValueError("Manifest de mise a jour non configure.")

    def _build_ssl_context(self) -> ssl.SSLContext:
        cafile = certifi.where()
        logger.info("Bundle SSL utilise pour les mises a jour: %s", cafile)
        return ssl.create_default_context(cafile=cafile)

    def check_for_updates(self, source: str = "manuel") -> UpdateCheckResult:
        manifest_url = ""
        try:
            manifest_url = self.get_manifest_url()
            manifest = self.fetch_manifest()
        except ValueError as error:
            logger.warning("Configuration update invalide: %s", error)
            result = UpdateCheckResult(False, str(error), error=str(error))
            self.record_history("verification", "erreur", str(error), source=source)
            return result
        except HTTPError as error:
            logger.warning("Erreur HTTP pendant la verification: %s", error)
            if error.code == 404:
                message = (
                    "Manifest de mise a jour introuvable (404). "
                    "Verifiez que update.json est bien pousse sur GitHub et que l'URL ou la branche configuree est correcte."
                )
            else:
                message = f"Verification des mises a jour impossible (HTTP {error.code})."
            result = UpdateCheckResult(False, message, error=f"{error} | URL: {manifest_url}")
            self.record_history("verification", "erreur", message, source=source)
            return result
        except ssl.SSLCertVerificationError as error:
            logger.warning("Erreur SSL pendant la verification: %s", error)
            message = (
                "Verification des mises a jour impossible: le certificat SSL du serveur n'a pas pu etre verifie. "
                "Installez la derniere version complete de PharmaDesk si le probleme persiste sur ce poste."
            )
            result = UpdateCheckResult(False, message, error=f"{error} | URL: {manifest_url}")
            self.record_history("verification", "erreur", message, source=source)
            return result
        except (URLError, TimeoutError) as error:
            logger.warning("Erreur reseau pendant la verification: %s", error)
            result = UpdateCheckResult(
                False,
                "Verification des mises a jour indisponible. Verifiez votre connexion reseau ou l'URL du manifest.",
                error=f"{error} | URL: {manifest_url}",
            )
            self.record_history("verification", "erreur", result.message, source=source)
            return result
        except Exception as error:
            logger.exception("Erreur inattendue pendant la verification")
            result = UpdateCheckResult(False, "Erreur inattendue pendant la verification des mises a jour.", error=str(error))
            self.record_history("verification", "erreur", result.message, source=source)
            return result

        if self._is_remote_newer(manifest):
            message = f"Nouvelle version disponible: {manifest.display_version}"
            logger.info("Mise a jour disponible detectee: %s", manifest.display_version)
            self.record_history("verification", "disponible", message, manifest=manifest, source=source)
            return UpdateCheckResult(True, message, manifest=manifest)

        logger.info("Application deja a jour: %s", self.local_display_version())
        self.record_history("verification", "ok", "Application deja a jour.", manifest=manifest, source=source)
        return UpdateCheckResult(False, "Application deja a jour.", manifest=manifest)

    def check_for_updates_async(self, root, callback, source: str = "manuel") -> None:
        result_queue: queue.Queue[UpdateCheckResult] = queue.Queue()

        def worker() -> None:
            result_queue.put(self.check_for_updates(source=source))

        def poll() -> None:
            try:
                result = result_queue.get_nowait()
            except queue.Empty:
                root.after(80, poll)
                return
            callback(result)

        threading.Thread(target=worker, daemon=True, name="update-check").start()
        root.after(80, poll)

    def fetch_manifest(self) -> UpdateManifest:
        manifest_url = self.get_manifest_url()
        logger.info("Lecture du manifest distant: %s", manifest_url)
        request = Request(
            manifest_url,
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache",
                "User-Agent": "PharmaDesk-Updater",
            },
        )

        with urlopen(request, timeout=8, context=self._build_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))

        version = str(payload.get("version") or "").strip()
        installer_url = str(payload.get("installer_url") or payload.get("download_url") or "").strip()
        if not version or not installer_url:
            raise ValueError("Le manifest distant doit contenir version et installer_url.")

        patch_value = payload.get("patch", 0)
        try:
            patch = int(patch_value)
        except (TypeError, ValueError) as error:
            raise ValueError("Le champ patch du manifest doit etre numerique.") from error

        installer_name = str(payload.get("installer_name") or Path(urlparse(installer_url).path).name or "PharmaDeskSetup.exe")
        return UpdateManifest(
            version=version,
            patch=patch,
            notes=str(payload.get("notes") or "").strip(),
            installer_url=installer_url,
            installer_name=installer_name,
            published_at=str(payload.get("published_at") or "").strip(),
            sha256=str(payload.get("sha256") or "").strip().lower(),
        )

    def download_update_async(self, root, manifest: UpdateManifest, on_progress, on_complete, source: str = "manuel") -> bool:
        with self._download_lock:
            if self._download_active:
                return False
            self._download_active = True

        event_queue: queue.Queue[tuple[str, object, object, object]] = queue.Queue()

        def worker() -> None:
            try:
                self.record_history("telechargement", "demarre", "Telechargement de l'installateur lance.", manifest=manifest, source=source)
                installer_path = self._download_update(manifest, event_queue)
                self.record_history("telechargement", "ok", f"Installateur telecharge: {installer_path}", manifest=manifest, source=source)
                event_queue.put(("done", installer_path, None, None))
            except Exception as error:
                logger.exception("Echec du telechargement de mise a jour")
                self.record_history("telechargement", "erreur", f"Telechargement impossible: {error}", manifest=manifest, source=source)
                event_queue.put(("error", f"Telechargement impossible: {error}", None, None))
            finally:
                with self._download_lock:
                    self._download_active = False

        def poll() -> None:
            finished = False
            while True:
                try:
                    event_type, value1, value2, value3 = event_queue.get_nowait()
                except queue.Empty:
                    break

                if event_type == "progress":
                    on_progress(int(value1), int(value2), str(value3))
                elif event_type == "done":
                    installer_path = str(value1)
                    on_complete(True, f"Installateur telecharge: {installer_path}", installer_path)
                    finished = True
                elif event_type == "error":
                    on_complete(False, str(value1), None)
                    finished = True

            if not finished:
                root.after(80, poll)

        threading.Thread(target=worker, daemon=True, name="update-download").start()
        root.after(80, poll)
        return True

    def _download_update(self, manifest: UpdateManifest, event_queue: queue.Queue[tuple[str, object, object, object]]) -> str:
        download_dir = Path(CONFIG.update_download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)

        destination = download_dir / manifest.installer_name
        temp_destination = destination.with_suffix(destination.suffix + ".part")
        logger.info("Telechargement de l'installateur vers %s", destination)

        request = Request(manifest.installer_url, headers={"User-Agent": "PharmaDesk-Updater"})
        with urlopen(request, timeout=20, context=self._build_ssl_context()) as response, temp_destination.open("wb") as output:
            total_size = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                event_queue.put(("progress", downloaded, total_size, "Telechargement de l'installateur"))

        temp_destination.replace(destination)
        if manifest.sha256:
            self._validate_checksum(destination, manifest.sha256)

        logger.info("Telechargement termine: %s", destination)
        return str(destination)

    def _validate_checksum(self, path: Path, expected_sha256: str) -> None:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while True:
                block = stream.read(1024 * 512)
                if not block:
                    break
                digest.update(block)
        actual_sha256 = digest.hexdigest().lower()
        if actual_sha256 != expected_sha256.lower():
            path.unlink(missing_ok=True)
            logger.error("Checksum SHA256 invalide pour %s", path)
            raise ValueError("Le controle d'integrite SHA256 de l'installateur a echoue.")

    def schedule_installer_launch(self, installer_path: str) -> tuple[bool, str]:
        absolute_path = str(Path(installer_path).resolve())
        if not Path(absolute_path).exists():
            self.record_history("installation", "erreur", "Installateur introuvable.", details=absolute_path)
            return False, "Installateur introuvable."

        installer_args = CONFIG.update_installer_args.strip()
        escaped_path = absolute_path.replace("'", "''")
        escaped_args = installer_args.replace("'", "''")
        command_parts = [
            "Start-Sleep -Seconds 1",
            f"Start-Process -FilePath '{escaped_path}'",
        ]
        if installer_args:
            command_parts[-1] += f" -ArgumentList '{escaped_args}'"
        command_parts[-1] += " -Verb RunAs"
        powershell_command = "; ".join(command_parts)

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-WindowStyle",
                    "Hidden",
                    "-Command",
                    powershell_command,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
        except OSError as error:
            logger.exception("Impossible de preparer le lancement de l'installateur")
            self.record_history("installation", "erreur", f"Impossible de lancer l'installateur: {error}", details=absolute_path)
            return False, f"Impossible de lancer l'installateur: {error}"

        logger.info("Installateur programme avec elevation: %s", absolute_path)
        self.record_history("installation", "ok", "Installateur programme avec elevation Windows.", details=absolute_path)
        return True, "L'installateur a ete prepare. L'application va se fermer."

    def list_history(self, limit: int = 100) -> list[dict[str, str]]:
        entries = self._load_history_entries()
        return entries[:limit]

    def record_history(
        self,
        action: str,
        status: str,
        message: str,
        manifest: UpdateManifest | None = None,
        source: str = "manuel",
        details: str = "",
    ) -> None:
        entries = self._load_history_entries()
        entry = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "status": status,
            "source": source,
            "version": manifest.display_version if manifest is not None else "-",
            "details": details or message,
            "message": message,
        }
        entries.insert(0, entry)
        HISTORY_PATH.write_text(json.dumps(entries[:300], indent=2, ensure_ascii=True), encoding="utf-8")

    def _load_history_entries(self) -> list[dict[str, str]]:
        if not HISTORY_PATH.exists():
            return []
        try:
            payload = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Historique des mises a jour illisible, reinitialisation implicite.")
            return []
        if not isinstance(payload, list):
            return []
        return [entry for entry in payload if isinstance(entry, dict)]

    def _is_remote_newer(self, manifest: UpdateManifest) -> bool:
        remote = self._release_tuple(manifest.version, manifest.patch)
        local = self._release_tuple(APP_VERSION, APP_PATCH)
        return remote > local

    def _release_tuple(self, version: str, patch: int) -> tuple[int, ...]:
        version_parts = [int(part) if part.isdigit() else 0 for part in str(version).split(".")]
        while len(version_parts) < 3:
            version_parts.append(0)
        version_parts = version_parts[:3]
        return (*version_parts, int(patch))


update_service = UpdateService()