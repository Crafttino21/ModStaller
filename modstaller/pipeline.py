"""Der komplette Weg von der IPA zur laufenden App."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .apple import anisette as anisette_mod
from .apple.devservices import DeveloperServices
from .apple.session import Session
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
    settings: Settings | None = None,
    strip_extensions: bool | None = None,
    revoke_conflicting_cert: bool = False,
    progress: Callable[[int], None] | None = None,
    on_step: Callable[[str], None] = _say,
) -> InstallOutcome:
    settings = settings or Settings.load()

    # 1. IPA zuerst pruefen - das ist billig und faengt die meisten Fehler,
    #    bevor wir Apples Kontingente anfassen.
    info = ipa_mod.inspect(ipa_path)
    on_step(f"IPA gelesen:\n{info.summary()}")
    if info.encrypted:
        raise SigningError(_(
            "This IPA is App Store encrypted (FairPlay DRM) and cannot be "
            "re-signed. A decrypted IPA is required."))

    # 2. Geraet - ebenfalls vor jedem Apple-Kontakt.
    async with ServiceProvider(udid) as sp:
        dev = await device_info(sp.lockdown)
        on_step("\n" + _("Device: {name}, iOS {version}",
                              name=dev.name, version=dev.ios_version))
        if not dev.developer_mode:
            raise SigningError(_(
                "Developer Mode is off. Turn it on under Settings > Privacy & "
                "Security > Developer Mode on the iPhone."))

        # 3. Anmeldung und Team.
        session = Session.load()
        if session is None:
            raise AppleError("Nicht angemeldet. Zuerst: modstaller login")
        ani = anisette_mod.build(settings.anisette_provider,
                                 settings.anisette_server)
        api = DeveloperServices(session, ani)

        teams = api.list_teams()
        team = pick_team(teams, team_id or settings.default_team_id)
        caps = Capabilities.for_team(team)
        on_step(f"Team:   {team}")

        # 4. Geraet beim Team anmelden (idempotent).
        api.register_device(team.team_id, dev.udid, dev.name)

        # 5. Zertifikat.
        on_step("\n" + _("Obtaining the certificate …"))
        p12, password = ensure_certificate(
            api, team, dev.name, revoke_conflicting=revoke_conflicting_cert)

        # 6. Extensions: bei Gratis-Accounts kosten sie je eine App-ID aus
        #    einem Kontingent von zehn pro Woche. Default ist deshalb, sie zu
        #    entfernen - die App selbst laeuft davon unbeeindruckt.
        strip = (caps.is_free and bool(info.extensions)
                 if strip_extensions is None else strip_extensions)
        if strip and info.extensions:
            on_step("  " + _("Removing {count} extension(s) (saves {count} "
                                 "App ID(s) from the weekly quota)",
                                 count=len(info.extensions)))

        # 7. App-ID und Profil.
        #
        # Die installierten Apps schuetzen ihre App-IDs vor dem Recycling -
        # sonst verliert irgendwann eine fremde App die Moeglichkeit, erneuert
        # zu werden, weil ModStaller ihre App-ID freigegeben hat.
        protected: set[str] = set()
        try:
            from .device.install import list_apps
            protected = set(await list_apps(sp))
        except Exception:
            pass

        wanted = derive_bundle_id(info.bundle_id, team.team_id)
        on_step(f"\nApp-ID {wanted} …")
        app_id = ensure_app_id(api, team, wanted, info.name,
                               reuse_when_exhausted=True, protected=protected)
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
        on_step(f"  Profil gueltig: {prof.days_left:.1f} Tage "
             f"({caps.describe()})")

        # 8. Signieren.
        out = OUT_DIR / f"{new_id}.ipa"
        on_step("\nSignieren …")
        started = time.time()
        sign(SignRequest(
            ipa=info.path, output=out, p12=p12, p12_password=password,
            profile=profile_path, bundle_id=new_id,
            strip_extensions=strip,
        ), zsign=find_zsign(settings.zsign_path) or settings.zsign_path)
        on_step(f"  fertig in {time.time() - started:.1f}s "
             f"({out.stat().st_size / 1e6:.0f} MB)")

        # 9. Installieren.
        on_step("\nInstallieren …")
        result = await install_ipa(sp, out, progress=progress)

        # 10. Merken, damit der Refresh spaeter weiss, was zu tun ist.
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
            strip_extensions=strip,
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
    """Erneuert Apps, deren Profil bald ablaeuft.

    Nutzt die beim Installieren gemerkte Original-IPA, damit die Bundle-ID
    stabil bleibt - sonst gilt die App fuer iOS als andere App und die
    gespeicherten Daten waeren weg.
    """
    settings = settings or Settings.load()
    threshold = (settings.renew_threshold_days if threshold_days is None
                 else threshold_days)

    if only:
        due = [r for r in store.all_installs() if r.bundle_id == only
               or r.original_bundle_id == only]
        if not due:
            raise SigningError(f"Nichts unter {only!r} installiert.")
    else:
        due = store.due_for_refresh(threshold)

    if not due:
        on_step(f"Nichts faellig (Schwelle: {threshold:.0f} Tage).")
        return []

    results: list[InstallOutcome] = []
    for rec in due:
        source = Path(rec.source_ipa)
        if not source.is_file():
            on_step("\n" + _("{name}: original IPA missing ({path}) - skipped.",
                                   name=rec.name, path=source))
            continue
        on_step("\n=== " + _("Renewing {name} ({expiry})",
                                   name=rec.name, expiry=rec.expiry_text) + " ===")
        results.append(await install(
            source, udid=udid or rec.udid, team_id=rec.team_id,
            settings=settings, strip_extensions=rec.strip_extensions,
            progress=progress, on_step=on_step,
        ))
    return results
