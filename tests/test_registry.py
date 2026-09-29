"""Devices ModStaller knows - the memory for devices that are not on the cable."""

from __future__ import annotations

import os
import stat

from modstaller.device import registry


def test_remember_creates_and_updates_without_losing_what_was_known():
    registry.remember("U1", name="iPhone of S", product_type="iPhone17,2",
                      wifi_mac="AA:BB:CC:DD:EE:FF")
    # Over the network less may be known - empty values keep the old ones.
    registry.remember("U1", name="", os_version="27.0")
    dev = registry.get("U1")
    assert dev.name == "iPhone of S"
    assert dev.os_version == "27.0"
    assert dev.wifi_mac == "aa:bb:cc:dd:ee:ff"
    assert registry.by_wifi_mac("AA:BB:CC:DD:EE:FF").udid == "U1"


def test_platform_comes_from_the_model():
    assert registry.platform_for("AppleTV14,1") == registry.TVOS
    assert registry.platform_for("", "AppleTV") == registry.TVOS
    assert registry.platform_for("iPhone17,2") == registry.IOS
    assert registry.platform_for("RealityDevice14,1") == registry.XROS
    assert registry.platform_for("", "RealityDevice") == registry.XROS
    # iPad and iPod touch are iOS devices as far as signing goes.
    assert registry.platform_for("iPad16,3") == registry.IOS
    assert registry.platform_for("iPod9,1") == registry.IOS


def test_pair_records_are_private_and_only_offered_with_wifi_on():
    registry.remember("U1", name="A")
    registry.save_pair_record("U1", {"HostID": "H", "DeviceCertificate": b"x"})
    assert registry.load_pair_record("U1")["HostID"] == "H"
    if os.name != "nt":
        mode = registry.pair_record_path("U1").stat().st_mode
        assert not mode & (stat.S_IRWXG | stat.S_IRWXO)
    assert registry.all_pair_records() == {}
    registry.remember("U1", wifi_enabled=True)
    assert set(registry.all_pair_records()) == {"U1"}


def test_forget_removes_the_pair_record_too():
    registry.remember("U1", name="A")
    registry.save_pair_record("U1", {"HostID": "H"})
    assert registry.forget("U1")
    assert registry.get("U1") is None
    assert not registry.pair_record_path("U1").exists()


def test_a_udid_cannot_escape_the_pairing_folder():
    assert registry.pair_record_path("../../etc/passwd").parent == registry.PAIRING_DIR


def test_remote_identifier_lookup():
    registry.remember("TV1", name="Living room", platform=registry.TVOS,
                      remote_identifier="ABC-123")
    assert registry.by_remote_identifier("ABC-123").is_tv


def test_clear_empties_on_purpose():
    registry.remember("U1", remote_identifier="U1", last_host="10.0.0.2", wifi_enabled=True)
    registry.remember("U1", wifi_enabled=False, clear=("remote_identifier", "last_host"))
    dev = registry.get("U1")
    assert (dev.remote_identifier, dev.last_host, dev.wifi_enabled) == ("", "", False)
