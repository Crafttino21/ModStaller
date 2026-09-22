"""SRP-6a in Apples Auspraegung.

Warum eigener Code statt einer Bibliothek: Apple weicht an drei Stellen vom
ueblichen Verhalten ab, und die gaengigen PyPI-Pakete koennen nicht alle drei.

1. Der Benutzername geht **nicht** in ``x`` ein: ``x = H(s | H(":" | p))``.
2. ``p`` ist nicht das Passwort, sondern ein daraus abgeleiteter Wert
   (siehe :func:`derive_password`) - Apple nennt die Verfahren ``s2k`` und
   ``s2k_fo``.
3. Zahlen werden nach RFC 5054 auf die Laenge von N linksseitig genullt,
   bevor sie gehasht werden.

Die Kernmathematik ist gegen die Testvektoren aus RFC 5054 Anhang B geprueft.
"""

from __future__ import annotations

import hashlib
import hmac
import os

# RFC 5054, 2048-Bit-Gruppe - die von Apple genutzte.
N_2048 = int(
    "AC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC3192943DB56050A37329CBB4"
    "A099ED8193E0757767A13DD52312AB4B03310DCD7F48A9DA04FD50E8083969EDB767B0CF60"
    "95179A163AB3661A05FBD5FAAAE82918A9962F0B93B855F97993EC975EEAA80D740ADBF4FF"
    "747359D041D5C33EA71D281E446B14773BCA97B43A23FB801676BD207A436C6481F1D2B907"
    "8717461A5B9D32E688F87748544523B524B0D57D5EA77A2775D2ECFA032CFBDBF52FB37861"
    "60279004E57AE6AF874E7303CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DB"
    "FBB694B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F9E4AFF73", 16)
G_2048 = 2

# RFC 5054, 1024-Bit-Gruppe - nur fuer die Testvektoren.
N_1024 = int(
    "EEAF0AB9ADB38DD69C33F80AFA8FC5E86072618775FF3C0B9EA2314C9C256576D674DF7496"
    "EA81D3383B4813D692C6E0E0D5D8E250B98BE48E495C1D6089DAD15DC7D7B46154D6B6CE8E"
    "F4AD69B15D4982559B297BCF1885C529F566660E57EC68EDBC3C05726CC02FD4CBF4976EAA"
    "9AFD5138FE8376435B9FC61D2FC0EB06E3", 16)
G_1024 = 2


def _pad(n: int, width: int) -> bytes:
    return n.to_bytes(width, "big")


def _hash_int(hash_alg, *values: bytes) -> int:
    h = hash_alg()
    for v in values:
        h.update(v)
    return int.from_bytes(h.digest(), "big")


def derive_password(password: str, salt: bytes, iterations: int,
                    protocol: str) -> bytes:
    """Apples ``s2k``/``s2k_fo``: das Passwort wird vorgehasht, dann gedehnt.

    ``s2k`` nutzt den rohen SHA-256-Digest, ``s2k_fo`` dessen Hex-Darstellung.
    Der Unterschied ist winzig und komplett ergebnisrelevant - Apple waehlt
    das Verfahren in der Antwort auf den ersten Request.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    if protocol == "s2k_fo":
        digest = digest.hex().encode("utf-8")
    elif protocol != "s2k":
        raise ValueError(f"Unbekanntes SRP-Protokoll: {protocol!r}")
    return hashlib.pbkdf2_hmac("sha256", digest, salt, iterations, 32)


class SRPClient:
    """Client-Seite eines SRP-6a-Handshakes.

    Args:
        username: Geht in M1 ein, per Default aber nicht in ``x``.
        hash_alg: ``hashlib.sha256`` fuer Apple.
        n, g: Die Gruppe.
        username_in_x: RFC-5054-Verhalten (True) vs. Apple (False).
        a: Nur fuer Tests vorgebbar, sonst zufaellig.
    """

    def __init__(self, username: str, *, hash_alg=hashlib.sha256,
                 n: int = N_2048, g: int = G_2048,
                 username_in_x: bool = False, a: int | None = None) -> None:
        self.I = username.encode("utf-8")
        self.H = hash_alg
        self.N = n
        self.g = g
        self.username_in_x = username_in_x
        self._width = (n.bit_length() + 7) // 8
        self.a = a if a is not None else int.from_bytes(os.urandom(32), "big")
        self.A = pow(g, self.a, n)
        self.K: bytes | None = None
        self.M1: bytes | None = None

    @property
    def A_bytes(self) -> bytes:
        return _pad(self.A, self._width)

    def _x(self, salt: bytes, password: bytes) -> int:
        inner = self.H((self.I if self.username_in_x else b"") + b":" + password
                       ).digest()
        return _hash_int(self.H, salt, inner)

    def process_challenge(self, salt: bytes, b_bytes: bytes,
                          password: bytes) -> bytes:
        """Verarbeitet Apples ``s``/``B`` und liefert den Beweis ``M1``."""
        B = int.from_bytes(b_bytes, "big")
        if B % self.N == 0:
            raise ValueError("Server hat ein ungueltiges B geschickt (B mod N == 0)")

        w = self._width
        k = _hash_int(self.H, _pad(self.N, w), _pad(self.g, w))
        u = _hash_int(self.H, self.A_bytes, _pad(B, w))
        if u == 0:
            raise ValueError("Ungueltiges u (== 0)")

        x = self._x(salt, password)
        # S = (B - k*g^x) ^ (a + u*x)  mod N
        S = pow((B - k * pow(self.g, x, self.N)) % self.N,
                self.a + u * x, self.N)
        self.K = self.H(_pad(S, w)).digest()

        # M1 = H( H(N) XOR H(g) | H(I) | s | A | B | K )
        hn = int.from_bytes(self.H(_pad(self.N, w)).digest(), "big")
        hg = int.from_bytes(self.H(_pad(self.g, w)).digest(), "big")
        xor = (hn ^ hg).to_bytes(self.H().digest_size, "big")

        h = self.H()
        h.update(xor)
        h.update(self.H(self.I).digest())
        h.update(salt)
        h.update(self.A_bytes)
        h.update(_pad(B, w))
        h.update(self.K)
        self.M1 = h.digest()
        return self.M1

    def verify_session(self, m2: bytes) -> bool:
        """Prueft Apples Gegenbeweis ``M2 = H(A | M1 | K)``."""
        if self.K is None or self.M1 is None:
            raise RuntimeError("process_challenge() muss zuerst laufen")
        h = self.H()
        h.update(self.A_bytes)
        h.update(self.M1)
        h.update(self.K)
        return hmac.compare_digest(h.digest(), m2)
