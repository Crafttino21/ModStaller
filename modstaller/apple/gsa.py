"""GrandSlam-Authentifizierung gegen Apple.

Ablauf:

1. ``init``     - wir schicken ``A``, Apple antwortet mit Salt, Iterationen,
                  ``B`` und dem gewaehlten s2k-Verfahren.
2. ``complete`` - wir schicken den SRP-Beweis ``M1``, Apple antwortet mit
                  ``M2`` und ``spd``: ein mit dem Session-Key verschluesseltes
                  Plist mit ``adsid`` und ``GsIdmsToken``.
3. Ggf. 2FA     - Apple schickt einen Code auf die vertrauten Geraete, wir
                  validieren ihn und wiederholen Schritt 1-2.
4. ``apptokens``- das Login-Token allein reicht developerservices2 nicht
                  ("Your session has expired"). Es muss gegen ein
                  app-spezifisches Token fuer ``com.apple.gs.xcode.auth``
                  getauscht werden. Der Tausch wird mit dem Session-Key aus
                  dem entschluesselten Login beglaubigt.

Das Passwort verlaesst den Rechner nie: SRP beweist seine Kenntnis, ohne es
zu uebertragen.
"""

from __future__ import annotations

import hashlib
import hmac
import plistlib
from base64 import b64encode
from dataclasses import dataclass
from typing import Callable

from ..errors import AppleError, InteractionRequired
from . import clientinfo, http
from .srp import SRPClient, derive_password

#: Das Token, mit dem developerservices2 angesprochen wird.
XCODE_APP = "com.apple.gs.xcode.auth"

#: Apple liefert das spd-Plist ohne XML-Header aus.
_PLIST_HEADER = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
)

#: Status-Codes, die Apple in ``Status.ec`` zurueckgibt.
ERR_INVALID_CREDENTIALS = -20101
ERR_INVALID_CODE = -21669
_MESSAGES = {
    ERR_INVALID_CREDENTIALS: "Apple-ID oder Passwort ist falsch.",
    ERR_INVALID_CODE: "Der 2FA-Code wurde nicht akzeptiert.",
}


@dataclass
class GSAResult:
    adsid: str
    idms_token: str
    #: Das app-spezifische Token fuer developerservices2. *Nicht* das
    #: Login-Token - damit weist Apple jede Anfrage als abgelaufen zurueck.
    app_token: str
    #: Basis fuer X-Apple-GS-Token: base64("<adsid>:<app_token>").
    identity_token: str

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "X-Apple-I-Identity-Id": self.adsid,
            "X-Apple-GS-Token": self.identity_token,
        }


def _session_key(srp_key: bytes, name: str) -> bytes:
    return hmac.new(srp_key, name.encode(), hashlib.sha256).digest()


def _decrypt_spd(srp_key: bytes, blob: bytes) -> dict:
    """Entschluesselt Apples ``spd`` (AES-256-CBC, Schluessel aus dem SRP-Key)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    key = _session_key(srp_key, "extra data key:")
    iv = _session_key(srp_key, "extra data iv:")[:16]
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = dec.update(blob) + dec.finalize()
    if plain:  # PKCS#7 abziehen
        pad = plain[-1]
        if 0 < pad <= 16:
            plain = plain[:-pad]
    return plistlib.loads(_PLIST_HEADER + plain)


#: Apple stellt dem verschluesselten Token eine Versionskennung voran und
#: nimmt sie zugleich als zusaetzliche authentifizierte Daten.
_TOKEN_VERSION = b"XYZ"


def _decrypt_app_token(session_key: bytes, blob: bytes) -> dict:
    """Entschluesselt die ``et``-Antwort (AES-GCM).

    Aufbau: 3 Byte Version, 16 Byte IV, Geheimtext, 16 Byte Pruefsumme.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not blob.startswith(_TOKEN_VERSION):
        raise AppleError(
            "Apples Token hat eine unerwartete Version "
            f"({blob[:3]!r} statt {_TOKEN_VERSION!r})."
        )
    try:
        plain = AESGCM(session_key).decrypt(blob[3:19], blob[19:],
                                            _TOKEN_VERSION)
    except Exception as exc:
        raise AppleError(
            "Apples App-Token liess sich nicht entschluesseln - der "
            "Session-Key passt nicht zur Antwort."
        ) from exc
    return plistlib.loads(_PLIST_HEADER + plain)


class GSAClient:
    """Fuehrt den GrandSlam-Handshake durch.

    Args:
        anisette: Provider der Attestation-Header.
        code_prompt: Wird fuer den 2FA-Code aufgerufen. ``None`` bedeutet
            nicht-interaktiv - dann fliegt :class:`InteractionRequired`, statt
            dass ein Daemon auf stdin blockiert.
    """

    def __init__(self, anisette, code_prompt: Callable[[], str] | None = None):
        self._ani = anisette
        self._prompt = code_prompt
        self._session = http.gsa_session()

    # -- Transport ---------------------------------------------------------

    def _cpd(self) -> dict:
        cpd = {
            "bootstrap": True,
            "icscrec": True,
            "pbe": False,
            "prkgen": True,
            "svct": "iCloud",
        }
        cpd.update(self._ani.headers())
        return cpd

    def _request(self, params: dict) -> dict:
        ci = clientinfo.sanitize(self._ani.client_info())
        clientinfo.assert_safe(ci, where="GSA")

        body = {"Header": {"Version": "1.0.1"},
                "Request": {"cpd": self._cpd(), **params}}
        # gsa_request sorgt fuer eine frische Verbindung: Apples Edge laesst
        # pro TCP-Verbindung nur einen Request an GsService2 durch, und
        # "complete" waere sonst der zweite.
        resp = http.gsa_request(
            self._session, "POST", http.GSA_URL, client_info=ci,
            headers={"X-MMe-Client-Info": ci}, data=plistlib.dumps(body),
        )
        resp.raise_for_status()
        try:
            return plistlib.loads(resp.content)["Response"]
        except Exception as exc:
            raise AppleError(
                f"Unerwartete GSA-Antwort (HTTP {resp.status_code}): "
                f"{resp.content[:200]!r}"
            ) from exc

    @staticmethod
    def _check(resp: dict) -> dict:
        status = resp.get("Status", resp)
        code = status.get("ec", 0)
        if code:
            msg = _MESSAGES.get(code) or status.get("em") or f"GSA-Fehler {code}"
            raise AppleError(f"{msg} (Code {code})")
        return resp

    # -- Ablauf ------------------------------------------------------------

    def authenticate(self, apple_id: str, password: str) -> GSAResult:
        spd, srp_key = self._handshake(apple_id, password)

        if self._needs_2fa(spd):
            self._do_two_factor(spd)
            # Nach bestandener 2FA gilt der Handshake neu - Apple haengt die
            # Vertrauensstellung an die ADI-Identitaet, nicht an die Session.
            spd, srp_key = self._handshake(apple_id, password)
            if self._needs_2fa(spd):
                raise AppleError(
                    "Apple verlangt nach der 2FA-Bestaetigung erneut einen Code. "
                    "Meist hilft es, den Provisioning-State zurueckzusetzen: "
                    "modstaller logout --forget-device"
                )

        adsid, token = spd.get("adsid"), spd.get("GsIdmsToken")
        if not adsid or not token:
            raise AppleError("GSA lieferte keine adsid/GsIdmsToken - "
                             "Login unvollstaendig.")

        app_token = self._fetch_app_token(spd, adsid, token)
        return GSAResult(
            adsid=adsid,
            idms_token=token,
            app_token=app_token,
            identity_token=b64encode(f"{adsid}:{app_token}".encode()).decode(),
        )

    def _fetch_app_token(self, spd: dict, adsid: str, idms_token: str) -> str:
        """Tauscht das Login-Token gegen eines fuer die Entwickler-API."""
        session_key = spd.get("sk")
        cookie = spd.get("c")
        if not session_key or cookie is None:
            raise AppleError(
                "GSA lieferte keinen Session-Key - ohne den laesst sich kein "
                "Token fuer die Entwickler-API anfordern."
            )

        # Beglaubigt die Anfrage: nur wer den Session-Key kennt, kann sie
        # stellen. Reihenfolge ist Teil des Protokolls.
        mac = hmac.new(bytes(session_key), digestmod=hashlib.sha256)
        mac.update(b"apptokens")
        mac.update(adsid.encode())
        mac.update(XCODE_APP.encode())

        resp = self._check(self._request({
            "u": adsid,
            "app": [XCODE_APP],
            "c": cookie,
            "t": idms_token,
            "checksum": mac.digest(),
            "o": "apptokens",
        }))

        encrypted = resp.get("et")
        if not encrypted:
            raise AppleError("Apple lieferte kein App-Token zurueck.")

        tokens = _decrypt_app_token(bytes(session_key), bytes(encrypted))
        entry = (tokens.get("t") or {}).get(XCODE_APP) or {}
        app_token = entry.get("token")
        if not app_token:
            raise AppleError(
                f"Apple hat kein Token fuer {XCODE_APP} ausgestellt. "
                "Meist fehlt dem Account die Entwickler-Registrierung - "
                "einmal auf developer.apple.com anmelden und die Bedingungen "
                "akzeptieren."
            )
        return app_token

    def _handshake(self, apple_id: str, password: str) -> tuple[dict, bytes]:
        srp = SRPClient(apple_id)
        init = self._check(self._request({
            "A2k": srp.A_bytes,
            "ps": ["s2k", "s2k_fo"],
            "u": apple_id,
            "o": "init",
        }))

        protocol = init.get("sp", "s2k")
        derived = derive_password(password, init["s"], init["i"], protocol)
        m1 = srp.process_challenge(init["s"], init["B"], derived)

        complete = self._check(self._request({
            "c": init["c"],
            "M1": m1,
            "u": apple_id,
            "o": "complete",
        }))

        if not srp.verify_session(complete["M2"]):
            raise AppleError(
                "Apples Sitzungsbeweis stimmt nicht. Die Gegenstelle konnte "
                "den Schluessel nicht belegen - Verbindung nicht vertrauen."
            )
        assert srp.K is not None
        return _decrypt_spd(srp.K, complete["spd"]), srp.K

    # -- Zwei-Faktor -------------------------------------------------------

    @staticmethod
    def _needs_2fa(spd: dict) -> bool:
        return spd.get("au") in ("trustedDeviceSecondaryAuth",
                                 "secondaryAuth", "smsSecondaryAuth")

    def _two_factor_headers(self, spd: dict) -> dict[str, str]:
        identity = b64encode(
            f"{spd['adsid']}:{spd['GsIdmsToken']}".encode()).decode()
        headers = {
            "Content-Type": "text/x-xml-plist",
            "Accept": "text/x-xml-plist",
            "User-Agent": http.USER_AGENT_XCODE,
            "Accept-Language": "en-us",
            "X-Apple-Identity-Token": identity,
        }
        ani = self._ani.headers()
        headers.update({k: v for k, v in ani.items() if k.startswith("X-")})
        headers["X-MMe-Client-Info"] = clientinfo.sanitize(self._ani.client_info())
        return headers

    def _do_two_factor(self, spd: dict) -> None:
        if self._prompt is None:
            raise InteractionRequired(
                "Apple verlangt einen 2FA-Code, aber ModStaller laeuft "
                "nicht-interaktiv. Einmal 'modstaller login' ausfuehren."
            )
        headers = self._two_factor_headers(spd)

        # Code an die vertrauten Geraete schicken.
        http.gsa_request(self._session, "GET",
                         "https://gsa.apple.com/auth/verify/trusteddevice",
                         client_info=headers["X-MMe-Client-Info"],
                         headers=headers)

        code = self._prompt().strip()
        if not code:
            raise AppleError("Kein 2FA-Code eingegeben.")

        resp = http.gsa_request(
            self._session, "GET",
            "https://gsa.apple.com/grandslam/GsService2/validate",
            client_info=headers["X-MMe-Client-Info"],
            headers={**headers, "security-code": code})
        try:
            self._check(plistlib.loads(resp.content))
        except plistlib.InvalidFileException:
            if resp.status_code >= 400:
                raise AppleError(
                    f"2FA-Validierung fehlgeschlagen (HTTP {resp.status_code})."
                ) from None
