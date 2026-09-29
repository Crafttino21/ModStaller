"""The protocol between the interface and the backend.

The interface only sees what goes over the wire here. A torn line, a
swallowed reply or a ``print`` on the wrong channel - and it hangs without
an error showing up anywhere.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys

import pytest

from modstaller import server as srv
from modstaller.errors import DeviceNotFound


class Wire:
    """A server on a pipe, read the way the interface reads it."""

    def __init__(self) -> None:
        self._r, w = os.pipe()
        os.set_blocking(self._r, False)
        self.server = srv.Server(w)
        self.server.loop = asyncio.get_running_loop()
        self._buf = b""

    def send(self, msg: dict | str) -> None:
        line = msg if isinstance(msg, str) else json.dumps(msg)
        self.server.handle_line(line.encode())

    def call(self, req_id, method: str, **params) -> None:
        self.send({"jsonrpc": "2.0", "id": req_id, "method": method,
                   "params": params})

    async def next(self, timeout: float = 5.0) -> dict:
        deadline = asyncio.get_running_loop().time() + timeout
        while b"\n" not in self._buf:
            try:
                self._buf += os.read(self._r, 65536)
            except BlockingIOError:
                if asyncio.get_running_loop().time() > deadline:
                    raise TimeoutError("no message from the server")
                await asyncio.sleep(0.01)
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    async def reply_to(self, req_id, timeout: float = 5.0) -> dict:
        while True:
            msg = await self.next(timeout)
            if msg.get("id") == req_id and "method" not in msg:
                return msg


async def test_unknown_method_is_an_error_not_silence():
    w = Wire()
    w.call(1, "doesnotexist")
    reply = await w.reply_to(1)
    assert reply["error"]["code"] == srv.METHOD_NOT_FOUND


async def test_garbage_gets_a_parse_error():
    w = Wire()
    w.send("{broken")
    assert (await w.next())["error"]["code"] == srv.PARSE_ERROR


async def test_user_errors_keep_their_message(monkeypatch):
    async def boom(server, job, params):
        raise DeviceNotFound("No iPhone found.")
    monkeypatch.setitem(srv.METHODS, "boom", boom)

    w = Wire()
    w.call(7, "boom")
    err = (await w.reply_to(7))["error"]
    assert err == {"code": srv.USER_ERROR, "message": "No iPhone found.",
                   "data": {"kind": "DeviceNotFound", "exitCode": 4}}


async def test_errors_say_what_kind_they_are(monkeypatch):
    """The refresh in the tray has nobody reading the message - it decides
    by the kind whether to wait for the iPhone or ask for a new sign-in."""
    from modstaller.errors import AppleRateLimited, InteractionRequired

    errors = iter([InteractionRequired("2FA needed."),
                   AppleRateLimited("Slow down."), KeyError("x")])

    async def boom(server, job, params):
        raise next(errors)
    monkeypatch.setitem(srv.METHODS, "boom", boom)

    w = Wire()
    w.call(1, "boom")
    assert (await w.reply_to(1))["error"]["data"] == {
        "kind": "InteractionRequired", "exitCode": 6}
    w.call(2, "boom")
    assert (await w.reply_to(2))["error"]["data"]["kind"] == "AppleRateLimited"
    w.call(3, "boom")
    unexpected = (await w.reply_to(3))["error"]
    assert unexpected["code"] == srv.INTERNAL_ERROR
    assert "data" not in unexpected


def test_an_app_says_whether_it_can_be_renewed_unattended(tmp_path):
    from modstaller.apple import session as session_mod
    from modstaller.state import store

    ipa = tmp_path / "a.ipa"
    ipa.write_bytes(b"")
    rec = store.InstallRecord(
        bundle_id="b.X", original_bundle_id="b", name="A", team_id="T",
        udid="U", source_ipa=str(ipa), app_id_id="1", profile_path="",
        expires_at=0.0, installed_at=0.0, adsid="a")
    app = srv._app_dict(rec)
    assert app["udid"] == "U"
    assert app["accountReady"] is False and app["sourceMissing"] is False

    session_mod.Session(adsid="a", idms_token="i", identity_token="t",
                        created_at=0.0, app_token="x").save()
    assert srv._app_dict(rec)["accountReady"] is True


async def test_missing_parameter_is_reported():
    w = Wire()
    w.call(2, "install")
    assert (await w.reply_to(2))["error"]["code"] == srv.INVALID_PARAMS


async def test_progress_and_log_carry_the_job_id(monkeypatch):
    async def work(server, job, params):
        async def inner():
            job.log("Signing …")
            job.progress(50)
            return "done"
        return await job.isolated(inner)
    monkeypatch.setitem(srv.METHODS, "work", work)

    w = Wire()
    w.call("j1", "work")
    seen = [await w.next() for _ in range(3)]
    assert seen[0] == {"jsonrpc": "2.0", "method": "log",
                       "params": {"job": "j1", "text": "Signing …"}}
    assert seen[1]["params"] == {"job": "j1", "pct": 50}
    assert seen[2]["result"] == "done"


async def test_cancel_stops_isolated_work(monkeypatch):
    """JIT waits until the app detaches - without cancel, possibly forever."""
    started = asyncio.Event()
    loop = asyncio.get_running_loop()

    async def forever(server, job, params):
        async def inner():
            loop.call_soon_threadsafe(started.set)
            await asyncio.sleep(3600)
        return await job.isolated(inner)
    monkeypatch.setitem(srv.METHODS, "forever", forever)

    w = Wire()
    w.call("long", "forever")
    await asyncio.wait_for(started.wait(), 5)
    w.call("c", "cancel", id="long")

    replies = {}
    while len(replies) < 2:
        msg = await w.next()
        replies[msg["id"]] = msg
    assert replies["c"]["result"] is True
    assert replies["long"]["error"]["code"] == srv.CANCELLED


async def test_status_is_answered_while_isolated_work_blocks(monkeypatch):
    """The pipeline calls Apple synchronously - the server must still reply."""
    import threading
    release = threading.Event()

    async def blocking(server, job, params):
        async def inner():
            release.wait(10)   # blocks the job's loop, not the server
        return await job.isolated(inner)
    monkeypatch.setitem(srv.METHODS, "blocking", blocking)

    w = Wire()
    w.call("b", "blocking")
    w.call("v", "version")
    assert "result" in await w.reply_to("v", timeout=3)
    release.set()
    await w.reply_to("b")


async def test_login_asks_the_ui_for_the_2fa_code(monkeypatch):
    got = {}

    def fake_login(apple_id, password, ani, code_prompt=None, debug=False):
        got["code"] = code_prompt()
        return type("S", (), {"adsid": "a"})()

    class FakeApi:
        def __init__(self, session, ani):
            pass

        def list_teams(self):
            return [type("T", (), {"team_id": "T1",
                                   "__str__": lambda _: "Team Santino [T1]"})()]

    monkeypatch.setattr("modstaller.apple.session.login", fake_login)
    monkeypatch.setattr("modstaller.apple.devservices.DeveloperServices",
                        FakeApi)
    monkeypatch.setattr(srv, "_anisette", lambda: None)

    w = Wire()
    w.call(1, "login", appleId="a@b.de", password="secret")
    while True:
        msg = await w.next()
        if msg.get("method") == "prompt.2fa":
            break
    # With several accounts the dialog has to say whose code it is.
    assert msg["params"] == {"appleId": "a@b.de"}
    w.send({"jsonrpc": "2.0", "id": msg["id"], "result": "123456"})

    reply = await w.reply_to(1)
    assert got["code"] == "123456"
    assert reply["result"] == {"teams": ["Team Santino [T1]"]}


def test_stray_prints_do_not_reach_the_protocol():
    code = (
        "import os, sys\n"
        "from modstaller.server import take_stdout\n"
        "out = take_stdout()\n"
        "print('loud')\n"
        "os.system('echo from-c')\n"
        "os.write(out, b'{\"ok\": 1}\\n')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=30)
    assert proc.stdout == '{"ok": 1}\n'
    assert "loud" in proc.stderr and "from-c" in proc.stderr


@pytest.mark.parametrize("value, expected", [
    (b"\x00", None),
    # str(), not "/x.ipa": on Windows it becomes "\\x.ipa".
    (__import__("pathlib").Path("/x.ipa"), str(__import__("pathlib").Path("/x.ipa"))),
])
def test_unusual_values_serialise(value, expected):
    assert srv._jsonable(value) == expected


async def test_serve_reads_lines_until_eof():
    """stdin is read in a thread - that works on Windows too."""
    r, w = os.pipe()
    wire = Wire()
    with os.fdopen(r, "rb") as stream:
        serving = asyncio.create_task(wire.server.serve(stream))
        os.write(w, b'{"jsonrpc":"2.0","id":1,"method":"version"}\n')
        assert "result" in await wire.reply_to(1)
        os.close(w)                       # interface gone
        await asyncio.wait_for(serving, 5)


async def test_first_name_is_looked_up_once_in_the_background(monkeypatch):
    """On the first start after the update the session has no first name
    yet. The status must not wait for Apple - it starts one lookup."""
    import asyncio
    looked_up = []

    def fake_api(adsid=None):
        class Api:
            def list_teams(self):
                looked_up.append(adsid)
                return []
        return Api()

    monkeypatch.setattr(srv, "_api", fake_api)
    w = Wire()
    srv._look_up_first_name(w.server, "a")
    srv._look_up_first_name(w.server, "a")  # second poll: no second lookup
    srv._look_up_first_name(w.server, "b")  # but every account gets one
    for _ in range(50):
        if len(looked_up) == 2:
            break
        await asyncio.sleep(0.01)
    assert sorted(looked_up) == ["a", "b"]


async def test_the_device_identity_stays_while_other_accounts_need_it():
    from modstaller.apple import session as session_mod
    for adsid, at in (("a", 1), ("b", 2)):
        session_mod.Session(adsid=adsid, idms_token="i", identity_token="t",
                            created_at=at, app_token="x").save()
    w = Wire()
    w.call(1, "logout", account="a", forgetDevice=True)
    assert "error" in await w.reply_to(1)
    assert len(session_mod.list_accounts()) == 2

    w.call(2, "logout", account="a")
    assert (await w.reply_to(2))["result"] is True
    assert [s.adsid for s in session_mod.list_accounts()] == ["b"]


async def test_status_names_a_missing_usb_service_and_logs_it_once(monkeypatch):
    """Without Apple Devices/iTunes on Windows no iPhone is ever listed. The
    status says why, and the logbook says it once - not every poll."""
    from modstaller.errors import UsbServiceUnavailable

    missing = True

    async def devices():
        if missing:
            raise UsbServiceUnavailable("service missing")
        return []
    monkeypatch.setattr("modstaller.device.connection.list_devices", devices)
    logged = []
    monkeypatch.setattr(srv.logbook, "log",
                        lambda source, message, *a, **k: logged.append(message))

    w = Wire()
    first = await srv._status(w.server, None, {})
    await srv._status(w.server, None, {})
    assert first["usbService"] == "missing"
    assert first["deviceAttached"] is False
    assert first["attached"] == []
    assert first["error"] == "service missing"
    assert len(logged) == 1

    missing = False
    back = await srv._status(w.server, None, {})
    assert back["usbService"] == "ok" and not back["error"]
    assert len(logged) == 2
