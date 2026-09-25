"""X-MMe-Client-Info: Aushandeln, Sanitisieren, Validieren.

Hintergrund
-----------
Apple weist seit Ende August 2026 an der Edge jeden Request an
``gsa.apple.com/grandslam/GsService2`` ab, dessen ``X-MMe-Client-Info`` den
Identifier ``com.apple.dt.Xcode`` traegt. Die Antwort ist ein HTTP 503 mit
einer 190 Byte grossen HTML-Seite nach ~0,2 s - also genau das, was ein
transienter Ausfall auch waere. Naives Retry-Verhalten wartet hier ewig.

Der Identifier muss stattdessen ``com.apple.akd`` lauten, Apples eigenen
Authentication-Daemon. Empirisch gegen Apple geprueft (2026-09-22):

    com.apple.dt.Xcode  -> HTTP 503, 190 B   (an der Edge abgewiesen)
    com.apple.akd/1.0   -> HTTP 404, 0 B     (durchgekommen, Service antwortet)

GSA setzt diesen Header getrennt von den uebrigen Auth-Headern. Wer ihn nur an
einer Call-Site korrigiert, laesst die anderen kaputt. Deshalb gibt es genau
dieses Modul - und :func:`assert_safe` als Transport-Guard, der jeden Ausreisser
lokal stoppt, bevor er ueberhaupt rausgeht.
"""

from __future__ import annotations

import re

from ..errors import ClientInfoPolicyViolation
from ..i18n import _

#: Der von Apple abgelehnte Identifier.
REJECTED_IDENTIFIER = "com.apple.dt.Xcode"

#: Womit wir ihn ersetzen.
AKD_IDENTIFIER = "com.apple.akd/1.0"

#: Fallback, falls ein Provider gar keine Client-Info liefert.
DEFAULT_CLIENT_INFO = (
    "<MacBookPro13,2> <macOS;13.1;22C65> "
    f"<com.apple.AuthKit/1 ({AKD_IDENTIFIER})>"
)

#: Erwartete Form: <Modell> <OS;Version;Build> <com.apple.AuthKit/N (app/ver)>
_SHAPE = re.compile(
    r"^<[^<>]+>\s+<[^<>]+>\s+<com\.apple\.AuthKit/\d+\s+\([^()<>]+\)>$"
)

#: Die App-Komponente in der dritten Klammer, z.B. "com.apple.dt.Xcode/3594.4.19".
_APP_COMPONENT = re.compile(r"\(([^()]+)\)>\s*$")


def sanitize(client_info: str | None) -> str:
    """Macht einen beliebigen Client-Info-String GSA-tauglich.

    Ersetzt die App-Komponente durch ``com.apple.akd/1.0``, wenn sie Xcode
    nennt. Modell- und OS-Angabe des Providers bleiben erhalten - die passen
    zur ADI-Identitaet des Rechners und sollen konsistent bleiben.
    """
    if not client_info or not client_info.strip():
        return DEFAULT_CLIENT_INFO

    cleaned = client_info.strip()
    if REJECTED_IDENTIFIER not in cleaned:
        return cleaned

    replaced, n = _APP_COMPONENT.subn(f"({AKD_IDENTIFIER})>", cleaned)
    if n == 0 or REJECTED_IDENTIFIER in replaced:
        # Unerwartete Form - lieber der bekannt gute Default als ein 503.
        return DEFAULT_CLIENT_INFO
    return replaced


def is_safe(client_info: str | None) -> bool:
    return bool(client_info) and REJECTED_IDENTIFIER not in client_info


def assert_safe(client_info: str | None, *, where: str = "GSA-Request") -> None:
    """Transport-Guard. Wirft lokal, bevor Apple mit 503 antworten kann."""
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
    """Formpruefung. Bewusst nur eine Warnung wert, kein harter Abbruch -
    Apple aendert die Form gelegentlich, und Form ist nicht Policy."""
    return bool(_SHAPE.match(client_info))
