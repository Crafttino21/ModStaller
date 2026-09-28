"""Translation of the texts that reach the user.

The source language in the code is English - the English sentence *is* the
key. That has two advantages: you read what it says right where it is used,
without looking up a catalog, and a missing translation falls back to English
instead of ``apps.install.error.3``.

    from .i18n import _
    raise DeviceError(_("No iPhone connected."))
    raise SigningError(_("zsign failed (exit {code}).", code=rc))

Placeholders are named, never positional: other languages order the parts
of a sentence differently.

The interface says which language applies when it connects (``i18n.set``).
The CLI sticks to the source language. Comments and docstrings are in
English, too.
"""

from __future__ import annotations

import json
from pathlib import Path

#: The catalogs live here, one JSON file per language.
LOCALE_DIR = Path(__file__).parent / "locale"

#: The source language needs no catalog.
SOURCE = "en"

_language = SOURCE
_catalog: dict[str, str] = {}


def available() -> list[str]:
    """Which languages are shipped - source language first."""
    others = sorted(p.stem for p in LOCALE_DIR.glob("*.json"))
    return [SOURCE] + [o for o in others if o != SOURCE]


def language() -> str:
    return _language


def set_language(lang: str) -> str:
    """Switches the language. Returns what actually applies.

    Anything unknown falls back to the source language instead of failing -
    an interface in a language we don't have should still work. A region
    suffix is dropped if only the language exists (``de-AT`` finds ``de``),
    and ``pt-BR`` counts as a language of its own.
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

    # Empty entries mean "not translated yet" - then English is better.
    _catalog = {k: v for k, v in raw.items() if isinstance(v, str) and v}
    _language = match
    return _language


def _(text: str, /, **params: object) -> str:
    """The translated sentence, with placeholders filled in."""
    out = _catalog.get(text, text)
    if not params:
        return out
    try:
        return out.format(**params)
    except (IndexError, KeyError):
        # A catalog with a wrong placeholder must not crash anything.
        return text.format(**params)


def _n(singular: str, plural: str, count: int, /, **params: object) -> str:
    """Singular or plural. ``count`` is available as ``{count}``.

    Deliberately only two forms: none of the shipped languages needs more.
    The catalog keys are the two English sentences.
    """
    return _(singular if count == 1 else plural, count=count, **params)
