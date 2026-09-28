"""Sign-in session: keep, reuse and renew tokens.

A normal run should *not* trigger a login. That is why the result of the
GSA handshake is stored on disk and reused for as long as Apple accepts it.
The password itself is never stored.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Callable

from ..config import SECRETS_DIR, read_secret, write_secret
from ..errors import AppleError, InteractionRequired
from ..i18n import _
from .gsa import GSAClient, GSAResult

SESSION_FILE = SECRETS_DIR / "session.json"

#: How long we consider a token valid without double-checking.
#: Apple states no lifetime; if it does expire, the first 401 reveals it and
#: we sign in again.
SESSION_MAX_AGE = 14 * 24 * 3600


@dataclass
class Session:
    adsid: str
    idms_token: str
    identity_token: str
    created_at: float
    app_token: str = ""
    #: For the greeting on the dashboard. Sessions from older versions don't
    #: have it - see :func:`remember_first_name`.
    first_name: str = ""

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def probably_valid(self) -> bool:
        return self.age < SESSION_MAX_AGE and self.usable

    @property
    def usable(self) -> bool:
        """Without an app token, developerservices2 rejects every request as
        expired. Sessions from older versions don't have one."""
        return bool(self.app_token)

    @property
    def auth_headers(self) -> dict[str, str]:
        """Authentication towards developerservices2.

        ``X-Apple-GS-Token`` carries the app token **raw** - not as
        base64("<adsid>:<token>"). With the encoded form Apple answers every
        request with "Your session has expired", even though the sign-in has
        just succeeded.
        """
        return {
            "X-Apple-I-Identity-Id": self.adsid,
            "X-Apple-GS-Token": self.app_token,
        }

    # -- Persistence -------------------------------------------------------

    def save(self) -> None:
        write_secret(SESSION_FILE, json.dumps(asdict(self)).encode())

    @classmethod
    def load(cls) -> "Session | None":
        if not SESSION_FILE.exists():
            return None
        try:
            session = cls(**json.loads(read_secret(SESSION_FILE)))
        except Exception:
            return None  # broken or old format - just sign in again
        return session if session.usable else None

    @classmethod
    def clear(cls) -> None:
        SESSION_FILE.unlink(missing_ok=True)

    @classmethod
    def from_gsa(cls, result: GSAResult) -> "Session":
        return cls(adsid=result.adsid, idms_token=result.idms_token,
                   identity_token=result.identity_token,
                   app_token=result.app_token, created_at=time.time(),
                   first_name=result.first_name)


def remember_first_name(teams) -> str:
    """Fills in the first name for sessions that predate it.

    An individual developer team is named after its holder ("Jane Doe"), so
    its first word is the first name - without asking for a new sign-in.
    Companies are left alone: their team name is not a person.
    """
    session = Session.load()
    if session is None or session.first_name:
        return session.first_name if session else ""
    for team in teams:
        if team.type.lower() in ("individual", "free") and team.name.strip():
            session.first_name = team.name.split()[0]
            session.save()
            break
    return session.first_name


def login(apple_id: str, password: str, anisette,
          code_prompt: Callable[[], str] | None = None,
          debug: bool = False) -> Session:
    client = GSAClient(anisette, code_prompt=code_prompt, debug=debug)
    session = Session.from_gsa(client.authenticate(apple_id, password))
    session.save()
    return session


def current(anisette, *, interactive: bool = True) -> Session:
    """The existing session, or a notice that a login is required."""
    session = Session.load()
    if session and session.probably_valid:
        return session
    if not interactive:
        raise InteractionRequired(_(
            "No valid sign-in. Run ‘modstaller login’ once."))
    raise AppleError(_("Not signed in. First: modstaller login"))
