"""Anisette-Provider: Apples Geraete-Attestation fuer GSA-Logins.

Ohne diese Header akzeptiert Apple keinen Login. Zwei Quellen:

* :class:`LocalProvider` (Default) - fuehrt Apples ADI-Libraries
  (``libstoreservicescore.so``, ``libCoreADI.so`` aus der Apple-Music-APK)
  lokal in einer ARM-Emulation aus. Nichts verlaesst den Rechner.
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
import secrets
import uuid
from pathlib import Path
from typing import Protocol

from ..config import ANISETTE_DIR, read_secret, write_secret
from ..errors import AppleError
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


class LocalProvider:
    """ADI-Emulation auf diesem Rechner."""

    name = "local"

    def __init__(self) -> None:
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
            raise AppleError(
                f"Anisette-Server {self._base} nicht erreichbar: {exc}"
            ) from exc
        data["X-MMe-Client-Info"] = self.client_info()
        return data


def build(provider: str = "local", server: str = "") -> AnisetteProvider:
    """Baut den konfigurierten Provider. 'local' faellt nicht still auf
    'remote' zurueck - wer lokal gewaehlt hat, will keine Daten verschicken."""
    if provider == "local":
        return LocalProvider()
    if provider == "remote":
        if not server:
            raise AppleError("anisette_provider = 'remote', aber kein "
                             "anisette_server konfiguriert.")
        return RemoteV3Provider(server)
    raise AppleError(f"Unbekannter anisette_provider: {provider!r}")
