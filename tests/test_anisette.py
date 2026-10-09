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
    cfg = None

    @classmethod
    def load(cls, *files, default_device_config=None):
        cls.loads += 1
        inst = cls()
        inst.cfg = default_device_config
        return inst

    init = load

    @property
    def is_provisioned(self):
        return True

    def save_libs(self, path):
        path.write_bytes(b"libs")

    def save_provisioning(self, path):
        # Carries the device ID, so a test can tell whose identity was saved.
        path.write_bytes(f"prov:{self.cfg.unique_device_id}".encode())

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


# -- Forgetting the device ---------------------------------------------------


def test_a_forgotten_identity_does_not_come_back_from_memory(fake_library):
    """The GUI backend keeps the emulation in memory and saves it on every
    call. Deleting the files alone would be undone by the next status poll."""
    provider = anisette.LocalProvider()
    provider.headers()
    old_id = provider._cfg.unique_device_id

    anisette.forget_device()
    assert not anisette.PROVISIONING_FILE.exists()
    provider.headers()

    assert provider._cfg.unique_device_id != old_id
    assert old_id not in anisette.PROVISIONING_FILE.read_text()
    assert fake_library.loads == 2


def test_a_forget_in_another_process_is_noticed(fake_library):
    """``logout --forget-device`` in a terminal while the GUI runs: the
    files are gone, but this process still holds the old identity."""
    provider = anisette.LocalProvider()
    provider.headers()
    old_id = provider._cfg.unique_device_id

    anisette.PROVISIONING_FILE.unlink()
    anisette.DEVICE_FILE.unlink()
    provider.headers()

    assert old_id not in anisette.PROVISIONING_FILE.read_text()
    assert provider._cfg.unique_device_id != old_id


def test_logout_forgets_the_device_even_when_nobody_is_signed_in(fake_library):
    """Exactly the state after a failed sign-in - and exactly when the error
    messages recommend ``logout --forget-device``."""
    import argparse

    from modstaller import cli
    anisette.LocalProvider().headers()

    args = argparse.Namespace(all=False, account=None, forget_device=True)
    assert cli._logout(args) == 0
    assert not anisette.PROVISIONING_FILE.exists()
    assert not anisette.DEVICE_FILE.exists()


def test_logout_without_forget_still_says_not_signed_in(fake_library):
    import argparse

    from modstaller import cli
    args = argparse.Namespace(all=False, account=None, forget_device=False)
    assert cli._logout(args) == 3


# -- Header hygiene ----------------------------------------------------------

from datetime import datetime, timedelta, timezone  # noqa: E402

#: 2026-10-09 23:39:28 in Central European Summer Time.
NOW = datetime(2026, 10, 9, 23, 39, 28, tzinfo=timezone(timedelta(hours=2)))


def test_windows_values_become_what_apple_clients_send():
    """What the library produced on a German Windows."""
    out = anisette.normalize_headers({
        "X-Apple-I-Client-Time": "2026-10-09T23:39:28+02:00Z",
        "X-Apple-I-TimeZone": "Mitteleuropäische Sommerzeit",
        "X-Apple-Locale": "German_Germany",
        "X-Apple-I-MD": "otp",
    }, now=NOW)
    assert out == {
        "X-Apple-I-Client-Time": "2026-10-09T21:39:28Z",
        "X-Apple-I-TimeZone": "GMT+2",
        "X-Apple-Locale": "en_US",
        "X-Apple-I-MD": "otp",
    }


def test_correct_values_pass_through_untouched():
    data = {"X-Apple-I-Client-Time": "2026-10-09T21:39:28Z",
            "X-Apple-I-TimeZone": "CEST", "X-Apple-Locale": "de_DE"}
    assert anisette.normalize_headers(data, now=NOW) == data


def test_a_non_latin_time_zone_never_reaches_the_wire():
    """http.client encodes headers as latin-1 - this would not even go out."""
    out = anisette.normalize_headers(
        {"X-Apple-I-TimeZone": "中国标准时间", "X-Odd": "naïve"}, now=NOW)
    assert out == {"X-Apple-I-TimeZone": "GMT+2"}


@pytest.mark.parametrize("minutes, expected", [
    (0, "GMT"), (120, "GMT+2"), (330, "GMT+5:30"), (-210, "GMT-3:30"),
])
def test_offsets_are_written_like_nstimezone(minutes, expected):
    assert anisette._gmt_abbreviation(timedelta(minutes=minutes)) == expected


def test_the_local_provider_hands_out_normalized_headers(fake_library,
                                                          monkeypatch):
    monkeypatch.setattr(FakeAnisette, "get_data", lambda self: {
        "X-Apple-I-TimeZone": "Mitteleuropäische Sommerzeit",
        "X-Apple-I-Client-Time": "2026-10-09T23:39:28+02:00Z",
    })
    headers = anisette.LocalProvider().headers()
    assert all(v.isascii() for v in headers.values())
    assert headers["X-Apple-I-Client-Time"] == "2026-10-09T21:39:28Z"
