"""Das GDB-Remote-Protokoll fuer die JIT-Freischaltung.

Die Tuecke liegt im Lesen: der Debugger schickt Empfangsbestaetigungen
getrennt vom eigentlichen Paket. Wer nur einmal liest, haelt ein blosses "+"
fuer die Antwort und meldet Fehlschlag, wo gerade alles geklappt hat - genau
dieser Fehler hat hier einmal zugeschlagen.
"""

from __future__ import annotations

import pytest

from modstaller.device.jit import _attached, _packet, _read_packet


class FakeConn:
    """Gibt vorbereitete Segmente zurueck - so, wie sie ueber die Leitung
    kaemen: Bestaetigung und Paket getrennt, Pakete auch mal zerstueckelt."""

    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)
        self.sent: list[bytes] = []

    async def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    async def recv_any(self, length: int = 4096) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""


# -- Paketbau --------------------------------------------------------------


def test_checksum_matches_known_packet():
    """Gegenprobe mit einem Wert, der in etablierten Werkzeugen fest
    verdrahtet ist - stimmt er, stimmt die Pruefsummenbildung."""
    assert _packet("QStartNoAckMode") == b"$QStartNoAckMode#b0"


def test_checksum_is_computed_not_guessed():
    """Die Pruefsumme von vAttach haengt an der Prozessnummer. Feste Werte
    gehen nur gut, solange niemand sie prueft."""
    assert _packet("vAttach;1") != _packet("vAttach;2")
    assert _packet("D") == b"$D#44"


# -- Lesen -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledgement_is_not_mistaken_for_a_reply():
    conn = FakeConn([b"+", b"$T11thread:1f4;#aa"])
    assert _attached(await _read_packet(conn))


@pytest.mark.asyncio
async def test_packet_split_across_segments_is_reassembled():
    conn = FakeConn([b"+$T11thr", b"ead:1f4", b";#aa"])
    assert _attached(await _read_packet(conn))


@pytest.mark.asyncio
async def test_error_reply_is_recognised_as_failure():
    conn = FakeConn([b"+", b"$E01#00"])
    assert not _attached(await _read_packet(conn))


@pytest.mark.asyncio
async def test_silence_does_not_hang_forever():
    assert not _attached(await _read_packet(FakeConn([]), timeout=0.2))


@pytest.mark.asyncio
async def test_only_acknowledgements_count_as_no_answer():
    conn = FakeConn([b"+", b"+", b"+"])
    assert not _attached(await _read_packet(conn, timeout=0.3))


@pytest.mark.parametrize("reply, expected", [
    ("$T11thread:1f4;#aa", True),
    ("$S05#b8", True),
    ("+$T11#00", True),
    ("$E01#00", False),
    ("$OK#9a", False),
    ("+", False),
    ("", False),
])
def test_attach_verdicts(reply, expected):
    assert _attached(reply) is expected
