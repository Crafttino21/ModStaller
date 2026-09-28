"""When ModStaller created App IDs - per team, for the last eight days.

Apple keeps counting a created App ID against the weekly quota even after
it was deleted, but no longer lists it. Without this log nobody could say
when that slot comes back (see quota.creation_times).
"""

from __future__ import annotations

import json
import time

from ..config import DATA_DIR

LOG_FILE = DATA_DIR / "appid_log.json"

#: Older entries no longer matter - the window is seven days.
KEEP = 8 * 86400


def _load() -> dict[str, list[dict]]:
    try:
        data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def created(team_id: str, identifier: str, when: float | None = None) -> None:
    when = time.time() if when is None else when
    data = _load()
    entries = [e for e in data.get(team_id, [])
               if isinstance(e, dict) and when - e.get("at", 0) < KEEP]
    entries.append({"identifier": identifier, "at": when})
    data[team_id] = entries
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass    # a missing log only makes the estimate vaguer


def times(team_id: str, now: float | None = None) -> list[float]:
    now = time.time() if now is None else now
    return sorted(e["at"] for e in _load().get(team_id, [])
                  if isinstance(e, dict) and isinstance(e.get("at"), (int, float))
                  and now - e["at"] < KEEP)
