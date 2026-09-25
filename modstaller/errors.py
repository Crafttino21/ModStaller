"""Ausnahme-Hierarchie und Uebersetzung von Apple-Fehlercodes in klare Meldungen."""

from __future__ import annotations

from .i18n import _


class ModStallerError(Exception):
    """Basis fuer alles, was ModStaller selbst als Fehler erkennt."""

    exit_code = 1


class ConfigError(ModStallerError):
    exit_code = 2


class DeviceError(ModStallerError):
    """Geraet fehlt, ist nicht gepairt oder ein Dienst antwortet nicht."""

    exit_code = 4


class DeviceNotFound(DeviceError):
    pass


class NotPaired(DeviceError):
    pass


class DeveloperModeDisabled(DeviceError):
    pass


class SigningError(ModStallerError):
    exit_code = 5


class InteractionRequired(ModStallerError):
    """Ein Prompt waere noetig, aber wir laufen nicht-interaktiv (Daemon)."""

    exit_code = 6


class AppleError(ModStallerError):
    """Alles, was von Apples Servern als Fehler zurueckkommt."""

    exit_code = 3


class ClientInfoPolicyViolation(AppleError):
    """Lokal ausgeloest, bevor ein Request rausgeht.

    Apple weist seit August/September 2026 jeden GSA-Request an der Edge mit
    HTTP 503 ab, dessen X-MMe-Client-Info ``com.apple.dt.Xcode`` nennt. Das ist
    von einem echten Ausfall nicht zu unterscheiden, deshalb pruefen wir vorher
    selbst und melden die Ursache im Klartext statt in Retries zu verhungern.
    """


class AnisetteClientInfoRejected(AppleError):
    """Apple hat den Client-Info-String an der Edge abgelehnt (HTTP 503)."""


class AppleAPIError(AppleError):
    """Ein ``resultCode != 0`` von developerservices2."""

    def __init__(self, code: int, result_string: str = "", user_string: str = ""):
        self.code = code
        self.result_string = result_string
        self.user_string = user_string
        super().__init__(user_string or result_string
                         or _("Apple error {code}", code=code))


# --- Fehlercodes, auf die wir gezielt reagieren -----------------------------
# Die Zahlen sind Apples, die Konsequenzen unsere.

DEVICE_ALREADY_REGISTERED = 35      # kein Fehler: Geraet war schon drin
INVALID_CSR = 3250
APP_ID_QUOTA_EXCEEDED = 9120        # Free: 10 App-IDs pro Woche aufgebraucht
APP_ID_UNAVAILABLE = 9401           # Identifier gehoert einem anderen Account
CERTIFICATE_NOT_FOUND = 7252        # DELETE auf ein bereits geloeschtes Zertifikat

#: Codes, die wir als Erfolg durchwinken statt als Fehler zu werfen.
BENIGN_CODES = frozenset({DEVICE_ALREADY_REGISTERED, CERTIFICATE_NOT_FOUND})

#: Klartext-Hinweise, die dem Nutzer sagen, was er *tun* kann. Uebersetzt
#: wird erst in remedy_for(): beim Import steht die Sprache noch nicht fest.
REMEDIES: dict[int, str] = {
    APP_ID_QUOTA_EXCEEDED: (
        "Apple allows ten *newly created* App IDs per week. Deleting existing "
        "ones does not help - the window counts creations, not the total. "
        "ModStaller therefore falls back to an existing, unused App ID; if "
        "there is none, the only option is to wait for the rolling seven-day "
        "window to open again."
    ),
    APP_ID_UNAVAILABLE: (
        "This bundle identifier is already taken by another Apple account. "
        "ModStaller automatically appends a different suffix."
    ),
    INVALID_CSR: (
        "Apple rejected the certificate signing request. The key is "
        "regenerated and submitted once more."
    ),
}


def remedy_for(code: int) -> str:
    text = REMEDIES.get(code, "")
    return _(text) if text else ""


class AppleRateLimited(AppleError):
    """Apple hat gedrosselt (HTTP 429). Weitere Versuche verschlimmern es."""

    exit_code = 7


def describe(exc: BaseException) -> str | None:
    """Klartext fuer Fehler, die der Nutzer verstehen soll.

    ``None`` heisst: unerwartet - der Aufrufer entscheidet, ob er einen
    Stacktrace zeigt. Netz- und Bibliotheksfehler sollen nicht als Traceback
    erscheinen.
    """
    if isinstance(exc, ModStallerError):
        return str(exc)
    try:
        import requests
    except ImportError:
        return None
    if isinstance(exc, requests.exceptions.RetryError):
        return _("Apple refused repeatedly and the attempt was given up.\n"
                 "Usually throttling - wait 15 to 60 minutes.")
    if isinstance(exc, requests.exceptions.SSLError):
        return _("TLS connection to Apple failed.\n{error}", error=exc)
    if isinstance(exc, requests.exceptions.RequestException):
        return _("Network problem while talking to Apple.\n{error}", error=exc)
    return None
