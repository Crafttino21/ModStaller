"""The IPA editor's plan: which App IDs an install costs, against the quota."""

from __future__ import annotations

import plistlib
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modstaller import plan as plan_mod
from modstaller import quota
from modstaller.apple.devservices import AppID, AppIdQuota
from modstaller.errors import SigningError
from modstaller.plan import QuotaExhausted, make_plan, resolve_keep
from modstaller.signing.ipa import inspect

TEAM = "PP2WVWJJYZ"


def make_ipa(tmp_path: Path, *, extensions=("Share", "Widget"), foreign=(),
             watch=False) -> Path:
    """A minimal IPA: an app with extensions whose IDs carry the app's."""
    ipa = tmp_path / "app.ipa"
    app = "Payload/Demo.app/"
    with zipfile.ZipFile(ipa, "w") as zf:
        zf.writestr(app + "Info.plist", plistlib.dumps({
            "CFBundleIdentifier": "com.example.demo",
            "CFBundleDisplayName": "Demo", "CFBundleShortVersionString": "1.0"}))
        zf.writestr(app + "Demo", b"\xcf\xfa\xed\xfe")
        for name in extensions:
            zf.writestr(f"{app}PlugIns/{name}.appex/Info.plist", plistlib.dumps({
                "CFBundleIdentifier": f"com.example.demo.{name.lower()}",
                "CFBundleDisplayName": name,
                "NSExtension": {"NSExtensionPointIdentifier": "com.apple.share-services"}}))
        for name in foreign:
            zf.writestr(f"{app}PlugIns/{name}.appex/Info.plist", plistlib.dumps({
                "CFBundleIdentifier": f"org.other.{name.lower()}"}))
        if watch:
            zf.writestr(app + "Watch/W.app/Info.plist", plistlib.dumps({}))
    return ipa


def app_id(identifier: str, days_old: float | None = None) -> AppID:
    expires = (datetime.now(timezone.utc) + timedelta(days=7 - days_old)
               if days_old is not None else None)
    return AppID(app_id_id=identifier[-6:], identifier=identifier, name="x",
                 expires_at=expires)


def test_the_ipa_tells_its_extensions_and_watch_app(tmp_path):
    info = inspect(make_ipa(tmp_path, foreign=("Odd",), watch=True))
    assert [e.name for e in info.extension_details] == ["Odd", "Share", "Widget"]
    assert info.extension_details[1].point == "com.apple.share-services"
    assert info.has_watch
    # zsign's rule: the app's old ID is replaced inside the extension's.
    share = info.extension_details[1]
    assert share.bundle_id_for("com.example.demo", "com.example.demo.T") == \
        "com.example.demo.T.share"
    # Without the app's ID as prefix it cannot move to our team.
    assert info.extension_details[0].bundle_id_for("com.example.demo", "x.y") is None


def test_by_default_free_accounts_keep_no_extensions(tmp_path):
    info = inspect(make_ipa(tmp_path))
    assert resolve_keep(info, None, is_free=True) == []
    assert resolve_keep(info, None, is_free=False) == [
        "PlugIns/Share.appex", "PlugIns/Widget.appex"]
    assert resolve_keep(info, ["PlugIns/Widget.appex"], is_free=True) == [
        "PlugIns/Widget.appex"]


def test_an_extension_that_cannot_move_cannot_be_kept(tmp_path):
    info = inspect(make_ipa(tmp_path, foreign=("Odd",)))
    with pytest.raises(SigningError, match="Odd"):
        resolve_keep(info, ["PlugIns/Odd.appex"], is_free=False)


def test_the_plan_counts_only_new_app_ids(tmp_path):
    info = inspect(make_ipa(tmp_path))
    existing = [app_id(f"com.example.demo.{TEAM}", 1)]
    p = make_plan(info, team_id=TEAM, is_free=True, app_ids=existing,
                  quota=AppIdQuota(10, 5),
                  keep=["PlugIns/Share.appex", "PlugIns/Widget.appex"])
    assert p.main_id == f"com.example.demo.{TEAM}"
    assert p.new_app_ids == [f"com.example.demo.{TEAM}.share",
                             f"com.example.demo.{TEAM}.widget"]


def test_a_custom_bundle_id_is_checked_and_moves_the_extensions(tmp_path):
    info = inspect(make_ipa(tmp_path))
    p = make_plan(info, team_id=TEAM, is_free=False, app_ids=[],
                  quota=AppIdQuota(None, None), keep=["PlugIns/Share.appex"],
                  bundle_id="ios.youtube.mine")
    assert p.identifiers == ["ios.youtube.mine", "ios.youtube.mine.share"]
    with pytest.raises(SigningError, match="not a valid bundle ID"):
        make_plan(info, team_id=TEAM, is_free=False, app_ids=[],
                  quota=AppIdQuota(None, None), keep=[], bundle_id="no spaces allowed")


def test_not_enough_quota_is_refused_before_anything_is_created(tmp_path):
    info = inspect(make_ipa(tmp_path))
    with pytest.raises(QuotaExhausted, match="needs 3 new App ID"):
        make_plan(info, team_id=TEAM, is_free=True, app_ids=[],
                  quota=AppIdQuota(10, 1), bundle_id="com.mine.demo",
                  keep=["PlugIns/Share.appex", "PlugIns/Widget.appex"])


def test_without_quota_the_app_moves_to_an_unused_app_id(tmp_path):
    info = inspect(make_ipa(tmp_path))
    spare = app_id("com.old.thing", 3)
    busy = app_id("com.busy.app", 2)
    p = make_plan(info, team_id=TEAM, is_free=True, app_ids=[busy, spare],
                  quota=AppIdQuota(10, 0), keep=[],
                  protected={"com.busy.app"})
    assert p.main_id == "com.old.thing" and p.spare == "com.old.thing"
    assert p.new_app_ids == [] and p.notes


def test_a_spare_can_be_chosen_explicitly(tmp_path):
    info = inspect(make_ipa(tmp_path))
    p = make_plan(info, team_id=TEAM, is_free=True,
                  app_ids=[app_id("com.old.thing", 3)], quota=AppIdQuota(10, 1),
                  keep=["PlugIns/Share.appex"], spare="com.old.thing")
    assert p.identifiers == ["com.old.thing", "com.old.thing.share"]
    assert p.new_app_ids == ["com.old.thing.share"]


def test_paid_accounts_are_not_limited(tmp_path):
    info = inspect(make_ipa(tmp_path))
    p = make_plan(info, team_id=TEAM, is_free=False, app_ids=[],
                  quota=AppIdQuota(None, 0),
                  keep=["PlugIns/Share.appex", "PlugIns/Widget.appex"])
    assert len(p.new_app_ids) == 3


# -- The quota itself --------------------------------------------------------


def test_apples_count_wins_and_the_next_free_slot_is_estimated():
    now = time.time()
    ids = [app_id("a.b", 2), app_id("c.d", 5)]
    # One more was created 6 days ago and deleted since - only our log knows.
    logged = [now - 6 * 86400]
    q = quota.team_quota(True, ids, AppIdQuota(10, 0), logged, now=now)
    assert q.available == 0
    assert q.next_free_at == pytest.approx(logged[0] + quota.WINDOW, abs=1)
    assert len(q.returns_at) == 3


def test_a_logged_creation_of_an_existing_app_id_counts_once():
    now = time.time()
    ids = [app_id("a.b", 2)]
    created = ids[0].expires_at.timestamp() - quota.WINDOW
    assert len(quota.creation_times(ids, [created + 5], now=now)) == 1


def test_without_apples_count_it_is_derived():
    q = quota.team_quota(True, [app_id("a.b", 1)], AppIdQuota(None, None), [])
    assert q.maximum == 10 and q.available == 9 and q.next_free_at is None


def test_paid_quota_has_no_limit():
    q = quota.team_quota(False, [], AppIdQuota(None, None), [])
    assert not q.is_free and q.available is None


def test_the_creation_log_keeps_a_week(tmp_path, monkeypatch):
    from modstaller.state import appid_log
    monkeypatch.setattr(appid_log, "LOG_FILE", tmp_path / "log.json")
    now = time.time()
    appid_log.created(TEAM, "a.b", when=now - 9 * 86400)
    appid_log.created(TEAM, "c.d", when=now - 86400)
    assert appid_log.times(TEAM, now=now) == [now - 86400]


def test_the_bundle_id_pattern():
    assert plan_mod.check_bundle_id(" ios.youtube.com ") == "ios.youtube.com"
    for bad in ("youtube", "a..b", "a.b c", "ä.b", ".a.b"):
        with pytest.raises(SigningError):
            plan_mod.check_bundle_id(bad)


@pytest.mark.parametrize("team, free", [
    # measured on a free account: xcodeFreeOnly is False there
    ({"xcodeFreeOnly": False, "memberships": [{"name": "Xcode Free Provisioning Program"}]}, True),
    ({"memberships": [{"name": "Apple Developer Program"}]}, False),
    ({"memberships": [{"name": "Xcode Free Provisioning Program"},
                      {"name": "Apple Developer Program"}]}, False),
    ({"xcodeFreeOnly": True}, True),
    ({"xcodeFreeOnly": False}, None),
    ({}, None),
])
def test_free_accounts_are_recognised_by_their_membership(team, free):
    from modstaller.apple.devservices import _free_only
    assert _free_only(team) is free
