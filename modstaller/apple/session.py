"""Anmeldesitzung: Token halten, wiederverwenden, erneuern.

Ein normaler Lauf soll *keinen* Login ausloesen. Deshalb liegt das Ergebnis
des GSA-Handshakes auf Platte und wird wiederverwendet, solange Apple es
akzeptiert. Das Passwort selbst wird nie gespeichert.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Callable

from ..config import SECRETS_DIR, read_secret, write_secret
from ..errors import AppleError, InteractionRequired
from .gsa import GSAClient, GSAResult

SESSION_FILE = SECRETS_DIR / "session.json"

#: Wie lange wir ein Token ohne Gegenprobe als gueltig ansehen.
#: Apple nennt keine Lebensdauer; laeuft es doch ab, faellt das beim ersten
#: 401 auf und wir melden uns neu an.
SESSION_MAX_AGE = 14 * 24 * 3600


@dataclass
class Session:
    adsid: str
    idms_token: str
    identity_token: str
    created_at: float

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def probably_valid(self) -> bool:
        return self.age < SESSION_MAX_AGE

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "X-Apple-I-Identity-Id": self.adsid,
            "X-Apple-GS-Token": self.identity_token,
        }

    # -- Persistenz --------------------------------------------------------

    def save(self) -> None:
        write_secret(SESSION_FILE, json.dumps(asdict(self)).encode())

    @classmethod
    def load(cls) -> "Session | None":
        if not SESSION_FILE.exists():
            return None
        try:
            return cls(**json.loads(read_secret(SESSION_FILE)))
        except Exception:
            return None  # kaputt oder altes Format - einfach neu anmelden

    @classmethod
    def clear(cls) -> None:
        SESSION_FILE.unlink(missing_ok=True)

    @classmethod
    def from_gsa(cls, result: GSAResult) -> "Session":
        return cls(adsid=result.adsid, idms_token=result.idms_token,
                   identity_token=result.identity_token, created_at=time.time())


def login(apple_id: str, password: str, anisette,
          code_prompt: Callable[[], str] | None = None) -> Session:
    client = GSAClient(anisette, code_prompt=code_prompt)
    session = Session.from_gsa(client.authenticate(apple_id, password))
    session.save()
    return session


def current(anisette, *, interactive: bool = True) -> Session:
    """Die bestehende Sitzung, oder ein Hinweis, dass ein Login noetig ist."""
    session = Session.load()
    if session and session.probably_valid:
        return session
    if not interactive:
        raise InteractionRequired(
            "Keine gueltige Anmeldung. Einmal 'modstaller login' ausfuehren."
        )
    raise AppleError("Nicht angemeldet. Zuerst: modstaller login")
