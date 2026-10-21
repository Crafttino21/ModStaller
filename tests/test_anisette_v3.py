"""The anisette-v3 server as provider (default since 1.4.0-rc.6, issue #4).

The server runs the ADI, this side keeps the state and talks to Apple. What
matters: the requests to Apple go out from here, the state survives a
restart, and the server's client info and user agent are what GSA hears.
"""

from __future__ import annotations

import json
import plistlib
from base64 import b64decode

import pytest

from modstaller.apple import anisette
from modstaller.apple.gsa import GSAClient
from modstaller.errors import AppleError

SERVER = "https://ani.example"
CLIENT_INFO = ("<MacBookPro13,3> <Mac OS X;10.12.6;16G29> "
               "<com.apple.AuthKit/1 (com.apple.akd/1.0)>")
USER_AGENT = "akd/1.0 CFNetwork/811.5.4 Darwin/16.7.0"


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

    def __init__(self):
        self.header_answers: list[dict] = []
        self.posted: list[dict] = []

    def get(self, url, timeout=None):
        assert url == f"{SERVER}/v3/client_info"
        return _Response({"client_info": CLIENT_INFO, "user_agent": USER_AGENT})

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
    assert state == {"identifier": identifier, "adi_pb": "YWRp"}
    assert remote._session.posted[-1] == state
    assert headers["X-Apple-I-MD"] == "otp"
    assert headers["X-MMe-Client-Info"] == CLIENT_INFO


def test_apple_hears_the_servers_device_not_ours(remote):
    """The provisioning requests go out from here - with the client info
    and user agent the server names."""
    remote.headers()
    steps = [entry for entry in remote.log
             if entry[0] == "apple" and entry[1] == "POST"]
    assert [s[2] for s in steps] == ["https://gsa.apple.com/start",
                                     "https://gsa.apple.com/finish"]
    for *_, headers in steps:
        assert headers["X-MMe-Client-Info"] == CLIENT_INFO
        assert headers["User-Agent"] == USER_AGENT
        assert headers["X-Mme-Device-Id"]


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
    assert sent["User-Agent"] == USER_AGENT
    assert sent["X-MMe-Client-Info"] == CLIENT_INFO
