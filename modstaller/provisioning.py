"""From sign-in to a profile ready for signing.

Bundles the steps Apple requires for a sideloadable app: pick a team,
register the device, obtain a certificate, create an App ID, download the
provisioning profile. Every step is idempotent - a second run uses up no
quota.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .apple.devservices import AppID, DeveloperServices, Profile, Team
from .config import PROFILES_DIR, write_secret
from .i18n import _
from .errors import (
    APP_ID_QUOTA_EXCEEDED, APP_ID_UNAVAILABLE, AppleAPIError, AppleError,
)
from .signing import csr as csrmod

#: A bundle identifier may only contain these characters.
_ID_SAFE = re.compile(r"[^A-Za-z0-9.\-]")


@dataclass
class Capabilities:
    """What the account allows. Derived from the team type and later
    corrected from the real profile lifetime - Apple changes the rules now
    and then, and measured values are more reliable than guessed ones."""

    is_free: bool
    profile_days: float = 7.0
    max_app_ids_per_week: int | None = 10
    max_apps_per_device: int | None = 3

    @classmethod
    def for_team(cls, team: Team) -> "Capabilities":
        """First guess from the team type - deliberately cautious.

        Apple reports the same type ``Individual`` for free *and* paid
        individual accounts, so the type alone cannot decide it. When in
        doubt we assume "free", because erring in that direction is cheap
        (an extension gets removed), while erring the other way is
        expensive: the weekly quota of ten App IDs is used up before the app
        is even installed.

        :meth:`reconcile` corrects the guess as soon as a real profile
        exists and its lifetime answers the question.
        """
        paid = cls(is_free=False, profile_days=365.0,
                   max_app_ids_per_week=None, max_apps_per_device=None)
        # Apple's own statement beats every guess (Team.free_only).
        if team.free_only is not None:
            return cls(is_free=True) if team.free_only else paid
        if team.type.lower().startswith(("company", "organization")):
            return paid
        return cls(is_free=True)

    def reconcile(self, profile: Profile) -> "Capabilities":
        """Corrects the guess based on the actual lifetime."""
        days = profile.days_left
        if days != days:  # NaN
            return self
        is_free = days <= 8.0
        return Capabilities(
            is_free=is_free,
            profile_days=days,
            max_app_ids_per_week=10 if is_free else None,
            max_apps_per_device=3 if is_free else None,
        )

    def describe(self) -> str:
        if self.is_free:
            return ("free account - profiles expire after 7 days, "
                    "max. 3 apps, 10 App IDs per week")
        return "paid developer account - profiles valid for 1 year"


def derive_bundle_id(original: str, team_id: str) -> str:
    """Unique bundle ID for this team.

    The original ID usually belongs to another team (Apple rejects it with
    error 9401), so we append the team ID. The result is stable - important,
    because a change on refresh would lose the app's data.
    """
    base = _ID_SAFE.sub("-", original or "com.modstaller.app").strip(".")
    # Append the team ID in its original spelling. That is the convention
    # the other tools in this space use as well - so ensure_app_id finds an
    # existing App ID again instead of creating a new one and using up
    # quota.
    return f"{base}.{team_id}"


def pick_team(teams: list[Team], preferred: str | None = None) -> Team:
    if not teams:
        raise AppleError(_(
            "Your Apple account has no developer team. Sign in once on "
            "developer.apple.com and accept the terms."))
    if preferred:
        for t in teams:
            if t.team_id == preferred:
                return t
        raise AppleError(_("Team {team} does not exist in this account.",
                           team=preferred))
    return teams[0]


def ensure_certificate(api: DeveloperServices, team: Team,
                       machine_name: str,
                       *, revoke_conflicting: bool = False) -> tuple[Path, str]:
    """Returns a PKCS#12 identity for zsign.

    The order matters, because Apple allows only very few development
    certificates per account and each new one pushes out an old one:

    1. Reuse an identity that is already complete locally.
    2. Otherwise check whether Apple already holds a certificate for *our*
       key - then just reassemble it without touching the quota.
    3. Only then request a new one.
    """
    existing = csrmod.load_p12(team.team_id)
    if existing:
        expiry = csrmod.certificate_expiry(team.team_id)
        if expiry and expiry > datetime.now(timezone.utc):
            return existing

    keypair = csrmod.load_keypair(team.team_id)

    # Step 2: does an existing certificate belong to our key?
    if keypair is not None:
        content = _fetch_own_certificate(api, team, keypair)
        if content:
            return csrmod.build_p12(team.team_id, keypair, content)

    # Step 3: request a new one.
    if keypair is None:
        keypair = csrmod.KeyPair.generate()
        csrmod.save_keypair(team.team_id, keypair)

    if revoke_conflicting:
        _revoke_foreign_certificates(api, team, keypair)

    try:
        cert = api.submit_csr(
            team.team_id,
            keypair.csr_pem(f"ModStaller {machine_name}"),
            machine_id=_machine_id(),
            machine_name=machine_name,
        )
    except AppleAPIError as exc:
        listing = ""
        try:
            listing = "\n".join(f"    {c}"
                                for c in api.list_certificates(team.team_id))
        except Exception:
            pass
        raise AppleError(
            _("Apple issued no certificate: {error}", error=exc) + "\n\n"
            + (_("Existing certificates:\n{listing}", listing=listing)
               + "\n\n" if listing else "")
            + _("Apple allows only a few development certificates per "
                "account, and a foreign one is worthless to us: its private "
                "key lives with the tool that requested it.\n"
                "Show them with:  modstaller certs\n"
                "Make room with:  modstaller install "
                "--revoke-conflicting-cert …\n"
                "Careful: apps signed with the revoked certificate will no "
                "longer start.")) from exc

    # Apple does not always include the content right away - the
    # certificate is issued anyway and then shows up in the list.
    content = cert.content or _fetch_own_certificate(api, team, keypair)
    if not content:
        raise AppleError(_(
            "Apple issued a certificate but returns its content neither in "
            "the response nor in the list. Check with ‘modstaller certs’ "
            "and try again."))
    return csrmod.build_p12(team.team_id, keypair, content)


def _belongs_to(cert_der: bytes, keypair) -> bool:
    """Does the certificate match our private key?

    The machine ID alone is not enough: it can repeat, and a certificate
    with a foreign key later produces a signature the iPhone silently
    rejects. Comparing the public keys is unambiguous.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    try:
        cert = x509.load_der_x509_certificate(cert_der)
    except ValueError:
        try:
            cert = x509.load_pem_x509_certificate(cert_der)
        except ValueError:
            return False

    fmt = dict(encoding=serialization.Encoding.DER,
               format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return (cert.public_key().public_bytes(**fmt)
            == keypair.private_key.public_key().public_bytes(**fmt))


def _fetch_own_certificate(api: DeveloperServices, team: Team,
                           keypair) -> bytes:
    """Looks up the certificate at Apple that belongs to our key."""
    for cert in api.list_certificates(team.team_id):
        if cert.content and _belongs_to(bytes(cert.content), keypair):
            return bytes(cert.content)
    return b""


def _revoke_foreign_certificates(api: DeveloperServices, team: Team,
                                 keypair) -> None:
    """Makes room for a certificate of our own.

    Free accounts may hold only one development certificate, and a foreign
    one cannot be shared. Anyone sideloading with two tools inevitably
    pushes out the other one.

    Our own is skipped - revoking it would be the exact opposite of what
    the call is for.
    """
    for cert in api.list_certificates(team.team_id):
        if cert.content and _belongs_to(bytes(cert.content), keypair):
            continue
        print(_("  Revoking foreign certificate: {cert}", cert=cert))
        try:
            api.revoke_certificate(team.team_id, cert.serial)
        except Exception as exc:
            print(_("    could not be revoked: {error}", error=exc))


def _machine_id() -> str:
    """Stable identifier of this machine towards Apple."""
    import uuid as _uuid
    from .apple.anisette import DEVICE_FILE
    import json
    from .config import read_secret
    if DEVICE_FILE.exists():
        return json.loads(read_secret(DEVICE_FILE))["unique_device_id"]
    return str(_uuid.uuid4()).upper()


def ensure_app_id(api: DeveloperServices, team: Team, identifier: str,
                  name: str, *, reuse_when_exhausted: bool = False,
                  protected: set[str] | None = None,
                  existing: list[AppID] | None = None) -> AppID:
    """Obtains the App ID. The result may carry a different identifier.

    Apple counts **newly created** App IDs in a rolling seven-day window,
    not the existing ones. Deleting one therefore gives no quota back - it
    would do nothing but harm, because a foreign app would lose the ability
    to be renewed.

    So once the window is exhausted, we fall back to an existing, unused
    App ID. The app then runs under its bundle ID; to iOS that is an app of
    its own, and the name on the home screen is unaffected.
    """
    from .state import appid_log

    if existing is None:
        existing = api.list_app_ids(team.team_id)
    for candidate in existing:
        if candidate.identifier.lower() == identifier.lower():
            return candidate

    def add(ident: str) -> AppID:
        created = api.add_app_id(team.team_id, ident, name)
        # Apple keeps counting it for a week even if it is deleted.
        appid_log.created(team.team_id, created.identifier)
        return created

    try:
        return add(identifier)
    except AppleAPIError as exc:
        if exc.code == APP_ID_UNAVAILABLE:
            # Identifier belongs to another account - vary the suffix.
            return add(f"{identifier}.ms")
        if exc.code == APP_ID_QUOTA_EXCEEDED and reuse_when_exhausted:
            spare = spare_app_id(existing, protected or set())
            if spare is not None:
                return spare
        raise


def app_id_in_use(identifier: str, protected: set[str]) -> bool:
    """Does this App ID belong to an installed app?

    Whatever lies beneath it is protected too: an extension's App ID
    carries the app's as a prefix, and without it the app can no longer be
    signed completely.
    """
    ident = identifier.lower()
    return any(ident == p.lower() or ident.startswith(p.lower() + ".")
               for p in protected)


def spare_app_id(existing: list[AppID], protected: set[str]) -> AppID | None:
    """An existing App ID that belongs to no installed app.

    ``protected`` are the bundle IDs on the device.
    """
    for candidate in existing:
        if not app_id_in_use(candidate.identifier, protected):
            return candidate
    return None


def fetch_profile(api: DeveloperServices, team: Team, app_id: AppID) -> Path:
    """Downloads the profile and stores it. Returns: path to the file."""
    profile = api.download_profile(team.team_id, app_id.app_id_id)
    target = PROFILES_DIR / team.team_id / f"{app_id.app_id_id}.mobileprovision"
    write_secret(target, profile.content)
    return target


def profile_info(path: Path) -> Profile:
    from .apple.devservices import _profile_expiry
    blob = path.read_bytes()
    return Profile(content=blob, expires_at=_profile_expiry(blob))
