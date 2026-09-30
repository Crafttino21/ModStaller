"""Keeps every test away from the real sign-ins and devices in the user's
data dir."""

from __future__ import annotations

import pytest

from modstaller import config
from modstaller.apple import session as session_mod
from modstaller.device import discovery, registry
from modstaller.store import catalog as store_catalog
from modstaller.store import images as store_images
from modstaller.store import probe as store_probe
from modstaller.store import sources as store_sources


@pytest.fixture(autouse=True)
def _private_accounts(tmp_path, monkeypatch):
    secrets = tmp_path / "secrets"
    monkeypatch.setattr(session_mod, "SESSION_FILE", secrets / "session.json")
    monkeypatch.setattr(session_mod, "ACCOUNTS_DIR", secrets / "accounts")
    monkeypatch.setattr(session_mod, "ACCOUNTS_INDEX",
                        secrets / "accounts.json")


@pytest.fixture(autouse=True)
def _private_devices(tmp_path, monkeypatch):
    """Known devices and their pair records - and no background search."""
    monkeypatch.setattr(registry, "DEVICES_FILE", tmp_path / "devices.json")
    monkeypatch.setattr(registry, "PAIRING_DIR", tmp_path / "secrets" / "pairing")
    monkeypatch.setattr(discovery, "SCANNER", None)


@pytest.fixture(autouse=True)
def _private_store(tmp_path, monkeypatch):
    """Store sources, caches and downloaded IPAs - and a fresh catalog."""
    monkeypatch.setattr(store_sources, "SOURCES_FILE", tmp_path / "sources.json")
    monkeypatch.setattr(store_sources, "CACHE", tmp_path / "store" / "sources")
    monkeypatch.setattr(store_images, "CACHE", tmp_path / "store" / "img")
    monkeypatch.setattr(config, "IPA_CACHE_DIR", tmp_path / "ipa")
    monkeypatch.setattr(store_catalog, "CATALOG", store_catalog.Catalog())
    monkeypatch.setattr(store_probe, "CACHE", tmp_path / "store" / "probe")
    # No reading of remote IPAs in tests - the ones about it switch it on.
    monkeypatch.setattr(store_catalog, "PROBE_LIMIT", -1)
