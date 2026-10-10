"""The two-factor step of the GrandSlam sign-in.

Every rule here guards against one outcome: Apple confirming nothing while
we believe it did. The user then sees "Apple asks for another code" - or a
"wrong password" at the token exchange - and nothing points back here.
"""

from __future__ import annotations

import plistlib

import pytest

from modstaller.apple import anisette, clientinfo
from modstaller.apple.gsa import (
    ERR_NOT_FULLY_AUTHENTICATED, ERR_TEMPORARILY_BLOCKED, VIA_SMS, XCODE_APP,
    GSAClient, GSAResult, GSAStatusError, _describe,
)
from modstaller.errors import AppleError

SPD = {"adsid": "000123-00-abc", "GsIdmsToken": "secret-token"}


class _FakeResponse:
    def __init__(self, status: int, content: bytes = b"", headers=None):
        self.status_code = status
        self.content = content
        self.headers: dict = headers or {}


class _Replay:
    """Session that replays responses and records what was sent."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.sent: list[dict] = []

    def close(self):
        pass

    def request(self, method, url, **kwargs):
        self.sent.append({"method": method, "url": url,
                          "headers": kwargs.get("headers", {}),
                          "data": kwargs.get("data")})
        return self._responses.pop(0)


class _Anisette:
    """A new one-time password on every call, like the real thing."""

    def __init__(self):
        self.calls = 0

    def headers(self):
        self.calls += 1
        return anisette.normalize_headers({
            "X-Apple-I-MD": f"otp-{self.calls}",
            "X-Apple-I-MD-M": "machine",
            "X-Apple-I-TimeZone": "Mitteleuropäische Sommerzeit",
            "X-MMe-Client-Info": clientinfo.DEFAULT_CLIENT_INFO,
        })

    def client_info(self):
        return clientinfo.DEFAULT_CLIENT_INFO


def _client(*responses, code="123456", debug=False) -> GSAClient:
    client = GSAClient(_Anisette(), code_prompt=lambda via: code, debug=debug)
    client._session = _Replay(*responses)
    return client


def _plist(**kw) -> bytes:
    return plistlib.dumps(kw)


def test_validate_gets_a_fresh_one_time_password():
    """The code typed by the user may be minutes old - the OTP must not be."""
    client = _client(_FakeResponse(200), _FakeResponse(200, _plist(ec=0)))
    client._do_two_factor(SPD)

    push, validate = client._session.sent
    assert push["headers"]["X-Apple-I-MD"] != validate["headers"]["X-Apple-I-MD"]
    assert validate["headers"]["security-code"] == "123456"
    assert validate["headers"]["X-Apple-App-Info"] == XCODE_APP


def test_two_factor_headers_are_ascii():
    """They are raw HTTP headers - latin-1 at best on the wire."""
    client = _client(_FakeResponse(200), _FakeResponse(200, _plist(ec=0)))
    client._do_two_factor(SPD)
    for sent in client._session.sent:
        assert all(str(v).isascii() for v in sent["headers"].values())


def test_a_validation_that_is_not_a_plist_is_not_a_success():
    """Taken for success, it leads straight to "asks for another code"."""
    client = _client(_FakeResponse(200),
                     _FakeResponse(200, b"<html><body>nope</body></html>"))
    with pytest.raises(AppleError, match="2FA validation failed"):
        client._do_two_factor(SPD)


def test_an_empty_validation_is_not_a_success():
    client = _client(_FakeResponse(200), _FakeResponse(204))
    with pytest.raises(AppleError, match="HTTP 204"):
        client._do_two_factor(SPD)


def test_a_rejected_code_says_so():
    client = _client(_FakeResponse(200),
                     _FakeResponse(400, _plist(ec=-21669, em="Wrong code.")))
    with pytest.raises(AppleError, match="not accepted"):
        client._do_two_factor(SPD)


def test_a_failed_push_does_not_ask_for_a_code():
    asked = []
    client = GSAClient(_Anisette(),
                       code_prompt=lambda via: asked.append(1) or "123456")
    client._session = _Replay(_FakeResponse(401, b"<html/>"))
    with pytest.raises(AppleError, match="HTTP 401"):
        client._do_two_factor(SPD)
    assert not asked


def test_debug_shows_both_answers_without_secrets(capsys):
    client = _client(_FakeResponse(200),
                     _FakeResponse(200, _plist(ec=0, GsIdmsToken="leak")),
                     debug=True)
    client._do_two_factor(SPD)
    out = capsys.readouterr().out
    assert "[trusteddevice] HTTP 200" in out
    assert "[validate] HTTP 200" in out
    assert "leak" not in out


def test_asking_again_after_two_factor_names_what_apple_wants():
    """The au value is what a bug report needs - trusted device or SMS."""
    client = _client()
    pending = ({**SPD}, b"key", {"Status": {"au": "trustedDeviceSecondaryAuth"}})
    client._handshake = lambda apple_id, password: pending
    client._do_two_factor = lambda spd, via: None
    with pytest.raises(AppleError) as exc:
        client.authenticate("someone@example.com", "pw")
    assert "au=trustedDeviceSecondaryAuth" in str(exc.value)
    assert "forget-device" in str(exc.value)


def test_the_second_factor_is_named():
    assert GSAClient._second_factor(
        {"Status": {"au": "smsSecondaryAuth"}}, {}) == "smsSecondaryAuth"
    assert GSAClient._second_factor({"Status": {"au": "other"}}, {}) is None


# -- Text message (au=secondaryAuth) ----------------------------------------


def _ok(body: bytes = b"{}", **headers):
    return _FakeResponse(200, body, headers)


def _secondary_auth_client(monkeypatch, *, token_exchange):
    """A client whose first handshake asks for a text message; counts the
    handshakes and hands the token exchange to ``token_exchange``."""
    client = _client()
    handshakes = []

    def handshake(apple_id, password):
        handshakes.append(1)
        return ({**SPD, "sk": b"k", "c": b"c"}, b"key",
                {"Status": {"au": "secondaryAuth"}})

    client._handshake = handshake
    client._do_two_factor = lambda spd, via: None
    monkeypatch.setattr(client, "_fetch_app_token", token_exchange)
    return client, handshakes


def test_secondary_auth_goes_the_text_message_route():
    """Issue #3: answered over the trusted-device route, a code still lands
    on the iPhone - but Apple asks again on every handshake."""
    seen = []
    client = _client()
    pending = ({**SPD}, b"key", {"Status": {"au": "secondaryAuth"}})
    client._handshake = lambda apple_id, password: pending
    client._do_two_factor = lambda spd, via: seen.append(via)
    client._confirmed_session = lambda spd: None
    with pytest.raises(AppleError, match="au=secondaryAuth"):
        client.authenticate("someone@example.com", "pw")
    assert seen == [VIA_SMS]


def test_the_session_a_text_message_confirmed_is_used_directly(monkeypatch):
    """Issue #3 with rc.2: code accepted, yet a fresh handshake asks again.
    The session the code confirmed goes to the token exchange first."""
    client, handshakes = _secondary_auth_client(
        monkeypatch, token_exchange=lambda spd, adsid, token: "app-token")
    result = client.authenticate("someone@example.com", "pw")
    assert isinstance(result, GSAResult) and result.app_token == "app-token"
    assert len(handshakes) == 1, "no second handshake needed"


def test_a_confirmed_session_apple_turns_down_falls_back_to_signing_in(
        monkeypatch):
    def pending(spd, adsid, token):
        raise GSAStatusError("not fully authenticated",
                             ERR_NOT_FULLY_AUTHENTICATED)

    client, handshakes = _secondary_auth_client(monkeypatch,
                                                token_exchange=pending)
    with pytest.raises(AppleError, match="au=secondaryAuth"):
        client.authenticate("someone@example.com", "pw")
    assert len(handshakes) == 2


def test_a_block_is_not_answered_with_another_attempt(monkeypatch):
    """-22411 grows with every attempt - no second handshake on top."""
    def blocked(spd, adsid, token):
        raise GSAStatusError("blocked", ERR_TEMPORARILY_BLOCKED)

    client, handshakes = _secondary_auth_client(monkeypatch,
                                                token_exchange=blocked)
    with pytest.raises(GSAStatusError):
        client.authenticate("someone@example.com", "pw")
    assert len(handshakes) == 1


def test_a_text_message_goes_load_send_confirm_trust():
    import json
    asked = []
    client = GSAClient(_Anisette(),
                       code_prompt=lambda via: asked.append(via) or "654321")
    client._session = _Replay(_ok(), _ok(), _ok(), _ok())
    client._do_two_factor(SPD, VIA_SMS)

    load, send, confirm, trust = client._session.sent
    assert (load["method"], load["url"]) == ("GET", "https://gsa.apple.com/auth")
    assert (send["method"], send["url"]) == (
        "PUT", "https://gsa.apple.com/auth/verify/phone")
    assert json.loads(send["data"]) == {"phoneNumber": {"id": 1}, "mode": "sms"}
    assert confirm["url"].endswith("/auth/verify/phone/securitycode")
    assert json.loads(confirm["data"])["securityCode"] == {"code": "654321"}
    assert trust["url"].endswith("/auth/2sv/trust")
    assert confirm["headers"]["Content-Type"] == "application/json"
    assert confirm["headers"]["User-Agent"].startswith("akd/")
    assert send["headers"]["X-Apple-I-MD"] != confirm["headers"]["X-Apple-I-MD"]
    assert asked == [VIA_SMS], "the prompt must say where to look for the code"


def test_the_number_comes_from_the_sign_in_page():
    import json
    page = json.dumps({"trustedPhoneNumbers": [
        {"id": 2, "pushMode": "voice"}, {"id": 3, "pushMode": "sms"}]}).encode()
    client = _client(_ok(page), _ok(), _ok(), _ok())
    client._do_two_factor(SPD, VIA_SMS)
    _load, send, confirm, _trust = client._session.sent
    assert json.loads(send["data"])["phoneNumber"] == {"id": 3}
    assert json.loads(confirm["data"])["phoneNumber"] == {"id": 3}


def test_the_web_sign_in_gets_its_session_markers_back():
    client = _client(_ok(**{"X-Apple-ID-Session-Id": "sid", "scnt": "s1"}),
                     _ok(scnt="s2"), _ok(), _ok())
    client._do_two_factor(SPD, VIA_SMS)
    _load, send, confirm, _trust = client._session.sent
    assert send["headers"]["X-Apple-ID-Session-Id"] == "sid"
    assert send["headers"]["scnt"] == "s1"
    assert confirm["headers"]["scnt"] == "s2", "always the latest one"


@pytest.mark.parametrize("refusal", [
    _FakeResponse(423, b"{}"),
    _FakeResponse(412, b"{}"),
    _FakeResponse(400, b'{"serviceErrors":[{"code":"-22979",'
                       b'"title":"Too many codes","message":"Wait."}]}'),
])
def test_a_refused_new_text_message_still_asks_for_the_last_code(refusal):
    """Apple won't send another one, but the last code still counts."""
    asked = []
    client = GSAClient(_Anisette(),
                       code_prompt=lambda via: asked.append(via) or "1")
    client._session = _Replay(_ok(), refusal, _ok(), _ok())
    client._do_two_factor(SPD, VIA_SMS)
    assert asked == [VIA_SMS]


def test_a_failed_trust_step_does_not_fail_the_sign_in():
    client = _client(_ok(), _ok(), _ok(), _FakeResponse(404, b""))
    client._do_two_factor(SPD, VIA_SMS)


def test_a_wrong_text_message_code_shows_apples_words():
    body = b'{"serviceErrors":[{"code":"-21669","title":"Incorrect Code",' \
           b'"message":"Incorrect verification code."}]}'
    client = _client(_ok(), _ok(), _FakeResponse(400, body))
    with pytest.raises(AppleError, match="Incorrect verification code"):
        client._do_two_factor(SPD, VIA_SMS)


def test_a_text_message_that_could_not_be_sent_says_so():
    client = _client(_ok(), _FakeResponse(500, b"<html/>"))
    with pytest.raises(AppleError, match="HTTP 500"):
        client._do_two_factor(SPD, VIA_SMS)


def test_the_trace_names_headers_and_device_but_not_their_values(capsys):
    client = _client(_ok(**{"X-Apple-ID-Session-Id": "SECRET-SID"}),
                     _ok(), _ok(), _ok(), debug=True)
    client._do_two_factor(SPD, VIA_SMS)
    out = capsys.readouterr().out
    assert "X-Apple-ID-Session-Id" in out and "SECRET-SID" not in out
    assert "[verify/phone/securitycode] HTTP 200" in out
    assert out.count(", device ") == 4


# -- Debug output that ends up in public bug reports --------------------------


def test_debug_output_hides_nested_tokens_and_personal_data():
    """Shaped like the spd from issue #3: the token sat two levels down."""
    out = _describe({
        "t": {"com.apple.gs.appleid.auth": {"duration": 3600,
                                            "token": "LEAKED-TOKEN"}},
        "additionalInfo": {
            "phoneNumbers": [{"phoneNumber": "+1 555 0100", "type": "2fa"}],
            "obfuscatedPhoneNumbers": [{"maskedPhoneNumber": "(•••) •••-••00"}],
        },
        "primaryEmail": "someone@example.com", "fn": "Sam", "ln": "Doe",
        "alias": ["alias@example.com"], "np": b"\x01" * 32,
        "url": "secondaryAuth", "status-code": 409,
    }, "spd")
    for leak in ("LEAKED-TOKEN", "555", "•••", "someone@", "Sam", "Doe",
                 "alias@", "\\x01"):
        assert leak not in out
    # What a diagnosis needs stays.
    assert "secondaryAuth" in out and "409" in out and "'2fa'" in out
