"""The complete path from the IPA to the running app."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .apple import anisette as anisette_mod
from .apple.devservices import DeveloperServices
from .apple.session import Session, remember_teams, session_for_team
from .config import ICONS_DIR, OUT_DIR, WORK_DIR, Settings, find_zsign
from .i18n import _
from .device.connection import ServiceProvider, device_info
from .device.install import install_ipa
from .errors import AppleError, SigningError
from .plan import make_plan, resolve_keep
from .provisioning import (
    Capabilities, ensure_app_id, ensure_certificate, fetch_profile, pick_team,
    profile_info,
)
from .signing import ipa as ipa_mod
from .signing.signer import SignRequest, sign
from .state import store

log = logging.getLogger(__name__)


@dataclass
class InstallOutcome:
    bundle_id: str
    name: str
    transport: str
    days_valid: float
    stripped_extensions: bool
    kept_extensions: int = 0
    new_app_ids: int = 0
    #: The store version a renewal updated the app to - empty if none.
    updated_to: str = ""


def _ipa_mismatch(ipa_platform: str, device_platform: str) -> str:
    if ipa_platform == "tvos":
        return _("This IPA is an Apple TV app - it cannot be installed on an "
                 "iPhone. Pick the Apple TV as the device.")
    if ipa_platform == "xros":
        return _("This IPA is an Apple Vision Pro app - it only runs on a "
                 "Vision Pro. Pick it as the device.")
    return _("This IPA is for iPhone and iPad - an Apple TV needs the app's "
             "tvOS version.")


#: UIDeviceFamily values: 1 iPhone/iPod touch, 2 iPad.
_IPHONE_FAMILY, _IPAD_FAMILY = 1, 2


def incompatibility(info, dev) -> str | None:
    """Why this IPA cannot go on this device - or None if it can.

    * Apple TV and Vision Pro apps only on their own device.
    * iPhone and iPad apps on a Vision Pro are fine - visionOS runs them
      ("Designed for iPad").
    * An iPhone app on an iPad runs in compatibility mode; an iPad-only app
      on an iPhone or iPod touch does not start at all.
    """
    if info.platform != dev.platform:
        if dev.platform == "xros" and info.platform == "ios":
            return None
        return _ipa_mismatch(info.platform, dev.platform)
    families = set(getattr(info, "device_families", None) or [])
    if (dev.platform == "ios" and families == {_IPAD_FAMILY}
            and not dev.product_type.startswith("iPad")):
        return _("This app is made for iPad only and does not start on an "
                 "{kind}.", kind=dev.kind)
    return None


def _store_fields(origin: dict | None, renewing) -> dict:
    if origin:
        return {"store_source": str(origin.get("source") or ""),
                "store_bundle_id": str(origin.get("bundleId") or ""),
                "store_version": str(origin.get("version") or "")}
    if renewing is not None:
        return {"store_source": renewing.store_source,
                "store_bundle_id": renewing.store_bundle_id,
                "store_version": renewing.store_version}
    return {}


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
    display_name: str | None = None,
    icon: Path | None = None,
    keep_extensions: list[str] | None = None,
    spare_app_id: str | None = None,
    store_origin: dict | None = None,
    progress: Callable[[int], None] | None = None,
    on_step: Callable[[str], None] = _say,
) -> InstallOutcome:
    """Signs and installs ``ipa_path``.

    ``store_origin`` (``{source, bundleId, version}``): the IPA came from
    the store - remembered, so the store can offer updates. A renewal keeps
    the origin of the app it renews unless a new one is given.

    ``bundle_id`` pins the identifier on the device instead of deriving it
    from the IPA - a renewal must hit exactly the app that is installed,
    even if it once got a recycled App ID or the IPA's own ID has changed
    since. ``renewing`` is that app's record; its history is kept.
    ``account`` is the adsid of the Apple account to sign with - the active
    one if not given.

    From the install screen's editor: ``display_name`` and ``icon`` (a
    square PNG) replace name and icon; ``keep_extensions`` lists the
    extensions that stay (None: none on free accounts, all on paid ones -
    or ``strip_extensions`` as before); ``spare_app_id`` puts the app under
    an existing, unused App ID. A ``bundle_id`` given without ``renewing``
    is the editor's own choice.
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
        dev = await device_info(sp.lockdown, sp.transport)
        on_step("\n" + _("Device: {name}, {os} {version}",
                              name=dev.name, os=dev.os_name, version=dev.ios_version))
        problem = incompatibility(info, dev)
        if problem:
            raise SigningError(problem)
        if dev.platform == "xros" and info.platform == "ios":
            on_step("  " + _("An iPhone/iPad app on the Vision Pro - visionOS "
                             "runs it in a window (“Designed for iPad”)."))
        if icon is not None and info.platform in ("tvos", "xros"):
            # tvOS and visionOS icons are layered image stacks - a PNG does
            # not replace them.
            on_step("  " + _("A new icon is not possible for Apple TV and "
                             "Vision Pro apps - the app keeps its own."))
            icon = None
        # Network-only devices do not always tell their Developer Mode -
        # the device check names it instead.
        if not dev.developer_mode and dev.platform == "ios":
            raise SigningError(_(
                "Developer Mode is off. Turn it on under Settings > Privacy & "
                "Security > Developer Mode on the iPhone."))

        # 3. Sign-in and team.
        session = Session.load(account)
        if session is None:
            raise AppleError("Not signed in. First run: modstaller login")
        ani = anisette_mod.build(settings.anisette_provider,
                                 settings.anisette_server)
        api = DeveloperServices(session, ani, platform=dev.platform)

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

        # 6. Which extensions stay. On free accounts each costs an App ID
        #    from a quota of ten per week - so by default none do; the app
        #    itself runs just fine without them.
        keep = resolve_keep(info, keep_extensions, caps.is_free, strip_extensions)
        drop = [p for p in info.extensions if p not in keep]
        if drop:
            on_step("  " + _("Removing {count} extension(s) (saves {count} "
                             "App ID(s) from the weekly quota)", count=len(drop)))
        if info.has_watch:
            on_step("  " + _("Removing the Apple Watch app - it cannot be "
                             "installed this way."))

        # 7. App IDs and profiles - planned first, so a quota that does not
        #    suffice stops us before anything is created.
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

        existing, quota = api.app_id_overview(team.team_id)
        plan = make_plan(info, team_id=team.team_id, is_free=caps.is_free,
                         app_ids=existing, quota=quota, keep=keep,
                         bundle_id=bundle_id, spare=spare_app_id,
                         pinned=renewing is not None, protected=protected)
        for note in plan.notes:
            on_step("  " + note)
        on_step(f"\nApp ID {plan.main_id} …")
        # A chosen or pinned ID never falls back to a spare one: that would
        # be a second app next to the one the user asked for.
        app_id = ensure_app_id(api, team, plan.main_id, display_name or info.name,
                               reuse_when_exhausted=not (bundle_id or spare_app_id),
                               protected=protected, existing=existing)
        new_id = app_id.identifier
        if new_id != plan.main_id:
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

        # Every kept extension needs its own App ID and profile - zsign
        # picks the matching one per bundle.
        ext_profiles: list[Path] = []
        by_path = {e.path: e for e in info.extension_details}
        for path in keep:
            ext = by_path[path]
            ident = ext.bundle_id_for(info.bundle_id, new_id)
            on_step(f"App ID {ident} …")
            ext_app = ensure_app_id(api, team, ident,
                                    f"{display_name or info.name} {ext.name}",
                                    existing=existing)
            ext_profiles.append(fetch_profile(api, team, ext_app))

        # 8. Sign. Only some extensions stay: unpack without the others and
        #    let zsign sign the folder.
        out = OUT_DIR / f"{new_id}.ipa"
        on_step("\nSigning …")
        started = time.time()
        source = info.path
        unpacked: Path | None = None
        if keep and drop:
            from .signing.prepare import unpack_without
            unpacked = unpack_without(info.path, info.app_dir, drop, WORK_DIR)
            source = unpacked
        try:
            sign(SignRequest(
                ipa=source, output=out, p12=p12, p12_password=password,
                profile=profile_path, extra_profiles=ext_profiles,
                bundle_id=new_id, display_name=display_name or None,
                strip_extensions=bool(info.extensions) and not keep,
                strip_watch=info.has_watch, icon=icon,
            ), zsign=find_zsign(settings.zsign_path) or settings.zsign_path,
               on_warning=on_step)
        finally:
            if unpacked is not None:
                shutil.rmtree(unpacked, ignore_errors=True)
        on_step(f"  done in {time.time() - started:.1f}s "
             f"({out.stat().st_size / 1e6:.0f} MB)")

        # 9. Install.
        on_step("\nInstalling …")
        result = await install_ipa(sp, out, progress=progress)

        # 10. Remember it, so the refresh later knows what to do - including
        #     the editor's choices.
        kept_icon = ""
        if icon is not None and icon.is_file():
            ICONS_DIR.mkdir(parents=True, exist_ok=True)
            stored = ICONS_DIR / f"{new_id}.png"
            if icon.resolve() != stored.resolve():
                shutil.copyfile(icon, stored)
            kept_icon = str(stored)
        store.record(store.InstallRecord(
            bundle_id=new_id,
            original_bundle_id=info.bundle_id,
            name=display_name or info.name,
            team_id=team.team_id,
            udid=dev.udid,
            platform=dev.platform,
            source_ipa=str(info.path.resolve()),
            app_id_id=app_id.app_id_id,
            profile_path=str(profile_path),
            expires_at=(prof.expires_at.timestamp() if prof.expires_at
                        else time.time() + caps.profile_days * 86400),
            installed_at=(renewing.installed_at if renewing
                          else time.time()),
            last_refresh_at=time.time() if renewing else 0.0,
            strip_extensions=not keep,
            adsid=session.adsid,
            display_name=display_name or "",
            icon_path=kept_icon,
            kept_extensions=keep,
            **_store_fields(store_origin, renewing),
        ))

    return InstallOutcome(bundle_id=new_id, name=display_name or info.name,
                          transport=result.transport,
                          days_valid=prof.days_left,
                          stripped_extensions=bool(drop),
                          kept_extensions=len(keep),
                          new_app_ids=len(plan.new_app_ids))


async def refresh(
    *,
    udid: str | None = None,
    settings: Settings | None = None,
    threshold_days: float | None = None,
    only: str | None = None,
    store_updates: bool = False,
    progress: Callable[[int], None] | None = None,
    on_step: Callable[[str], None] = _say,
) -> list[InstallOutcome]:
    """Renews apps whose profile expires soon.

    Uses the original IPA remembered at install time and signs it under the
    bundle ID the app has *on the device* - not one derived from the IPA.
    Those can differ (a recycled App ID, a newer IPA with a new ID), and a
    different ID is a second app to iOS: installed next to the old one, with
    none of its data.

    ``store_updates``: an app from the store is brought to the newest version
    its source offers on the way - same bundle ID, so the data stays. If the
    original IPA of a store app is gone, the store fetches it again anyway.
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
        origin = None
        if rec.store_bundle_id and (store_updates or not source.is_file()):
            fetched = await asyncio.to_thread(
                _store_ipa, rec, store_updates, on_step)
            if fetched is not None:
                source, origin = fetched
        if not source.is_file():
            on_step("\n" + _("{name}: original IPA missing ({path}) - skipped.",
                                   name=rec.name, path=source))
            continue
        account = account_for(rec)
        if account is None:
            on_step("\n" + _("{name}: the Apple account of team {team} is not "
                             "signed in - skipped.",
                             name=rec.name, team=rec.team_id))
            continue
        on_step("\n=== " + _("Renewing {name} ({expiry})",
                                   name=rec.name, expiry=rec.expiry_text) + " ===")
        outcome = await install(
            source, udid=udid or rec.udid, team_id=rec.team_id,
            account=account,
            settings=settings, strip_extensions=rec.strip_extensions,
            bundle_id=rec.bundle_id, renewing=rec,
            display_name=rec.display_name or None,
            icon=(Path(rec.icon_path) if rec.icon_path
                  and Path(rec.icon_path).is_file() else None),
            keep_extensions=rec.kept_extensions,
            store_origin=origin,
            progress=progress, on_step=on_step,
        )
        if origin and origin["version"] != rec.store_version:
            outcome.updated_to = origin["version"]
        results.append(outcome)
    return results


def _store_ipa(rec, update: bool, on_step) -> tuple[Path, dict] | None:
    """The IPA a store app is renewed with: a newer version if ``update``,
    else the installed one again (when its file is gone). None: keep what
    there is - a store that cannot be reached must never stop a renewal."""
    from .store import download as store_download
    from .store.catalog import CATALOG
    from .store.updates import newer

    try:
        CATALOG.ensure_loaded()
        app = CATALOG.find(rec.store_bundle_id, rec.store_source)
        if app is None:
            return None
        if update and newer(rec.store_version, app.version):
            version = app.version
            on_step("\n" + _("{name}: version {version} is available in the store - "
                             "updating while renewing.", name=rec.name, version=version))
        else:
            version = rec.store_version or None
        path = store_download.download(app, version)
        return path, {"source": app.source_url, "bundleId": app.bundle_id,
                      "version": version or app.version}
    except Exception as exc:
        log.warning("Store lookup for %s failed: %s", rec.bundle_id, exc)
        on_step("\n" + _("{name}: the store is not reachable ({error}) - renewing "
                         "the installed version.", name=rec.name, error=exc))
        return None


def account_for(rec: "store.InstallRecord") -> str | None:
    """The account that renews ``rec``: the one that signed it, else the one
    its team belongs to. Records from before accounts were tracked fall back
    to the active account - as they always did."""
    if rec.adsid:
        return rec.adsid if Session.load(rec.adsid) else None
    session = session_for_team(rec.team_id) or Session.load()
    return session.adsid if session else None
