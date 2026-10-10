"""GrandSlam authentication against Apple.

Flow:

1. ``init``     - we send ``A``, Apple responds with salt, iterations,
                  ``B`` and the chosen s2k scheme.
2. ``complete`` - we send the SRP proof ``M1``, Apple responds with
                  ``M2`` and ``spd``: a plist encrypted with the session key,
                  containing ``adsid`` and ``GsIdmsToken``.
3. 2FA, if any  - ``Status.au`` says how: ``trustedDeviceSecondaryAuth`` is
                  a push to the trusted devices, validated over GsService2,
                  then steps 1-2 again. ``secondaryAuth`` is a text message
                  to the trusted phone number over Apple's web sign-in; the
                  session it confirms goes straight to step 4, with steps
                  1-2 again only as the fallback.
4. ``apptokens``- the login token alone is not enough for
                  developerservices2 ("Your session has expired"). It has to
                  be exchanged for an app-specific token for
                  ``com.apple.gs.xcode.auth``. The exchange is authenticated
                  with the session key from the decrypted login.

The password never leaves the machine: SRP proves knowledge of it without
transmitting it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import plistlib
from base64 import b64encode
from dataclasses import dataclass
from typing import Callable

import requests

from ..errors import AppleError, InteractionRequired
from ..i18n import _
from . import clientinfo, http
from .srp import SRPClient, derive_password

#: The token used to talk to developerservices2.
XCODE_APP = "com.apple.gs.xcode.auth"

#: Apple delivers the spd plist without an XML header.
_PLIST_HEADER = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
)

#: Status codes Apple returns in ``Status.ec``.
ERR_INVALID_CREDENTIALS = -20101
ERR_INVALID_CODE = -21669
#: Apple reports these two during the token exchange when the session is not
#: fully confirmed. The wording ("wrong password") is reliably misleading.
ERR_NOT_FULLY_AUTHENTICATED = -22406
ERR_TEMPORARILY_BLOCKED = -22411

#: Where Apple sends the two-factor code - what the code prompt is told.
VIA_DEVICE = "device"
VIA_SMS = "sms"

_TRUSTED_DEVICE_URL = "https://gsa.apple.com/auth/verify/trusteddevice"
_VALIDATE_URL = "https://gsa.apple.com/grandslam/GsService2/validate"
#: The web sign-in Apple names with au=secondaryAuth.
_AUTH_URL = "https://gsa.apple.com/auth"
#: Without a trailing slash - with one, Apple answers 405.
_SMS_URL = "https://gsa.apple.com/auth/verify/phone"
_SMS_CODE_URL = "https://gsa.apple.com/auth/verify/phone/securitycode"
_TRUST_URL = "https://gsa.apple.com/auth/2sv/trust"
#: Apple's first trusted number - when the sign-in page names none.
_PHONE_ID = 1
#: serviceErrors that refuse a *new* text message - the last code still
#: counts (as isideload handles them).
_CODE_STILL_VALID = frozenset({"-22979", "-22981"})
#: Session markers of the web sign-in, by lower-case name.
_WEB_SESSION_HEADERS = {"x-apple-id-session-id": "X-Apple-ID-Session-Id",
                        "scnt": "scnt"}

#: Translated on lookup, not at import time.
_MESSAGES = {
    ERR_INVALID_CREDENTIALS: "Apple ID or password is wrong.",
    ERR_INVALID_CODE: "The two-factor code was not accepted.",
}

_HINTS = {
    ERR_NOT_FULLY_AUTHENTICATED: (
        "Apple calls this a wrong password but usually means a session that "
        "was never fully confirmed - typically a pending two-factor "
        "confirmation. If the password is definitely correct, this often "
        "helps: modstaller logout --forget-device, then sign in again."
    ),
    ERR_TEMPORARILY_BLOCKED: (
        "Apple is temporarily blocking this account, usually after several "
        "failed attempts in quick succession. Wait about an hour; further "
        "attempts extend the block."
    ),
}


class GSAStatusError(AppleError):
    """A non-zero ``Status.ec`` - with the code, so callers can tell a
    pending confirmation from a block."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


@dataclass
class GSAResult:
    adsid: str
    idms_token: str
    #: The app-specific token for developerservices2. *Not* the login
    #: token - with that, Apple rejects every request as expired.
    app_token: str
    #: Basis for X-Apple-GS-Token: base64("<adsid>:<app_token>").
    identity_token: str
    #: The account holder's first name (``fn`` in the spd) - for a greeting,
    #: nothing else. Empty if Apple leaves it out.
    first_name: str = ""

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "X-Apple-I-Identity-Id": self.adsid,
            "X-Apple-GS-Token": self.identity_token,
        }


def _session_key(srp_key: bytes, name: str) -> bytes:
    return hmac.new(srp_key, name.encode(), hashlib.sha256).digest()


def _decrypt_spd(srp_key: bytes, blob: bytes) -> dict:
    """Decrypts Apple's ``spd`` (AES-256-CBC, key derived from the SRP key)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    key = _session_key(srp_key, "extra data key:")
    iv = _session_key(srp_key, "extra data iv:")[:16]
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = dec.update(blob) + dec.finalize()
    if plain:  # strip PKCS#7
        pad = plain[-1]
        if 0 < pad <= 16:
            plain = plain[:-pad]
    return plistlib.loads(_PLIST_HEADER + plain)


#: Apple prefixes the encrypted token with a version tag and also uses it as
#: additional authenticated data.
_TOKEN_VERSION = b"XYZ"


def _decrypt_app_token(session_key: bytes, blob: bytes) -> dict:
    """Decrypts the ``et`` response (AES-GCM).

    Layout: 3-byte version, 16-byte IV, ciphertext, 16-byte tag.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not blob.startswith(_TOKEN_VERSION):
        raise AppleError(_(
            "Apple’s token has an unexpected version ({got!r} instead of "
            "{expected!r}).", got=blob[:3], expected=_TOKEN_VERSION))
    try:
        plain = AESGCM(session_key).decrypt(blob[3:19], blob[19:],
                                            _TOKEN_VERSION)
    except Exception as exc:
        raise AppleError(_(
            "Apple’s app token could not be decrypted - the session key "
            "does not match the response.")) from exc
    return plistlib.loads(_PLIST_HEADER + plain)


#: Fields that must never be printed - not even in diagnostic mode. Key
#: material, proofs and tokens.
_NEVER_PRINT = frozenset({
    "sk", "spd", "M1", "M2", "B", "A2k", "c", "et", "checksum", "s", "np",
    "GsIdmsToken", "token", "pet", "adsid", "DsPrsId", "acname", "altDSID",
})

#: Personal data. Not key material, but debug output ends up pasted into
#: public bug reports - names, addresses and phone numbers have no business
#: there.
_PERSONAL = frozenset({
    "fn", "ln", "primaryEmail", "alias", "appleId", "phoneNumber",
    "maskedPhoneNumber", "numberWithDialCode", "obfuscatedNumber",
    "lastTwoDigits", "custodianUuid",
})


def _shown(key, value) -> str:
    """One value for :func:`_describe` - hidden wherever it sits.

    Recursive: the token for ``com.apple.gs.appleid.auth`` sits two levels
    down, inside ``t``.
    """
    if key in _NEVER_PRINT or key in _PERSONAL:
        return (f"<{len(value)} bytes>" if isinstance(value, (bytes, bytearray))
                else "<hidden>")
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}={_shown(k, v)}"
                               for k, v in sorted(value.items())) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_shown(None, v) for v in value) + "]"
    return repr(value)


def _identity_tag(headers: dict) -> str:
    """A short fingerprint of the device a request speaks for.

    Shows in a trace whether every step - handshake, code, handshake again -
    was the same device to Apple; a changing identity makes Apple ask for a
    code over and over. The hash reveals none of the identifiers.
    """
    parts = [str(headers.get(k, "")) for k in
             ("X-Mme-Device-Id", "X-Apple-I-MD-M", "X-Apple-I-MD-LU")]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:8]


def _describe(data: dict, label: str) -> str:
    """Describes a response without revealing its content.

    When debugging, what almost always matters is *which* fields Apple
    sends - not what they contain. Values are therefore shown only for
    harmless fields.
    """
    lines = [f"  [{label}] Fields: {', '.join(sorted(data))}"]
    for key in sorted(data):
        lines.append(f"      {key}: {_shown(key, data[key])[:220]}")
    return "\n".join(lines)


class GSAClient:
    """Performs the GrandSlam handshake.

    Args:
        anisette: Provider of the attestation headers.
        code_prompt: Called for the 2FA code, with where Apple sent it:
            :data:`VIA_DEVICE` or :data:`VIA_SMS`. ``None`` means
            non-interactive - then :class:`InteractionRequired` is raised
            instead of a daemon blocking on stdin.
    """

    def __init__(self, anisette,
                 code_prompt: Callable[[str], str] | None = None,
                 debug: bool = False):
        self._ani = anisette
        self._prompt = code_prompt
        self._debug = debug
        self._session = http.gsa_session()
        #: Session markers of Apple's web sign-in (SMS route), echoed back.
        self._web_session: dict[str, str] = {}

    def _trace(self, data: dict, label: str) -> None:
        if self._debug:
            print(_describe(data, label), flush=True)

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

        cpd = self._cpd()
        if self._debug:
            print(f"  [{params.get('o', '?')}] device {_identity_tag(cpd)}",
                  flush=True)
        body = {"Header": {"Version": "1.0.1"},
                "Request": {"cpd": cpd, **params}}
        # gsa_request ensures a fresh connection: Apple's edge lets only one
        # request to GsService2 through per TCP connection, and "complete"
        # would otherwise be the second.
        resp = http.gsa_request(
            self._session, "POST", http.GSA_URL, client_info=ci,
            headers={"X-MMe-Client-Info": ci}, data=plistlib.dumps(body),
        )
        resp.raise_for_status()
        try:
            parsed = plistlib.loads(resp.content)["Response"]
            self._trace(parsed, params.get("o", "?"))
            return parsed
        except Exception as exc:
            raise AppleError(
                f"Unexpected GSA response (HTTP {resp.status_code}): "
                f"{resp.content[:200]!r}"
            ) from exc

    @staticmethod
    def _check(resp: dict) -> dict:
        status = resp.get("Status", resp)
        code = status.get("ec", 0)
        if code:
            table = _MESSAGES.get(code)
            msg = (_(table) if table else
                   status.get("em") or _("GSA error {code}", code=code))
            hint = _HINTS.get(code)
            hint = _(hint) if hint else None
            raise GSAStatusError(f"{msg} (Code {code})"
                                 + (f"\n\n{hint}" if hint else ""), code)
        return resp

    # -- Flow --------------------------------------------------------------

    def authenticate(self, apple_id: str, password: str) -> GSAResult:
        spd, srp_key, complete = self._handshake(apple_id, password)
        self._trace(spd, "spd (decrypted)")

        au = self._second_factor(complete, spd)
        if au:
            via = self._SECOND_FACTOR[au]
            if self._debug:
                print(f"  -> Apple requires a second confirmation "
                      f"(au={au}, via {via}).", flush=True)
            self._do_two_factor(spd, via)
            if via == VIA_SMS:
                confirmed = self._confirmed_session(spd)
                if confirmed:
                    return confirmed
            # After passing 2FA the handshake starts over - Apple ties the
            # trust to the ADI identity, not to the session.
            spd, srp_key, complete = self._handshake(apple_id, password)
            self._trace(spd, "spd (after 2FA)")
            still = self._second_factor(complete, spd)
            if still:
                # The au value stays untranslated: it is what a bug report
                # needs to tell trusted-device from SMS confirmation.
                raise AppleError(_(
                    "Apple asks for another code after the two-factor "
                    "confirmation. Resetting the provisioning state usually "
                    "helps: modstaller logout --forget-device")
                    + f" (au={still})")
        return self._result(spd)

    def _confirmed_session(self, spd: dict) -> GSAResult | None:
        """After a text-message confirmation: the session it confirmed.

        The SMS route runs over Apple's web sign-in (``gsa.apple.com/auth``),
        which confirms the session it was started for. A fresh handshake
        can come back asking for a code all over again (issue #3, and the
        same loop in other GrandSlam clients). So the confirmed session gets
        the token exchange first; only if Apple turns it down does the
        handshake start over.
        """
        try:
            return self._result(spd)
        except GSAStatusError as exc:
            if exc.code == ERR_TEMPORARILY_BLOCKED:
                raise
            if self._debug:
                print(f"  -> Confirmed session not accepted (Code {exc.code})"
                      f" - signing in again.", flush=True)
            return None

    def _result(self, spd: dict) -> GSAResult:
        adsid, token = spd.get("adsid"), spd.get("GsIdmsToken")
        if not adsid or not token:
            raise AppleError(_("GSA returned no adsid/GsIdmsToken - "
                               "the sign-in is incomplete."))

        app_token = self._fetch_app_token(spd, adsid, token)
        return GSAResult(
            adsid=adsid,
            idms_token=token,
            app_token=app_token,
            identity_token=b64encode(f"{adsid}:{app_token}".encode()).decode(),
            first_name=str(spd.get("fn") or "").strip(),
        )

    def _fetch_app_token(self, spd: dict, adsid: str, idms_token: str) -> str:
        """Exchanges the login token for one for the developer API."""
        session_key = spd.get("sk")
        cookie = spd.get("c")
        if not session_key or cookie is None:
            raise AppleError(_(
                "GSA returned no session key - without it no token for the "
                "developer API can be requested."))

        # Authenticates the request: only someone who knows the session key
        # can make it. The order is part of the protocol.
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
            raise AppleError(_("Apple returned no app token."))

        tokens = _decrypt_app_token(bytes(session_key), bytes(encrypted))
        entry = (tokens.get("t") or {}).get(XCODE_APP) or {}
        app_token = entry.get("token")
        if not app_token:
            raise AppleError(_(
                "Apple issued no token for {app}. Usually the account is not "
                "registered as a developer - sign in once on "
                "developer.apple.com and accept the terms.", app=XCODE_APP))
        return app_token

    def _handshake(self, apple_id: str,
                   password: str) -> tuple[dict, bytes, dict]:
        """Returns: decrypted ``spd``, SRP key, raw ``complete`` response.

        The raw response is needed because Apple puts the hint about a
        required two-factor confirmation in ``Status.au`` - i.e. *next to*
        the encrypted spd, not inside it.
        """
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
            raise AppleError(_(
                "Apple’s session proof does not match. The other side could "
                "not prove the key - do not trust this connection."))
        assert srp.K is not None
        return _decrypt_spd(srp.K, complete["spd"]), srp.K, complete

    # -- Two-factor -------------------------------------------------------

    #: Values with which Apple requests a second confirmation - and how it
    #: wants it. ``secondaryAuth`` is the text message to the trusted phone
    #: number. Answered over the trusted-device route instead, a code still
    #: lands on the iPhone, but the session is never confirmed: Apple asks
    #: again on the next handshake.
    _SECOND_FACTOR = {
        "trustedDeviceSecondaryAuth": VIA_DEVICE,
        "secondaryAuth": VIA_SMS,
        "smsSecondaryAuth": VIA_SMS,
    }

    @classmethod
    def _second_factor(cls, complete: dict, spd: dict) -> str | None:
        """Looks for the 2FA hint everywhere Apple puts it and returns it.

        Primarily ``Status.au`` in the ``complete`` response. If that is
        missed, the login appears to succeed but yields an only half-valid
        session - and Apple answers the subsequent token exchange with
        "Enter the correct password", which points in completely the wrong
        direction.
        """
        candidates = (
            (complete.get("Status") or {}).get("au"),
            complete.get("au"),
            spd.get("au"),
        )
        return next((c for c in candidates if c in cls._SECOND_FACTOR), None)

    @classmethod
    def _needs_2fa(cls, complete: dict, spd: dict) -> bool:
        return cls._second_factor(complete, spd) is not None

    def _two_factor_headers(self, spd: dict) -> dict[str, str]:
        identity = b64encode(
            f"{spd['adsid']}:{spd['GsIdmsToken']}".encode()).decode()
        headers = {
            "Content-Type": "text/x-xml-plist",
            "Accept": "text/x-xml-plist",
            "User-Agent": http.USER_AGENT_XCODE,
            "Accept-Language": "en-us",
            "X-Apple-Identity-Token": identity,
            # As AltSign sends them: Apple attributes this step to Xcode.
            "X-Apple-App-Info": XCODE_APP,
            "X-Xcode-Version": http.XCODE_VERSION,
        }
        ani = self._ani.headers()
        headers.update({k: v for k, v in ani.items() if k.startswith("X-")})
        headers["X-MMe-Client-Info"] = clientinfo.sanitize(self._ani.client_info())
        return headers

    @staticmethod
    def _plist(resp) -> dict | None:
        """The response body as a plist - ``None`` for anything else (an
        HTML error page, an empty body, JSON)."""
        try:
            parsed = plistlib.loads(resp.content)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _trace_response(self, resp, label: str, parsed: dict | None,
                        sent: dict | None = None) -> None:
        """Status, which headers and cookies Apple handed out (names only),
        the device the request spoke for, and the redacted body."""
        if not self._debug:
            return
        names = sorted(k for k in (resp.headers or {})
                       if k.lower().startswith(("x-apple", "scnt")))
        cookies = sorted(c.name for c in getattr(resp, "cookies", None) or ())
        line = (f"  [{label}] HTTP {resp.status_code}, "
                f"{len(resp.content or b'')} bytes")
        if sent is not None:
            line += f", device {_identity_tag(sent)}"
        if names:
            line += f"\n      response headers: {', '.join(names)}"
        if cookies:
            line += f"\n      cookies: {', '.join(cookies)}"
        print(line, flush=True)
        if parsed is not None:
            self._trace(parsed, label)

    def _do_two_factor(self, spd: dict, via: str = VIA_DEVICE) -> None:
        if self._prompt is None:
            raise InteractionRequired(_(
                "Apple requires a two-factor code, but ModStaller is running "
                "non-interactively. Run ‘modstaller login’ once."))
        if via == VIA_SMS:
            phone_id = self._trusted_phone_id(spd)
            self._send_sms(spd, phone_id)
        else:
            self._send_to_devices(spd)

        code = self._prompt(via).strip()
        if not code:
            raise AppleError(_("No two-factor code was entered."))

        # Both build their headers afresh: the one-time password from
        # sending is as old as the time it took to type the code.
        if via == VIA_SMS:
            self._confirm_sms(spd, code, phone_id)
            self._trust_device(spd)
        else:
            self._confirm_on_device(spd, code)

    # -- ... via the trusted devices ---------------------------------------

    def _send_to_devices(self, spd: dict) -> None:
        headers = self._two_factor_headers(spd)
        resp = http.gsa_request(
            self._session, "GET", _TRUSTED_DEVICE_URL,
            client_info=headers["X-MMe-Client-Info"], headers=headers)
        parsed = self._plist(resp)
        self._trace_response(resp, "trusteddevice", parsed, headers)
        if resp.status_code >= 400:
            # Apple's own reason first, if it sent one.
            self._check(parsed or {})
            raise AppleError(_(
                "Apple could not send a two-factor code (HTTP {status}).",
                status=resp.status_code))

    def _confirm_on_device(self, spd: dict, code: str) -> None:
        headers = self._two_factor_headers(spd)
        resp = http.gsa_request(
            self._session, "GET", _VALIDATE_URL,
            client_info=headers["X-MMe-Client-Info"],
            headers={**headers, "security-code": code})
        parsed = self._plist(resp)
        self._trace_response(resp, "validate", parsed, headers)
        # No plist means no confirmation - whatever the status says. Taking
        # it for success leads straight to "asks for another code".
        if parsed is None:
            raise AppleError(
                f"2FA validation failed (HTTP {resp.status_code}).")
        self._check(parsed)

    # -- ... via text message ------------------------------------------------
    #
    # This is Apple's web sign-in (gsa.apple.com/auth), not GrandSlam: JSON,
    # session markers in headers, errors as "serviceErrors". The order -
    # load the page, send, confirm - follows isideload, whose SMS route is
    # known to get through to a signed-in session.

    def _sms_headers(self, spd: dict) -> dict[str, str]:
        return {**self._two_factor_headers(spd),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": http.USER_AGENT_AKD,
                **self._web_session}

    def _web_request(self, spd: dict, method: str, url: str, label: str,
                     body: dict | None = None) -> tuple:
        headers = self._sms_headers(spd)
        resp = http.gsa_request(
            self._session, method, url,
            client_info=headers["X-MMe-Client-Info"], headers=headers,
            data=None if body is None else json.dumps(body).encode())
        # The web sign-in ties its steps together with these two headers -
        # a browser sends back what it was given.
        for key, value in (resp.headers or {}).items():
            canonical = _WEB_SESSION_HEADERS.get(key.lower())
            if canonical:
                self._web_session[canonical] = value
        parsed = self._json(resp)
        self._trace_response(resp, label, parsed, headers)
        return resp, parsed

    @staticmethod
    def _sms_body(phone_id: int, code: str | None = None) -> dict:
        body: dict = {"phoneNumber": {"id": phone_id}, "mode": "sms"}
        if code is not None:
            body["securityCode"] = {"code": code}
        return body

    @staticmethod
    def _json(resp) -> dict | None:
        try:
            parsed = json.loads(resp.content)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _service_error(parsed: dict | None) -> tuple[str, str] | None:
        """Apple's code and wording from a JSON error (``serviceErrors``)."""
        errors = (parsed or {}).get("serviceErrors")
        if not isinstance(errors, list) or not errors \
                or not isinstance(errors[0], dict):
            return None
        parts = [p.strip() for p in (errors[0].get("title"),
                                     errors[0].get("message"))
                 if isinstance(p, str) and p.strip()]
        return str(errors[0].get("code", "")), ": ".join(dict.fromkeys(parts))

    def _trusted_phone_id(self, spd: dict) -> int:
        """Loads the sign-in page Apple named in ``au``, as Apple's own
        client does first. Its JSON lists the trusted numbers with the ids
        the phone endpoints expect. Falls back to the first number."""
        _resp, parsed = self._web_request(spd, "GET", _AUTH_URL, "auth")
        numbers = [n for n in (parsed or {}).get("trustedPhoneNumbers") or ()
                   if isinstance(n, dict) and isinstance(n.get("id"), int)]
        texts = [n for n in numbers if n.get("pushMode") == "sms"]
        return (texts or numbers or [{"id": _PHONE_ID}])[0]["id"]

    def _send_sms(self, spd: dict, phone_id: int) -> None:
        resp, parsed = self._web_request(spd, "PUT", _SMS_URL, "verify/phone",
                                         self._sms_body(phone_id))
        # 412: a challenge is already active. 423: codes were sent already.
        # Either way, the last code that arrived still counts.
        if 200 <= resp.status_code < 300 or resp.status_code in (412, 423):
            return
        error = self._service_error(parsed)
        if error and error[0] in _CODE_STILL_VALID:
            return
        raise AppleError((error and error[1]) or _(
            "Apple could not send a two-factor code (HTTP {status}).",
            status=resp.status_code))

    def _confirm_sms(self, spd: dict, code: str, phone_id: int) -> None:
        resp, parsed = self._web_request(
            spd, "POST", _SMS_CODE_URL, "verify/phone/securitycode",
            self._sms_body(phone_id, code))
        if 200 <= resp.status_code < 300:
            return
        error = self._service_error(parsed)
        if error and error[1]:
            raise AppleError(error[1])
        if resp.status_code in (400, 401, 403):
            raise AppleError(f"{_(_MESSAGES[ERR_INVALID_CODE])} "
                             f"(HTTP {resp.status_code})")
        raise AppleError(f"2FA validation failed (HTTP {resp.status_code}).")

    def _trust_device(self, spd: dict) -> None:
        """Asks the web sign-in to trust this device - the step a browser
        takes after the code. Best effort: the code is confirmed either way,
        and what Apple answers ends up in the trace."""
        try:
            self._web_request(spd, "GET", _TRUST_URL, "2sv/trust")
        except (AppleError, requests.RequestException) as exc:
            if self._debug:
                print(f"  [2sv/trust] failed: {exc}", flush=True)
