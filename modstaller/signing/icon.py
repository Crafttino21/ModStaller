"""The app icon inside an IPA - found and turned into a normal PNG.

Xcode runs ``pngcrush -iphone`` over the icons it copies into the bundle.
The result is Apple's CgBI variant: an extra ``CgBI`` chunk, the image data
as raw deflate without zlib wrapper, BGRA instead of RGBA and premultiplied
alpha. Browsers cannot show that - :func:`uncrush` makes a standard PNG out
of it (the same steps as zsign's ``-x``).

Icons that live only in ``Assets.car`` are not found here - the editor then
shows a placeholder, and a new icon still works (zsign ``-I`` adds files).
"""

from __future__ import annotations

import struct
import zlib

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _chunks(data: bytes):
    pos = 8
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        yield kind, data[pos + 8:pos + 8 + length]
        pos += 12 + length


def png_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(PNG_MAGIC):
        return None
    for kind, body in _chunks(data):
        if kind == b"IHDR" and len(body) >= 8:
            return struct.unpack(">II", body[:8])
    return None


def _chunk(kind: bytes, body: bytes) -> bytes:
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))


def _unfilter(raw: bytes, width: int, height: int, bpp: int) -> bytearray:
    """Undoes the PNG row filters (spec 9.2) - needed before touching pixels."""
    stride = width * bpp
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        ftype = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def uncrush(data: bytes) -> bytes:
    """A standard PNG from a CgBI PNG. Anything else comes back unchanged."""
    if not data.startswith(PNG_MAGIC):
        return data
    chunks = list(_chunks(data))
    if not chunks or chunks[0][0] != b"CgBI":
        return data
    ihdr = next(body for kind, body in chunks if kind == b"IHDR")
    width, height, depth, color = struct.unpack(">IIBB", ihdr[:10])
    if depth != 8 or color not in (2, 6):
        return data     # never seen in practice - leave it to the caller
    bpp = 4 if color == 6 else 3
    idat = b"".join(body for kind, body in chunks if kind == b"IDAT")
    pixels = _unfilter(zlib.decompress(idat, -15), width, height, bpp)

    # BGR(A) -> RGB(A); undo the premultiplied alpha.
    for i in range(0, len(pixels), bpp):
        b, g, r = pixels[i], pixels[i + 1], pixels[i + 2]
        if bpp == 4:
            a = pixels[i + 3]
            if a:
                r, g, b = (min(255, r * 255 // a), min(255, g * 255 // a),
                           min(255, b * 255 // a))
        pixels[i], pixels[i + 1], pixels[i + 2] = r, g, b

    stride = width * bpp
    raw = b"".join(b"\x00" + bytes(pixels[y * stride:(y + 1) * stride])
                   for y in range(height))
    return (PNG_MAGIC + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(raw, 6)) + _chunk(b"IEND", b""))


def icon_names(info: dict) -> list[str]:
    """The icon file prefixes the Info.plist declares (iPhone before iPad)."""
    names: list[str] = []
    for key in ("CFBundleIcons", "CFBundleIcons~ipad"):
        primary = (info.get(key) or {}).get("CFBundlePrimaryIcon") or {}
        if isinstance(primary, dict):
            names += [n for n in primary.get("CFBundleIconFiles") or []
                      if isinstance(n, str)]
    names += [n for n in info.get("CFBundleIconFiles") or [] if isinstance(n, str)]
    if isinstance(info.get("CFBundleIconFile"), str):
        names.append(info["CFBundleIconFile"])
    seen: set[str] = set()
    return [n.removesuffix(".png") for n in names
            if n and not (n in seen or seen.add(n))]


def best_icon(files: dict[str, bytes], names: list[str]) -> bytes | None:
    """The largest declared icon among ``files`` (file name -> content),
    as a standard PNG."""
    best, best_size = None, 0
    for fname, data in files.items():
        if not fname.lower().endswith(".png"):
            continue
        if not any(fname.startswith(n) for n in names):
            continue
        size = png_size(data)
        if size and size[0] * size[1] > best_size:
            best, best_size = data, size[0] * size[1]
    if best is None:
        return None
    try:
        return uncrush(best)
    except (zlib.error, ValueError, IndexError, StopIteration, struct.error):
        return None
