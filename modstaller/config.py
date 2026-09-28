"""Paths, settings and creating the state directories.

Secrets are stored as 0600 in 0700 directories. Only files that are properly
restrictive are read - better to fail loudly than to leak silently.

Windows has no Unix permissions: there everything lives under
``%LOCALAPPDATA%\\modstaller``, protected by the NTFS permissions of the
user profile. Deliberately not under ``%APPDATA%``: that is where the
interface (Electron) creates its "ModStaller" folder - and Windows is
case-insensitive.
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


#: Unix file permissions only exist here - on Windows ``st_mode`` is always
#: "open" for group/others and says nothing about access.
POSIX = os.name != "nt"


def base_dirs(env: dict | None = None, *, posix: bool = POSIX,
              home: Path | None = None) -> tuple[Path, Path, Path, Path]:
    """Config, data, cache and state directories for this system."""
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
#: Icons chosen in the editor - kept so a renewal can apply them again.
ICONS_DIR = DATA_DIR / "icons"
WORK_DIR = CACHE_DIR / "work"
OUT_DIR = CACHE_DIR / "out"
LOCK_FILE = STATE_DIR / "modstaller.lock"
DB_FILE = DATA_DIR / "state.db"

#: The log shared by CLI and interface (see logbook.py). Private: it names
#: devices and apps.
LOG_FILE = STATE_DIR / "modstaller.log"

#: Apple's private CA chain for gsa.apple.com. The host is *not* signed by a
#: public CA but by "Apple Server Authentication CA". Without this bundle
#: every connection fails with CERTIFICATE_VERIFY_FAILED.
GSA_CA_BUNDLE = Path(__file__).parent / "apple" / "certs" / "apple-gsa-ca.pem"

#: Directories that hold secrets - strictly 0700.
_PRIVATE_DIRS = (DATA_DIR, SECRETS_DIR, ANISETTE_DIR, CERTS_DIR, PROFILES_DIR,
                 IPA_CACHE_DIR, STATE_DIR)
_PUBLIC_DIRS = (CONFIG_DIR, CACHE_DIR, WORK_DIR, OUT_DIR)


def find_zsign(configured: str = "zsign") -> str | None:
    """Where zsign is - on the PATH or right next to our own .exe.

    The Windows CLI ships as a zip with ``modstaller.exe`` and ``zsign.exe``
    side by side, without a PATH entry. Windows would find zsign there on its
    own when running it, but ``shutil.which`` (and so the system check)
    would not.
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


#: Without it, os.open on Windows opens in *text* mode and writes every
#: b"\n" as b"\r\n" - which broke every binary secret there (profiles,
#: identity.p12, cert.der; up to 1.3.0-rc.1). Zero on POSIX.
O_BINARY = getattr(os, "O_BINARY", 0)


def write_secret(path: Path, data: bytes) -> None:
    """Writes a file that is 0600 from the start - never briefly open."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | O_BINARY, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    path.chmod(0o600)


def undo_text_mode(data: bytes) -> bytes:
    """Reverses what a text-mode write on Windows did to binary data.

    Such a write turns every b"\n" into b"\r\n" - an original b"\r\n"
    became b"\r\r\n". Replacing b"\r\n" with b"\n" therefore restores
    the original exactly. Only apply it to data that no longer parses.
    """
    return data.replace(b"\r\n", b"\n")


def read_secret(path: Path) -> bytes:
    """Reads a secret file and refuses it if its permissions are too open."""
    mode = path.stat().st_mode
    if POSIX and mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ConfigError(_(
            "{path} is readable by group or others (mode {mode}). "
            "Fix it with: chmod 600 {path}",
            path=path, mode=oct(mode & 0o777)))
    return path.read_bytes()


@dataclass
class Settings:
    """What may go into config.toml. No secrets."""

    #: "local" uses the ADI libraries on this machine, "remote" an
    #: anisette-v3 server. Local is the default - on Windows too - so that
    #: no device identifiers leave the system.
    anisette_provider: str = "local"
    anisette_server: str = "https://ani.sidestore.io"
    default_udid: str | None = None
    default_team_id: str | None = None
    #: Free accounts: profiles expire after 7 days; renew from this point on.
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
