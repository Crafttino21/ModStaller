"""The log: what goes in, what doesn't - and what goes out live."""

from __future__ import annotations

import asyncio
import logging

import pytest

from modstaller import logbook
from modstaller import server as srv
from modstaller.errors import DeviceNotFound
from modstaller.logbook import SUCCESS, Logbook

from test_server import Wire


@pytest.fixture
def book():
    """A fresh logbook on the root logger, as setup() attaches it."""
    b = Logbook()
    root = logging.getLogger()
    own = logging.getLogger("modstaller")
    old_level = own.level
    own.setLevel(logging.INFO)
    root.addHandler(b)
    yield b
    root.removeHandler(b)
    own.setLevel(old_level)


def _messages(book, level=None):
    return [e.message for e in book.history() if level is None or e.level == level]


def test_multiline_messages_become_separate_entries(book):
    logbook.log(logbook.INSTALL, "\nIPA read:\n  Name  X\n")
    assert _messages(book) == ["IPA read:", "  Name  X"]


def test_levels_and_sources(book):
    logbook.log(logbook.JIT, "done", SUCCESS)
    logging.getLogger("pymobiledevice3.lockdown").warning("flaky")
    jit, lib = book.history()
    assert (jit.level, jit.source) == ("success", "jit")
    assert (lib.level, lib.source) == ("warn", "device")


def test_listeners_get_entries_live_and_can_leave(book):
    got = []
    leave = book.subscribe(got.append)
    logbook.log(logbook.SYSTEM, "one")
    leave()
    logbook.log(logbook.SYSTEM, "two")
    assert [e.message for e in got] == ["one"]


def test_history_is_bounded():
    b = Logbook(keep=3)
    for i in range(5):
        b.emit(logging.makeLogRecord({"msg": str(i), "levelno": logging.INFO}))
    assert [e.message for e in b.history()] == ["2", "3", "4"]
    assert [e.message for e in b.history(limit=1)] == ["4"]


def test_apple_id_is_masked():
    assert logbook.mask_apple_id("santino@example.de") == "sa***@example.de"
    assert "santino" not in logbook.mask_apple_id("santino")


# -- Server actions ------------------------------------------------------------


async def test_action_logs_start_and_result(book, monkeypatch):
    async def fake_install(server, job, params):
        job.log("Signieren …")
        return {"name": "Amethyst", "bundleId": "net.x.T", "daysValid": 6.9,
                "transport": "lockdown", "strippedExtensions": False}
    monkeypatch.setitem(srv.METHODS, "install", fake_install)

    w = Wire()
    w.server.book = book
    w.call(1, "install", path="/home/u/Downloads/amethyst.ipa")
    await w.reply_to(1)

    assert _messages(book)[0] == "Installation: amethyst.ipa"
    assert "Signieren …" in _messages(book)
    [done] = _messages(book, "success")
    assert done.startswith("Amethyst installiert als net.x.T - 7 Tage gültig")
    assert {e.job for e in book.history()} == {1}


async def test_failed_action_is_logged_as_error(book, monkeypatch):
    async def boom(server, job, params):
        raise DeviceNotFound("Kein iPhone gefunden.")
    monkeypatch.setitem(srv.METHODS, "jit", boom)

    w = Wire()
    w.call(2, "jit", bundleId="net.x")
    await w.reply_to(2)
    assert _messages(book, "error") == ["JIT fehlgeschlagen: Kein iPhone gefunden."]


async def test_password_never_reaches_the_log(book, monkeypatch):
    async def fake_login(server, job, params):
        return {"teams": []}
    monkeypatch.setitem(srv.METHODS, "login", fake_login)

    w = Wire()
    w.call(3, "login", appleId="santino@example.de", password="geheim123")
    await w.reply_to(3)
    text = " ".join(_messages(book))
    assert "geheim123" not in text and "santino@" not in text
    assert "sa***@example.de" in text


async def test_polling_is_not_logged(book):
    w = Wire()
    w.call(4, "version")
    await w.reply_to(4)
    assert book.history() == []


async def test_entries_go_live_to_the_ui(monkeypatch):
    b = Logbook()
    w = Wire()
    w.server._unsubscribe()                 # don't hang on the global logbook
    w.server.book = b
    b.subscribe(lambda e: w.server.notify("log.entry", e.as_dict()))
    b.emit(logging.makeLogRecord({"msg": "hallo", "levelno": logging.INFO,
                                  "source": "system"}))
    msg = await w.next()
    assert msg["method"] == "log.entry"
    assert msg["params"]["message"] == "hallo"


# -- Device events ---------------------------------------------------------------


class _Srv:
    def __init__(self):
        self.seen_devices = {}


def _dev(dev_mode=True):
    return {"name": "iPhone von S", "model": "iPhone 16 Pro Max",
            "iosVersion": "27.0", "developerMode": dev_mode}


def test_device_connect_mode_change_and_disconnect(book):
    s = _Srv()
    srv._log_device_changes(s, ["A"], _dev(False), "")
    srv._log_device_changes(s, ["A"], _dev(False), "")      # unchanged: quiet
    srv._log_device_changes(s, ["A"], _dev(True), "")
    srv._log_device_changes(s, [], None, "")
    assert _messages(book) == [
        "iPhone verbunden: iPhone von S · iPhone 16 Pro Max · iOS 27.0",
        "Entwicklermodus ist aus - sideloadete Apps starten so nicht.",
        "Entwicklermodus ist jetzt an.",
        "iPhone von S getrennt",
    ]


def test_locked_phone_is_reported_once(book):
    s = _Srv()
    for _ in range(3):
        srv._log_device_changes(s, ["A"], None, "Das iPhone ist gesperrt.")
    assert _messages(book, "warn") == [
        "iPhone angesteckt, aber nicht bereit: Das iPhone ist gesperrt."]
