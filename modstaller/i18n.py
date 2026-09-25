"""Uebersetzung der Texte, die beim Nutzer ankommen.

Quellsprache im Code ist Englisch - der englische Satz *ist* der Schluessel.
Das hat zwei Vorteile: man liest an der Fundstelle, was dort steht, ohne einen
Katalog aufzuschlagen, und eine fehlende Uebersetzung faellt auf Englisch
zurueck statt auf ``apps.install.error.3``.

    from .i18n import _
    raise DeviceError(_("No iPhone connected."))
    raise SigningError(_("zsign failed (exit {code}).", code=rc))

Platzhalter sind benannt, nie positionell: in anderen Sprachen steht die
Reihenfolge der Satzteile anders.

Welche Sprache gilt, sagt die Oberflaeche beim Verbinden (``i18n.set``). Die
CLI bleibt bei der Quellsprache. Kommentare und Docstrings sind deutsch und
bleiben es - die liest niemand ausser uns.
"""

from __future__ import annotations

import json
from pathlib import Path

#: Hier liegen die Kataloge, eine JSON-Datei je Sprache.
LOCALE_DIR = Path(__file__).parent / "locale"

#: Die Quellsprache braucht keinen Katalog.
SOURCE = "en"

_language = SOURCE
_catalog: dict[str, str] = {}


def available() -> list[str]:
    """Welche Sprachen mitgeliefert sind - Quellsprache zuerst."""
    others = sorted(p.stem for p in LOCALE_DIR.glob("*.json"))
    return [SOURCE] + [o for o in others if o != SOURCE]


def language() -> str:
    return _language


def set_language(lang: str) -> str:
    """Stellt die Sprache um. Rueckgabe: was tatsaechlich gilt.

    Unbekanntes faellt auf die Quellsprache zurueck, statt zu scheitern - eine
    Oberflaeche in einer Sprache, die wir nicht haben, soll trotzdem laufen.
    Ein Regionszusatz wird abgeschnitten, wenn nur die Sprache vorliegt
    (``de-AT`` findet ``de``), und ``pt-BR`` zaehlt als eigene Sprache.
    """
    global _language, _catalog

    wanted = (lang or "").replace("_", "-").strip()
    have = available()
    for candidate in (wanted, wanted.split("-")[0]):
        match = next((h for h in have if h.lower() == candidate.lower()), None)
        if match:
            break
    else:
        match = None

    match = match or SOURCE
    if match == SOURCE:
        _language, _catalog = SOURCE, {}
        return _language

    try:
        raw = json.loads((LOCALE_DIR / f"{match}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _language, _catalog = SOURCE, {}
        return _language

    # Leere Eintraege heissen "noch nicht uebersetzt" - dann lieber Englisch.
    _catalog = {k: v for k, v in raw.items() if isinstance(v, str) and v}
    _language = match
    return _language


def _(text: str, /, **params: object) -> str:
    """Der uebersetzte Satz, mit eingesetzten Platzhaltern."""
    out = _catalog.get(text, text)
    if not params:
        return out
    try:
        return out.format(**params)
    except (IndexError, KeyError):
        # Ein Katalog mit falschem Platzhalter darf nichts abstuerzen lassen.
        return text.format(**params)


def _n(singular: str, plural: str, count: int, /, **params: object) -> str:
    """Ein- oder Mehrzahl. ``count`` steht als ``{count}`` zur Verfuegung.

    Bewusst nur zwei Formen: mehr braucht keine der mitgelieferten Sprachen.
    Die Katalogschluessel sind die beiden englischen Saetze.
    """
    return _(singular if count == 1 else plural, count=count, **params)
