"""Das JIT-Protokoll: Rahmung, Registerlesen, Haltepunkt-Erkennung.

Auf Geraeten mit TXM/SPTM ist JIT keine einmalige Freischaltung mehr, sondern
ein Gespraech: die App bittet per Haltepunkt um Vorbereitung eines Bereichs,
der Debugger schreibt in jede Seite und antwortet mit der Adresse. Faellt ein
Glied dieser Kette aus, bleibt die App wortlos beim Start haengen - deshalb
steht jedes einzeln unter Test.
"""

from __future__ import annotations

import pytest

from modstaller.device.gdb import (
    REG_PC, REG_X0, REG_X1, REG_X16, GdbClient, StopReply, frame, int_to_le_hex,
    le_hex_to_int,
)
from modstaller.device.jit import PAGE_SIZE, _brk_immediate, _is_brk, _prepare_region


class FakeConn:
    """Liefert vorbereitete Segmente - auch zerstueckelt und mit getrennten
    Empfangsbestaetigungen, so wie es ueber die Leitung ankommt."""

    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)
        self.sent: list[bytes] = []

    async def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    async def recv_any(self, length: int = 4096) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""


# -- Rahmung ---------------------------------------------------------------


def test_checksum_matches_known_packet():
    """Gegenprobe mit einem Wert, der anderswo fest verdrahtet ist."""
    assert frame("QStartNoAckMode") == b"$QStartNoAckMode#b0"
    assert frame("D") == b"$D#44"


def test_checksum_is_computed_not_guessed():
    """Bei vAttach haengt die Pruefsumme an der Prozessnummer."""
    assert frame("vAttach;1") != frame("vAttach;2")


def test_register_encoding_roundtrip():
    for value in (0, 1, 0x4000, 0x1029B1FB8, 2 ** 48 - 1):
        assert le_hex_to_int(int_to_le_hex(value)) == value


# -- Antworten lesen -------------------------------------------------------


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


# -- Haltepunkte -----------------------------------------------------------


def test_recognises_the_jit_breakpoint():
    instruction = 0xD43E01A0            # brk #0xf00d
    assert _is_brk(instruction)
    assert _brk_immediate(instruction) == 0xF00D


def test_ordinary_instruction_is_not_a_breakpoint():
    assert not _is_brk(0xD503201F)      # nop


# -- Speicherfreigabe ------------------------------------------------------


class RecordingGdb:
    def __init__(self):
        self.reads: list[tuple[int, int]] = []
        self.writes: list[tuple[int, bytes]] = []

    async def read_memory(self, address: int, length: int) -> bytes:
        self.reads.append((address, length))
        return b"\x42"

    async def write_memory(self, address: int, data: bytes) -> None:
        self.writes.append((address, data))


@pytest.mark.asyncio
async def test_every_page_is_touched_exactly_once():
    """Das Ausfuehrungsrecht entsteht durch den Schreibzugriff selbst -
    eine uebersprungene Seite faellt erst zur Laufzeit auf."""
    gdb = RecordingGdb()
    pages = await _prepare_region(gdb, 0x100000000, 3 * PAGE_SIZE)
    assert pages == 3
    assert [a for a, _ in gdb.writes] == [
        0x100000000, 0x100000000 + PAGE_SIZE, 0x100000000 + 2 * PAGE_SIZE]


@pytest.mark.asyncio
async def test_content_is_written_back_unchanged():
    """Geschrieben wird, was gelesen wurde - der Zugriff zaehlt, nicht der
    Inhalt. Etwas anderes hineinzuschreiben wuerde den Code zerstoeren."""
    gdb = RecordingGdb()
    await _prepare_region(gdb, 0x100000000, PAGE_SIZE)
    assert gdb.writes == [(0x100000000, b"\x42")]


@pytest.mark.asyncio
async def test_partial_page_still_gets_touched():
    gdb = RecordingGdb()
    assert await _prepare_region(gdb, 0x100000000, 100) == 1


# -- Die Gespraechsfuehrung ------------------------------------------------

from modstaller.device.jit import (  # noqa: E402
    BRK_JIT, BRK_LEGACY, CMD_DETACH, CMD_PREPARE_REGION,
    CMD_SET_DETACH_AFTER_FIRST, Jit26Session, JitResult,
)


class ScriptedGdb:
    """Ein Debugger, der eine vorbereitete Folge von Halten abspielt."""

    ALLOCATED = 0x200000000

    def __init__(self, stops: list[StopReply], instruction: int):
        self._stops = list(stops)
        self._instruction = instruction
        self.registers: dict[int, int] = {}
        self.prepared: list[tuple[int, int]] = []
        self.detached = False
        self.allocations: list[int] = []

    async def cont(self, timeout=None) -> StopReply:
        return self._stops.pop(0) if self._stops else StopReply("")

    async def read_memory(self, address: int, length: int) -> bytes:
        if length == 4:
            return self._instruction.to_bytes(4, "little")
        return b"\x00" * length

    async def write_memory(self, address: int, data: bytes) -> None:
        self.prepared.append((address, len(data)))

    async def set_register(self, number: int, value: int, thread: str) -> None:
        self.registers[number] = value

    async def allocate(self, size: int, permissions: str = "rx") -> int:
        self.allocations.append(size)
        return self.ALLOCATED

    async def detach(self) -> None:
        self.detached = True


def _stop(regs: dict[int, int]) -> StopReply:
    body = "".join(f"{n:02x}:{int_to_le_hex(v)};" for n, v in regs.items())
    return StopReply(f"T11thread:1f4;{body}")


BRK_INSTR = 0xD43E01A0        # brk #0xf00d
BRK_69_INSTR = 0xD4200D20     # brk #0x69


@pytest.mark.asyncio
async def test_legacy_breakpoint_reads_the_size_from_x0():
    """Beim alten Aufruf steht in x0 die *Groesse*, nicht die Adresse.

    Wer das mit dem neueren verwechselt, fordert einen Bereich an der Adresse
    "Groesse" an - die App bekommt Unsinn und wartet weiter auf JIT.
    """
    gdb = ScriptedGdb([_stop({REG_PC: 0x1000, REG_X0: 0x400000, REG_X1: 0})],
                      BRK_69_INSTR)
    result = JitResult("x", 1)
    await Jit26Session(gdb, result, lambda m: None).run()

    assert gdb.allocations == [0x400000], "Groesse muss aus x0 kommen"
    assert gdb.registers[REG_X0] == ScriptedGdb.ALLOCATED, \
        "die zugeteilte Adresse muss zurueckgemeldet werden"
    assert result.prepared_regions == 1


@pytest.mark.asyncio
async def test_new_call_reads_address_from_x0_and_size_from_x1():
    gdb = ScriptedGdb([_stop({REG_PC: 0x1000, REG_X16: CMD_PREPARE_REGION,
                                REG_X0: 0x140000000, REG_X1: PAGE_SIZE})],
                      BRK_INSTR)
    result = JitResult("x", 1)
    await Jit26Session(gdb, result, lambda m: None).run()

    assert gdb.allocations == [], "mit gegebener Adresse wird nichts zugeteilt"
    assert gdb.prepared == [(0x140000000, 1)]
    assert result.prepared_bytes == PAGE_SIZE


@pytest.mark.asyncio
async def test_zero_address_lets_the_debugger_choose():
    gdb = ScriptedGdb([_stop({REG_PC: 0x1000, REG_X16: CMD_PREPARE_REGION,
                                REG_X0: 0, REG_X1: PAGE_SIZE})], BRK_INSTR)
    await Jit26Session(gdb, JitResult("x", 1), lambda m: None).run()
    assert gdb.allocations == [PAGE_SIZE]


@pytest.mark.asyncio
async def test_detach_ends_the_conversation():
    gdb = ScriptedGdb([_stop({REG_PC: 0x1000, REG_X16: CMD_DETACH})],
                      BRK_INSTR)
    result = JitResult("x", 1)
    await Jit26Session(gdb, result, lambda m: None).run()
    assert gdb.detached and result.detached_cleanly


@pytest.mark.asyncio
async def test_detach_after_first_request_is_honoured():
    """Manche Apps lassen den Debugger nach der ersten Anfrage gehen."""
    gdb = ScriptedGdb([
        _stop({REG_PC: 0x1000, REG_X16: CMD_SET_DETACH_AFTER_FIRST,
                 REG_X0: 1}),
        _stop({REG_PC: 0x1000, REG_X0: 0x8000, REG_X1: 0}),
    ], BRK_INSTR)
    # Der zweite Halt ist ein 0x69 - dafuer braucht es die andere Instruktion.
    gdb._instruction = BRK_INSTR
    result = JitResult("x", 1)
    session = Jit26Session(gdb, result, lambda m: None)
    # Ersten Halt verarbeiten, dann auf den alten Haltepunkt umschalten.
    await session._handle(gdb._stops.pop(0))
    assert session._detach_after_first
    gdb._instruction = BRK_69_INSTR
    await session._handle(gdb._stops.pop(0))
    assert gdb.detached, "nach der ersten Anfrage muss geloest werden"


@pytest.mark.asyncio
async def test_program_counter_moves_past_the_breakpoint():
    """Ohne das haelt die App an derselben Stelle wieder an - endlos."""
    gdb = ScriptedGdb([_stop({REG_PC: 0x1000, REG_X16: CMD_DETACH})],
                      BRK_INSTR)
    await Jit26Session(gdb, JitResult("x", 1), lambda m: None).run()
    assert gdb.registers[REG_PC] == 0x1004
