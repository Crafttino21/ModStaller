"""A minimal client for the GDB remote protocol.

Only as much as enabling JIT needs: attach, continue, read and write
registers and memory, detach. The protocol frames every packet as
``$<payload>#<checksum>`` and acknowledges it with ``+``.

The acknowledgements often arrive in separate segments. Mistaking them for
the reply turns successes into failures - so we always read up to the
complete packet here.
"""

from __future__ import annotations

import asyncio
import re

from ..errors import DeviceError
from ..i18n import _

DEFAULT_TIMEOUT = 20.0

#: How many packets go out back to back before we read the replies.
BATCH = 128

#: ARM64 register numbers as they appear in the stop reply.
REG_X0 = 0x00
REG_X1 = 0x01
REG_X16 = 0x10
REG_PC = 0x20

_STOP_THREAD = re.compile(r"thread:([0-9a-fA-F]+);")
_STOP_SIGNAL = re.compile(r"^T([0-9a-fA-F]{2})")


def checksum(payload: str) -> str:
    return f"{sum(payload.encode()) & 0xFF:02x}"


def frame(payload: str) -> bytes:
    return f"${payload}#{checksum(payload)}".encode()


def le_hex_to_int(hex_str: str) -> int:
    """Register values appear in the reply as little-endian hex strings."""
    raw = bytes.fromhex(hex_str)
    return int.from_bytes(raw, "little")


def int_to_le_hex(value: int, width: int = 8) -> str:
    return value.to_bytes(width, "little").hex()


class StopReply:
    """The reply with which the debugger reports a stop."""

    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.registers: dict[int, int] = {}
        for number, value in re.findall(r"([0-9a-fA-F]{2}):([0-9a-fA-F]+);",
                                        raw):
            try:
                self.registers[int(number, 16)] = le_hex_to_int(value)
            except ValueError:
                continue
        match = _STOP_THREAD.search(raw)
        self.thread = match.group(1) if match else None
        match = _STOP_SIGNAL.match(raw.lstrip("+$"))
        self.signal = match.group(1) if match else None

    def register(self, number: int) -> int | None:
        return self.registers.get(number)

    @property
    def is_stop(self) -> bool:
        body = self.raw.lstrip("+-$")
        return bool(body) and body[0] in ("T", "S")


class GdbClient:
    """Speaks the protocol over an existing connection."""

    def __init__(self, conn, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._conn = conn
        self._timeout = timeout
        self._buffer = ""

    async def _read_packet(self, timeout: float | None = None) -> str:
        limit = self._timeout if timeout is None else timeout
        loop = asyncio.get_running_loop()
        deadline = loop.time() + limit
        while True:
            start = self._buffer.find("$")
            if start >= 0:
                end = self._buffer.find("#", start)
                if end >= 0 and len(self._buffer) >= end + 3:
                    packet = self._buffer[start + 1:end]
                    self._buffer = self._buffer[end + 3:]
                    return packet

            remaining = deadline - loop.time()
            if remaining <= 0:
                return ""
            try:
                chunk = await asyncio.wait_for(self._conn.recv_any(),
                                               timeout=remaining)
            except asyncio.TimeoutError:
                return ""
            if not chunk:
                return ""
            self._buffer += chunk.decode("utf-8", "replace")

    async def send(self, payload: str, *, expect_reply: bool = True,
                   timeout: float | None = None) -> str:
        await self._conn.sendall(frame(payload))
        return await self._read_packet(timeout) if expect_reply else ""

    async def send_batch(self, payloads: list[str], *,
                         batch: int = BATCH) -> list[str]:
        """Sends many packets at once and collects one reply for each.

        One round trip per packet is what makes large regions slow: a few
        hundred MB are tens of thousands of pages. In no-ack mode the
        debugger answers in order, so we send ``batch`` packets back to
        back and only then read their replies.
        """
        replies: list[str] = []
        for start in range(0, len(payloads), batch):
            chunk = payloads[start:start + batch]
            await self._conn.sendall(b"".join(frame(p) for p in chunk))
            for _p in chunk:
                replies.append(await self._read_packet())
        return replies

    # -- The commands we need ---------------------------------------------

    async def start_no_ack_mode(self) -> None:
        await self.send("QStartNoAckMode")
        await self.send("QSetDetachOnError:1")

    async def attach(self, pid: int) -> StopReply:
        return StopReply(await self.send(f"vAttach;{pid:x}"))

    async def cont(self, timeout: float | None = None) -> StopReply:
        return StopReply(await self.send("c", timeout=timeout))

    async def cont_with_signal(self, signal: str, thread: str) -> None:
        await self.send(f"vCont;S{signal}:{thread}", expect_reply=False)

    async def read_memory(self, address: int, length: int) -> bytes:
        reply = await self.send(f"m{address:x},{length:x}")
        if not reply or reply.startswith("E"):
            raise DeviceError(_(
                "Memory at 0x{address:x} is not readable (reply: {reply!r})",
                address=address, reply=reply))
        return bytes.fromhex(reply)

    async def write_memory(self, address: int, data: bytes) -> None:
        reply = await self.send(f"M{address:x},{len(data):x}:{data.hex()}")
        if reply.startswith("E"):
            raise DeviceError(_(
                "Memory at 0x{address:x} is not writable (reply: {reply!r})",
                address=address, reply=reply))

    async def set_register(self, number: int, value: int, thread: str) -> None:
        await self.send(f"P{number:x}={int_to_le_hex(value)};thread:{thread};")

    async def allocate(self, size: int, permissions: str = "rx") -> int:
        """Requests memory from the debugger (``_M`` is an Apple extension)."""
        reply = await self.send(f"_M{size:x},{permissions}")
        if not reply or reply.startswith("E"):
            raise DeviceError(
                f"Could not allocate {permissions} memory "
                f"(reply: {reply!r})")
        return int(reply, 16)

    async def detach(self) -> None:
        await self.send("D", expect_reply=False)
