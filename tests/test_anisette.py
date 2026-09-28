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


# -- One emulation at a time -------------------------------------------------


class UcError(Exception):
    """Named like Unicorn's - that is what the provider looks for."""


class FakeAnisette:
    """Stands in for the anisette library: counts how many threads are inside
    the "emulation" at once, and can break once like Unicorn does."""

    loads = 0
    inside = 0
    most_inside = 0
    break_next = False

    @classmethod
    def load(cls, *files, default_device_config=None):
        cls.loads += 1
        return cls()

    init = load

    @property
    def is_provisioned(self):
        return True

    def save_libs(self, path):
        path.write_bytes(b"libs")

    def save_provisioning(self, path):
        path.write_bytes(b"prov")

    def get_data(self):
        import time
        cls = type(self)
        cls.inside += 1
        cls.most_inside = max(cls.most_inside, cls.inside)
        try:
            time.sleep(0.02)
            if cls.break_next:
                cls.break_next = False
                raise UcError("Invalid memory read (UC_ERR_READ_UNMAPPED)")
            return {"X-Apple-I-MD": "otp"}
        finally:
            cls.inside -= 1


@pytest.fixture
def fake_library(monkeypatch, tmp_path):
    import sys
    import types

    lib = types.ModuleType("anisette")
    lib.Anisette = FakeAnisette
    device = types.ModuleType("anisette._device")
    device.AnisetteDeviceConfig = lambda **kw: types.SimpleNamespace(**kw)
    monkeypatch.setitem(sys.modules, "anisette", lib)
    monkeypatch.setitem(sys.modules, "anisette._device", device)
    for name in ("ANISETTE_DIR", "PROVISIONING_FILE", "LIBS_FILE", "DEVICE_FILE"):
        target = tmp_path if name == "ANISETTE_DIR" else tmp_path / name.lower()
        monkeypatch.setattr(anisette, name, target)
    monkeypatch.setattr(anisette, "control_flow_guard_active", lambda: False)
    monkeypatch.setattr(anisette, "_shared_ani", None)
    FakeAnisette.loads = FakeAnisette.inside = FakeAnisette.most_inside = 0
    FakeAnisette.break_next = False
    return FakeAnisette


def test_threads_never_run_the_emulation_at_the_same_time(fake_library):
    import threading

    errors = []

    def work():
        try:
            anisette.LocalProvider().headers()
        except Exception as exc:   # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert fake_library.most_inside == 1
    assert fake_library.loads == 1, "one instance per process, not one per call"


def test_a_broken_emulation_is_reloaded_and_retried_once(fake_library):
    provider = anisette.LocalProvider()
    fake_library.break_next = True
    assert provider.headers()["X-Apple-I-MD"] == "otp"
    assert fake_library.loads == 2


def test_other_errors_are_not_swallowed(fake_library, monkeypatch):
    provider = anisette.LocalProvider()

    def boom(self):
        raise RuntimeError("network")
    monkeypatch.setattr(FakeAnisette, "get_data", boom)
    with pytest.raises(RuntimeError, match="network"):
        provider.headers()
