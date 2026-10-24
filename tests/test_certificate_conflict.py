"""Apple's development certificate slots are taken by other tools.

Before, the interface only said which command-line flag would make room.
Now the error names the certificates in the way, and the install can be
repeated with the one the user picked - only that one is revoked, and never
a certificate of our own.
"""

from __future__ import annotations

import datetime

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

from modstaller import server as srv
from modstaller.apple.devservices import Certificate, Team
from modstaller.errors import AppleAPIError, AppleError, CertificateConflict
from modstaller.provisioning import ensure_certificate
from modstaller.signing import csr

TEAM = Team(team_id="PP2WVWJJYZ", name="Sam", type="Individual", status="active")
NOW = datetime.datetime.now(datetime.timezone.utc)
_CA = csr.KeyPair.generate().private_key


def _issue(public_key) -> bytes:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "iOS Development: Sam")])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(public_key).serial_number(x509.random_serial_number())
            .not_valid_before(NOW).not_valid_after(NOW + datetime.timedelta(days=365))
            .sign(_CA, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.DER)


def _foreign(name: str, serial: str) -> Certificate:
    """A certificate whose private key lives with another tool."""
    other = csr.KeyPair.generate().private_key.public_key()
    return Certificate(cert_id=f"ID{serial}", serial=serial, name=name,
                       content=_issue(other), expires_at=NOW)


class FakeApple:
    """Two slots, both taken - like a free account next to SideStore and
    Sideloadly."""

    def __init__(self, certs: list[Certificate], slots: int = 2):
        self.certs = list(certs)
        self.slots = slots
        self.revoked: list[str] = []
        self.requests = 0

    def list_certificates(self, team_id):
        return list(self.certs)

    def revoke_certificate(self, team_id, serial):
        self.revoked.append(serial)
        self.certs = [c for c in self.certs if c.serial != serial]

    def submit_csr(self, team_id, csr_pem, machine_id, machine_name):
        self.requests += 1
        if len(self.certs) >= self.slots:
            raise AppleAPIError(7460, "You already have a current iOS Development "
                                "certificate or a pending certificate request.")
        request = x509.load_pem_x509_csr(csr_pem.encode())
        cert = Certificate(cert_id="NEW", serial="NEWSERIAL", name=machine_name,
                           content=_issue(request.public_key()), expires_at=NOW)
        self.certs.append(cert)
        return cert


@pytest.fixture(autouse=True)
def certs_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(csr, "CERTS_DIR", tmp_path / "certs")


def _quiet(_text):
    pass


def test_full_slots_name_the_certificates_in_the_way():
    apple = FakeApple([_foreign("iPhone von Sam", "S1"), _foreign("DESKTOP-1", "S2")])
    with pytest.raises(CertificateConflict) as caught:
        ensure_certificate(apple, TEAM, "iPhone von Sam", say=_quiet)
    assert [c.serial for c in caught.value.certificates] == ["S1", "S2"]
    assert apple.revoked == [], "nothing goes without being asked"


def test_the_picked_certificate_makes_room_and_only_that_one():
    apple = FakeApple([_foreign("iPhone von Sam", "S1"), _foreign("DESKTOP-1", "S2")])
    said: list[str] = []
    p12, password = ensure_certificate(apple, TEAM, "iPhone von Sam",
                                       revoke="S2", say=said.append)
    assert apple.revoked == ["S2"]
    assert [c.serial for c in apple.certs] == ["S1", "NEWSERIAL"]
    assert p12.is_file() and password
    assert any("DESKTOP-1" in line for line in said), "the log says what went"


def test_the_certificate_id_picks_as_well():
    apple = FakeApple([_foreign("A", "S1"), _foreign("B", "S2")])
    ensure_certificate(apple, TEAM, "dev", revoke="IDS1", say=_quiet)
    assert apple.revoked == ["S1"]


def test_our_own_certificate_is_never_revoked():
    """Picked in an old dialog, but ours by now: it is reused instead."""
    kp = csr.KeyPair.generate()
    csr.save_keypair(TEAM.team_id, kp)
    ours = Certificate(cert_id="IDOURS", serial="OURS", name="dev",
                       content=_issue(kp.private_key.public_key()), expires_at=NOW)
    apple = FakeApple([ours, _foreign("B", "S2")])
    ensure_certificate(apple, TEAM, "dev", revoke="OURS", say=_quiet)
    assert apple.revoked == [] and apple.requests == 0


def test_a_certificate_gone_in_the_meantime_is_no_obstacle():
    apple = FakeApple([_foreign("A", "S1")])
    ensure_certificate(apple, TEAM, "dev", revoke="GONE", say=_quiet)
    assert apple.revoked == [] and apple.requests == 1


def test_a_refusal_without_certificates_is_no_conflict():
    apple = FakeApple([], slots=0)
    with pytest.raises(AppleError) as caught:
        ensure_certificate(apple, TEAM, "dev", say=_quiet)
    assert not isinstance(caught.value, CertificateConflict)


def test_the_interface_gets_the_certificates_with_the_error():
    conflict = CertificateConflict("full", [_foreign("DESKTOP-1", "S2")])
    data = srv._error_kind(conflict)
    assert data["kind"] == "CertificateConflict"
    assert data["exitCode"] == AppleError.exit_code
    assert [(c["serial"], c["name"], c["certId"]) for c in data["certificates"]] == [
        ("S2", "DESKTOP-1", "IDS2")]
    assert data["certificates"][0]["expiresAt"] == NOW.isoformat()
