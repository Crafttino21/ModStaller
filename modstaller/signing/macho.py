"""Is an app binary still App Store encrypted (FairPlay)?

The answer is in the binary itself: the load command
``LC_ENCRYPTION_INFO(_64)`` carries ``cryptid`` - non-zero while the code is
encrypted, zero once it was decrypted. Decrypted and modded IPAs (YTLite and
friends) often still contain the ``SC_Info/`` folder, so that folder proves
nothing - up to 1.3.0-rc.1 it made ModStaller refuse perfectly good IPAs.

Only the headers are read: for a fat binary the slice table, then per slice
the Mach-O header and its load commands - a few kilobytes, even out of a
compressed IPA member (``ZipExtFile`` can seek).
"""

from __future__ import annotations

import struct
from typing import BinaryIO

FAT_MAGIC, FAT_MAGIC_64 = 0xCAFEBABE, 0xCAFEBABF
MH_MAGIC, MH_MAGIC_64 = 0xFEEDFACE, 0xFEEDFACF
LC_ENCRYPTION_INFO, LC_ENCRYPTION_INFO_64 = 0x21, 0x2C

#: More load commands than this is no real binary - stop instead of reading.
MAX_COMMANDS_SIZE = 16 * 1024 * 1024


class NotMachO(ValueError):
    pass


def _slice_offsets(f: BinaryIO) -> list[int]:
    head = f.read(8)
    if len(head) < 8:
        raise NotMachO("too short")
    magic, count = struct.unpack(">II", head)
    if magic not in (FAT_MAGIC, FAT_MAGIC_64):
        return [0]
    if count > 64:
        raise NotMachO("implausible fat header")
    size = 20 if magic == FAT_MAGIC else 32
    table = f.read(count * size)
    offsets = []
    for i in range(count):
        entry = table[i * size:(i + 1) * size]
        offsets.append(struct.unpack(">I", entry[8:12])[0] if size == 20
                       else struct.unpack(">Q", entry[8:16])[0])
    return offsets


def _slice_cryptids(f: BinaryIO, offset: int) -> list[int]:
    f.seek(offset)
    header = f.read(32)
    if len(header) < 28:
        raise NotMachO("truncated header")
    magic = struct.unpack("<I", header[:4])[0]
    if magic == MH_MAGIC_64:
        header_size = 32
    elif magic == MH_MAGIC:
        header_size = 28
    else:
        raise NotMachO(f"magic {magic:#x}")
    ncmds, sizeofcmds = struct.unpack("<II", header[16:24])
    if sizeofcmds > MAX_COMMANDS_SIZE:
        raise NotMachO("implausible load commands")
    f.seek(offset + header_size)
    cmds = f.read(sizeofcmds)
    out, pos = [], 0
    for _ in range(ncmds):
        if pos + 8 > len(cmds):
            break
        cmd, cmdsize = struct.unpack("<II", cmds[pos:pos + 8])
        if cmd in (LC_ENCRYPTION_INFO, LC_ENCRYPTION_INFO_64) and pos + 20 <= len(cmds):
            out.append(struct.unpack("<I", cmds[pos + 16:pos + 20])[0])
        if cmdsize < 8:
            break
        pos += cmdsize
    return out


def cryptids(f: BinaryIO) -> list[int]:
    """Every ``cryptid`` in the binary (one per slice that has the command).

    Raises :class:`NotMachO` for anything that is not a Mach-O file.
    """
    out: list[int] = []
    for offset in _slice_offsets(f):
        out += _slice_cryptids(f, offset)
    return out


def is_encrypted(f: BinaryIO) -> bool:
    return any(c != 0 for c in cryptids(f))
