"""developerservices2.apple.com - dieselbe API, die Xcode fuer Free
Provisioning benutzt.

Die .action-Endpunkte sprechen Plist, der neuere /services/v1-Teil JSON.
Antworten tragen einen ``resultCode``; alles ausser 0 ist ein Fehler, wobei
einige Codes in Wahrheit Erfolg bedeuten (siehe :mod:`..errors`).
"""

from __future__ import annotations

import plistlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..errors import (
    APP_ID_QUOTA_EXCEEDED, APP_ID_UNAVAILABLE, BENIGN_CODES,
    AppleAPIError, AppleError, remedy_for,
)
from . import clientinfo, http

#: Xcodes Client-Id. Die API erwartet sie.
CLIENT_ID = "XABBG36SBA"


@dataclass(frozen=True)
class Team:
    team_id: str
    name: str
    type: str
    status: str

    @property
    def is_free(self) -> bool:
        # Apple nennt Gratis-Teams "Individual" mit Typ "Free"; der Typ ist
        # das verlaesslichere Signal, wird aber spaeter ohnehin anhand der
        # echten Profil-Laufzeit gegengeprueft.
        return self.type.lower().startswith("free")

    def __str__(self) -> str:
        return f"{self.name} [{self.team_id}] - {'kostenlos' if self.is_free else 'bezahlt'}"


@dataclass(frozen=True)
class Certificate:
    cert_id: str
    serial: str
    name: str
    content: bytes


@dataclass(frozen=True)
class AppID:
    app_id_id: str
    identifier: str
    name: str


@dataclass(frozen=True)
class Profile:
    content: bytes
    expires_at: datetime | None

    @property
    def days_left(self) -> float:
        if self.expires_at is None:
            return float("nan")
        return (self.expires_at - datetime.now(timezone.utc)).total_seconds() / 86400


class DeveloperServices:
    """Client fuer Apples Entwickler-API."""

    def __init__(self, session, anisette) -> None:
        self._session = session
        self._ani = anisette
        self._http = http.dev_session()

    # -- Transport ---------------------------------------------------------

    def _post(self, action: str, params: dict[str, Any] | None = None,
              *, team_id: str | None = None) -> dict:
        url = f"{http.DEV_SERVICES}/{http.PROTOCOL_VERSION}/{action}"
        body: dict[str, Any] = {
            "clientId": CLIENT_ID,
            "protocolVersion": http.PROTOCOL_VERSION,
            "requestId": str(uuid.uuid4()).upper(),
            "userLocale": ["en_US"],
        }
        if team_id:
            body["teamId"] = team_id
        body.update(params or {})

        headers = {
            **self._session.auth_headers,
            "X-Apple-App-Info": "com.apple.gs.xcode.auth",
            "X-Xcode-Version": "14.2 (14C18)",
        }
        ani = self._ani.headers()
        headers.update({k: v for k, v in ani.items() if k.startswith("X-")})
        headers["X-MMe-Client-Info"] = clientinfo.sanitize(self._ani.client_info())

        resp = self._http.post(url, data=plistlib.dumps(body),
                               headers=headers, timeout=45)
        if resp.status_code in (401, 403):
            raise AppleError(
                "Apple hat die Anmeldung abgelehnt (HTTP "
                f"{resp.status_code}). Bitte neu anmelden: modstaller login"
            )
        resp.raise_for_status()
        try:
            data = plistlib.loads(resp.content)
        except Exception as exc:
            raise AppleError(
                f"Unlesbare Antwort von {action}: {resp.content[:200]!r}"
            ) from exc
        return self._check(data, action)

    @staticmethod
    def _check(data: dict, action: str) -> dict:
        code = data.get("resultCode", 0)
        if not code or code in BENIGN_CODES:
            return data
        message = (data.get("userString") or data.get("resultString")
                   or f"Fehler {code} bei {action}")
        hint = remedy_for(code)
        raise AppleAPIError(code, data.get("resultString", ""),
                            f"{message}\n{hint}" if hint else message)

    # -- Teams -------------------------------------------------------------

    def list_teams(self) -> list[Team]:
        data = self._post("listTeams.action")
        return [
            Team(team_id=t["teamId"], name=t.get("name", "?"),
                 type=t.get("type", "?"), status=t.get("status", "?"))
            for t in data.get("teams", [])
        ]

    # -- Geraete -----------------------------------------------------------

    def register_device(self, team_id: str, udid: str, name: str) -> None:
        """Meldet das iPhone beim Team an. Schon registriert = Erfolg."""
        self._post("ios/addDevice.action", {"deviceNumber": udid, "name": name},
                   team_id=team_id)

    def list_devices(self, team_id: str) -> list[dict]:
        return self._post("ios/listDevices.action", team_id=team_id).get("devices", [])

    # -- Zertifikate -------------------------------------------------------

    def submit_csr(self, team_id: str, csr_pem: str, machine_id: str,
                   machine_name: str) -> Certificate:
        data = self._post("ios/submitDevelopmentCSR.action", {
            "csrContent": csr_pem,
            "machineId": machine_id,
            "machineName": machine_name,
        }, team_id=team_id)
        req = data.get("certRequest") or {}
        return Certificate(
            cert_id=req.get("certificateId", ""),
            serial=req.get("serialNumber", ""),
            name=req.get("name", "ModStaller"),
            content=req.get("certificatePage") or req.get("certContent") or b"",
        )

    def list_certificates(self, team_id: str) -> list[dict]:
        data = self._post("ios/listAllDevelopmentCerts.action", team_id=team_id)
        return data.get("certificates", [])

    def revoke_certificate(self, team_id: str, serial: str) -> None:
        self._post("ios/revokeDevelopmentCert.action",
                   {"serialNumber": serial}, team_id=team_id)

    # -- App-IDs -----------------------------------------------------------

    def list_app_ids(self, team_id: str) -> list[AppID]:
        data = self._post("ios/listAppIds.action", team_id=team_id)
        return [
            AppID(app_id_id=a.get("appIdId", ""), identifier=a.get("identifier", ""),
                  name=a.get("name", ""))
            for a in data.get("appIds", [])
        ]

    def add_app_id(self, team_id: str, identifier: str, name: str) -> AppID:
        # Apple akzeptiert im Namen nur Buchstaben, Ziffern und Leerzeichen.
        safe = "".join(c if c.isalnum() or c == " " else " " for c in name).strip()
        data = self._post("ios/addAppId.action",
                          {"identifier": identifier, "name": safe or "ModStaller App"},
                          team_id=team_id)
        a = data.get("appId") or {}
        return AppID(app_id_id=a.get("appIdId", ""),
                     identifier=a.get("identifier", identifier),
                     name=a.get("name", safe))

    def delete_app_id(self, team_id: str, app_id_id: str) -> None:
        self._post("ios/deleteAppId.action", {"appIdId": app_id_id}, team_id=team_id)

    # -- Provisioning-Profile ---------------------------------------------

    def download_profile(self, team_id: str, app_id_id: str) -> Profile:
        data = self._post("ios/downloadTeamProvisioningProfile.action",
                          {"appIdId": app_id_id}, team_id=team_id)
        prof = data.get("provisioningProfile") or {}
        content = prof.get("encodedProfile")
        if not content:
            raise AppleError("Apple lieferte ein leeres Provisioning-Profil.")
        return Profile(content=bytes(content),
                       expires_at=_profile_expiry(bytes(content)))


def _profile_expiry(blob: bytes) -> datetime | None:
    """Liest das Ablaufdatum aus dem Profil.

    Das Profil ist ein CMS-Container; das Plist darin steht im Klartext,
    deshalb reicht es, den Plist-Teil herauszuschneiden.
    """
    start = blob.find(b"<?xml")
    end = blob.find(b"</plist>")
    if start < 0 or end < 0:
        return None
    try:
        plist = plistlib.loads(blob[start:end + 8])
    except Exception:
        return None
    value = plist.get("ExpirationDate")
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return None
