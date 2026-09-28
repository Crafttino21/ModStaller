"""App icons (Apple's CgBI PNGs) and unpacking an IPA without extensions."""

from __future__ import annotations

import plistlib
import struct
import zipfile
import zlib

import pytest

from modstaller.errors import SigningError
from modstaller.signing import icon
from modstaller.signing.ipa import icon_png
from modstaller.signing.prepare import unpack_without

#: 2x2 RGBA: opaque red, half-transparent green, blue, fully transparent.
PIXELS = [(255, 0, 0, 255), (0, 200, 0, 128), (0, 0, 255, 255), (0, 0, 0, 0)]


def _chunk(kind, body):
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))


def cgbi_png() -> bytes:
    """What Xcode's pngcrush makes of PIXELS: BGRA, premultiplied, raw
    deflate, a CgBI chunk up front - and a Sub filter on the second row so
    the unfiltering is exercised too."""
    def pre(r, g, b, a):
        return bytes([b * a // 255, g * a // 255, r * a // 255, a])
    row0 = b"\x00" + pre(*PIXELS[0]) + pre(*PIXELS[1])
    p2, p3 = pre(*PIXELS[2]), pre(*PIXELS[3])
    sub = bytes((p3[i] - p2[i]) & 0xFF for i in range(4))
    row1 = b"\x01" + p2 + sub
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    idat = comp.compress(row0 + row1) + comp.flush()
    ihdr = struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0)
    return (icon.PNG_MAGIC + _chunk(b"CgBI", b"\x50\x00\x20\x06")
            + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b""))


def decode_rgba(png: bytes) -> list[tuple[int, ...]]:
    chunks = dict(icon._chunks(png))
    raw = zlib.decompress(chunks[b"IDAT"])
    w, h = struct.unpack(">II", chunks[b"IHDR"][:8])
    px = icon._unfilter(raw, w, h, 4)
    return [tuple(px[i:i + 4]) for i in range(0, len(px), 4)]


def test_a_crushed_png_becomes_a_normal_one():
    out = icon.uncrush(cgbi_png())
    assert b"CgBI" not in out
    got = decode_rgba(out)
    assert got[0] == (255, 0, 0, 255)
    assert got[2] == (0, 0, 255, 255)
    assert got[1][3] == 128 and abs(got[1][1] - 200) <= 2   # un-premultiplied
    assert got[3][3] == 0


def test_a_normal_png_passes_unchanged():
    normal = icon.uncrush(cgbi_png())
    assert icon.uncrush(normal) == normal


def test_the_largest_declared_icon_is_taken(tmp_path):
    small = icon.uncrush(cgbi_png())
    big = small.replace(struct.pack(">II", 2, 2), struct.pack(">II", 4, 4), 1)
    ipa = tmp_path / "a.ipa"
    with zipfile.ZipFile(ipa, "w") as zf:
        zf.writestr("Payload/A.app/Info.plist", plistlib.dumps({
            "CFBundleIcons": {"CFBundlePrimaryIcon": {"CFBundleIconFiles": ["AppIcon60x60"]}}}))
        zf.writestr("Payload/A.app/AppIcon60x60@2x.png", small)
        zf.writestr("Payload/A.app/AppIcon60x60@3x.png", big)
        zf.writestr("Payload/A.app/Other.png", big + b"x")
    assert icon_png(ipa) == big


def test_no_declared_icon_means_none(tmp_path):
    ipa = tmp_path / "a.ipa"
    with zipfile.ZipFile(ipa, "w") as zf:
        zf.writestr("Payload/A.app/Info.plist", plistlib.dumps({}))
    assert icon_png(ipa) is None


def _ipa(tmp_path, extra=()):
    ipa = tmp_path / "in.ipa"
    with zipfile.ZipFile(ipa, "w") as zf:
        exe = zipfile.ZipInfo("Payload/A.app/A")
        exe.external_attr = 0o755 << 16
        zf.writestr(exe, b"bin")
        for name in ("Keep", "Drop"):
            zf.writestr(f"Payload/A.app/PlugIns/{name}.appex/Info.plist", b"p")
            zf.writestr(f"Payload/A.app/PlugIns/{name}.appex/{name}", b"x")
        for name in extra:
            zf.writestr(name, b"evil")
    return ipa


def test_unpacking_leaves_out_the_dropped_extension(tmp_path):
    out = unpack_without(_ipa(tmp_path), "A.app", ["PlugIns/Drop.appex"], tmp_path / "w")
    app = out / "Payload" / "A.app"
    assert (app / "PlugIns" / "Keep.appex" / "Keep").read_bytes() == b"x"
    assert not (app / "PlugIns" / "Drop.appex").exists()
    assert (app / "A").stat().st_mode & 0o100, "executables stay executable"


@pytest.mark.parametrize("evil", ["../escape.txt", "Payload/../../escape.txt"])
def test_no_entry_leaves_the_folder(tmp_path, evil):
    with pytest.raises(SigningError, match="unsafe path"):
        unpack_without(_ipa(tmp_path, [evil]), "A.app", [], tmp_path / "w")
    assert not (tmp_path / "escape.txt").exists()
    assert not any((tmp_path / "w").iterdir()), "nothing half-unpacked stays"


def test_zsign_gets_every_profile_the_icon_and_a_harmless_cwd(tmp_path, monkeypatch):
    """Extension profiles each go in as their own -m; a folder is signed with
    the folder as working directory, so zsign's cache ends up in there."""
    from modstaller.signing import signer

    seen = {}

    def fake_run(cmd, timeout, cwd, **kw):
        seen.update(cmd=cmd, cwd=cwd)
        (tmp_path / "out.ipa").write_bytes(b"ipa")
        class P:
            returncode = 0
            stdout = stderr = ""
        return P()
    monkeypatch.setattr(signer.subprocess, "run", fake_run)
    folder = tmp_path / "unpacked"
    folder.mkdir()
    for name in ("app.prov", "ext.prov", "icon.png"):
        (tmp_path / name).write_bytes(b"x")

    signer.sign(signer.SignRequest(
        ipa=folder, output=tmp_path / "out.ipa", p12=tmp_path / "k.p12",
        p12_password="pw", profile=tmp_path / "app.prov",
        extra_profiles=[tmp_path / "ext.prov"], icon=tmp_path / "icon.png",
        display_name="MyTube", bundle_id="ios.youtube.mine", strip_watch=True))

    cmd = seen["cmd"]
    profiles = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-m"]
    assert profiles == [str(tmp_path / "app.prov"), str(tmp_path / "ext.prov")]
    assert cmd[cmd.index("-I") + 1] == str(tmp_path / "icon.png")
    assert cmd[cmd.index("-n") + 1] == "MyTube" and "-W" in cmd
    assert cmd[-1] == str(folder) and seen["cwd"] == str(folder)
