"""What an install will cost - decided before anything is created at Apple.

The install screen shows it live while the IPA is being edited (name, icon,
bundle ID, which extensions stay), and the pipeline follows exactly the same
plan. Everything here is pure: the caller brings the IPA info and Apple's
App ID list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .apple.devservices import AppID, AppIdQuota
from .errors import AppleError, SigningError
from .i18n import _
from .provisioning import app_id_in_use, derive_bundle_id
from .quota import demand
from .signing.ipa import ExtensionInfo, IPAInfo

#: Letters, digits and hyphens, at least two dot-separated parts.
BUNDLE_ID = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")


class QuotaExhausted(AppleError):
    """More new App IDs needed than the free account has left this week."""


def check_bundle_id(identifier: str) -> str:
    identifier = identifier.strip()
    if not BUNDLE_ID.match(identifier) or len(identifier) > 155:
        raise SigningError(_(
            "“{id}” is not a valid bundle ID - letters, digits and hyphens, "
            "separated by dots (e.g. com.example.app).", id=identifier))
    return identifier


def movable(info: IPAInfo) -> dict[str, ExtensionInfo]:
    """Extensions that can be kept: their ID carries the app's as prefix."""
    return {e.path: e for e in info.extension_details
            if e.bundle_id_for(info.bundle_id, info.bundle_id) is not None}


def default_keep(info: IPAInfo, is_free: bool, strip: bool | None = None) -> list[str]:
    """Without a choice: none on free accounts (each costs an App ID), all
    on paid ones. ``strip`` is the older all-or-nothing switch."""
    strip_all = is_free if strip is None else strip
    return [] if strip_all else [p for p in info.extensions if p in movable(info)]


def resolve_keep(info: IPAInfo, keep: list[str] | None, is_free: bool,
                 strip: bool | None = None) -> list[str]:
    if keep is None:
        return default_keep(info, is_free, strip)
    can = movable(info)
    unknown = [k for k in keep if k not in can]
    if unknown:
        raise SigningError(_("These extensions cannot be kept: {names}",
                             names=", ".join(unknown)))
    return [p for p in info.extensions if p in keep]   # the IPA's order


@dataclass
class Plan:
    main_id: str
    #: (extension path, App ID identifier) for every kept extension.
    extensions: list[tuple[str, str]]
    new_app_ids: list[str]
    #: Set when the app goes under an existing, unused App ID.
    spare: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def identifiers(self) -> list[str]:
        return [self.main_id] + [i for _p, i in self.extensions]


def _extension_ids(info: IPAInfo, keep: list[str], main_id: str) -> list[tuple[str, str]]:
    can = movable(info)
    return [(p, can[p].bundle_id_for(info.bundle_id, main_id)) for p in keep]


def spare_candidates(app_ids: list[AppID], protected: set[str]) -> list[AppID]:
    """Existing App IDs no installed app depends on - reusable for free."""
    return [a for a in app_ids if not app_id_in_use(a.identifier, protected)]


def make_plan(info: IPAInfo, *, team_id: str, is_free: bool,
              app_ids: list[AppID], quota: AppIdQuota,
              keep: list[str], bundle_id: str | None = None,
              spare: str | None = None, pinned: bool = False,
              protected: set[str] | None = None) -> Plan:
    """Decides the identifiers and checks them against the quota.

    ``bundle_id``: chosen in the editor (or pinned for a renewal - then
    ``pinned``). ``spare``: the user picked an existing App ID for the app.
    Without either, a free account that cannot afford a new App ID for the
    app falls back to a spare one on its own - as before.
    """
    protected = protected or set()
    if spare:
        match = next((a for a in app_ids if a.identifier.lower() == spare.lower()), None)
        if match is None:
            raise AppleError(_("The App ID {id} does not exist (any more).", id=spare))
        main = match.identifier
    elif bundle_id:
        main = bundle_id if pinned else check_bundle_id(bundle_id)
    else:
        main = derive_bundle_id(info.bundle_id, team_id)

    def build(main_id: str, used_spare: str | None) -> Plan:
        exts = _extension_ids(info, keep, main_id)
        need = demand([main_id] + [i for _p, i in exts], app_ids)
        return Plan(main_id=main_id, extensions=exts,
                    new_app_ids=need.new_app_ids, spare=used_spare or spare)

    plan = build(main, None)
    available = quota.available
    if not is_free or available is None or len(plan.new_app_ids) <= available:
        return plan

    # Free account, not enough left. The app itself may move to a spare
    # App ID - but only if nobody chose its identifier.
    if not (bundle_id or spare) and main in plan.new_app_ids:
        for candidate in spare_candidates(app_ids, protected):
            alt = build(candidate.identifier, candidate.identifier)
            if len(alt.new_app_ids) <= available:
                alt.notes.append(_(
                    "Not enough App IDs left this week - the app goes under "
                    "the unused App ID {id}.", id=candidate.identifier))
                return alt

    raise QuotaExhausted(_(
        "This install needs {needed} new App ID(s), but only {available} of "
        "{maximum} are left this week. Leave out extensions or reuse an "
        "unused App ID in the install screen.",
        needed=len(plan.new_app_ids), available=available,
        maximum=quota.maximum if quota.maximum is not None else "?"))
