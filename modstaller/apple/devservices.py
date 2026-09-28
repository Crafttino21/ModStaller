"""developerservices2.apple.com - the same API Xcode uses for free
provisioning.

The .action endpoints speak plist, the newer /services/v1 part JSON.
Responses carry a ``resultCode``; anything other than 0 is an error, although
some codes actually mean success (see :mod:`..errors`).
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
from ..i18n import _
from . import http

#: Xcode's client ID. The API expects it.
CLIENT_ID = "XABBG36SBA"

#: Xcode version we claim to be.
XCODE_VERSION = "11.2 (11B41)"

#: Exactly the Anisette headers developerservices2 expects - a fixed list
#: rather than "everything starting with X-", so it is clear what belongs
#: here and what only the sign-in needs.
_ANISETTE_HEADERS = (
    "X-Apple-I-MD",
    "X-Apple-I-MD-M",
    "X-Apple-I-MD-LU",
    "X-Apple-I-MD-RINFO",
    "X-Apple-I-Client-Time",
    "X-Apple-I-TimeZone",
    "X-Apple-Locale",
    "X-Mme-Device-Id",
    "X-MMe-Client-Info",
)


@dataclass(frozen=True)
class Team:
    team_id: str
    name: str
    type: str
    status: str

    @property
    def is_free(self) -> bool:
        """Only reliable if Apple explicitly calls the type "Free".

        Otherwise Apple reports ``Individual`` for single accounts -
        regardless of whether they are paid. Guessing here means guessing
        wrong; only the lifetime of a real profile answers the question.
        """
        return self.type.lower().startswith("free")

    def __str__(self) -> str:
        return f"{self.name} [{self.team_id}] - type {self.type}"


@dataclass(frozen=True)
class Certificate:
    cert_id: str
    serial: str
    #: Name of the machine that requested the certificate - the only usable
    #: distinguishing feature, because Apple gives all of them the same name
    #: "iOS Development: <Person>".
    name: str
    content: bytes
    expires_at: object = None
    machine_id: str = ""

    def __str__(self) -> str:
        when = (_(", expires {date}", date=f"{self.expires_at:%d.%m.%Y}")
                if self.expires_at else "")
        return f"{self.name} [{self.cert_id}]{when}"


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
    """Client for Apple's developer API."""

    def __init__(self, session, anisette) -> None:
        self._session = session
        self._ani = anisette
        self._http = http.dev_session()

    # -- Transport ---------------------------------------------------------

    def _post(self, action: str, params: dict[str, Any] | None = None,
              *, team_id: str | None = None) -> dict:
        # The client ID also goes into the URL. If it is missing there,
        # Apple rejects the request with resultCode 1100 ("session has
        # expired") - even though the session is fresh and the error has
        # nothing to do with it.
        url = (f"{http.DEV_SERVICES}/{http.PROTOCOL_VERSION}/{action}"
               f"?clientId={CLIENT_ID}")
        body: dict[str, Any] = {
            "clientId": CLIENT_ID,
            "protocolVersion": http.PROTOCOL_VERSION,
            "requestId": str(uuid.uuid4()).upper(),
            "userLocale": ["en_US"],
        }
        if team_id:
            body["teamId"] = team_id
        body.update(params or {})

        ani = self._ani.headers()
        headers = {
            "X-Apple-App-Info": "com.apple.gs.xcode.auth",
            "X-Xcode-Version": XCODE_VERSION,
            **self._session.auth_headers,
        }
        headers.update({k: ani[k] for k in _ANISETTE_HEADERS if k in ani})
        # Apple expects the locale under two names.
        headers.setdefault("X-Apple-I-Locale", ani.get("X-Apple-Locale", "en_US"))

        resp = self._http.post(url, data=plistlib.dumps(body),
                               headers=headers, timeout=45)
        if resp.status_code in (401, 403):
            raise AppleError(_(
                "Apple rejected the sign-in (HTTP {status}). Please sign in "
                "again: modstaller login", status=resp.status_code))
        resp.raise_for_status()
        try:
            data = plistlib.loads(resp.content)
        except Exception as exc:
            raise AppleError(
                f"Unreadable response from {action}: {resp.content[:200]!r}"
            ) from exc
        return self._check(data, action)

    @staticmethod
    def _check(data: dict, action: str) -> dict:
        code = data.get("resultCode", 0)
        if not code or code in BENIGN_CODES:
            return data
        message = (data.get("userString") or data.get("resultString")
                   or _("Error {code} at {action}", code=code, action=action))
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

    # -- Devices -----------------------------------------------------------

    def register_device(self, team_id: str, udid: str, name: str) -> None:
        """Registers the iPhone with the team. Already registered = success."""
        self._post("ios/addDevice.action", {"deviceNumber": udid, "name": name},
                   team_id=team_id)

    def list_devices(self, team_id: str) -> list[dict]:
        return self._post("ios/listDevices.action", team_id=team_id).get("devices", [])

    # -- Certificates -----------------------------------------------------

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

    def list_certificates(self, team_id: str) -> list[Certificate]:
        data = self._post("ios/listAllDevelopmentCerts.action", team_id=team_id)
        return [
            Certificate(
                cert_id=c.get("certificateId", ""),
                serial=c.get("serialNumber", ""),
                name=c.get("machineName") or c.get("name", "?"),
                content=c.get("certContent") or b"",
                expires_at=c.get("expirationDate"),
                machine_id=c.get("machineId", ""),
            )
            for c in data.get("certificates", [])
        ]

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
        # Apple accepts only letters, digits and spaces in the name.
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

    # -- Provisioning profiles --------------------------------------------

    def download_profile(self, team_id: str, app_id_id: str) -> Profile:
        data = self._post("ios/downloadTeamProvisioningProfile.action",
                          {"appIdId": app_id_id}, team_id=team_id)
        prof = data.get("provisioningProfile") or {}
        content = prof.get("encodedProfile")
        if not content:
            raise AppleError(_("Apple returned an empty provisioning profile."))
        return Profile(content=bytes(content),
                       expires_at=_profile_expiry(bytes(content)))


def _profile_expiry(blob: bytes) -> datetime | None:
    """Reads the expiry date from the profile.

    The profile is a CMS container; the plist inside is plain text, so it
    is enough to cut out the plist part.
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
