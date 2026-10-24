"""An Apple session that has run out must lead back to the sign-in form.

Before, the status kept calling the account signed in, every call failed
with "Your session has expired" - and nothing ever offered the form again.
"""

from __future__ import annotations

import plistlib
import time

import pytest

from modstaller import server as srv
from modstaller.apple import devservices
from modstaller.apple import session as session_mod
from modstaller.apple.gsa import GSAResult
from modstaller.errors import APP_ID_QUOTA_EXCEEDED, SESSION_EXPIRED, AppleError


class _Resp:
    def __init__(self, status: int, body: dict | None = None):
        self.status_code = status
        self.content = plistlib.dumps(body or {})

    def raise_for_status(self):
        pass


class _Ani:
    def headers(self):
        return {}


def _signed_in() -> session_mod.Session:
    # With a first name, the status starts no lookup of its own at Apple.
    s = session_mod.Session(adsid="a", idms_token="i", identity_token="t",
                            created_at=time.time(), app_token="x",
                            apple_id="someone@example.com", first_name="Sam")
    s.save()
    return s


def _api(session, resp):
    api = devservices.DeveloperServices(session, _Ani())
    api._http = type("Http", (), {"post": lambda self, *a, **kw: resp})()
    return api


@pytest.mark.parametrize("resp", [
    _Resp(200, {"resultCode": SESSION_EXPIRED,
                "resultString": "Your session has expired. Please log in."}),
    _Resp(401),
])
def test_apple_turning_the_session_down_marks_it(resp):
    with pytest.raises(AppleError):
        _api(_signed_in(), resp).list_teams()
    stored = session_mod.Session.load("a")
    assert stored.expired and not stored.probably_valid
    assert stored.apple_id == "someone@example.com", "it fills in the sign-in"


def test_other_errors_leave_the_session_alone():
    s = _signed_in()
    with pytest.raises(AppleError):
        _api(s, _Resp(200, {"resultCode": APP_ID_QUOTA_EXCEEDED})).list_teams()
    assert not session_mod.Session.load("a").expired


def test_signing_in_again_replaces_the_expired_session():
    _signed_in().mark_expired()
    session_mod.Session.from_gsa(
        GSAResult(adsid="a", idms_token="i2", app_token="y",
                  identity_token="t2"), apple_id="someone@example.com").save()
    assert not session_mod.Session.load("a").expired


def test_marking_does_not_bring_back_a_signed_out_account():
    s = _signed_in()
    session_mod.Session.clear("a")
    s.mark_expired()
    assert session_mod.Session.load("a") is None


async def test_the_status_offers_the_sign_in_again(monkeypatch):
    async def no_devices():
        return []
    monkeypatch.setattr("modstaller.device.discovery.usbmux_refs", no_devices)
    _signed_in().mark_expired()

    import os
    r, w = os.pipe()
    try:
        st = await srv._status(srv.Server(w), None, {})
    finally:
        os.close(r)
    assert st["loggedIn"] is False
    assert st["accounts"][0]["expired"] is True
    assert st["accounts"][0]["appleId"] == "someone@example.com"
