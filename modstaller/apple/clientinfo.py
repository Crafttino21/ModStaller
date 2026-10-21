"""X-MMe-Client-Info: negotiating, sanitizing, validating.

Background
----------
Since late August 2026 Apple rejects at the edge every request to
``gsa.apple.com/grandslam/GsService2`` whose ``X-MMe-Client-Info`` carries
the identifier ``com.apple.dt.Xcode``. The response is an HTTP 503 with a
190-byte HTML page after ~0.2 s - exactly what a transient outage would look
like. Naive retry behaviour waits forever here.

The identifier must instead be ``com.apple.akd``, Apple's own authentication
daemon. Verified empirically against Apple (2026-09-22):

    com.apple.dt.Xcode  -> HTTP 503, 190 B   (rejected at the edge)
    com.apple.akd/1.0   -> HTTP 404, 0 B     (got through, service responds)

GSA sets this header separately from the other auth headers. Fixing it at
only one call site leaves the others broken. That is why this one module
exists - plus :func:`assert_safe` as a transport guard that stops any stray
value locally, before it even goes out.

Since 2026-10-12 Apple also answers the very first sign-in request with
``ec=-80045`` ("This action cannot be completed at this time") when the
client info claims macOS. The anisette data comes from an emulated *Android*
ADI - locally from the ``anisette`` library as well as from every
anisette-v3 server - and Apple now checks that the two fit together. So the
sign-in claims Android (:func:`for_auth`), as iloader/isideload do since
2.3.7/0.4.5. Provisioning keeps the macOS value: the URL bag Apple hands out
for an Android client info is the wrong one.
"""

from __future__ import annotations

import re

from ..errors import ClientInfoPolicyViolation
from ..i18n import _

#: The identifier Apple rejects.
REJECTED_IDENTIFIER = "com.apple.dt.Xcode"

#: What we replace it with.
AKD_IDENTIFIER = "com.apple.akd/1.0"

#: Fallback in case a provider supplies no client info at all.
DEFAULT_CLIENT_INFO = (
    "<MacBookPro13,2> <macOS;13.1;22C65> "
    f"<com.apple.AuthKit/1 ({AKD_IDENTIFIER})>"
)

#: What GSA gets to see during sign-in - matching the Android ADI.
ANDROID_CLIENT_INFO = (
    "<Pixel 7> <Android;14;UQ1A.240205.002> "
    f"<com.apple.AuthKit/1 ({AKD_IDENTIFIER})>"
)

#: The OS bracket of a client info that claims macOS.
_MACOS = re.compile(r"<macOS;")

#: Expected shape: <model> <OS;version;build> <com.apple.AuthKit/N (app/ver)>
_SHAPE = re.compile(
    r"^<[^<>]+>\s+<[^<>]+>\s+<com\.apple\.AuthKit/\d+\s+\([^()<>]+\)>$"
)

#: The app component in the third bracket, e.g. "com.apple.dt.Xcode/3594.4.19".
_APP_COMPONENT = re.compile(r"\(([^()]+)\)>\s*$")


def sanitize(client_info: str | None) -> str:
    """Makes an arbitrary client info string acceptable to GSA.

    Replaces the app component with ``com.apple.akd/1.0`` if it names Xcode.
    The provider's model and OS details are kept - they match the machine's
    ADI identity and should stay consistent.
    """
    if not client_info or not client_info.strip():
        return DEFAULT_CLIENT_INFO

    cleaned = client_info.strip()
    if REJECTED_IDENTIFIER not in cleaned:
        return cleaned

    replaced, n = _APP_COMPONENT.subn(f"({AKD_IDENTIFIER})>", cleaned)
    if n == 0 or REJECTED_IDENTIFIER in replaced:
        # Unexpected shape - better the known-good default than a 503.
        return DEFAULT_CLIENT_INFO
    return replaced


def for_auth(client_info: str | None) -> str:
    """The client info for sign-in and the developer API.

    A macOS claim becomes :data:`ANDROID_CLIENT_INFO` - Apple rejects it
    next to Android anisette data with -80045. Anything else (say an
    anisette server that already names its own platform) only gets
    :func:`sanitize`.
    """
    cleaned = sanitize(client_info)
    if _MACOS.search(cleaned):
        return ANDROID_CLIENT_INFO
    return cleaned


def is_safe(client_info: str | None) -> bool:
    return bool(client_info) and REJECTED_IDENTIFIER not in client_info


def assert_safe(client_info: str | None, *, where: str = "GSA request") -> None:
    """Transport guard. Raises locally before Apple can answer with a 503."""
    if not client_info:
        raise ClientInfoPolicyViolation(_(
            "{where}: X-MMe-Client-Info is missing. Apple would reject the "
            "request.", where=where))
    if REJECTED_IDENTIFIER in client_info:
        raise ClientInfoPolicyViolation(_(
            "{where}: X-MMe-Client-Info states {rejected!r}. Since August "
            "2026 Apple answers that with HTTP 503 at the edge. Expected is "
            "{wanted!r}. Seen: {seen!r}",
            where=where, rejected=REJECTED_IDENTIFIER,
            wanted=AKD_IDENTIFIER, seen=client_info))


def looks_well_formed(client_info: str) -> bool:
    """Shape check. Deliberately worth only a warning, not a hard abort -
    Apple changes the shape occasionally, and shape is not policy."""
    return bool(_SHAPE.match(client_info))
