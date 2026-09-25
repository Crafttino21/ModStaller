"""Pfade, Einstellungen und das Anlegen der State-Verzeichnisse.

Secrets liegen unter 0600 in 0700-Verzeichnissen. Gelesen wird nur, was auch
korrekt restriktiv ist - lieber lautstark abbrechen als still leaken.

Unter Windows gibt es keine Unix-Rechte: dort liegt alles unter
``%LOCALAPPDATA%\\modstaller``, das die NTFS-Rechte des Benutzerprofils
schuetzen. Bewusst nicht unter ``%APPDATA%``: dort legt die Oberflaeche
(Electron) ihren Ordner "ModStaller" an - und Windows unterscheidet keine
Gross-/Kleinschreibung.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError
from .i18n import _

APP_NAME = "modstaller"


#: Unix-Dateirechte gibt es nur hier - unter Windows ist ``st_mode`` fuer
#: Gruppe/Andere immer "offen" und sagt nichts ueber den Zugriff aus.
POSIX = os.name != "nt"


def base_dirs(env: dict | None = None, *, posix: bool = POSIX,
              home: Path | None = None) -> tuple[Path, Path, Path, Path]:
    """Konfig-, Daten-, Cache- und State-Verzeichnis fuer dieses System."""
    env = os.environ if env is None else env
    home = home or Path.home()
    if not posix:
        base = Path(env.get("LOCALAPPDATA") or home / "AppData" / "Local") / APP_NAME
        return base, base / "data", base / "cache", base / "state"

    def xdg(var: str, default: str) -> Path:
        return Path(env.get(var) or home / default) / APP_NAME

    return (xdg("XDG_CONFIG_HOME", ".config"), xdg("XDG_DATA_HOME", ".local/share"),
            xdg("XDG_CACHE_HOME", ".cache"), xdg("XDG_STATE_HOME", ".local/state"))


CONFIG_DIR, DATA_DIR, CACHE_DIR, STATE_DIR = base_dirs()

CONFIG_FILE = CONFIG_DIR / "config.toml"
SECRETS_DIR = DATA_DIR / "secrets"
ANISETTE_DIR = SECRETS_DIR / "anisette"
CERTS_DIR = SECRETS_DIR / "certs"
PROFILES_DIR = DATA_DIR / "profiles"
IPA_CACHE_DIR = DATA_DIR / "ipa"
WORK_DIR = CACHE_DIR / "work"
OUT_DIR = CACHE_DIR / "out"
LOCK_FILE = STATE_DIR / "modstaller.lock"
DB_FILE = DATA_DIR / "state.db"

#: Apples private CA-Kette fuer gsa.apple.com. Der Host wird *nicht* von einer
#: oeffentlichen CA signiert, sondern von "Apple Server Authentication CA".
#: Ohne dieses Bundle scheitert jede Verbindung mit CERTIFICATE_VERIFY_FAILED.
GSA_CA_BUNDLE = Path(__file__).parent / "apple" / "certs" / "apple-gsa-ca.pem"

#: Verzeichnisse, die Secrets enthalten - strikt 0700.
_PRIVATE_DIRS = (DATA_DIR, SECRETS_DIR, ANISETTE_DIR, CERTS_DIR, PROFILES_DIR,
                 IPA_CACHE_DIR, STATE_DIR)
_PUBLIC_DIRS = (CONFIG_DIR, CACHE_DIR, WORK_DIR, OUT_DIR)


def find_zsign(configured: str = "zsign") -> str | None:
    """Wo zsign liegt - im PATH oder direkt neben der eigenen .exe.

    Die Windows-CLI kommt als Zip mit ``modstaller.exe`` und ``zsign.exe``
    nebeneinander, ohne PATH-Eintrag. Beim Aufruf faende Windows zsign dort
    zwar von selbst, ``shutil.which`` (und damit der Systemcheck) aber nicht.
    """
    if found := shutil.which(configured):
        return found
    if getattr(sys, "frozen", False):
        beside = Path(sys.executable).parent / ("zsign" if POSIX else "zsign.exe")
        if beside.is_file():
            return str(beside)
    return None


def ensure_dirs() -> None:
    for d in _PRIVATE_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        d.chmod(0o700)
    for d in _PUBLIC_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def write_secret(path: Path, data: bytes) -> None:
    """Schreibt eine Datei, die von Anfang an 0600 ist - nie kurz offen."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    path.chmod(0o600)


def read_secret(path: Path) -> bytes:
    """Liest eine Secret-Datei und verweigert sie, wenn sie zu offen liegt."""
    mode = path.stat().st_mode
    if POSIX and mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ConfigError(_(
            "{path} is readable by group or others (mode {mode}). "
            "Fix it with: chmod 600 {path}",
            path=path, mode=oct(mode & 0o777)))
    return path.read_bytes()


@dataclass
class Settings:
    """Was in config.toml stehen darf. Keine Secrets."""

    #: "local" nutzt die ADI-Libraries auf diesem Rechner, "remote" einen
    #: anisette-v3-Server. Lokal ist Default - auch unter Windows -, damit
    #: keine Geraete-Identifier das System verlassen.
    anisette_provider: str = "local"
    anisette_server: str = "https://ani.sidestore.io"
    default_udid: str | None = None
    default_team_id: str | None = None
    #: Free-Accounts: Profile laufen nach 7 Tagen ab, ab hier wird erneuert.
    renew_threshold_days: float = 2.0
    zsign_path: str = "zsign"
    extra: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or CONFIG_FILE
        if not path.exists():
            return cls()
        try:
            raw = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(_("{path} is not valid TOML: {error}",
                                path=path, error=exc)) from exc
        known = {f for f in cls.__dataclass_fields__ if f != "extra"}
        kwargs = {k: v for k, v in raw.items() if k in known}
        return cls(**kwargs, extra={k: v for k, v in raw.items() if k not in known})
