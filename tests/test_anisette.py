"""The Anisette source: emulated locally or fetched from a server.

The focus is on the one condition under which the local emulation must not
run: active Control Flow Guard. Unicorn then uses ``longjmp`` to jump out of
JIT-generated code, and Windows kills the process via ``__fastfail`` - no
Python error, nothing to catch. So the check has to apply *before* the
import, and provably so.
"""

from __future__ import annotations

import pytest

from modstaller.apple import anisette
from modstaller.errors import AppleError


@pytest.fixture
def guarded(monkeypatch):
    """A process with Control Flow Guard active."""
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
    # The message must name the way out, not just the problem.
    assert 'anisette_provider = "remote"' in str(exc.value)


def test_the_escape_hatch_opens_it_again(guarded, monkeypatch):
    monkeypatch.setenv(anisette.ALLOW_LOCAL_ENV, "1")
    assert anisette.local_supported()


def test_posix_never_asks_windows_about_mitigations(monkeypatch):
    monkeypatch.setattr(anisette, "POSIX", True)
    assert anisette.control_flow_guard_active() is False


def test_the_real_probe_answers_for_this_process():
    """Whatever the system: an answer, not an error."""
    assert isinstance(anisette.control_flow_guard_active(), bool)


def test_build_picks_the_configured_provider(guarded):
    remote = anisette.build("remote", "https://example.invalid")
    assert remote.name == "remote"
    # 'local' does not silently fall back to 'remote': whoever chose local
    # doesn't want to send data anywhere - better a loud no.
    with pytest.raises(AppleError):
        anisette.build("local")


def test_remote_without_a_server_is_refused():
    with pytest.raises(AppleError, match="anisette_server"):
        anisette.build("remote", "")
