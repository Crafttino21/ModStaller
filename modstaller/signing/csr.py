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

from ..config import CERTS_DIR, read_secret, write_secret

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


def load_keypair(team_id: str) -> KeyPair | None:
    p = key_path(team_id)
    return KeyPair.load(read_secret(p)) if p.exists() else None


def save_keypair(team_id: str, kp: KeyPair) -> None:
    write_secret(key_path(team_id), kp.pem)


def build_p12(team_id: str, kp: KeyPair, cert_der: bytes) -> tuple[Path, str]:
    """Builds the PKCS#12 identity that zsign expects.

    Returns:
        Path to the .p12 and its password.
    """
    try:
        cert = x509.load_der_x509_certificate(cert_der)
    except ValueError:
        cert = x509.load_pem_x509_certificate(cert_der)

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
    p, pw = p12_path(team_id), pass_path(team_id)
    if p.exists() and pw.exists():
        return p, read_secret(pw).decode()
    return None


def certificate_expiry(team_id: str):
    p = cert_path(team_id)
    if not p.exists():
        return None
    raw = read_secret(p)
    try:
        cert = x509.load_der_x509_certificate(raw)
    except ValueError:
        cert = x509.load_pem_x509_certificate(raw)
    return cert.not_valid_after_utc
