"""Das Protokoll zwischen Oberflaeche und Backend.

Die Oberflaeche sieht nur, was hier ueber die Leitung geht. Eine zerrissene
Zeile, eine verschluckte Antwort oder ein ``print`` im falschen Kanal - und
sie haengt, ohne dass irgendwo ein Fehler steht.
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
    """Ein Server an einer Pipe, gelesen wie von der Oberflaeche."""

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
                    raise TimeoutError("keine Nachricht vom Server")
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
    w.call(1, "gibtsnicht")
    reply = await w.reply_to(1)
    assert reply["error"]["code"] == srv.METHOD_NOT_FOUND


async def test_garbage_gets_a_parse_error():
    w = Wire()
    w.send("{kaputt")
    assert (await w.next())["error"]["code"] == srv.PARSE_ERROR


async def test_user_errors_keep_their_message(monkeypatch):
    async def boom(server, job, params):
        raise DeviceNotFound("Kein iPhone gefunden.")
    monkeypatch.setitem(srv.METHODS, "boom", boom)

    w = Wire()
    w.call(7, "boom")
    err = (await w.reply_to(7))["error"]
    assert err == {"code": srv.USER_ERROR, "message": "Kein iPhone gefunden."}


async def test_missing_parameter_is_reported():
    w = Wire()
    w.call(2, "install")
    assert (await w.reply_to(2))["error"]["code"] == srv.INVALID_PARAMS


async def test_progress_and_log_carry_the_job_id(monkeypatch):
    async def work(server, job, params):
        async def inner():
            job.log("Signieren …")
            job.progress(50)
            return "fertig"
        return await job.isolated(inner)
    monkeypatch.setitem(srv.METHODS, "work", work)

    w = Wire()
    w.call("j1", "work")
    seen = [await w.next() for _ in range(3)]
    assert seen[0] == {"jsonrpc": "2.0", "method": "log",
                       "params": {"job": "j1", "text": "Signieren …"}}
    assert seen[1]["params"] == {"job": "j1", "pct": 50}
    assert seen[2]["result"] == "fertig"


async def test_cancel_stops_isolated_work(monkeypatch):
    """JIT wartet, bis sich die App abmeldet - ohne Abbruch notfalls ewig."""
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
    """Die Pipeline ruft Apple synchron auf - der Server muss trotzdem antworten."""
    import threading
    release = threading.Event()

    async def blocking(server, job, params):
        async def inner():
            release.wait(10)   # blockiert den Loop des Jobs, nicht den Server
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
        return object()

    class FakeApi:
        def __init__(self, session, ani):
            pass

        def list_teams(self):
            return ["Team Santino [T1]"]

    monkeypatch.setattr("modstaller.apple.session.login", fake_login)
    monkeypatch.setattr("modstaller.apple.devservices.DeveloperServices",
                        FakeApi)
    monkeypatch.setattr(srv, "_anisette", lambda: None)

    w = Wire()
    w.call(1, "login", appleId="a@b.de", password="geheim")
    while True:
        msg = await w.next()
        if msg.get("method") == "prompt.2fa":
            break
    w.send({"jsonrpc": "2.0", "id": msg["id"], "result": "123456"})

    reply = await w.reply_to(1)
    assert got["code"] == "123456"
    assert reply["result"] == {"teams": ["Team Santino [T1]"]}


def test_stray_prints_do_not_reach_the_protocol():
    code = (
        "import os, sys\n"
        "from modstaller.server import take_stdout\n"
        "out = take_stdout()\n"
        "print('laut')\n"
        "os.system('echo aus-c')\n"
        "os.write(out, b'{\"ok\": 1}\\n')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, timeout=30)
    assert proc.stdout == '{"ok": 1}\n'
    assert "laut" in proc.stderr and "aus-c" in proc.stderr


@pytest.mark.parametrize("value, expected", [
    (b"\x00", None),
    (__import__("pathlib").Path("/x.ipa"), "/x.ipa"),
])
def test_unusual_values_serialise(value, expected):
    assert srv._jsonable(value) == expected


async def test_serve_reads_lines_until_eof():
    """stdin wird in einem Thread gelesen - das geht auch unter Windows."""
    r, w = os.pipe()
    wire = Wire()
    with os.fdopen(r, "rb") as stream:
        serving = asyncio.create_task(wire.server.serve(stream))
        os.write(w, b'{"jsonrpc":"2.0","id":1,"method":"version"}\n')
        assert "result" in await wire.reply_to(1)
        os.close(w)                       # Oberflaeche weg
        await asyncio.wait_for(serving, 5)
