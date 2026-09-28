"""Sign-in session: keep, reuse and renew tokens.

A normal run should *not* trigger a login. That is why the result of the
GSA handshake is stored on disk and reused for as long as Apple accepts it.
The password itself is never stored.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from typing import Callable

from ..config import SECRETS_DIR, read_secret, write_secret
from ..errors import AppleError, InteractionRequired
from ..i18n import _
from .gsa import GSAClient, GSAResult

#: Where the one session of older versions lived. Moved into
#: :data:`ACCOUNTS_DIR` on first use - see :func:`_migrate`.
SESSION_FILE = SECRETS_DIR / "session.json"
#: One file per signed-in Apple account, named after its adsid.
ACCOUNTS_DIR = SECRETS_DIR / "accounts"
#: Which account is active (new installs use it) and which team belongs to
#: which account (a renewal must sign with the account that owns the team).
ACCOUNTS_INDEX = SECRETS_DIR / "accounts.json"

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
    #: The Apple ID, to tell accounts apart. Sessions from older versions
    #: don't have it until the next sign-in.
    apple_id: str = ""

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

    @property
    def label(self) -> str:
        """How the account is shown when there is more than one."""
        return self.apple_id or self.first_name or self.adsid

    # -- Persistence -------------------------------------------------------

    def save(self) -> None:
        _migrate()
        write_secret(_account_file(self.adsid),
                     json.dumps(asdict(self)).encode())
        index = _read_index()
        if not index["active"]:
            index["active"] = self.adsid
            _write_index(index)

    @classmethod
    def load(cls, adsid: str | None = None) -> "Session | None":
        """The session of ``adsid`` - or of the active account."""
        _migrate()
        if adsid is None:
            adsid = active_adsid()
            if adsid is None:
                return None
        return _load_file(_account_file(adsid))

    @classmethod
    def clear(cls, adsid: str | None = None) -> None:
        """Signs one account out - the active one unless ``adsid`` says
        otherwise. The next account moves up to active."""
        _migrate()
        index = _read_index()
        adsid = adsid or active_adsid()
        if not adsid:
            return
        _account_file(adsid).unlink(missing_ok=True)
        index["teams"] = {t: a for t, a in index["teams"].items()
                          if a != adsid}
        if index["active"] == adsid:
            rest = list_accounts()
            index["active"] = rest[0].adsid if rest else None
        _write_index(index)

    @classmethod
    def from_gsa(cls, result: GSAResult, apple_id: str = "") -> "Session":
        return cls(adsid=result.adsid, idms_token=result.idms_token,
                   identity_token=result.identity_token,
                   app_token=result.app_token, created_at=time.time(),
                   first_name=result.first_name, apple_id=apple_id)


# -- Several accounts ------------------------------------------------------


def _account_file(adsid: str):
    # The adsid comes from Apple - never let it pick a path of its own.
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", adsid).lstrip(".") or "_"
    return ACCOUNTS_DIR / f"{safe}.json"


def _load_file(path) -> "Session | None":
    if not path.exists():
        return None
    try:
        session = Session(**json.loads(read_secret(path)))
    except Exception:
        return None  # broken or old format - just sign in again
    return session if session.usable else None


def _read_index() -> dict:
    index = {"active": None, "teams": {}}
    if ACCOUNTS_INDEX.exists():
        try:
            raw = json.loads(read_secret(ACCOUNTS_INDEX))
            if isinstance(raw.get("active"), str):
                index["active"] = raw["active"]
            if isinstance(raw.get("teams"), dict):
                index["teams"] = {str(t): str(a)
                                  for t, a in raw["teams"].items()}
        except Exception:
            pass
    return index


def _write_index(index: dict) -> None:
    # The status is polled while this is written - never show it half done.
    tmp = ACCOUNTS_INDEX.with_suffix(".tmp")
    write_secret(tmp, json.dumps(index, indent=2).encode())
    os.replace(tmp, ACCOUNTS_INDEX)


def _migrate() -> None:
    """Moves the single session of older versions into the account list."""
    if not SESSION_FILE.exists():
        return
    session = _load_file(SESSION_FILE)
    if session is not None:
        write_secret(_account_file(session.adsid),
                     json.dumps(asdict(session)).encode())
        index = _read_index()
        index["active"] = index["active"] or session.adsid
        _write_index(index)
    SESSION_FILE.unlink(missing_ok=True)


def list_accounts() -> list[Session]:
    """Every signed-in account, in the order they were added."""
    _migrate()
    if not ACCOUNTS_DIR.is_dir():
        return []
    found = (_load_file(f) for f in ACCOUNTS_DIR.glob("*.json"))
    return sorted((s for s in found if s is not None),
                  key=lambda s: s.created_at)


def active_adsid() -> str | None:
    """The account new installs use. If the one marked active is gone, the
    oldest remaining account takes its place."""
    _migrate()
    active = _read_index()["active"]
    if active and _account_file(active).exists():
        return active
    rest = list_accounts()
    return rest[0].adsid if rest else None


def set_active(adsid: str) -> None:
    if Session.load(adsid) is None:
        raise AppleError(_("This account is not signed in."))
    index = _read_index()
    index["active"] = adsid
    _write_index(index)


def find_account(key: str) -> "Session | None":
    """An account by Apple ID (any case) or adsid - for the command line."""
    key = key.strip().lower()
    for s in list_accounts():
        if key in (s.adsid.lower(), s.apple_id.lower()):
            return s
    return None


def remember_teams(adsid: str, teams) -> None:
    """Notes which account a team belongs to, so a renewal later signs with
    the right account."""
    index = _read_index()
    changed = False
    for team in teams:
        if index["teams"].get(team.team_id) != adsid:
            index["teams"][team.team_id] = adsid
            changed = True
    if changed:
        _write_index(index)


def session_for_team(team_id: str) -> "Session | None":
    adsid = _read_index()["teams"].get(team_id)
    return Session.load(adsid) if adsid else None


def remember_first_name(teams, adsid: str | None = None) -> str:
    """Fills in the first name for sessions that predate it.

    An individual developer team is named after its holder ("Jane Doe"), so
    its first word is the first name - without asking for a new sign-in.
    Companies are left alone: their team name is not a person.
    """
    session = Session.load(adsid)
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
    session = Session.from_gsa(client.authenticate(apple_id, password),
                               apple_id=apple_id)
    session.save()
    set_active(session.adsid)
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
