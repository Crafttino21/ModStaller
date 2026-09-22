"""Ausnahme-Hierarchie und Uebersetzung von Apple-Fehlercodes in klare Meldungen."""

from __future__ import annotations


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
        super().__init__(user_string or result_string or f"Apple-Fehler {code}")


# --- Fehlercodes, auf die wir gezielt reagieren -----------------------------
# Die Zahlen sind Apples, die Konsequenzen unsere.

DEVICE_ALREADY_REGISTERED = 35      # kein Fehler: Geraet war schon drin
INVALID_CSR = 3250
APP_ID_QUOTA_EXCEEDED = 9120        # Free: 10 App-IDs pro Woche aufgebraucht
APP_ID_UNAVAILABLE = 9401           # Identifier gehoert einem anderen Account
CERTIFICATE_NOT_FOUND = 7252        # DELETE auf ein bereits geloeschtes Zertifikat

#: Codes, die wir als Erfolg durchwinken statt als Fehler zu werfen.
BENIGN_CODES = frozenset({DEVICE_ALREADY_REGISTERED, CERTIFICATE_NOT_FOUND})

#: Klartext-Hinweise, die dem Nutzer sagen, was er *tun* kann.
REMEDIES: dict[int, str] = {
    APP_ID_QUOTA_EXCEEDED: (
        "Das Wochenkontingent von 10 App-IDs ist aufgebraucht. ModStaller kann "
        "eine alte, ungenutzte App-ID recyceln (--recycle-app-ids) oder du "
        "wartest, bis das rollierende 7-Tage-Fenster wieder aufgeht."
    ),
    APP_ID_UNAVAILABLE: (
        "Dieser Bundle-Identifier ist bereits von einem anderen Apple-Account "
        "belegt. ModStaller haengt automatisch ein anderes Suffix an."
    ),
    INVALID_CSR: (
        "Apple hat den Certificate Signing Request abgelehnt. Der Schluessel "
        "wird neu erzeugt und einmal erneut eingereicht."
    ),
}


def remedy_for(code: int) -> str:
    return REMEDIES.get(code, "")


class AppleRateLimited(AppleError):
    """Apple hat gedrosselt (HTTP 429). Weitere Versuche verschlimmern es."""

    exit_code = 7
