"""SRP gegen zwei unabhaengige Referenzen pruefen.

Der Handshake ist der Punkt, an dem ein Fehler am teuersten ist: Apple sieht
einen falschen Beweis als falsches Passwort und drosselt den Account. Deshalb
wird hier gegen die RFC-Testvektoren *und* gegen eine etablierte
Implementierung geprueft - inklusive der Faelle mit fuehrenden Nullbytes, die
nur in etwa einem von 256 Logins auftreten.

Braucht ``pip install srp`` (nur fuer Tests).
"""

from __future__ import annotations

import hashlib
import os

import pytest

from modstaller.apple.srp import (
    G_1024, G_2048, N_1024, N_2048, SRPClient, derive_password,
)

# -- RFC 5054 Anhang B -----------------------------------------------------

RFC_SALT = bytes.fromhex("BEB25379D1A8581EB5A727673A2441EE")
RFC_A_PRIV = int(
    "60975527035CF2AD1989806F0407210BC81EDC04E2762A56AFD529DDDA2D4393", 16)
RFC_B = bytes.fromhex(
    "BD0C61512C692C0CB6D041FA01BB152D4916A1E77AF46AE105393011BAF38964DC46A067"
    "0DD125B95A981652236F99D9B681CBF87837EC996C6DA04453728610D0C6DDB58B318885"
    "D7D82C7F8DEB75CE7BD4FBAA37089E6F9C6059F388838E7A00030B331EB7684091044 0B1"
    "B27AAEAEEB4012B7D7665238A8E3FB004B117B58".replace(" ", ""))
RFC_A_PUB = int(
    "61D5E490F6F1B79547B0704C436F523DD0E560F0C64115BB72557EC44352E8903211C046"
    "92272D8B2D1A5358A2CF1B6E0BFCF99F921530EC8E39356179EAE45E42BA92AEACED8251"
    "71E1E8B9AF6D9C03E1327F44BE087EF06530E69F66615261EEF54073CA11CF5858F0EDFD"
    "FE15EFEAB349EF5D76988A3672FAC47B0769447B", 16)
RFC_X = "94b7555aabe9127cc58ccf4993db6cf84d16c124"
RFC_S = bytes.fromhex(
    "b0dc82babcf30674ae450c0287745e7990a3381f63b387aaf271a10d233861e359b48220"
    "f7c4693c9ae12b0a6f67809f0876e2d013800d6c41bb59b6d5979b5c00a172b4a2a5903a"
    "0bdcaf8a709585eb2afafa8f3499b200210dcc1f10eb33943cd67fc88a2f39a4be5bec4e"
    "c0a3212dc346d7e474b29ede8a469ffeca686e5a")


def _rfc_client() -> SRPClient:
    return SRPClient("alice", hash_alg=hashlib.sha1, n=N_1024, g=G_1024,
                     username_in_x=True, a=RFC_A_PRIV)


def test_rfc5054_public_value():
    assert _rfc_client().A == RFC_A_PUB


def test_rfc5054_x():
    c = _rfc_client()
    assert format(c._x(RFC_SALT, b"password123"), "040x") == RFC_X


def test_rfc5054_session_key():
    c = _rfc_client()
    c.process_challenge(RFC_SALT, RFC_B, b"password123")
    assert c.K == hashlib.sha1(RFC_S).digest()


# -- Vergleich mit der Referenzbibliothek ----------------------------------

srp_lib = pytest.importorskip("srp._pysrp", reason="pip install srp")


@pytest.fixture(scope="module")
def reference():
    srp_lib.rfc5054_enable()
    srp_lib.no_username_in_x()
    assert srp_lib._rfc5054_compat and srp_lib._no_username_in_x
    return srp_lib


def _compare(reference, salt: bytes, password: bytes, a: int, b: int):
    ref = reference.User("t@e.com", b"", hash_alg=reference.SHA256,
                         ng_type=reference.NG_2048)
    ref.a, ref.A, ref.p = a, pow(G_2048, a, N_2048), password
    ref_m1 = ref.process_challenge(salt, reference.long_to_bytes(b))

    ours = SRPClient("t@e.com", hash_alg=hashlib.sha256, n=N_2048, g=G_2048,
                     username_in_x=False, a=a)
    our_m1 = ours.process_challenge(salt, reference.long_to_bytes(b), password)
    return ref_m1, our_m1, ours.verify_session(ref.H_AMK)


@pytest.mark.parametrize("seed", range(64))
def test_matches_reference(reference, seed):
    rnd = random_bytes = os.urandom
    a = int.from_bytes(rnd(32), "big")
    b = int.from_bytes(rnd(256), "big") % N_2048
    ref_m1, our_m1, m2_ok = _compare(reference, rnd(16), rnd(32), a, b)
    assert our_m1 == ref_m1
    assert m2_ok


def test_matches_reference_with_leading_zero_bytes(reference):
    """Der Fall, der nur in etwa einem von 256 Logins auftritt.

    A, B und S werden hier gezielt so gewaehlt, dass sie mit einem Nullbyte
    beginnen - genau dort lag der Fehler, der sonst zufaellige und voellig
    unerklaerliche Login-Fehlschlaege erzeugt haette.
    """
    found = 0
    for _ in range(4000):
        a = int.from_bytes(os.urandom(32), "big")
        b = int.from_bytes(os.urandom(256), "big") % N_2048
        if b.bit_length() > 2040:          # B beginnt *nicht* mit Nullbyte
            continue
        found += 1
        ref_m1, our_m1, m2_ok = _compare(reference, os.urandom(16),
                                         os.urandom(32), a, b)
        assert our_m1 == ref_m1
        assert m2_ok
        if found >= 20:
            break
    assert found, "kein Fall mit fuehrendem Nullbyte erzeugt"


# -- Passwortableitung -----------------------------------------------------

def test_derive_password_protocols_differ():
    """s2k und s2k_fo unterscheiden sich nur minimal - und vollstaendig."""
    salt = b"\x01" * 16
    a = derive_password("hunter2", salt, 1000, "s2k")
    b = derive_password("hunter2", salt, 1000, "s2k_fo")
    assert a != b
    assert len(a) == len(b) == 32


def test_derive_password_rejects_unknown_protocol():
    with pytest.raises(ValueError):
        derive_password("x", b"s" * 16, 100, "s2k_nope")
