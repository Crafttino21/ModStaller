"""Key pair and certificate signing request.

The private key is created here and never leaves the computer - Apple only
gets the CSR and returns the certificate. Both together are later handed to
zsign as PKCS#12.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from typing import Callable, TypeVar

from ..config import CERTS_DIR, read_secret, undo_text_mode, write_secret
from ..errors import ConfigError
from ..i18n import _

T = TypeVar("T")

KEY_SIZE = 2048


@dataclass
class KeyPair:
    private_key: rsa.RSAPrivateKey

    @property
    def pem(self) -> bytes:
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def csr_pem(self, common_name: str = "ModStaller") -> str:
        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            ]))
            .sign(self.private_key, hashes.SHA256())
        )
        return csr.public_bytes(serialization.Encoding.PEM).decode()

    @classmethod
    def generate(cls) -> "KeyPair":
        return cls(rsa.generate_private_key(public_exponent=65537,
                                            key_size=KEY_SIZE))

    @classmethod
    def load(cls, pem: bytes) -> "KeyPair":
        key = serialization.load_pem_private_key(pem, password=None)
        assert isinstance(key, rsa.RSAPrivateKey)
        return cls(key)


def _team_dir(team_id: str) -> Path:
    d = CERTS_DIR / team_id
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    return d


def key_path(team_id: str) -> Path:
    return _team_dir(team_id) / "key.pem"


def cert_path(team_id: str) -> Path:
    return _team_dir(team_id) / "cert.der"


def p12_path(team_id: str) -> Path:
    return _team_dir(team_id) / "identity.p12"


def pass_path(team_id: str) -> Path:
    return _team_dir(team_id) / "identity.pass"


def _load_healed(path: Path, parse: Callable[[bytes], T]) -> T | None:
    """``parse`` applied to the file - repaired first if need be.

    Up to 1.3.0-rc.1, Windows wrote these files in text mode (every b"\n"
    became b"\r\n", see config.O_BINARY). Such a file is repaired and
    written back, so no new certificate is needed. None: unusable.
    """
    raw = read_secret(path)
    try:
        return parse(raw)
    except Exception:
        pass
    fixed = undo_text_mode(raw)
    if fixed == raw:
        return None
    try:
        value = parse(fixed)
    except Exception:
        return None
    write_secret(path, fixed)
    return value


def _certificate(raw: bytes) -> x509.Certificate:
    try:
        return x509.load_der_x509_certificate(raw)
    except ValueError:
        return x509.load_pem_x509_certificate(raw)


def load_keypair(team_id: str) -> KeyPair | None:
    p = key_path(team_id)
    if not p.exists():
        return None
    kp = _load_healed(p, KeyPair.load)
    if kp is None:
        # Not silently a new key: that would need a new certificate, and
        # Apple allows only a few.
        raise ConfigError(_(
            "The private key {path} is damaged. Delete the folder {folder} - "
            "ModStaller then requests a new certificate.",
            path=p, folder=p.parent))
    return kp


def save_keypair(team_id: str, kp: KeyPair) -> None:
    write_secret(key_path(team_id), kp.pem)


def build_p12(team_id: str, kp: KeyPair, cert_der: bytes) -> tuple[Path, str]:
    """Builds the PKCS#12 identity that zsign expects.

    Returns:
        Path to the .p12 and its password.
    """
    cert = _certificate(cert_der)

    password = secrets.token_urlsafe(24)
    blob = pkcs12.serialize_key_and_certificates(
        name=b"ModStaller",
        key=kp.private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            password.encode()),
    )
    write_secret(p12_path(team_id), blob)
    write_secret(pass_path(team_id), password.encode())
    write_secret(cert_path(team_id), cert_der)
    return p12_path(team_id), password


def load_p12(team_id: str) -> tuple[Path, str] | None:
    """The local identity - None if it is missing or unusable (then it is
    rebuilt from Apple's certificate for our key, see ensure_certificate)."""
    p, pw = p12_path(team_id), pass_path(team_id)
    if not (p.exists() and pw.exists()):
        return None
    password = read_secret(pw).decode().strip()
    ok = _load_healed(p, lambda data: pkcs12.load_key_and_certificates(
        data, password.encode()))
    return (p, password) if ok is not None else None


def certificate_expiry(team_id: str):
    p = cert_path(team_id)
    if not p.exists():
        return None
    cert = _load_healed(p, _certificate)
    # Unreadable: then the identity is rebuilt instead of crashing
    # (ensure_certificate, step 2).
    return cert.not_valid_after_utc if cert is not None else None
