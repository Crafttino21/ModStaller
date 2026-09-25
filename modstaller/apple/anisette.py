"""Anisette-Provider: Apples Geraete-Attestation fuer GSA-Logins.

Ohne diese Header akzeptiert Apple keinen Login. Zwei Quellen:

* :class:`LocalProvider` (Default) - fuehrt Apples ADI-Libraries
  (``libstoreservicescore.so``, ``libCoreADI.so`` aus der Apple-Music-APK)
  lokal in einer ARM-Emulation aus. Nichts verlaesst den Rechner. Setzt unter
  Windows voraus, dass Control Flow Guard aus ist - siehe
  :func:`local_supported`.
* :class:`RemoteV3Provider` - anisette-v3-Protokoll gegen einen fremden
  Server. Nur als Fallback; Geraete-Identifier gehen dann an einen Dritten.

Zwei Dinge korrigiert dieses Modul am Verhalten der ``anisette``-Bibliothek:

1. Ihr Default-``server_friendly_description`` traegt ``com.apple.dt.Xcode``,
   was Apple seit August 2026 mit HTTP 503 abweist. Siehe :mod:`.clientinfo`.
2. Ihre Default-Device-Config hat *hartcodierte* IDs, die jede Installation
   der Bibliothek teilt. Wir erzeugen pro Installation eigene, stabile IDs.
"""

from __future__ import annotations

import json
import os
import secrets
import uuid
from pathlib import Path
from typing import Protocol

from ..config import (ANISETTE_DIR, CONFIG_FILE, POSIX, read_secret,
                      write_secret)
from ..errors import AppleError
from ..i18n import _
from . import clientinfo

#: Provisioning-State (adi.pb). Apple bindet die 2FA-Vertrauensstellung daran.
#: Geht die Datei verloren, fragt Apple bei jedem Lauf wieder einen Code ab -
#: was den unbeaufsichtigten Refresh-Daemon unbrauchbar macht.
PROVISIONING_FILE = ANISETTE_DIR / "provisioning.bin"
LIBS_FILE = ANISETTE_DIR / "libs.bin"
DEVICE_FILE = ANISETTE_DIR / "device.json"


class AnisetteProvider(Protocol):
    def headers(self) -> dict[str, str]: ...
    def client_info(self) -> str: ...


def _load_or_create_device() -> dict[str, str]:
    """Eine stabile, pro Installation eigene Geraete-Identitaet.

    Stabil, weil Apple wechselnde Identitaeten als verdaechtig behandelt und
    dann erneut 2FA verlangt. Eigen, weil die Defaults der Bibliothek von
    allen ihren Nutzern geteilt werden.
    """
    if DEVICE_FILE.exists():
        return json.loads(read_secret(DEVICE_FILE))

    device = {
        "server_friendly_description": clientinfo.DEFAULT_CLIENT_INFO,
        "unique_device_id": str(uuid.uuid4()).upper(),
        "adi_id": secrets.token_hex(8),
        "local_user_uuid": secrets.token_hex(32).upper(),
    }
    write_secret(DEVICE_FILE, json.dumps(device, indent=2).encode())
    return device


#: Notausgang, falls jemand es trotzdem versuchen will.
ALLOW_LOCAL_ENV = "MODSTALLER_ALLOW_LOCAL_ANISETTE"

#: ProcessControlFlowGuardPolicy aus PROCESS_MITIGATION_POLICY.
_CFG_POLICY = 7


def control_flow_guard_active() -> bool:
    """Ob fuer *diesen* Prozess Control Flow Guard aktiv ist.

    Entschieden wird das von der Haupt-EXE, fuer den ganzen Prozess. Gemessen
    statt geraten: gepackte Programme, die :func:`packaging.build_backend
    .clear_cfg` durchlaufen haben, sind sauber, aeltere nicht - und in der
    Entwicklung laeuft ohnehin ``python.exe``, die CFG nie setzt.
    """
    if POSIX:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.GetProcessMitigationPolicy.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t]
        k32.GetProcessMitigationPolicy.restype = wintypes.BOOL

        flags = ctypes.c_uint32()
        if not k32.GetProcessMitigationPolicy(
                k32.GetCurrentProcess(), _CFG_POLICY,
                ctypes.byref(flags), ctypes.sizeof(flags)):
            return False
        return bool(flags.value & 1)        # EnableControlFlowGuard
    except Exception:
        # Nicht feststellbar - dann nicht im Weg stehen.
        return False


def local_supported() -> bool:
    """Ob die lokale ADI-Emulation in diesem Prozess laufen kann.

    Mit aktivem Control Flow Guard nicht: ``unicorn.dll`` springt mit
    ``longjmp`` aus JIT-erzeugtem Code heraus, MSVCs Laufzeit findet dafuer
    keinen Eintrag in der CFG-Tabelle und ruft ``__fastfail`` (0xC0000409,
    FAST_FAIL_INVALID_SET_OF_CONTEXT). Kein Fehler, den man abfangen koennte -
    der Prozess ist sofort weg, und mit ihm das Backend der Oberflaeche. Die
    Sperre greift deshalb *vor* dem Import von ``anisette``, damit
    ``unicorn.dll`` gar nicht erst geladen wird.
    """
    return (not control_flow_guard_active()
            or os.environ.get(ALLOW_LOCAL_ENV) == "1")


class LocalProvider:
    """ADI-Emulation auf diesem Rechner."""

    name = "local"

    def __init__(self) -> None:
        if not local_supported():
            raise AppleError(_(
                "The local Anisette emulation cannot run in this build: "
                "Control Flow Guard is active for the process, and the ARM "
                "emulation (Unicorn) then aborts in native code "
                "(0xC0000409). A current ModStaller build for Windows does "
                "not set that flag - otherwise an Anisette server helps. "
                "In {config}:\n"
                '  anisette_provider = "remote"\n'
                '  anisette_server = "https://ani.sidestore.io"',
                config=CONFIG_FILE))
        from anisette import Anisette
        from anisette._device import AnisetteDeviceConfig

        ANISETTE_DIR.mkdir(parents=True, exist_ok=True)
        ANISETTE_DIR.chmod(0o700)

        device = _load_or_create_device()
        # Client-Info hier schon sanitisieren: dann stimmt die Identitaet, mit
        # der provisioniert wird, mit der ueberein, mit der wir spaeter reden.
        device["server_friendly_description"] = clientinfo.sanitize(
            device["server_friendly_description"]
        )
        self._cfg = AnisetteDeviceConfig(**device)

        existing = [p for p in (LIBS_FILE, PROVISIONING_FILE) if p.exists()]
        if existing:
            self._ani = Anisette.load(*existing, default_device_config=self._cfg)
        else:
            self._ani = Anisette.init(default_device_config=self._cfg)
        self._persist()

    def _persist(self) -> None:
        if not LIBS_FILE.exists():
            self._ani.save_libs(LIBS_FILE)
            LIBS_FILE.chmod(0o600)
        if self._ani.is_provisioned:
            self._ani.save_provisioning(PROVISIONING_FILE)
            PROVISIONING_FILE.chmod(0o600)

    def headers(self) -> dict[str, str]:
        data = dict(self._ani.get_data())
        self._persist()
        data["X-MMe-Client-Info"] = self.client_info()
        return data

    def client_info(self) -> str:
        return clientinfo.sanitize(self._cfg.server_friendly_description)


class RemoteV3Provider:
    """anisette-v3-Protokoll gegen einen fremden Server."""

    name = "remote"

    def __init__(self, base_url: str, timeout: float = 20.0) -> None:
        import requests

        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._client_info: str | None = None

    def client_info(self) -> str:
        # Den Server nach seiner Client-Info *fragen* statt sie zu raten -
        # dann trifft uns Apples naechste Aenderung nicht erneut.
        if self._client_info is None:
            try:
                r = self._session.get(f"{self._base}/v3/client_info",
                                      timeout=self._timeout)
                r.raise_for_status()
                raw = r.json().get("client_info")
            except Exception:
                raw = None
            self._client_info = clientinfo.sanitize(raw)
        return self._client_info

    def headers(self) -> dict[str, str]:
        try:
            r = self._session.get(f"{self._base}/v3/get_headers",
                                  timeout=self._timeout)
            r.raise_for_status()
            data = {k: v for k, v in r.json().items() if k.lower() != "result"}
        except Exception as exc:
            raise AppleError(_(
                "Anisette server {url} not reachable: {error}",
                url=self._base, error=exc)) from exc
        data["X-MMe-Client-Info"] = self.client_info()
        return data


def build(provider: str = "local", server: str = "") -> AnisetteProvider:
    """Baut den konfigurierten Provider. 'local' faellt nicht still auf
    'remote' zurueck - wer lokal gewaehlt hat, will keine Daten verschicken."""
    if provider == "local":
        return LocalProvider()
    if provider == "remote":
        if not server:
            raise AppleError(_("anisette_provider = ‘remote’, but no "
                               "anisette_server is configured."))
        return RemoteV3Provider(server)
    raise AppleError(_("Unknown anisette_provider: {provider!r}",
                       provider=provider))
