"""Was installiert ist und wann es ablaeuft.

Absichtlich eine schlichte JSON-Datei: der Datenbestand ist klein, und der
Refresh-Daemon soll ihn auch dann noch lesen koennen, wenn ModStaller selbst
gerade kaputt ist.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from ..config import DATA_DIR, read_secret, write_secret

INSTALLS_FILE = DATA_DIR / "apps.json"


@dataclass
class InstallRecord:
    bundle_id: str               # die neue, signierte ID auf dem Geraet
    original_bundle_id: str
    name: str
    team_id: str
    udid: str
    source_ipa: str              # Pfad zur Original-IPA, fuer den Refresh
    app_id_id: str
    profile_path: str
    expires_at: float            # Unix-Zeit
    installed_at: float = field(default_factory=time.time)
    last_refresh_at: float = 0.0
    strip_extensions: bool = False

    @property
    def days_left(self) -> float:
        return (self.expires_at - time.time()) / 86400

    @property
    def expiry_text(self) -> str:
        d = self.days_left
        if d < 0:
            return "abgelaufen"
        when = datetime.fromtimestamp(self.expires_at, timezone.utc).astimezone()
        return f"noch {d:.1f} Tage (bis {when:%d.%m. %H:%M})"


def _load_raw() -> dict:
    if not INSTALLS_FILE.exists():
        return {}
    try:
        return json.loads(read_secret(INSTALLS_FILE))
    except Exception:
        return {}


def all_installs() -> list[InstallRecord]:
    out = []
    for raw in _load_raw().values():
        try:
            out.append(InstallRecord(**raw))
        except TypeError:
            continue  # aelteres Format - ignorieren statt abstuerzen
    return sorted(out, key=lambda r: r.expires_at)


def record(entry: InstallRecord) -> None:
    data = _load_raw()
    data[entry.bundle_id] = asdict(entry)
    write_secret(INSTALLS_FILE, json.dumps(data, indent=2).encode())


def forget(bundle_id: str) -> bool:
    data = _load_raw()
    if bundle_id not in data:
        return False
    del data[bundle_id]
    write_secret(INSTALLS_FILE, json.dumps(data, indent=2).encode())
    return True


def due_for_refresh(threshold_days: float) -> list[InstallRecord]:
    return [r for r in all_installs() if r.days_left <= threshold_days]
