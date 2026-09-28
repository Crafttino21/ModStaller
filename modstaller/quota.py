"""How much is left: App IDs this week and app slots on the iPhone.

Free accounts have two limits that people keep running into:

* **App IDs**: at most ten may be *created* in a rolling seven-day window.
  Apple counts creations, not existing ones - deleting gives nothing back.
  Apple reports the count itself (``listAppIds``: ``maxQuantity`` /
  ``availableQuantity``); when the next one frees up it does not say. That
  is estimated from the creation times: Apple's ``expirationDate`` (created
  + 7 days) for the App IDs that still exist, and our own log for the ones
  deleted since (:mod:`.state.appid_log`).
* **Apps on the device**: at most three apps with a free profile at once.

Paid accounts have neither limit in practice.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .apple.devservices import AppID, AppIdQuota

#: Apple's window for newly created App IDs.
WINDOW = 7 * 86400


@dataclass
class TeamQuota:
    is_free: bool
    maximum: int | None           # App IDs per window (None: no limit)
    available: int | None         # still open in the window (None: unknown)
    #: When the next App ID becomes available again - an estimate, and
    #: only when none is available right now.
    next_free_at: float | None = None
    #: Creation times inside the window, oldest first - the UI shows when
    #: each one returns.
    returns_at: list[float] = field(default_factory=list)


def creation_times(app_ids: list[AppID], logged: list[float],
                   now: float | None = None) -> list[float]:
    """When the App IDs counted in the window were created (oldest first).

    Existing ones: expirationDate - 7 days. Deleted ones: only our log knows
    them; a logged time that matches an existing App ID within a minute is
    the same creation and counts once.
    """
    now = time.time() if now is None else now
    known = [a.expires_at.timestamp() - WINDOW for a in app_ids if a.expires_at]
    times = list(known)
    for t in logged:
        if not any(abs(t - k) < 60 for k in known):
            times.append(t)
    return sorted(t for t in times if now - WINDOW < t <= now)


def team_quota(is_free: bool, app_ids: list[AppID], quota: AppIdQuota,
               logged: list[float], now: float | None = None) -> TeamQuota:
    now = time.time() if now is None else now
    if not is_free:
        return TeamQuota(is_free=False, maximum=quota.maximum,
                         available=quota.available)
    maximum = quota.maximum if quota.maximum is not None else 10
    created = creation_times(app_ids, logged, now)
    available = quota.available
    if available is None:
        # Apple did not say - count what we know of (a lower bound on use).
        available = max(0, maximum - len(created))
    returns = [t + WINDOW for t in created]
    next_free = returns[0] if available == 0 and returns else None
    return TeamQuota(is_free=True, maximum=maximum, available=available,
                     next_free_at=next_free, returns_at=returns)


@dataclass
class Demand:
    """What an install would take from the quota."""
    new_app_ids: list[str]        # identifiers that do not exist yet
    existing: list[str]           # already registered - cost nothing

    @property
    def cost(self) -> int:
        return len(self.new_app_ids)


def demand(identifiers: list[str], app_ids: list[AppID]) -> Demand:
    have = {a.identifier.lower() for a in app_ids}
    new = [i for i in identifiers if i.lower() not in have]
    return Demand(new_app_ids=new,
                  existing=[i for i in identifiers if i.lower() in have])
