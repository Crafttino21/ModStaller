"""Wo ModStaller seine Daten ablegt - und dass Secrets geschuetzt bleiben."""

from __future__ import annotations

from pathlib import Path

import pytest

from modstaller import config
from modstaller.errors import ConfigError


def test_linux_follows_xdg():
    cfg, data, cache, state = config.base_dirs(
        {"XDG_DATA_HOME": "/x/data"}, posix=True, home=Path("/home/u"))
    assert cfg == Path("/home/u/.config/modstaller")
    assert data == Path("/x/data/modstaller")
    assert cache == Path("/home/u/.cache/modstaller")
    assert state == Path("/home/u/.local/state/modstaller")


def test_windows_keeps_everything_in_localappdata():
    """Nicht in %APPDATA%: dort liegt der Ordner der Oberflaeche (Electron)."""
    local = Path("C:/Users/u/AppData/Local")
    cfg, data, cache, state = config.base_dirs(
        {"LOCALAPPDATA": str(local), "APPDATA": "C:/Users/u/AppData/Roaming"},
        posix=False)
    assert cfg == local / "modstaller"
    assert {data.parent, cache.parent, state.parent} == {cfg}


def test_windows_without_localappdata_falls_back_to_the_profile():
    cfg, *_ = config.base_dirs({}, posix=False, home=Path("C:/Users/u"))
    assert cfg == Path("C:/Users/u/AppData/Local/modstaller")


def test_anisette_stays_local_by_default(monkeypatch):
    """Auf jeder Plattform: Geraete-Identifier bleiben auf dem Rechner."""
    for posix in (True, False):
        monkeypatch.setattr(config, "POSIX", posix)
        assert config.Settings().anisette_provider == "local"


def test_the_config_file_can_switch_to_a_server(tmp_path):
    f = tmp_path / "config.toml"
    f.write_text('anisette_provider = "remote"\n')
    assert config.Settings.load(f).anisette_provider == "remote"


@pytest.mark.skipif(not config.POSIX, reason="Unix-Rechte gibt es nur auf POSIX")
def test_open_secret_is_refused_on_posix(tmp_path):
    f = tmp_path / "secret"
    f.write_bytes(b"x")
    f.chmod(0o644)
    with pytest.raises(ConfigError):
        config.read_secret(f)


def test_permission_check_is_skipped_on_windows(tmp_path, monkeypatch):
    """Unter Windows ist st_mode immer "offen" - das darf kein Secret sperren."""
    f = tmp_path / "secret"
    f.write_bytes(b"x")
    f.chmod(0o644)
    monkeypatch.setattr(config, "POSIX", False)
    assert config.read_secret(f) == b"x"


def test_zsign_next_to_the_frozen_exe_is_found(tmp_path, monkeypatch):
    """CLI-Zip unter Windows: zsign.exe liegt neben modstaller.exe, nicht im PATH."""
    import sys
    name = "zsign" if config.POSIX else "zsign.exe"
    (tmp_path / name).write_bytes(b"")
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "modstaller"))
    assert config.find_zsign("zsign") == str(tmp_path / name)


def test_zsign_missing_is_none(monkeypatch):
    monkeypatch.setenv("PATH", "")
    assert config.find_zsign("zsign") is None
