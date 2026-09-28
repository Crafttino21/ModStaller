"""Up to 1.3.0-rc.1 Windows wrote secrets in text mode - every b"\\n" became
b"\\r\\n", which broke profiles, identity.p12 and cert.der. And FairPlay was
detected by a folder that decrypted IPAs keep. Both, and the self-healing of
files damaged back then."""

from __future__ import annotations

import datetime
import io
import plistlib
import struct
import zipfile

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from modstaller import config
from modstaller.errors import ConfigError
from modstaller.signing import csr, macho
from modstaller.signing.ipa import inspect

BINARY = b"a\nb\r\nc\x1a\r\x00\n"


def test_secrets_are_written_byte_for_byte(tmp_path):
    """Runs on the Windows CI runner too - there it caught the bug."""
    p = tmp_path / "s" / "blob"
    config.write_secret(p, BINARY)
    assert p.read_bytes() == BINARY


def test_undoing_text_mode_is_exact():
    damaged = BINARY.replace(b"\n", b"\r\n")
    assert config.undo_text_mode(damaged) == BINARY


# -- Self-healing of the identity ------------------------------------------


@pytest.fixture
def certs(tmp_path, monkeypatch):
    monkeypatch.setattr(csr, "CERTS_DIR", tmp_path / "certs")
    return tmp_path / "certs"


def _identity(team: str) -> tuple[csr.KeyPair, bytes]:
    kp = csr.KeyPair.generate()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "t")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(kp.private_key.public_key()).serial_number(7)
            .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=300))
            .sign(kp.private_key, hashes.SHA256()))
    return kp, cert.public_bytes(serialization.Encoding.DER)


def _text_mode(path):
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))


def test_damaged_identity_files_heal_without_a_new_certificate(certs):
    kp, der = _identity("T1")
    csr.save_keypair("T1", kp)
    p12, password = csr.build_p12("T1", kp, der)
    for f in (csr.cert_path("T1"), csr.p12_path("T1"), csr.key_path("T1")):
        _text_mode(f)

    assert csr.certificate_expiry("T1") is not None
    assert csr.cert_path("T1").read_bytes() == der, "repaired on disk"
    assert csr.load_p12("T1") == (p12, password)
    pkcs12.load_key_and_certificates(p12.read_bytes(), password.encode())
    assert csr.load_keypair("T1") is not None


def test_unusable_identity_is_rebuilt_instead_of_crashing(certs):
    kp, der = _identity("T2")
    csr.build_p12("T2", kp, der)
    csr.cert_path("T2").write_bytes(b"-----BEGIN nonsense")
    csr.p12_path("T2").write_bytes(b"garbage")
    # None sends ensure_certificate to step 2: rebuild from Apple's copy.
    assert csr.certificate_expiry("T2") is None
    assert csr.load_p12("T2") is None


def test_an_unreadable_key_is_named_not_replaced(certs):
    config.write_secret(csr.key_path("T3"), b"not a key")
    with pytest.raises(ConfigError, match="damaged"):
        csr.load_keypair("T3")


# -- FairPlay: cryptid, not SC_Info ------------------------------------------


def thin(cryptid: int | None, *, bits64: bool = True) -> bytes:
    """A Mach-O header with one load command - LC_ENCRYPTION_INFO(_64) if
    ``cryptid`` is given, else an unrelated one."""
    if cryptid is None:
        cmd = struct.pack("<II", 0x19, 16) + b"\0" * 8
    elif bits64:
        cmd = struct.pack("<IIIIII", macho.LC_ENCRYPTION_INFO_64, 24, 0x4000, 0x1000, cryptid, 0)
    else:
        cmd = struct.pack("<IIIII", macho.LC_ENCRYPTION_INFO, 20, 0x4000, 0x1000, cryptid)
    magic, size = (macho.MH_MAGIC_64, 32) if bits64 else (macho.MH_MAGIC, 28)
    header = struct.pack("<IiiIIII", magic, 12, 0, 2, 1, len(cmd), 0)
    return header + (b"\0\0\0\0" if bits64 else b"") + cmd


def fat(*slices: bytes) -> bytes:
    offsets, body, pos = [], b"", 0x1000
    for s in slices:
        offsets.append(pos)
        body += s.ljust(0x1000, b"\0")
        pos += 0x1000
    table = b"".join(struct.pack(">IIIII", 12, 0, off, len(s), 12)
                     for off, s in zip(offsets, slices))
    head = struct.pack(">II", macho.FAT_MAGIC, len(slices)) + table
    return head.ljust(0x1000, b"\0") + body


@pytest.mark.parametrize("binary, encrypted", [
    (thin(0), False),
    (thin(1), True),
    (thin(1, bits64=False), True),
    (thin(None), False),
    (fat(thin(0, bits64=False), thin(0)), False),
    (fat(thin(0, bits64=False), thin(1)), True),
])
def test_cryptid_decides(binary, encrypted):
    assert macho.is_encrypted(io.BytesIO(binary)) is encrypted


def test_not_a_macho_is_said_so():
    with pytest.raises(macho.NotMachO):
        macho.cryptids(io.BytesIO(b"#!/bin/sh\necho hi\n"))


def _ipa(tmp_path, binary: bytes, sc_info: bool) -> str:
    path = tmp_path / "a.ipa"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Payload/A.app/Info.plist", plistlib.dumps(
            {"CFBundleIdentifier": "a.b", "CFBundleExecutable": "A"}))
        zf.writestr("Payload/A.app/A", binary)
        if sc_info:
            zf.writestr("Payload/A.app/SC_Info/A.sinf", b"x")
    return str(path)


def test_a_decrypted_ipa_with_sc_info_is_not_encrypted(tmp_path):
    """YTLite & co: decrypted, but the SC_Info folder is still there."""
    assert not inspect(_ipa(tmp_path, thin(0), sc_info=True)).encrypted


def test_an_encrypted_ipa_is_recognised(tmp_path):
    assert inspect(_ipa(tmp_path, fat(thin(1, bits64=False), thin(1)), sc_info=True)).encrypted


def test_an_unreadable_binary_does_not_block(tmp_path):
    assert not inspect(_ipa(tmp_path, b"not mach-o", sc_info=True)).encrypted
