"""Renewing: the app on the device is the one that gets renewed."""

from __future__ import annotations

import pytest

from modstaller import pipeline
from modstaller.state import store


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
