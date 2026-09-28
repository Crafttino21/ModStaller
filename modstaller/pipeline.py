"""The complete path from the IPA to the running app."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .apple import anisette as anisette_mod
from .apple.devservices import DeveloperServices
from .apple.session import Session, remember_teams, session_for_team
from .config import OUT_DIR, Settings, find_zsign
from .i18n import _
from .device.connection import ServiceProvider, device_info
from .device.install import install_ipa
from .errors import AppleError, SigningError
from .provisioning import (
    Capabilities, derive_bundle_id, ensure_app_id, ensure_certificate,
    fetch_profile, pick_team, profile_info,
)
from .signing import ipa as ipa_mod
from .signing.signer import SignRequest, sign
from .state import store


@dataclass
class InstallOutcome:
    bundle_id: str
    name: str
    transport: str
    days_valid: float
    stripped_extensions: bool


def _say(msg: str) -> None:
    print(msg, flush=True)


async def install(
    ipa_path: Path,
    *,
    udid: str | None = None,
    team_id: str | None = None,
    account: str | None = None,
    settings: Settings | None = None,
    strip_extensions: bool | None = None,
    revoke_conflicting_cert: bool = False,
    bundle_id: str | None = None,
    renewing: "store.InstallRecord | None" = None,
    progress: Callable[[int], None] | None = None,
    on_step: Callable[[str], None] = _say,
) -> InstallOutcome:
    """Signs and installs ``ipa_path``.

    ``bundle_id`` pins the identifier on the device instead of deriving it
    from the IPA - a renewal must hit exactly the app that is installed,
    even if it once got a recycled App ID or the IPA's own ID has changed
    since. ``renewing`` is that app's record; its history is kept.
    ``account`` is the adsid of the Apple account to sign with - the active
    one if not given.
    """
    settings = settings or Settings.load()

    # 1. Check the IPA first - that is cheap and catches most errors
    #    before we touch Apple's quotas.
    info = ipa_mod.inspect(ipa_path)
    on_step(f"IPA read:\n{info.summary()}")
    if info.encrypted:
        raise SigningError(_(
            "This IPA is App Store encrypted (FairPlay DRM) and cannot be "
            "re-signed. A decrypted IPA is required."))

    # 2. Device - likewise before any contact with Apple.
    async with ServiceProvider(udid) as sp:
        dev = await device_info(sp.lockdown)
        on_step("\n" + _("Device: {name}, iOS {version}",
                              name=dev.name, version=dev.ios_version))
        if not dev.developer_mode:
            raise SigningError(_(
                "Developer Mode is off. Turn it on under Settings > Privacy & "
                "Security > Developer Mode on the iPhone."))

        # 3. Sign-in and team.
        session = Session.load(account)
        if session is None:
            raise AppleError("Not signed in. First run: modstaller login")
        ani = anisette_mod.build(settings.anisette_provider,
                                 settings.anisette_server)
        api = DeveloperServices(session, ani)

        teams = api.list_teams()
        remember_teams(session.adsid, teams)
        team = pick_team(teams, team_id or settings.default_team_id)
        caps = Capabilities.for_team(team)
        on_step(f"Team:   {team}")

        # 4. Register the device with the team (idempotent).
        api.register_device(team.team_id, dev.udid, dev.name)

        # 5. Certificate.
        on_step("\n" + _("Obtaining the certificate …"))
        p12, password = ensure_certificate(
            api, team, dev.name, revoke_conflicting=revoke_conflicting_cert)

        # 6. Extensions: on free accounts each one costs an App ID from a
        #    quota of ten per week. The default is therefore to remove them -
        #    the app itself runs just fine without them.
        strip = (caps.is_free and bool(info.extensions)
                 if strip_extensions is None else strip_extensions)
        if strip and info.extensions:
            on_step("  " + _("Removing {count} extension(s) (saves {count} "
                                 "App ID(s) from the weekly quota)",
                                 count=len(info.extensions)))

        # 7. App ID and profile.
        #
        # The installed apps protect their App IDs from being recycled -
        # otherwise a foreign app would eventually lose the ability to be
        # renewed because ModStaller gave away its App ID.
        protected: set[str] = set()
        try:
            from .device.install import list_apps
            protected = set(await list_apps(sp))
        except Exception:
            pass

        wanted = bundle_id or derive_bundle_id(info.bundle_id, team.team_id)
        on_step(f"\nApp ID {wanted} …")
        # A pinned ID never falls back to a spare one: that would be a
        # second app next to the one we are meant to renew.
        app_id = ensure_app_id(api, team, wanted, info.name,
                               reuse_when_exhausted=bundle_id is None,
                               protected=protected)
        new_id = app_id.identifier
        if new_id != wanted:
            on_step(_(
                "  Weekly quota exhausted - ModStaller reuses the free App ID"
                "\n  {app_id}. The app runs under it perfectly normally; "
                "only\n  the internal identifier does not match the name.",
                app_id=new_id))
        profile_path = fetch_profile(api, team, app_id)
        prof = profile_info(profile_path)
        caps = caps.reconcile(prof)
        on_step(f"  Profile valid: {prof.days_left:.1f} days "
             f"({caps.describe()})")

        # 8. Sign.
        out = OUT_DIR / f"{new_id}.ipa"
        on_step("\nSigning …")
        started = time.time()
        sign(SignRequest(
            ipa=info.path, output=out, p12=p12, p12_password=password,
            profile=profile_path, bundle_id=new_id,
            strip_extensions=strip,
        ), zsign=find_zsign(settings.zsign_path) or settings.zsign_path)
        on_step(f"  done in {time.time() - started:.1f}s "
             f"({out.stat().st_size / 1e6:.0f} MB)")

        # 9. Install.
        on_step("\nInstalling …")
        result = await install_ipa(sp, out, progress=progress)

        # 10. Remember it, so the refresh later knows what to do.
        store.record(store.InstallRecord(
            bundle_id=new_id,
            original_bundle_id=info.bundle_id,
            name=info.name,
            team_id=team.team_id,
            udid=dev.udid,
            source_ipa=str(info.path.resolve()),
            app_id_id=app_id.app_id_id,
            profile_path=str(profile_path),
            expires_at=(prof.expires_at.timestamp() if prof.expires_at
                        else time.time() + caps.profile_days * 86400),
            installed_at=(renewing.installed_at if renewing
                          else time.time()),
            last_refresh_at=time.time() if renewing else 0.0,
            strip_extensions=strip,
            adsid=session.adsid,
        ))

    return InstallOutcome(bundle_id=new_id, name=info.name,
                          transport=result.transport,
                          days_valid=prof.days_left,
                          stripped_extensions=strip)


async def refresh(
    *,
    udid: str | None = None,
    settings: Settings | None = None,
    threshold_days: float | None = None,
    only: str | None = None,
    progress: Callable[[int], None] | None = None,
    on_step: Callable[[str], None] = _say,
) -> list[InstallOutcome]:
    """Renews apps whose profile expires soon.

    Uses the original IPA remembered at install time and signs it under the
    bundle ID the app has *on the device* - not one derived from the IPA.
    Those can differ (a recycled App ID, a newer IPA with a new ID), and a
    different ID is a second app to iOS: installed next to the old one, with
    none of its data.
    """
    settings = settings or Settings.load()
    threshold = (settings.renew_threshold_days if threshold_days is None
                 else threshold_days)

    if only:
        due = [r for r in store.all_installs() if r.bundle_id == only
               or r.original_bundle_id == only]
        if not due:
            raise SigningError(f"Nothing installed under {only!r}.")
    else:
        due = store.due_for_refresh(threshold)

    if not due:
        on_step(f"Nothing due (threshold: {threshold:.0f} days).")
        return []

    results: list[InstallOutcome] = []
    for rec in due:
        source = Path(rec.source_ipa)
        if not source.is_file():
            on_step("\n" + _("{name}: original IPA missing ({path}) - skipped.",
                                   name=rec.name, path=source))
            continue
        account = _account_for(rec)
        if account is None:
            on_step("\n" + _("{name}: the Apple account of team {team} is not "
                             "signed in - skipped.",
                             name=rec.name, team=rec.team_id))
            continue
        on_step("\n=== " + _("Renewing {name} ({expiry})",
                                   name=rec.name, expiry=rec.expiry_text) + " ===")
        results.append(await install(
            source, udid=udid or rec.udid, team_id=rec.team_id,
            account=account,
            settings=settings, strip_extensions=rec.strip_extensions,
            bundle_id=rec.bundle_id, renewing=rec,
            progress=progress, on_step=on_step,
        ))
    return results


def _account_for(rec: "store.InstallRecord") -> str | None:
    """The account that renews ``rec``: the one that signed it, else the one
    its team belongs to. Records from before accounts were tracked fall back
    to the active account - as they always did."""
    if rec.adsid:
        return rec.adsid if Session.load(rec.adsid) else None
    session = session_for_team(rec.team_id) or Session.load()
    return session.adsid if session else None
