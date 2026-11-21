"""Local session storage, separate from the catalog cache."""

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from ..api.auth import StoredToken


class FileTokenStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = RLock()

    def load(self) -> StoredToken | None:
        with self._lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, ValueError):
                return None
            if not isinstance(data, dict):
                return None
            token, profile_id = data.get("token"), data.get("profile_id")
            if not isinstance(token, str) or not token or (profile_id is not None and type(profile_id) is not int):
                return None
            return StoredToken(token, profile_id)

    def save(self, token: StoredToken) -> None:
        with self._lock:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as file:
                temporary = Path(file.name)
                try:
                    json.dump({"token": token.token, "profile_id": token.profile_id}, file)
                    file.close()
                    os.replace(temporary, self.path)
                finally:
                    file.close()
                    temporary.unlink(missing_ok=True)

    def migrate_from(self, legacy: Path) -> None:
        with self._lock:
            if legacy == self.path or self.path.exists() or not legacy.is_file():
                return
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            legacy.replace(self.path)

    def clear(self) -> None:
        with self._lock:
            self.path.unlink(missing_ok=True)
