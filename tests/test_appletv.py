"""Apple TV: signing per platform, the IPA's platform, pairing by PIN."""

from __future__ import annotations

import plistlib
import zipfile

import pytest

from modstaller.apple import devservices
from modstaller.signing.ipa import inspect, platform_of


# -- Apple's API --------------------------------------------------------------


class _Resp:
    status_code = 200

    def __init__(self, body):
        self.content = plistlib.dumps(body)

    def raise_for_status(self):
        pass


class _Http:
    def __init__(self):
        self.bodies = []

    def post(self, url, data, headers, timeout):
        self.bodies.append((url, plistlib.loads(data)))
        return _Resp({"resultCode": 0, "devices": [], "appIds": []})


class _Session:
    auth_headers = {}


class _Ani:
    def headers(self):
        return {}


def _api(platform):
    api = devservices.DeveloperServices(_Session(), _Ani(), platform=platform)
    api._http = _Http()
    return api


@pytest.mark.parametrize("platform, expected", [
    ("ios", None),
    ("tvos", ("tvos", "tvOS")),
])
def test_device_and_profile_calls_name_the_platform(platform, expected):
    api = _api(platform)
    api.register_device("T", "UDID", "Living room")
    api.list_app_ids("T")
    for url, body in api._http.bodies:
        assert "/ios/" in url, "the path stays ios/ - the body says tvOS"
        got = (body.get("DTDK_Platform"), body.get("subPlatform"))
        assert got == (expected or (None, None))


def test_certificates_are_shared_across_platforms():
    api = _api("tvos")
    api._http.post = lambda url, data, headers, timeout: (
        api._http.bodies.append((url, plistlib.loads(data))) or _Resp({"certificates": []}))
    api.list_certificates("T")
    assert "DTDK_Platform" not in api._http.bodies[0][1]


# -- The IPA's platform -------------------------------------------------------


@pytest.mark.parametrize("info, platform", [
    ({"CFBundleSupportedPlatforms": ["AppleTVOS"]}, "tvos"),
    ({"CFBundleSupportedPlatforms": ["iPhoneOS"], "UIDeviceFamily": [1, 2]}, "ios"),
    ({"UIDeviceFamily": [3]}, "tvos"),
    ({"DTPlatformName": "appletvos"}, "tvos"),
    ({}, "ios"),
])
def test_platform_of(info, platform):
    assert platform_of(info) == platform


def test_inspect_reports_the_platform(tmp_path):
    ipa = tmp_path / "tv.ipa"
    with zipfile.ZipFile(ipa, "w") as zf:
        zf.writestr("Payload/Tv.app/Info.plist", plistlib.dumps({
            "CFBundleIdentifier": "com.example.tv", "CFBundleName": "Tv",
            "CFBundleSupportedPlatforms": ["AppleTVOS"], "MinimumOSVersion": "17.0"}))
        zf.writestr("Payload/Tv.app/Tv", b"\xcf\xfa\xed\xfe")
    info = inspect(ipa)
    assert info.platform == "tvos"
    assert "min. tvOS" in info.summary()


def test_a_mismatch_says_which_way_round():
    from modstaller.pipeline import _ipa_mismatch
    assert "Apple TV app" in _ipa_mismatch("tvos", "ios")
    assert "tvOS version" in _ipa_mismatch("ios", "tvos")


# -- Pairing by PIN -------------------------------------------------------------


async def test_the_pin_is_asked_for_not_read_from_the_terminal(monkeypatch):
    from pymobiledevice3.remote import tunnel_service as ts

    from modstaller.device import tvpair

    asked = []

    async def ask_pin(name):
        asked.append(name)
        return "123456"

    service = tvpair._pin_pairing_class()("ID", "10.0.0.5", 49152, ask_pin, "Living room")
    sent = []

    async def send(data):
        sent.append(data)

    async def receive_plain():
        # tvOS answers right away with the pairing data - no consent dialog.
        return {"event": {"_0": {"pairingData": {"_0": {"data": "cGQ="}}}}}
    monkeypatch.setattr(service, "_send_pairing_data", send)
    monkeypatch.setattr(service, "_receive_plain_response", receive_plain)
    monkeypatch.setattr(service, "decode_tlv", lambda parsed: {
        ts.PairingDataComponentType.PUBLIC_KEY: b"pk", ts.PairingDataComponentType.SALT: b"salt"})
    monkeypatch.setattr(ts.PairingDataComponentTLVBuf, "parse", lambda data: data)
    monkeypatch.setattr("builtins.input", lambda *a: pytest.fail("must not read stdin"))

    result = await service._request_pair_consent()
    assert asked == ["Living room"]
    assert result.pin == "123456"
    assert sent[0]["kind"] == "setupManualPairing"


async def test_no_pin_cancels(monkeypatch):
    from pymobiledevice3.remote import tunnel_service as ts

    from modstaller.device import tvpair
    from modstaller.errors import DeviceError

    async def ask_pin(name):
        return None

    service = tvpair._pin_pairing_class()("ID", "10.0.0.5", 49152, ask_pin, "TV")

    async def send(data):
        pass

    async def receive_plain():
        return {"event": {"_0": {"pairingData": {"_0": {"data": "cGQ="}}}}}
    monkeypatch.setattr(service, "_send_pairing_data", send)
    monkeypatch.setattr(service, "_receive_plain_response", receive_plain)
    with pytest.raises(DeviceError, match="cancelled"):
        await service._request_pair_consent()


async def test_pairing_asks_the_interface_for_the_pin(monkeypatch):
    """pair.start: the PIN comes from the interface as a prompt.pin request."""
    from modstaller import server as srv
    from modstaller.device import registry, tvpair
    from tests.test_server import Wire

    async def fake_pair(identifier, host, port, *, name, ask_pin, on_step):
        pin = await ask_pin(name)
        assert pin == "654321"
        return registry.remember("TVUDID", name=name, product_type="AppleTV14,1",
                                 os_version="18.1", platform=registry.TVOS,
                                 remote_identifier=identifier)
    monkeypatch.setattr(tvpair, "pair", fake_pair)

    w = Wire()
    w.call(1, "pair.start", identifier="ID", host="10.0.0.5", port=49152, name="Living room")
    while True:
        msg = await w.next()
        if msg.get("method") == "prompt.pin":
            break
    assert msg["params"] == {"name": "Living room"}
    w.send({"jsonrpc": "2.0", "id": msg["id"], "result": " 654321 "})
    reply = await w.reply_to(1)
    assert reply["result"]["udid"] == "TVUDID"
    assert srv  # imported for the method registry
