"""Die Anisette-Quelle: lokal emuliert oder von einem Server geholt.

Der Schwerpunkt liegt auf der einen Bedingung, unter der die lokale Emulation
nicht laufen darf: aktives Control Flow Guard. Unicorn springt dann mit
``longjmp`` aus JIT-erzeugtem Code, und Windows beendet den Prozess per
``__fastfail`` - kein Python-Fehler, nichts zum Abfangen. Die Sperre muss also
*vor* dem Import greifen, und zwar nachweislich.
"""

from __future__ import annotations

import pytest

from modstaller.apple import anisette
from modstaller.errors import AppleError


@pytest.fixture
def guarded(monkeypatch):
    """Ein Prozess mit aktivem Control Flow Guard."""
    monkeypatch.setattr(anisette, "control_flow_guard_active", lambda: True)
    monkeypatch.delenv(anisette.ALLOW_LOCAL_ENV, raising=False)


def test_local_emulation_runs_without_control_flow_guard(monkeypatch):
    monkeypatch.setattr(anisette, "control_flow_guard_active", lambda: False)
    assert anisette.local_supported()


def test_local_emulation_is_refused_under_control_flow_guard(guarded):
    assert not anisette.local_supported()


def test_a_guarded_process_gets_a_readable_error_not_a_native_crash(guarded):
    with pytest.raises(AppleError) as exc:
        anisette.LocalProvider()
    # Die Meldung muss den Ausweg nennen, nicht nur das Problem.
    assert 'anisette_provider = "remote"' in str(exc.value)


def test_the_escape_hatch_opens_it_again(guarded, monkeypatch):
    monkeypatch.setenv(anisette.ALLOW_LOCAL_ENV, "1")
    assert anisette.local_supported()


def test_posix_never_asks_windows_about_mitigations(monkeypatch):
    monkeypatch.setattr(anisette, "POSIX", True)
    assert anisette.control_flow_guard_active() is False


def test_the_real_probe_answers_for_this_process():
    """Egal welches System: eine Antwort, kein Fehler."""
    assert isinstance(anisette.control_flow_guard_active(), bool)


def test_build_picks_the_configured_provider(guarded):
    remote = anisette.build("remote", "https://example.invalid")
    assert remote.name == "remote"
    # 'local' faellt nicht still auf 'remote' zurueck: wer lokal gewaehlt hat,
    # will keine Daten verschicken - dann lieber ein lautes Nein.
    with pytest.raises(AppleError):
        anisette.build("local")


def test_remote_without_a_server_is_refused():
    with pytest.raises(AppleError, match="anisette_server"):
        anisette.build("remote", "")
