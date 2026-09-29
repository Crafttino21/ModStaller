"""The JIT protocol: framing, register reading, breakpoint detection.

On devices with TXM/SPTM, JIT is no longer a one-off unlock but a
conversation: the app asks via breakpoint for a region to be prepared, the
debugger writes into every page and answers with the address. If one link in
this chain fails, the app silently hangs on launch - so each one is tested
individually.
"""

from __future__ import annotations

import pytest

from modstaller.device.gdb import (
    REG_PC, REG_X0, REG_X1, REG_X16, GdbClient, StopReply, frame, int_to_le_hex,
    le_hex_to_int,
)
from modstaller.device.jit import PAGE_SIZE, has_txm, touch_pages


class FakeConn:
    """Delivers prepared segments - fragmented too, and with separate
    acknowledgements, just as they arrive over the wire."""

    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)
        self.sent: list[bytes] = []

    async def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    async def recv_any(self, length: int = 4096) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""


# -- Framing ---------------------------------------------------------------


def test_checksum_matches_known_packet():
    """Cross-check against a value that is hard-wired elsewhere."""
    assert frame("QStartNoAckMode") == b"$QStartNoAckMode#b0"
    assert frame("D") == b"$D#44"


def test_checksum_is_computed_not_guessed():
    """With vAttach the checksum depends on the process number."""
    assert frame("vAttach;1") != frame("vAttach;2")


def test_register_encoding_roundtrip():
    for value in (0, 1, 0x4000, 0x1029B1FB8, 2 ** 48 - 1):
        assert le_hex_to_int(int_to_le_hex(value)) == value


# -- Reading replies -------------------------------------------------------


STOP = ("T11thread:1f4;00:0000000000000000;01:0040000000000000;"
        "10:0100000000000000;20:b81f9b0201000000;")


def test_stop_reply_extracts_registers():
    reply = StopReply(STOP)
    assert reply.thread == "1f4"
    assert reply.signal == "11"
    assert reply.register(REG_X16) == 1
    assert reply.register(REG_X1) == 0x4000
    assert reply.register(REG_PC) == 0x1029B1FB8
    assert reply.register(REG_X0) == 0
    assert reply.is_stop


@pytest.mark.parametrize("raw, expected", [
    ("T11thread:1;", True),
    ("S05", True),
    ("E01", False),
    ("OK", False),
    ("", False),
])
def test_stop_detection(raw, expected):
    assert StopReply(raw).is_stop is expected


@pytest.mark.asyncio
async def test_acknowledgement_is_not_mistaken_for_a_reply():
    gdb = GdbClient(FakeConn([b"+", b"$OK#9a"]))
    assert await gdb.send("QStartNoAckMode") == "OK"


@pytest.mark.asyncio
async def test_packet_split_across_segments_is_reassembled():
    gdb = GdbClient(FakeConn([b"+$T11thr", b"ead:1f4", b";#aa"]))
    assert StopReply(await gdb.send("c")).thread == "1f4"


@pytest.mark.asyncio
async def test_silence_does_not_hang_forever():
    gdb = GdbClient(FakeConn([]), timeout=0.2)
    assert await gdb.send("c") == ""


@pytest.mark.asyncio
async def test_a_batch_goes_out_in_one_piece():
    """One round trip per page is what made large regions take minutes."""
    conn = FakeConn([b"$OK#9a$OK", b"#9a$E01#a6"])
    gdb = GdbClient(conn)
    assert await gdb.send_batch(["M1,1:00", "M2,1:00", "M3,1:00"]) == \
        ["OK", "OK", "E01"]
    assert len(conn.sent) == 1


@pytest.mark.asyncio
async def test_batches_are_split():
    conn = FakeConn([b"$OK#9a"] * 5)
    await GdbClient(conn).send_batch(["D"] * 5, batch=2)
    assert len(conn.sent) == 3


# -- Which devices need the conversation -----------------------------------


@pytest.mark.parametrize("product, version, expected", [
    ("iPhone14,2", "26.0", True),       # 13 Pro, A15: first with TXM
    ("iPhone13,4", "26.1", False),      # 12 Pro Max, A14
    ("iPhone17,1", "18.6", False),      # TXM, but iOS 18 doesn't lock JIT
    ("iPad14,5", "26.0", True),         # iPad Pro M2
    ("iPad13,8", "26.0", False),        # iPad Pro M1
    ("iPhone13,4", "27.0", True),       # iOS 27: everything
    ("iPad8,11", "27.0", False),        # ... except these two
    ("?", "26.0", True),                # unknown: rather talk
    ("iPhone14,2", "?", True),
])
def test_txm_detection(product, version, expected):
    assert has_txm(product, version) is expected


# -- The conversation (jit_host.js against a simulated debugserver) --------

from modstaller.device.jit import JitResult, ScriptHost  # noqa: E402
from modstaller.errors import DeviceError  # noqa: E402

BRK_F00D = 0xD43E01A0        # brk #0xf00d
BRK_69 = 0xD4200D20          # brk #0x69
NOP = 0xD503201F


class FakeDebugger:
    """Plays debugserver: answers the raw packets the script sends."""

    ALLOCATED = 0x200000000

    def __init__(self, stops: list[str], code: dict[int, int],
                 memory: dict[int, bytes] | None = None):
        self.stops = list(stops)
        self.code = code
        self.memory = memory or {}
        self.sent: list[str] = []
        self.registers: dict[int, int] = {}
        self.writes: list[tuple[int, bytes]] = []
        self.allocations: list[int] = []
        self.batches: list[int] = []
        self.detached = False

    async def send(self, payload: str, *, expect_reply: bool = True,
                   timeout: float | None = None) -> str:
        self.sent.append(payload)
        reply = self._answer(payload)
        return reply if expect_reply else ""

    async def send_batch(self, payloads: list[str], *, batch: int = 128):
        self.batches.append(len(payloads))
        return [self._answer(p) for p in payloads]

    def _answer(self, payload: str) -> str:
        if payload == "c" or payload.startswith("vCont"):
            return self.stops.pop(0) if self.stops else ""
        if payload == "D":
            self.detached = True
            return "OK"
        if payload.startswith("_M"):
            size = int(payload[2:].split(",")[0], 16)
            self.allocations.append(size)
            return f"{self.ALLOCATED:x}"
        if payload.startswith("m"):
            address, length = (int(v, 16) for v in payload[1:].split(","))
            if address in self.code:
                return self.code[address].to_bytes(4, "little").hex()
            if address in self.memory:
                return self.memory[address][:length].hex()
            return "42" * length
        if payload.startswith("M"):
            where, data = payload[1:].split(":")
            self.writes.append((int(where.split(",")[0], 16),
                                bytes.fromhex(data)))
            return "OK"
        if payload.startswith("P"):
            number, value = payload[1:].split(";")[0].split("=")
            self.registers[int(number, 16)] = le_hex_to_int(value)
            return "OK"
        return ""


def _stop(pc: int, signal: str = "05", **regs: int) -> str:
    numbers = {"x0": 0x00, "x1": 0x01, "x16": 0x10}
    body = "".join(f"{numbers[k]:02x}:{int_to_le_hex(v)};"
                   for k, v in regs.items())
    return f"T{signal}thread:1f4;{body}20:{int_to_le_hex(pc)};"


async def _talk(gdb: FakeDebugger, **kwargs) -> tuple[JitResult, list[str]]:
    said: list[str] = []
    result = JitResult("x", 1)
    await ScriptHost(gdb, result, said.append, **kwargs).run()
    return result, said


@pytest.mark.asyncio
async def test_region_at_the_apps_address():
    gdb = FakeDebugger([_stop(0x1000, x16=1, x0=0x140000000,
                              x1=2 * PAGE_SIZE)], {0x1000: BRK_F00D})
    result, _said = await _talk(gdb)

    assert gdb.allocations == [], "nothing is allocated when an address is given"
    assert [a for a, _d in gdb.writes] == [0x140000000,
                                           0x140000000 + PAGE_SIZE]
    assert gdb.registers[REG_X0] == 0x140000000, "address goes back in x0"
    assert gdb.registers[REG_PC] == 0x1004, "the app must not stop there again"
    assert result.prepared_regions == 1
    assert result.prepared_bytes == 2 * PAGE_SIZE


@pytest.mark.asyncio
async def test_pages_keep_their_content():
    """What was read is written back - the access counts, not the content.
    Writing anything else would destroy code already in the region."""
    gdb = FakeDebugger([_stop(0x1000, x16=1, x0=0x140000000, x1=PAGE_SIZE)],
                       {0x1000: BRK_F00D})
    await _talk(gdb)
    assert gdb.writes == [(0x140000000, b"\x42")]


@pytest.mark.asyncio
async def test_zero_address_lets_the_debugger_choose():
    gdb = FakeDebugger([_stop(0x1000, x16=1, x0=0, x1=PAGE_SIZE)],
                       {0x1000: BRK_F00D})
    await _talk(gdb)
    assert gdb.allocations == [PAGE_SIZE]
    assert gdb.registers[REG_X0] == FakeDebugger.ALLOCATED


@pytest.mark.asyncio
async def test_detach_ends_the_conversation():
    gdb = FakeDebugger([_stop(0x1000, x16=0)], {0x1000: BRK_F00D})
    result, said = await _talk(gdb)
    assert gdb.detached and result.detached_cleanly
    assert result.notes == []
    assert any("JIT is in place" in s for s in said)


#: Modelled on what Amethyst sends: the old brk #0x69 (size in x0) mapped
#: onto PrepareRegion, plus a command that detaches after the first region.
EXTENSION = """
logLevel = LOG_INFO;
let detachAfterFirst = false;
legacyCommands[0x69] = function (brkResponse) {
    x1 = x0;
    x0 = 0;
    JIT26PrepareRegion(brkResponse);
    if (detachAfterFirst) {
        JIT26Detach();
    }
};
commands[3] = function (brkResponse) {
    detachAfterFirst = x0 != 0;
};
"""


@pytest.mark.asyncio
async def test_an_extension_from_the_app_really_runs():
    """The reason for the port: newer apps bring their own commands. Before,
    the script was accepted and ignored - the app then waited forever."""
    script = EXTENSION.encode() + b"\x00"
    gdb = FakeDebugger(
        [_stop(0x1000, x16=2, x0=0x5000, x1=len(script)),
         _stop(0x1000, x16=3, x0=1),
         _stop(0x2000, x0=0x400000)],
        {0x1000: BRK_F00D, 0x2000: BRK_69},
        memory={0x5000: script})
    result, said = await _talk(gdb)

    assert any("extension" in s for s in said)
    assert gdb.allocations == [0x400000], "size must come from x0"
    assert gdb.registers[REG_X0] == FakeDebugger.ALLOCATED
    assert result.prepared_regions == 1
    assert gdb.detached, "command 3 asked to detach after the first region"
    assert result.notes == []


@pytest.mark.asyncio
async def test_old_breakpoint_without_extension_answers_the_universal_marker():
    """Amethyst probes with brk #0x69 first and only goes on if x0 holds
    0x690000E0 - what StikDebug's "P0=E0000069" really puts there (P takes
    little-endian bytes). Anything else and the app refuses: "legacy
    script, not supported"."""
    gdb = FakeDebugger([_stop(0x2000, x0=0x400000)], {0x2000: BRK_69})
    result, _said = await _talk(gdb)
    assert gdb.allocations == []
    assert gdb.registers[REG_X0] & 0xFFFFFFFF == 0x690000E0
    assert result.prepared_regions == 0


@pytest.mark.asyncio
async def test_a_broken_extension_is_reported_not_fatal():
    script = b"this is not javascript(\x00"
    gdb = FakeDebugger([_stop(0x1000, x16=2, x0=0x5000, x1=len(script)),
                        _stop(0x1000, x16=0)],
                       {0x1000: BRK_F00D}, memory={0x5000: script})
    result, _said = await _talk(gdb)
    assert any("extension failed" in n for n in result.notes)
    assert result.detached_cleanly


@pytest.mark.asyncio
async def test_ordinary_signal_is_passed_on():
    """Otherwise the debugger swallows a crash of the app. The reply to
    vCont is already the next stop - no extra continue."""
    gdb = FakeDebugger([_stop(0x3000, signal="0b"), _stop(0x1000, x16=0)],
                       {0x3000: NOP, 0x1000: BRK_F00D})
    await _talk(gdb)
    assert "vCont;S0b:1f4" in gdb.sent
    assert gdb.sent.count("c") == 1
    assert gdb.detached


@pytest.mark.asyncio
async def test_unknown_command_is_noted():
    gdb = FakeDebugger([_stop(0x1000, x16=9)], {0x1000: BRK_F00D})
    result, _said = await _talk(gdb)
    assert "Skipped unknown command 9." in result.notes


@pytest.mark.asyncio
async def test_silence_and_exit_end_the_conversation():
    result, _said = await _talk(FakeDebugger([], {}))
    assert any("stopped reporting back" in n for n in result.notes)
    result, _said = await _talk(FakeDebugger(["W00"], {}))
    assert any("quit" in n for n in result.notes)


@pytest.mark.asyncio
async def test_a_connection_error_surfaces_as_itself():
    """Not as a JavaScript exception wrapping it."""
    class Broken(FakeDebugger):
        async def send(self, payload, **kwargs):
            raise DeviceError("cable pulled")

    with pytest.raises(DeviceError, match="cable pulled"):
        await _talk(Broken([], {}))


@pytest.mark.asyncio
async def test_verbose_passes_the_trace_on():
    gdb = FakeDebugger([_stop(0x1000, x16=0)], {0x1000: BRK_F00D})
    _result, said = await _talk(gdb, verbose=True)
    assert any("Breakpoint 0xf00d" in s for s in said)


# -- Memory release --------------------------------------------------------


@pytest.mark.asyncio
async def test_every_page_is_touched_exactly_once():
    """The right to execute comes from the write access itself - a skipped
    page only shows up at runtime."""
    gdb = FakeDebugger([], {})
    assert await touch_pages(gdb, 0x100000000, 3 * PAGE_SIZE) == 3
    assert [a for a, _d in gdb.writes] == [
        0x100000000, 0x100000000 + PAGE_SIZE, 0x100000000 + 2 * PAGE_SIZE]
    assert gdb.batches == [3, 3], "one batch to read, one to write back"


@pytest.mark.asyncio
async def test_partial_page_still_gets_touched():
    assert await touch_pages(FakeDebugger([], {}), 0x100000000, 100) == 1


@pytest.mark.asyncio
async def test_unreadable_page_is_an_error():
    class Unreadable(FakeDebugger):
        def _answer(self, payload):
            return "E08" if payload.startswith("m") else super()._answer(payload)

    with pytest.raises(DeviceError):
        await touch_pages(Unreadable([], {}), 0x100000000, PAGE_SIZE)


# -- Before iOS 17: no tunnel ---------------------------------------------------


class _Dvt:
    def __init__(self, provider):
        _Dvt.provider = provider

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass


class _Control:
    def __init__(self, dvt):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass

    async def launch(self, bundle_id, kill_existing, start_suspended):
        assert start_suspended
        return 4242


class _LegacyLockdown:
    def __init__(self):
        self.started = []

    async def start_lockdown_service(self, name):
        self.started.append(name)
        return "conn"


class _SP:
    def __init__(self):
        self.lockdown = _LegacyLockdown()

    async def rsd(self):
        raise AssertionError("no tunnel below iOS 17")


@pytest.fixture
def fake_dvt(monkeypatch):
    monkeypatch.setattr("pymobiledevice3.services.dvt.instruments.dvt_provider.DvtProvider", _Dvt)
    monkeypatch.setattr(
        "pymobiledevice3.services.dvt.instruments.process_control.ProcessControl", _Control)


@pytest.mark.parametrize("version", ["15.8", "12.5.7", "16.7.10"])
async def test_below_ios_17_jit_uses_the_lockdown_debugserver(fake_dvt, version):
    """iPod touch 7 (iOS 15) and older iPhones/iPads: DVT and debugserver
    are plain lockdown services - asking for the tunnel would fail."""
    from modstaller.device.connection import DeviceInfo
    from modstaller.device.jit import LEGACY_DEBUGSERVER, _launch_and_attach

    sp = _SP()
    info = DeviceInfo(udid="X", name="iPod", product_type="iPod9,1", ios_version=version,
                      build="B", developer_mode=False)
    pid, conn = await _launch_and_attach(sp, info, "com.example.emu", lambda m: None)
    assert (pid, conn) == (4242, "conn")
    assert sp.lockdown.started == [LEGACY_DEBUGSERVER]
    assert _Dvt.provider is sp.lockdown
    assert has_txm("iPod9,1", version) is False
