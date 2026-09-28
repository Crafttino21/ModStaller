"""Transport rules against Apple's edge.

Both rules checked here were learned the hard way and look harmless in the
code - which is exactly why they are under test.
"""

from __future__ import annotations

import plistlib

import pytest
import requests

from modstaller.apple import clientinfo, http
from modstaller.errors import (
    AnisetteClientInfoRejected, AppleRateLimited, ClientInfoPolicyViolation,
)

XCODE_CI = ("<MacBookPro13,2> <macOS;13.1;22C65> "
            "<com.apple.AuthKit/1 (com.apple.dt.Xcode/3594.4.19)>")


class _FakeResponse:
    def __init__(self, status: int, content: bytes = b"", headers=None):
        self.status_code = status
        self.content = content
        self.headers = headers or {}


class _RecordingSession(requests.Session):
    """Session that replays responses and counts connection closes."""

    def __init__(self, statuses: list[int]):
        super().__init__()
        self._statuses = list(statuses)
        self.sent: list[dict] = []
        self.closes = 0

    def close(self):
        self.closes += 1

    def request(self, method, url, **kwargs):  # type: ignore[override]
        self.sent.append({"method": method, "headers": kwargs.get("headers", {})})
        return _FakeResponse(self._statuses.pop(0))


# -- One connection per request -------------------------------------------


def test_gsa_session_forces_connection_close():
    """Apple's edge lets only one request through per TCP connection."""
    assert http.gsa_session().headers["Connection"] == "close"


def test_gsa_request_closes_connection_before_each_attempt():
    session = _RecordingSession([200])
    http.gsa_request(session, "POST", http.GSA_URL,
                     client_info=clientinfo.DEFAULT_CLIENT_INFO)
    assert session.closes == 1
    assert session.sent[0]["headers"]["Connection"] == "close"


def test_gsa_request_retries_429_on_fresh_connections():
    """The remaining 429 is an IP budget and clears up - so try again.

    Harmless, because the edge rejects before the auth service and the SRP
    cookie is not consumed.
    """
    session = _RecordingSession([429, 429, 200])
    http.GSA_RETRY_DELAY, original = 0.0, http.GSA_RETRY_DELAY
    try:
        resp = http.gsa_request(session, "POST", http.GSA_URL,
                                client_info=clientinfo.DEFAULT_CLIENT_INFO)
    finally:
        http.GSA_RETRY_DELAY = original
    assert resp.status_code == 200
    assert session.closes == 3, "every attempt needs its own connection"


def test_gsa_request_gives_up_with_clear_message():
    session = _RecordingSession([429] * http.GSA_MAX_ATTEMPTS)
    http.GSA_RETRY_DELAY, original = 0.0, http.GSA_RETRY_DELAY
    try:
        with pytest.raises(AppleRateLimited) as exc:
            http.gsa_request(session, "POST", http.GSA_URL,
                             client_info=clientinfo.DEFAULT_CLIENT_INFO)
    finally:
        http.GSA_RETRY_DELAY = original
    assert "IP address" in str(exc.value)


def test_dev_session_does_not_retry_429():
    """429 never belongs in a blind retry."""
    assert 429 not in http._DEV_RETRY
    assert http._NO_RETRY == ()


# -- Client info guard ----------------------------------------------------


def test_guard_blocks_xcode_identifier_before_sending():
    with pytest.raises(ClientInfoPolicyViolation):
        http.gsa_session().post(http.GSA_URL,
                                headers={"X-MMe-Client-Info": XCODE_CI},
                                data=b"<plist/>")


def test_guard_blocks_missing_client_info():
    with pytest.raises(ClientInfoPolicyViolation):
        http.gsa_session().post(http.GSA_URL, data=b"<plist/>")


def test_sanitize_keeps_hardware_but_replaces_identifier():
    out = clientinfo.sanitize(XCODE_CI)
    assert "com.apple.akd" in out
    assert "com.apple.dt.Xcode" not in out
    assert "MacBookPro13,2" in out, "hardware identity must be preserved"


def test_503_with_small_body_is_diagnosed_not_retried():
    """Apple's edge rejection looks like an outage. It isn't one."""
    page = (b"<html><head><title>503</title></head><body>"
            b"<center>Apple</center></body></html>")
    with pytest.raises(AnisetteClientInfoRejected):
        http.check_edge_rejection(_FakeResponse(503, page), XCODE_CI)


def test_503_with_large_body_passes_through():
    http.check_edge_rejection(_FakeResponse(503, b"x" * 5000),
                              clientinfo.DEFAULT_CLIENT_INFO)


def test_rate_limit_reports_retry_after():
    with pytest.raises(AppleRateLimited) as exc:
        http.check_rate_limit(_FakeResponse(429, b"", {"Retry-After": "600"}),
                              attempts=4)
    assert "10 minutes" in str(exc.value)


# -- 2FA detection --------------------------------------------------------

from modstaller.apple.gsa import GSAClient, _describe  # noqa: E402


@pytest.mark.parametrize("complete, spd, expected", [
    ({"Status": {"au": "trustedDeviceSecondaryAuth"}}, {}, True),
    ({"au": "secondaryAuth"}, {}, True),
    ({}, {"au": "smsSecondaryAuth"}, True),
    ({"Status": {"ec": 0}}, {"adsid": "x"}, False),
    ({}, {}, False),
])
def test_two_factor_detected_wherever_apple_puts_it(complete, spd, expected):
    """Apple puts the hint in Status.au, not in the encrypted spd.

    If that is missed, the login appears to succeed and the subsequent token
    exchange fails with "Enter the correct password" - wording that points
    in completely the wrong direction.
    """
    assert GSAClient._needs_2fa(complete, spd) is expected


def test_describe_never_leaks_secrets():
    out = _describe({
        "sk": b"\x01" * 32, "spd": b"\x02" * 64, "GsIdmsToken": "secret",
        "Status": {"ec": 0, "au": "trustedDeviceSecondaryAuth"},
        "ptxid": "harmless",
    }, "test")
    assert "secret" not in out
    assert "trustedDeviceSecondaryAuth" in out, "diagnostics must stay useful"
    assert "harmless" in out
    assert "<hidden>" in out or "bytes>" in out


# -- The first name for the greeting -----------------------------------------

from modstaller.apple import session as session_mod  # noqa: E402
from modstaller.apple.devservices import Team  # noqa: E402


def _session(tmp_path, monkeypatch, **kw):
    monkeypatch.setattr(session_mod, "SESSION_FILE", tmp_path / "session.json")
    s = session_mod.Session(adsid="a", idms_token="i", identity_token="t",
                            created_at=0.0, app_token="x", **kw)
    s.save()
    return s


def test_an_old_session_without_first_name_still_loads(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(session_mod, "SESSION_FILE", tmp_path / "session.json")
    from modstaller.config import write_secret
    write_secret(tmp_path / "session.json", json.dumps({
        "adsid": "a", "idms_token": "i", "identity_token": "t",
        "created_at": 0.0, "app_token": "x"}).encode())
    assert session_mod.Session.load().first_name == ""


def test_first_name_is_taken_from_an_individual_team(tmp_path, monkeypatch):
    _session(tmp_path, monkeypatch)
    teams = [Team("T1", "Santino Fietz", "Individual", "active")]
    assert session_mod.remember_first_name(teams) == "Santino"
    assert session_mod.Session.load().first_name == "Santino"


def test_a_company_team_is_not_a_person(tmp_path, monkeypatch):
    _session(tmp_path, monkeypatch)
    teams = [Team("T1", "Example GmbH", "Company/Organization", "active")]
    assert session_mod.remember_first_name(teams) == ""


def test_the_name_from_sign_in_wins(tmp_path, monkeypatch):
    _session(tmp_path, monkeypatch, first_name="Sam")
    teams = [Team("T1", "Santino Fietz", "Individual", "active")]
    assert session_mod.remember_first_name(teams) == "Sam"


# -- Several accounts --------------------------------------------------------


def _account(adsid, created_at, **kw):
    s = session_mod.Session(adsid=adsid, idms_token="i", identity_token="t",
                            created_at=created_at, app_token="x", **kw)
    s.save()
    return s


def test_the_old_single_session_becomes_the_active_account(tmp_path):
    import json
    from modstaller.config import write_secret
    write_secret(session_mod.SESSION_FILE, json.dumps({
        "adsid": "old", "idms_token": "i", "identity_token": "t",
        "created_at": 0.0, "app_token": "x", "first_name": "Sam"}).encode())
    assert session_mod.Session.load().first_name == "Sam"
    assert session_mod.active_adsid() == "old"
    assert not session_mod.SESSION_FILE.exists()


def test_a_second_account_does_not_replace_the_first():
    _account("a", 1, apple_id="a@x.de")
    _account("b", 2, apple_id="b@x.de")
    assert [s.adsid for s in session_mod.list_accounts()] == ["a", "b"]
    assert session_mod.Session.load().adsid == "a"
    session_mod.set_active("b")
    assert session_mod.Session.load().adsid == "b"
    assert session_mod.find_account("B@X.DE").adsid == "b"


def test_signing_out_the_active_account_moves_the_next_one_up():
    _account("a", 1)
    _account("b", 2)
    session_mod.remember_teams("a", [Team("T1", "A", "Individual", "active")])
    session_mod.Session.clear()
    assert session_mod.active_adsid() == "b"
    assert session_mod.session_for_team("T1") is None
    session_mod.Session.clear()
    assert session_mod.active_adsid() is None
    assert session_mod.Session.load() is None


def test_setting_an_unknown_account_active_fails():
    import pytest
    from modstaller.errors import AppleError
    with pytest.raises(AppleError):
        session_mod.set_active("nobody")


def test_a_team_is_mapped_to_its_account():
    _account("a", 1)
    _account("b", 2)
    session_mod.remember_teams("b", [Team("T2", "B", "Individual", "active")])
    assert session_mod.session_for_team("T2").adsid == "b"


def test_an_adsid_cannot_escape_the_accounts_dir():
    path = session_mod._account_file("../../evil")
    assert path.parent == session_mod.ACCOUNTS_DIR
