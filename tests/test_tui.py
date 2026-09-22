"""Die Logik hinter der Oberflaeche.

Die Darstellung selbst pruefen wir nicht - aber *was* angeboten wird, haengt
vom Zustand ab, und genau daran entscheidet sich, ob die Oberflaeche hilft
oder im Weg steht.
"""

from __future__ import annotations

import time

from modstaller.state.store import InstallRecord
from modstaller.tui import URGENT_DAYS, Status, build_menu


def _app(name: str, days_left: float) -> InstallRecord:
    return InstallRecord(
        bundle_id=f"com.test.{name}", original_bundle_id="com.test",
        name=name, team_id="T", udid="U", source_ipa="/x.ipa",
        app_id_id="A", profile_path="/p",
        expires_at=time.time() + days_left * 86400,
    )


def _labels(status: Status) -> list[str]:
    return [c.title for c in build_menu(status)]


def test_login_comes_first_when_missing():
    """Ohne Anmeldung nuetzt kein anderer Menuepunkt etwas."""
    assert _labels(Status(logged_in=False, apps=[]))[0] == "Bei Apple anmelden"


def test_login_absent_when_signed_in():
    assert "Bei Apple anmelden" not in _labels(Status(logged_in=True, apps=[]))


def test_expiring_app_is_offered_prominently():
    st = Status(logged_in=True, apps=[_app("PojavLauncher", 0.5)])
    assert "laeuft ab" in _labels(st)[0]


def test_healthy_app_is_not_pushed_to_the_top():
    st = Status(logged_in=True, apps=[_app("PojavLauncher", 6.5)])
    assert _labels(st)[0] == "App installieren"


def test_urgent_threshold_is_inclusive():
    assert Status(apps=[_app("x", URGENT_DAYS)]).urgent
    assert not Status(apps=[_app("x", URGENT_DAYS + 0.1)]).urgent


def test_expired_app_counts_as_urgent():
    assert Status(apps=[_app("x", -1.0)]).urgent


def test_only_one_expiry_shortcut_even_with_several_due():
    st = Status(logged_in=True, apps=[_app("A", 0.1), _app("B", 0.2)])
    assert sum("laeuft ab" in label for label in _labels(st)) == 1


def test_menu_always_offers_a_way_out():
    for st in (Status(logged_in=False, apps=[]),
               Status(logged_in=True, apps=[_app("x", 0.1)])):
        assert _labels(st)[-1] == "Beenden"


def test_status_without_device_is_not_an_error():
    st = Status(logged_in=True, apps=[])
    assert st.has_device is False
    assert st.error == ""
