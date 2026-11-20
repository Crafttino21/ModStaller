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

Since October 2026 the client info also has to fit the anisette data
behind it. Android anisette data is refused either way: next to a macOS
client info with -80045, next to an Android one with this same HTTP 503
(1.4.0-rc.5, issue #4). The anisette-v3 server therefore names the client
info - see ``anisette.RemoteV3Provider``.

November 2026, two more rules (AltStore #1853, #1864, #1875; iloader 2.4.1
and 2.4.2 ran into both):

* The Mac the public anisette servers report, macOS 10.12.6, is too old.
  Apple answers some accounts with -23782 ("A Mac with macOS version 10.13
  or later is required") and confirms the others by text message instead of
  on a trusted device - the code is taken, and the next handshake asks for
  one again (issues #3, #7). :func:`outdated_mac` spots it, and
  :data:`CURRENT_MAC` stands in for it.
* The OS has to be spelled ``Mac OS X``, as Apple's own frameworks still
  send it. ``<macOS;…>`` gets the 503 at the edge. Verified against Apple
  (2026-11-20, made-up account, ``init``):

    <Mac OS X;10.12.6;16G29>  -> got through
    <macOS;27.2;26B123>       -> HTTP 503, 190 B
    <Mac OS X;27.2;26B123>    -> got through
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
    "<MacBookPro13,2> <Mac OS X;13.1;22C65> "
    f"<com.apple.AuthKit/1 ({AKD_IDENTIFIER})>"
)

#: A current Mac as akd introduces itself, with the user agent that belongs
#: to it - the macOS 27.2 machine AltStore #1864 signed in with through
#: trusted-device 2FA, spelled the way the edge lets through. Stands in for
#: an anisette server's outdated Mac; the server's ADI is a Mac's either way.
CURRENT_MAC = (f"<Mac17,3> <Mac OS X;27.2;26B123> "
               f"<com.apple.AuthKit/1 ({AKD_IDENTIFIER})>")
CURRENT_MAC_USER_AGENT = "akd/1.0 CFNetwork/3896.200.61 Darwin/27.2.0"

#: Macs older than this are outdated for Apple: 10.12 gets -23782 or the
#: text-message route, and Advanced Data Protection needs 13.1.
_MIN_MAC = (13, 1)

#: Expected shape: <model> <OS;version;build> <com.apple.AuthKit/N (app/ver)>
_SHAPE = re.compile(
    r"^<[^<>]+>\s+<[^<>]+>\s+<com\.apple\.AuthKit/\d+\s+\([^()<>]+\)>$"
)

#: The app component in the third bracket, e.g. "com.apple.dt.Xcode/3594.4.19".
_APP_COMPONENT = re.compile(r"\(([^()]+)\)>\s*$")

#: The OS bracket: "<Mac OS X;10.12.6;16G29>".
_OS = re.compile(r"^<[^<>]+>\s+<(?P<os>[^;<>]+);(?P<version>[^;<>]+);")


def sanitize(client_info: str | None) -> str:
    """Makes an arbitrary client info string acceptable to GSA.

    Replaces the app component with ``com.apple.akd/1.0`` if it names Xcode,
    and spells the OS ``Mac OS X``. The provider's model and OS details are
    kept - they match the machine's ADI identity and should stay consistent.
    """
    if not client_info or not client_info.strip():
        return DEFAULT_CLIENT_INFO

    cleaned = client_info.strip().replace("<macOS;", "<Mac OS X;")
    if REJECTED_IDENTIFIER not in cleaned:
        return cleaned

    replaced, n = _APP_COMPONENT.subn(f"({AKD_IDENTIFIER})>", cleaned)
    if n == 0 or REJECTED_IDENTIFIER in replaced:
        # Unexpected shape - better the known-good default than a 503.
        return DEFAULT_CLIENT_INFO
    return replaced


def outdated_mac(client_info: str) -> bool:
    """Does the client info name a Mac older than Apple still lets sign in
    properly? Anything that is not a Mac - a Windows ADI, say - is left
    alone."""
    m = _OS.match(client_info.strip())
    if not m or m["os"].strip() not in ("Mac OS X", "macOS"):
        return False
    try:
        version = tuple(int(part) for part in m["version"].split(".")[:2])
    except ValueError:
        return False
    return version < _MIN_MAC


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
