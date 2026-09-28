"""Exception hierarchy and translation of Apple error codes into clear messages."""

from __future__ import annotations

from .i18n import _


class ModStallerError(Exception):
    """Base for everything ModStaller itself recognizes as an error."""

    exit_code = 1


class ConfigError(ModStallerError):
    exit_code = 2


class DeviceError(ModStallerError):
    """Device is missing, not paired, or a service does not respond."""

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
    """A prompt would be needed, but we run non-interactively (daemon)."""

    exit_code = 6


class AppleError(ModStallerError):
    """Anything that comes back from Apple's servers as an error."""

    exit_code = 3


class ClientInfoPolicyViolation(AppleError):
    """Raised locally, before a request goes out.

    Since August/September 2026 Apple rejects every GSA request at the edge
    with HTTP 503 if its X-MMe-Client-Info names ``com.apple.dt.Xcode``. That
    is indistinguishable from a real outage, so we check beforehand ourselves
    and report the cause in plain words instead of starving in retries.
    """


class AnisetteClientInfoRejected(AppleError):
    """Apple rejected the client info string at the edge (HTTP 503)."""


class AppleAPIError(AppleError):
    """A ``resultCode != 0`` from developerservices2."""

    def __init__(self, code: int, result_string: str = "", user_string: str = ""):
        self.code = code
        self.result_string = result_string
        self.user_string = user_string
        super().__init__(user_string or result_string
                         or _("Apple error {code}", code=code))


# --- Error codes we handle specifically -------------------------------------
# The numbers are Apple's, the consequences ours.

DEVICE_ALREADY_REGISTERED = 35      # not an error: device was already registered
INVALID_CSR = 3250
APP_ID_QUOTA_EXCEEDED = 9120        # Free: 10 App IDs per week used up
APP_ID_UNAVAILABLE = 9401           # identifier belongs to another account
CERTIFICATE_NOT_FOUND = 7252        # DELETE on an already deleted certificate

#: Codes we wave through as success instead of raising an error.
BENIGN_CODES = frozenset({DEVICE_ALREADY_REGISTERED, CERTIFICATE_NOT_FOUND})

#: Plain-language hints telling the user what they can *do*. Translation
#: happens only in remedy_for(): at import time the language isn't set yet.
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
    """Apple throttled us (HTTP 429). Further attempts make it worse."""

    exit_code = 7


def describe(exc: BaseException) -> str | None:
    """Plain text for errors the user is meant to understand.

    ``None`` means: unexpected - the caller decides whether to show a stack
    trace. Network and library errors should not show up as a traceback.
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
