"""The two-factor step of the GrandSlam sign-in.

Every rule here guards against one outcome: Apple confirming nothing while
we believe it did. The user then sees "Apple asks for another code" - or a
"wrong password" at the token exchange - and nothing points back here.
"""

from __future__ import annotations

import plistlib

import pytest

from modstaller.apple import anisette, clientinfo
from modstaller.apple.gsa import VIA_SMS, XCODE_APP, GSAClient, _describe
from modstaller.errors import AppleError

SPD = {"adsid": "000123-00-abc", "GsIdmsToken": "secret-token"}


class _FakeResponse:
    def __init__(self, status: int, content: bytes = b""):
        self.status_code = status
        self.content = content
        self.headers: dict = {}


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


def test_secondary_auth_goes_the_text_message_route():
    """Issue #3: answered over the trusted-device route, a code still lands
    on the iPhone - but Apple asks again on every handshake."""
    seen = []
    client = _client()
    pending = ({**SPD}, b"key", {"Status": {"au": "secondaryAuth"}})
    client._handshake = lambda apple_id, password: pending
    client._do_two_factor = lambda spd, via: seen.append(via)
    with pytest.raises(AppleError, match="au=secondaryAuth"):
        client.authenticate("someone@example.com", "pw")
    assert seen == [VIA_SMS]


def test_a_text_message_code_is_requested_and_confirmed_as_json():
    import json
    asked = []
    client = GSAClient(_Anisette(),
                       code_prompt=lambda via: asked.append(via) or "654321")
    client._session = _Replay(_FakeResponse(200, b"{}"),
                              _FakeResponse(200, b"{}"))
    client._do_two_factor(SPD, VIA_SMS)

    send, confirm = client._session.sent
    assert send["url"].endswith("/auth/verify/phone")
    assert json.loads(send["data"]) == {"phoneNumber": {"id": 1}, "mode": "sms"}
    assert confirm["url"].endswith("/auth/verify/phone/securitycode")
    assert json.loads(confirm["data"])["securityCode"] == {"code": "654321"}
    assert confirm["headers"]["Content-Type"].startswith("application/json")
    assert send["headers"]["X-Apple-I-MD"] != confirm["headers"]["X-Apple-I-MD"]
    assert asked == [VIA_SMS], "the prompt must say where to look for the code"


def test_codes_already_sent_are_not_an_error():
    """423: Apple has sent codes already - the last one still counts."""
    client = _client(_FakeResponse(423, b"{}"), _FakeResponse(200, b"{}"))
    client._do_two_factor(SPD, VIA_SMS)


def test_a_wrong_text_message_code_shows_apples_words():
    body = b'{"serviceErrors":[{"code":"-21669","title":"Incorrect Code",' \
           b'"message":"Incorrect verification code."}]}'
    client = _client(_FakeResponse(200, b"{}"), _FakeResponse(400, body))
    with pytest.raises(AppleError, match="Incorrect verification code"):
        client._do_two_factor(SPD, VIA_SMS)


def test_a_text_message_that_could_not_be_sent_says_so():
    client = _client(_FakeResponse(500, b"<html/>"))
    with pytest.raises(AppleError, match="HTTP 500"):
        client._do_two_factor(SPD, VIA_SMS)


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
