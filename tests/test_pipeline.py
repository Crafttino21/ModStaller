"""Renewing: the app on the device is the one that gets renewed."""

from __future__ import annotations

import pytest

from modstaller import pipeline
from modstaller.apple import session as session_mod
from modstaller.apple.devservices import Team
from modstaller.state import store


def _sign_in(adsid: str, created_at: float = 0.0) -> None:
    session_mod.Session(adsid=adsid, idms_token="i", identity_token="t",
                        created_at=created_at, app_token="x").save()


def _record(tmp_path, **kw) -> store.InstallRecord:
    ipa = tmp_path / "amethyst.ipa"
    ipa.write_bytes(b"")
    base = dict(
        bundle_id="net.kdt.pojavlauncher.PP2WVWJJYZ",
        original_bundle_id="org.angelauramc.amethyst", name="Amethyst",
        team_id="PP2WVWJJYZ", udid="U", source_ipa=str(ipa),
        app_id_id="473C88F74A", profile_path="", expires_at=0.0,
        installed_at=1000.0)
    base.update(kw)
    return store.InstallRecord(**base)


@pytest.mark.asyncio
async def test_renewal_keeps_the_bundle_id_on_the_device(tmp_path,
                                                         monkeypatch):
    """The app once got a recycled App ID. Deriving the ID from the IPA
    again gave a second app next to it - with none of its data."""
    _sign_in("a")
    rec = _record(tmp_path)
    calls = []

    async def fake_install(path, **kw):
        calls.append(kw)
        return pipeline.InstallOutcome(kw["bundle_id"], "Amethyst", "rsd",
                                       7.0, False)

    monkeypatch.setattr(store, "all_installs", lambda: [rec])
    monkeypatch.setattr(pipeline, "install", fake_install)
    [out] = await pipeline.refresh(only=rec.bundle_id, on_step=lambda m: None)

    assert calls[0]["bundle_id"] == "net.kdt.pojavlauncher.PP2WVWJJYZ"
    assert calls[0]["renewing"] is rec
    assert out.bundle_id == rec.bundle_id


async def _renewed_with(tmp_path, monkeypatch, rec) -> list:
    calls = []

    async def fake_install(path, **kw):
        calls.append(kw["account"])
        return pipeline.InstallOutcome(kw["bundle_id"], rec.name, "rsd",
                                       7.0, False)

    monkeypatch.setattr(store, "all_installs", lambda: [rec])
    monkeypatch.setattr(pipeline, "install", fake_install)
    await pipeline.refresh(only=rec.bundle_id, on_step=lambda m: None)
    return calls


@pytest.mark.asyncio
async def test_renewal_signs_with_the_account_that_installed_it(
        tmp_path, monkeypatch):
    _sign_in("a", 1)
    _sign_in("b", 2)          # "a" stays active
    rec = _record(tmp_path, adsid="b")
    assert await _renewed_with(tmp_path, monkeypatch, rec) == ["b"]


@pytest.mark.asyncio
async def test_an_old_record_is_renewed_by_the_account_owning_its_team(
        tmp_path, monkeypatch):
    _sign_in("a", 1)
    _sign_in("b", 2)
    session_mod.remember_teams(
        "b", [Team("PP2WVWJJYZ", "Sam Doe", "Individual", "active")])
    rec = _record(tmp_path)   # from before accounts were tracked
    assert await _renewed_with(tmp_path, monkeypatch, rec) == ["b"]


@pytest.mark.asyncio
async def test_a_signed_out_account_skips_its_apps(tmp_path, monkeypatch):
    _sign_in("a")
    rec = _record(tmp_path, adsid="gone")
    assert await _renewed_with(tmp_path, monkeypatch, rec) == []


def test_an_old_record_without_account_still_loads(tmp_path, monkeypatch):
    import json
    from dataclasses import asdict
    from modstaller.config import write_secret
    raw = asdict(_record(tmp_path))
    del raw["adsid"]
    monkeypatch.setattr(store, "INSTALLS_FILE", tmp_path / "apps.json")
    write_secret(tmp_path / "apps.json",
                 json.dumps({raw["bundle_id"]: raw}).encode())
    [rec] = store.all_installs()
    assert rec.adsid == ""
