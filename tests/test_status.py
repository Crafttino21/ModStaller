"""Die Zustandslogik hinter der Oberflaeche.

*Was* angeboten wird, haengt vom Zustand ab - und genau daran entscheidet
sich, ob die Oberflaeche hilft oder im Weg steht.
"""

from __future__ import annotations

import time

from modstaller.state.store import InstallRecord
from modstaller.status import URGENT_DAYS, Status


def _app(name: str, days_left: float) -> InstallRecord:
    return InstallRecord(
        bundle_id=f"com.test.{name}", original_bundle_id="com.test",
        name=name, team_id="T", udid="U", source_ipa="/x.ipa",
        app_id_id="A", profile_path="/p",
        expires_at=time.time() + days_left * 86400,
    )


def test_urgent_threshold_is_inclusive():
    assert Status(apps=[_app("x", URGENT_DAYS)]).urgent
    assert not Status(apps=[_app("x", URGENT_DAYS + 0.1)]).urgent


def test_expired_app_counts_as_urgent():
    assert Status(apps=[_app("x", -1.0)]).urgent


def test_healthy_app_is_not_urgent():
    assert not Status(apps=[_app("PojavLauncher", 6.5)]).urgent


def test_status_without_device_is_not_an_error():
    st = Status(logged_in=True)
    assert st.has_device is False
    assert st.error == ""
    assert st.urgent == []
