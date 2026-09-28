"""Origin of installed apps and usage of App IDs.

Both are pure functions over data coming from the iPhone or from Apple -
the examples here were read off a real device (iOS 27).
"""

from __future__ import annotations

from modstaller.apple.devservices import AppID
from modstaller.device.install import app_origin
from modstaller.provisioning import app_id_in_use, spare_app_id


def meta(signer: str, *, task_allow: bool = False, team: str = "") -> dict:
    ent: dict = {}
    if task_allow:
        ent["get-task-allow"] = True
    if team:
        ent["com.apple.developer.team-identifier"] = team
    return {"SignerIdentity": signer, "Entitlements": ent}


def test_an_app_from_the_store_is_not_a_sideload():
    o = app_origin(meta("Apple iPhone OS Application Signing", team="Q6L2SF6YDW"))
    assert o["origin"] == "store"
    assert not o["sideloaded"] and not o["developerSigned"]


def test_testflight_is_not_a_sideload_either():
    """Without this case every beta app would count as sideloaded."""
    o = app_origin(meta("TestFlight Beta Distribution", team="BUMSKVQ3D9"))
    assert o["origin"] == "testflight"
    assert not o["sideloaded"]


def test_a_developer_signed_app_is_a_sideload():
    o = app_origin(meta("iPhone Developer: wer@example.com (KAJDACPP3P)",
                        task_allow=True, team="PP2WVWJJYZ"))
    assert o["origin"] == "developer"
    assert o["sideloaded"] and o["developerSigned"]
    # The team ID is in the entitlements, not in the identity's name.
    assert o["teamId"] == "PP2WVWJJYZ"


def test_anything_else_counts_as_a_sideload_but_not_as_developer():
    """Enterprise-signed IPAs: sideloaded, but no JIT and no 7-day expiry."""
    o = app_origin(meta("Some Company Inc.", team="ABCDE12345"))
    assert o["origin"] == "other"
    assert o["sideloaded"] and not o["developerSigned"]


def test_an_app_without_signature_fields_does_not_crash():
    o = app_origin({})
    assert o["origin"] == "other" and o["teamId"] == ""


def test_an_app_id_of_an_installed_app_is_in_use():
    assert app_id_in_use("com.x.app", {"com.x.app"})


def test_the_app_id_of_an_extension_counts_as_used():
    """An extension's App ID carries the app's as a prefix."""
    assert app_id_in_use("com.x.app.share", {"com.x.app"})


def test_an_unrelated_app_id_is_free():
    assert not app_id_in_use("com.y.other", {"com.x.app"})
    # Not a plain prefix check: "com.x.apple" does not hang off "com.x.app".
    assert not app_id_in_use("com.x.applesauce", {"com.x.app"})


def test_the_spare_is_the_first_one_nobody_needs():
    existing = [AppID("1", "com.x.app", "App"),
                AppID("2", "com.x.app.share", "Share"),
                AppID("3", "com.y.alt", "Alt")]
    spare = spare_app_id(existing, {"com.x.app"})
    assert spare is not None and spare.identifier == "com.y.alt"


def test_without_a_spare_the_answer_is_none():
    existing = [AppID("1", "com.x.app", "App")]
    assert spare_app_id(existing, {"com.x.app"}) is None
