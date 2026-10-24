"""The "What's new" popup after an update (gui/src/lib/whatsnew.json).

Every release brings an entry - packaging/check-version.py refuses one
without - and every text in it is translated like the rest of the interface.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WHATS_NEW = ROOT / "gui" / "src" / "lib" / "whatsnew.json"
LOCALES = sorted((ROOT / "gui" / "src" / "lib" / "locale").glob("*.ts"))

_spec = importlib.util.spec_from_file_location(
    "check_version", ROOT / "packaging" / "check-version.py")
check_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_version)

ENTRIES = json.loads(WHATS_NEW.read_text(encoding="utf-8"))


def _texts() -> list[str]:
    out = []
    for e in ENTRIES:
        out += ([e["highlight"]] if e.get("highlight") else []) + e["items"]
    return out


def test_entries_are_one_per_plain_version():
    versions = [e["version"] for e in ENTRIES]
    assert all(re.fullmatch(r"\d+\.\d+\.\d+", v) for v in versions), versions
    assert len(set(versions)) == len(versions)
    assert all(e["items"] for e in ENTRIES)


def test_the_current_version_has_an_entry():
    """Else its update would bring no popup - release.sh stops at that too."""
    version = json.loads((ROOT / "gui" / "package.json").read_text())["version"]
    assert check_version.missing_whats_new(version) == []


@pytest.mark.parametrize("catalog", LOCALES, ids=lambda p: p.stem)
def test_every_text_is_translated(catalog):
    text = catalog.read_text(encoding="utf-8")
    missing = [s for s in _texts()
               if "  " + json.dumps(s, ensure_ascii=False) + ":" not in text]
    assert missing == []


def test_a_release_without_an_entry_is_refused(tmp_path):
    path = tmp_path / "whatsnew.json"
    path.write_text(json.dumps([{"version": "2.0.0", "items": ["x"]}]))
    assert check_version.missing_whats_new("2.0.0", path) == []
    assert check_version.missing_whats_new("2.0.0-rc.3", path) == [], \
        "a pre-release shares the entry of its version"
    assert check_version.missing_whats_new("2.0.1", path)
    path.write_text(json.dumps([{"version": "2.0.1", "items": []}]))
    assert check_version.missing_whats_new("2.0.1", path), "an empty entry is none"
    assert check_version.missing_whats_new("2.0.1", tmp_path / "gone.json")
