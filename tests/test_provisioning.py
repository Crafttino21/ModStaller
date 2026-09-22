"""Kontingent-Logik.

Apple laesst pro Woche zehn *neu angelegte* App-IDs zu. Vorhandene zu
loeschen gibt kein Kontingent zurueck - wer es doch tut, nimmt einer fremden
App die Moeglichkeit, je wieder erneuert zu werden. Deshalb wird
ausgewichen, nicht geloescht, und was auf dem Geraet liegt, bleibt tabu.
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
    """Die Extension traegt die App-ID der App als Praefix - ohne sie laesst
    sich die App nicht mehr vollstaendig signieren."""
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
    """'…youtubeXY' faengt zwar mit '…youtube' an, gehoert aber nicht dazu."""
    existing = [_app_id("com.google.ios.youtube.PP2WVWJJYZextra")]
    assert spare_app_id(existing, INSTALLED) is not None


def test_no_candidates_yields_none():
    assert spare_app_id([], INSTALLED) is None


def test_case_differences_still_protect():
    existing = [_app_id("COM.SIDESTORE.SIDESTORE.PP2WVWJJYZ")]
    assert spare_app_id(existing, INSTALLED) is None


# -- Bundle-ID und Account-Art --------------------------------------------


def test_bundle_id_keeps_team_id_spelling():
    """Gross-/Kleinschreibung entscheidet, ob eine vorhandene App-ID
    getroffen wird - und damit, ob Kontingent verbraucht wird."""
    assert (derive_bundle_id("com.google.ios.youtube", "PP2WVWJJYZ")
            == "com.google.ios.youtube.PP2WVWJJYZ")


@pytest.mark.parametrize("team_type", ["Individual", "Free", "individual"])
def test_individual_accounts_are_assumed_free(team_type):
    """Apple meldet kostenlose wie bezahlte Einzelaccounts als 'Individual'.
    Der Irrtum Richtung 'kostenlos' kostet eine Extension, der umgekehrte
    das gesamte Wochenkontingent."""
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
