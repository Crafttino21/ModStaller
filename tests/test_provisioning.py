"""Quota logic.

Apple allows ten *newly created* App IDs per week. Deleting existing ones
gives no quota back - whoever does it anyway takes away a foreign app's
ability to ever be renewed. So we fall back rather than delete, and
whatever is on the device stays off-limits.
"""

from __future__ import annotations

import pytest

from modstaller.apple.devservices import AppID, Team
from modstaller.provisioning import Capabilities, derive_bundle_id, spare_app_id


def _app_id(identifier: str) -> AppID:
    return AppID(app_id_id=identifier.upper(), identifier=identifier,
                 name=identifier)


INSTALLED = {
    "com.SideStore.SideStore.PP2WVWJJYZ",
    "com.google.ios.youtube.PP2WVWJJYZ",
}


def test_installed_app_id_is_never_offered():
    existing = [_app_id("com.SideStore.SideStore.PP2WVWJJYZ")]
    assert spare_app_id(existing, INSTALLED) is None


def test_extension_of_installed_app_is_protected():
    """The extension carries the app's App ID as a prefix - without it the
    app can no longer be signed completely."""
    existing = [_app_id("com.google.ios.youtube.PP2WVWJJYZ.OpenYouTube.Extension")]
    assert spare_app_id(existing, INSTALLED) is None


def test_unused_app_id_is_offered():
    existing = [
        _app_id("com.SideStore.SideStore.PP2WVWJJYZ"),
        _app_id("net.kdt.pojavlauncher.PP2WVWJJYZ"),
    ]
    spare = spare_app_id(existing, INSTALLED)
    assert spare is not None
    assert spare.identifier == "net.kdt.pojavlauncher.PP2WVWJJYZ"


def test_similar_prefix_is_not_confused_with_a_child():
    """'…youtubeXY' does start with '…youtube', but does not belong to it."""
    existing = [_app_id("com.google.ios.youtube.PP2WVWJJYZextra")]
    assert spare_app_id(existing, INSTALLED) is not None


def test_no_candidates_yields_none():
    assert spare_app_id([], INSTALLED) is None


def test_case_differences_still_protect():
    existing = [_app_id("COM.SIDESTORE.SIDESTORE.PP2WVWJJYZ")]
    assert spare_app_id(existing, INSTALLED) is None


# -- Bundle ID and account type -------------------------------------------


def test_bundle_id_keeps_team_id_spelling():
    """Upper/lower case decides whether an existing App ID is matched -
    and with that, whether quota is used up."""
    assert (derive_bundle_id("com.google.ios.youtube", "PP2WVWJJYZ")
            == "com.google.ios.youtube.PP2WVWJJYZ")


@pytest.mark.parametrize("team_type", ["Individual", "Free", "individual"])
def test_individual_accounts_are_assumed_free(team_type):
    """Apple reports free and paid individual accounts alike as 'Individual'.
    Erring towards 'free' costs an extension, the other way round the whole
    weekly quota."""
    caps = Capabilities.for_team(Team("T", "n", team_type, "active"))
    assert caps.is_free


@pytest.mark.parametrize("team_type", ["Company/Organization", "Organization"])
def test_organisations_are_treated_as_paid(team_type):
    assert not Capabilities.for_team(Team("T", "n", team_type, "active")).is_free


def test_capabilities_correct_themselves_from_the_real_profile():
    from modstaller.apple.devservices import Profile
    from datetime import datetime, timedelta, timezone

    paid = Capabilities.for_team(Team("T", "n", "Individual", "active")).reconcile(
        Profile(content=b"", expires_at=datetime.now(timezone.utc)
                + timedelta(days=365)))
    assert not paid.is_free
    assert paid.max_app_ids_per_week is None

    free = Capabilities.for_team(Team("T", "n", "Company", "active")).reconcile(
        Profile(content=b"", expires_at=datetime.now(timezone.utc)
                + timedelta(days=7)))
    assert free.is_free
