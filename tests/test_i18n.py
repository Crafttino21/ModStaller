"""Translation: the source language is English, catalogs are only stand-ins.

The catalogs themselves are not checked for wording here - but they are
checked for fitting together technically: same placeholders, no entry
without a counterpart in the source. A catalog with a wrong ``{name}``
would otherwise only be noticed by the user.
"""

from __future__ import annotations

import json
import re

import pytest

from modstaller import i18n

#: Placeholders like {name} or {days:.1f} - the part after the colon doesn't count.
PLACEHOLDER = re.compile(r"\{(\w+)[^}]*\}")


@pytest.fixture(autouse=True)
def source_language():
    """Every test starts in English and leaves it that way."""
    i18n.set_language(i18n.SOURCE)
    yield
    i18n.set_language(i18n.SOURCE)


def catalog(lang: str) -> dict:
    return json.loads((i18n.LOCALE_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def test_english_is_the_source_and_needs_no_catalog():
    assert i18n.available()[0] == "en"
    assert not (i18n.LOCALE_DIR / "en.json").exists()


def test_without_a_catalog_the_text_passes_through():
    assert i18n._("Developer Mode is on.") == "Developer Mode is on."


def test_a_known_language_translates():
    assert i18n.set_language("de") == "de"
    assert i18n._("Developer Mode is on.") == "Entwicklermodus ist an."


def test_a_region_falls_back_to_its_language():
    """de-AT doesn't exist - German does."""
    assert i18n.set_language("de-AT") == "de"
    assert i18n.set_language("de_CH") == "de"


def test_an_unknown_language_falls_back_to_english():
    assert i18n.set_language("kli") == "en"
    assert i18n._("Developer Mode is on.") == "Developer Mode is on."


def test_an_untranslated_text_stays_english():
    i18n.set_language("de")
    assert i18n._("Something nobody translated") == "Something nobody translated"


def test_placeholders_are_filled():
    i18n.set_language("de")
    assert i18n._("Unknown fix: {fix}", fix="x") == "Unbekannte Korrektur: x"


def test_a_broken_catalog_entry_does_not_break_the_message(monkeypatch):
    """Better the English sentence than an exception in the middle of an error path."""
    monkeypatch.setitem(i18n._catalog, "Unknown fix: {fix}", "Kaputt: {nope}")
    assert i18n._("Unknown fix: {fix}", fix="x") == "Unknown fix: x"


def test_singular_and_plural_pick_different_texts():
    assert i18n._n("{count} app", "{count} apps", 1) == "1 app"
    assert i18n._n("{count} app", "{count} apps", 3) == "3 apps"


@pytest.mark.parametrize("lang", [p.stem for p in i18n.LOCALE_DIR.glob("*.json")])
def test_every_catalog_keeps_the_placeholders_of_its_source(lang):
    for source, translated in catalog(lang).items():
        if not translated:
            continue
        assert PLACEHOLDER.findall(source) == PLACEHOLDER.findall(translated) or \
            set(PLACEHOLDER.findall(source)) == set(PLACEHOLDER.findall(translated)), \
            f"{lang}: placeholders do not match {source!r}"


@pytest.mark.parametrize("lang", [p.stem for p in i18n.LOCALE_DIR.glob("*.json")])
def test_no_catalog_entry_is_an_orphan(lang):
    """An entry no source code uses any more is silent dead weight."""
    import ast
    import pathlib

    used: set[str] = set()
    root = pathlib.Path(i18n.__file__).parent
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name not in ("_", "_n"):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    used.add(arg.value)

    # Whatever goes through a table (REMEDIES, _MESSAGES, _HINTS) is a
    # constant elsewhere - so also collect all string constants.
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                used.add(node.value)

    orphans = [k for k in catalog(lang) if k not in used]
    assert not orphans, f"{lang}: no longer used: {orphans[:3]}"
