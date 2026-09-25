"""Transport-Regeln gegen Apples Edge.

Beide hier geprueften Regeln sind teuer erkauft und sehen im Code harmlos
aus - genau deshalb stehen sie unter Test.
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
    """Session, die Antworten abspielt und Verbindungsabbrueche mitzaehlt."""

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


# -- Verbindung pro Request ------------------------------------------------


def test_gsa_session_forces_connection_close():
    """Apples Edge laesst pro TCP-Verbindung nur einen Request durch."""
    assert http.gsa_session().headers["Connection"] == "close"


def test_gsa_request_closes_connection_before_each_attempt():
    session = _RecordingSession([200])
    http.gsa_request(session, "POST", http.GSA_URL,
                     client_info=clientinfo.DEFAULT_CLIENT_INFO)
    assert session.closes == 1
    assert session.sent[0]["headers"]["Connection"] == "close"


def test_gsa_request_retries_429_on_fresh_connections():
    """Der Rest-429 ist ein IP-Budget und klart auf - also einmal nachfassen.

    Unbedenklich, weil die Edge vor dem Auth-Dienst abweist und das
    SRP-Cookie dabei nicht verbraucht wird.
    """
    session = _RecordingSession([429, 429, 200])
    http.GSA_RETRY_DELAY, original = 0.0, http.GSA_RETRY_DELAY
    try:
        resp = http.gsa_request(session, "POST", http.GSA_URL,
                                client_info=clientinfo.DEFAULT_CLIENT_INFO)
    finally:
        http.GSA_RETRY_DELAY = original
    assert resp.status_code == 200
    assert session.closes == 3, "jeder Versuch braucht eine eigene Verbindung"


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
    """429 gehoert nie in eine blinde Wiederholung."""
    assert 429 not in http._DEV_RETRY
    assert http._NO_RETRY == ()


# -- Client-Info-Guard -----------------------------------------------------


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
    assert "MacBookPro13,2" in out, "Hardware-Identitaet muss erhalten bleiben"


def test_503_with_small_body_is_diagnosed_not_retried():
    """Apples Edge-Ablehnung sieht aus wie ein Ausfall. Sie ist keiner."""
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


# -- 2FA-Erkennung ---------------------------------------------------------

from modstaller.apple.gsa import GSAClient, _describe  # noqa: E402


@pytest.mark.parametrize("complete, spd, expected", [
    ({"Status": {"au": "trustedDeviceSecondaryAuth"}}, {}, True),
    ({"au": "secondaryAuth"}, {}, True),
    ({}, {"au": "smsSecondaryAuth"}, True),
    ({"Status": {"ec": 0}}, {"adsid": "x"}, False),
    ({}, {}, False),
])
def test_two_factor_detected_wherever_apple_puts_it(complete, spd, expected):
    """Apple legt den Hinweis in Status.au ab, nicht im verschluesselten spd.

    Wird das uebersehen, laeuft der Login scheinbar durch und der
    anschliessende Token-Tausch scheitert mit "Enter the correct password" -
    ein Wortlaut, der in die voellig falsche Richtung zeigt.
    """
    assert GSAClient._needs_2fa(complete, spd) is expected


def test_describe_never_leaks_secrets():
    out = _describe({
        "sk": b"\x01" * 32, "spd": b"\x02" * 64, "GsIdmsToken": "geheim",
        "Status": {"ec": 0, "au": "trustedDeviceSecondaryAuth"},
        "ptxid": "harmlos",
    }, "test")
    assert "geheim" not in out
    assert "trustedDeviceSecondaryAuth" in out, "Diagnose muss brauchbar bleiben"
    assert "harmlos" in out
    assert "<verborgen>" in out or "Byte>" in out
