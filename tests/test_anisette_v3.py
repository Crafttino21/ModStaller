"""The anisette-v3 server as provider (default since 1.4.0-rc.6, issue #4).

The server runs the ADI, this side keeps the state and talks to Apple. What
matters: the requests to Apple go out from here, the state survives a
restart, and GSA hears the server's client info and user agent - unless the
server names a Mac too old for Apple, as all public ones do (macOS 10.12.6).
"""

from __future__ import annotations

import json
import plistlib
from base64 import b64decode

import pytest

from modstaller.apple import anisette, clientinfo
from modstaller.apple.gsa import GSAClient
from modstaller.errors import AppleError

SERVER = "https://ani.example"
#: What mac-ani.jkcoxson.com reports (2026-11-20).
CLIENT_INFO = ("<MacBookPro13,3> <Mac OS X;10.12.6;16G29> "
               "<com.apple.AuthKit/1 (com.apple.akd/1.0)>")
USER_AGENT = "akd/1.0 CFNetwork/811.5.4 Darwin/16.7.0"
#: What goes to Apple in its place.
SENT_INFO = clientinfo.CURRENT_MAC
SENT_UA = clientinfo.CURRENT_MAC_USER_AGENT


class _Response:
    def __init__(self, data=None, content: bytes = b"", status: int = 200):
        self._data = data
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._data


class _Server:
    """The HTTP half of the server: client info and headers."""

    def __init__(self, client_info=CLIENT_INFO, user_agent=USER_AGENT):
        self.header_answers: list[dict] = []
        self.posted: list[dict] = []
        self.info = {"client_info": client_info, "user_agent": user_agent}

    def get(self, url, timeout=None):
        assert url == f"{SERVER}/v3/client_info"
        return _Response(self.info)

    def post(self, url, timeout=None, json=None):
        assert url == f"{SERVER}/v3/get_headers"
        self.posted.append(json)
        if self.header_answers:
            return _Response(self.header_answers.pop(0))
        return _Response({"result": "Headers", "X-Apple-I-MD": "otp",
                          "X-Apple-I-MD-M": "machine",
                          "X-Apple-I-MD-RINFO": "17106176"})


class _Socket:
    """The provisioning session as the server runs it."""

    def __init__(self, log: list):
        self._script = [
            {"result": "GiveIdentifier"},
            {"result": "GiveStartProvisioningData"},
            {"result": "GiveEndProvisioningData", "cpim": "the-cpim"},
            {"result": "ProvisioningSuccess", "adi_pb": "YWRp"},
        ]
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def recv(self, timeout=None):
        return json.dumps(self._script.pop(0))

    def send(self, text):
        self.log.append(("ws", json.loads(text)))


@pytest.fixture
def remote(monkeypatch, tmp_path):
    """A provider against a fake server; Apple answers from here, too."""
    monkeypatch.setattr(anisette, "ANISETTE_DIR", tmp_path)
    monkeypatch.setattr(anisette, "REMOTE_STATE_FILE", tmp_path / "remote.json")
    log: list = []

    def apple(session, method, url, *, client_info, headers=None, **kw):
        log.append(("apple", method, url, headers or {}))
        if url.endswith("/lookup"):
            return _Response(content=plistlib.dumps({"urls": {
                "midStartProvisioning": "https://gsa.apple.com/start",
                "midFinishProvisioning": "https://gsa.apple.com/finish"}}))
        sent = plistlib.loads(kw["data"])["Request"]
        if url.endswith("/start"):
            body = {"spim": "the-spim"}
        else:
            assert sent == {"cpim": "the-cpim"}
            body = {"ptm": "the-ptm", "tk": "the-tk"}
        return _Response(content=plistlib.dumps({"Response": body}))

    monkeypatch.setattr("modstaller.apple.http.gsa_request", apple)
    sockets = []

    def connect(url, timeout):
        assert url == "wss://ani.example/v3/provisioning_session"
        sockets.append(url)
        return _Socket(log)

    provider = anisette.RemoteV3Provider(SERVER, connect=connect)
    provider._session = _Server()
    provider.log, provider.sockets = log, sockets
    return provider


def test_provisioning_runs_through_and_the_state_is_kept(remote):
    headers = remote.headers()
    ws = [entry[1] for entry in remote.log if entry[0] == "ws"]
    identifier = ws[0]["identifier"]
    assert len(b64decode(identifier)) == 16
    assert ws[1:] == [{"spim": "the-spim"},
                      {"ptm": "the-ptm", "tk": "the-tk"}]
    state = json.loads(anisette.REMOTE_STATE_FILE.read_text())[SERVER]
    assert state == {"identifier": identifier, "adi_pb": "YWRp",
                     "client_info": SENT_INFO}
    assert remote._session.posted[-1] == {"identifier": identifier,
                                          "adi_pb": "YWRp"}
    assert headers["X-Apple-I-MD"] == "otp"
    assert headers["X-MMe-Client-Info"] == SENT_INFO


def test_apple_hears_a_current_mac_instead_of_the_servers_outdated_one(remote):
    """The provisioning requests go out from here. The servers' macOS
    10.12.6 gets -23782 or the text-message route that never confirms
    (issues #3, #7) - so a current Mac, with the user agent that fits it,
    from the URL bag on."""
    remote.headers()
    steps = [entry for entry in remote.log if entry[0] == "apple"]
    assert [s[1:3] for s in steps] == [
        ("GET", "https://gsa.apple.com/grandslam/GsService2/lookup"),
        ("POST", "https://gsa.apple.com/start"),
        ("POST", "https://gsa.apple.com/finish")]
    for *_, headers in steps:
        assert headers["X-MMe-Client-Info"] == SENT_INFO
        assert headers["User-Agent"] == SENT_UA
    for *_, headers in steps[1:]:
        assert headers["X-Mme-Device-Id"]


def test_a_server_naming_a_current_mac_is_believed(remote):
    """Spelled the way the edge lets through: <macOS;…> gets HTTP 503."""
    remote._session = _Server(
        "<Mac16,1> <macOS;26.6;25F84> <com.apple.AuthKit/1 (com.apple.akd/1.0)>",
        "akd/1.0 CFNetwork/3826.600.41 Darwin/25.6.0")
    assert remote.client_info() == ("<Mac16,1> <Mac OS X;26.6;25F84> "
                                    "<com.apple.AuthKit/1 (com.apple.akd/1.0)>")
    assert remote.user_agent() == "akd/1.0 CFNetwork/3826.600.41 Darwin/25.6.0"


def test_config_toml_has_the_last_word(remote):
    """For when Apple changes the rules again before an update is out."""
    provider = anisette.RemoteV3Provider(
        SERVER, client_info="<Mac18,1> <macOS;28.0;27A1> <com.apple.AuthKit/1 "
                            "(com.apple.akd/1.0)>",
        user_agent="akd/1.0 CFNetwork/4000 Darwin/28.0.0")
    provider._session = _Server()
    assert provider.client_info() == ("<Mac18,1> <Mac OS X;28.0;27A1> "
                                      "<com.apple.AuthKit/1 (com.apple.akd/1.0)>")
    assert provider.user_agent() == "akd/1.0 CFNetwork/4000 Darwin/28.0.0"


def test_a_device_provisioned_as_another_mac_is_provisioned_anew(remote):
    """1.4.0 provisioned as the server's 10.12.6 Mac and kept no client
    info - Apple has to meet the current Mac from the provisioning on."""
    anisette.REMOTE_STATE_FILE.write_text(json.dumps(
        {SERVER: {"identifier": "AAAAAAAAAAAAAAAAAAAAAA==", "adi_pb": "b2xk"}}))
    remote.headers()
    assert len(remote.sockets) == 1
    state = json.loads(anisette.REMOTE_STATE_FILE.read_text())[SERVER]
    assert state["adi_pb"] == "YWRp" and state["client_info"] == SENT_INFO


def test_two_factor_requests_carry_the_routing_info(remote):
    """Without X-Apple-I-MD-RINFO Apple takes the code but asks for another
    one on the next handshake (au=trustedDeviceSecondaryAuth again)."""
    client = GSAClient(remote)
    headers = client._two_factor_headers({"adsid": "a", "GsIdmsToken": "t"})
    assert headers["X-Apple-I-MD-RINFO"] == "17106176"
    assert headers["X-Apple-I-MD-M"] == "machine"


def test_the_text_message_route_keeps_the_user_agent_that_fits(remote):
    """It used to send a fixed macOS 14 user agent next to the server's
    10.12 client info - and got HTTP 403 for /auth and verify/phone."""
    headers = GSAClient(remote)._sms_headers({"adsid": "a", "GsIdmsToken": "t"})
    assert headers["User-Agent"] == SENT_UA
    assert headers["X-MMe-Client-Info"] == SENT_INFO
    assert headers["Content-Type"] == "application/json"


def test_the_handshake_leaves_the_routing_info_out(remote):
    """As isideload - only the two-factor requests carry it."""
    cpd = GSAClient(remote)._cpd()
    assert "X-Apple-I-MD-RINFO" not in cpd
    assert cpd["X-Apple-I-MD-M"] == "machine"


def test_the_websocket_trusts_certifi_without_system_cas(monkeypatch):
    """Issue #6: the Linux build's OpenSSL (Ubuntu's) finds no CAs on Arch
    or CachyOS. The provisioning WebSocket must still verify the server -
    against certifi's roots, as the HTTP requests do."""
    import ssl

    from websockets.sync import client

    monkeypatch.setattr(ssl.SSLContext, "load_default_certs",
                        lambda self, purpose=None: None)
    seen = []
    monkeypatch.setattr(client, "connect",
                        lambda url, **kwargs: seen.append(kwargs) or "ws")

    assert anisette._connect_websocket("wss://ani.example/v3/x", 5) == "ws"
    ctx = seen[0]["ssl"]
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    assert ctx.get_ca_certs()

    anisette._connect_websocket("ws://ani.example/v3/x", 5)
    assert "ssl" not in seen[1]       # websockets refuses ssl= for ws://


def test_a_second_run_does_not_provision_again(remote):
    first = remote.headers()
    again = anisette.RemoteV3Provider(SERVER, connect=remote._connect)
    again._session = _Server()
    second = again.headers()
    assert len(remote.sockets) == 1
    assert first["X-Mme-Device-Id"] == second["X-Mme-Device-Id"]


def test_a_forgotten_provisioning_is_redone_once(remote):
    """-45061: the server no longer knows the adi.pb."""
    remote.headers()
    remote._session.header_answers = [
        {"result": "GetHeadersError", "message": "ADI error -45061"}]
    assert remote.headers()["X-Apple-I-MD"] == "otp"
    assert len(remote.sockets) == 2


def test_a_server_error_says_so(remote):
    remote._session.header_answers = [
        {"result": "GetHeadersError", "message": "boom"}]
    with pytest.raises(AppleError, match="boom"):
        remote.headers()


def test_forget_device_drops_the_server_state_too(remote, monkeypatch):
    monkeypatch.setattr(anisette, "_shared_ani", None)
    monkeypatch.setattr(anisette, "PROVISIONING_FILE",
                        anisette.ANISETTE_DIR / "p.bin")
    monkeypatch.setattr(anisette, "DEVICE_FILE", anisette.ANISETTE_DIR / "d.json")
    remote.headers()
    anisette.forget_device()
    assert not anisette.REMOTE_STATE_FILE.exists()


def test_an_unreachable_server_is_named():
    provider = anisette.RemoteV3Provider("https://ani.invalid", timeout=0.01)

    class Down:
        def get(self, *a, **kw):
            raise OSError("no route")

    provider._session = Down()
    with pytest.raises(AppleError, match="ani.invalid"):
        provider.client_info()


def test_gsa_sends_the_user_agent_that_fits_the_client_info(remote,
                                                           monkeypatch):
    sent = {}

    def capture(session, method, url, *, client_info, headers=None, **kw):
        sent.update(headers or {})
        raise RuntimeError("stop here")

    client = GSAClient(remote)
    monkeypatch.setattr("modstaller.apple.http.gsa_request", capture)
    monkeypatch.setattr(remote, "headers", lambda: {"X-Apple-I-MD": "otp"})
    with pytest.raises(RuntimeError, match="stop here"):
        client._request({"o": "init"})
    assert sent["User-Agent"] == SENT_UA
    assert sent["X-MMe-Client-Info"] == SENT_INFO
