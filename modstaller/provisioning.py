"""Von der Anmeldung zum unterschriftsreifen Profil.

Buendelt die Schritte, die Apple fuer eine sideloadbare App verlangt:
Team waehlen, Geraet registrieren, Zertifikat besorgen, App-ID anlegen,
Provisioning-Profil herunterladen. Jeder Schritt ist idempotent - ein zweiter
Lauf verbraucht kein Kontingent.
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

#: Ein Bundle-Identifier darf nur diese Zeichen tragen.
_ID_SAFE = re.compile(r"[^A-Za-z0-9.\-]")


@dataclass
class Capabilities:
    """Was der Account hergibt. Aus dem Team-Typ abgeleitet und spaeter
    anhand der echten Profil-Laufzeit korrigiert - Apple aendert die Regeln
    gelegentlich, gemessene Werte sind verlaesslicher als geratene."""

    is_free: bool
    profile_days: float = 7.0
    max_app_ids_per_week: int | None = 10
    max_apps_per_device: int | None = 3

    @classmethod
    def for_team(cls, team: Team) -> "Capabilities":
        """Erste Annahme aus dem Team-Typ - bewusst vorsichtig.

        Apple meldet fuer kostenlose *und* bezahlte Einzelaccounts denselben
        Typ ``Individual``. Aus dem Typ allein laesst sich das also nicht
        entscheiden. Wir nehmen im Zweifel "kostenlos" an, weil der Irrtum in
        diese Richtung billig ist (eine Extension wird entfernt), in die
        andere aber teuer: dann ist das Wochenkontingent von zehn App-IDs
        verbraucht, bevor die App installiert ist.

        :meth:`reconcile` korrigiert die Annahme, sobald ein echtes Profil
        vorliegt und seine Laufzeit die Frage beantwortet.
        """
        if team.type.lower().startswith(("company", "organization")):
            return cls(is_free=False, profile_days=365.0,
                       max_app_ids_per_week=None, max_apps_per_device=None)
        return cls(is_free=True)

    def reconcile(self, profile: Profile) -> "Capabilities":
        """Korrigiert die Annahme anhand der tatsaechlichen Laufzeit."""
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
            return ("kostenloser Account - Profile laufen nach 7 Tagen ab, "
                    "max. 3 Apps, 10 App-IDs pro Woche")
        return "bezahlter Developer-Account - Profile 1 Jahr gueltig"


def derive_bundle_id(original: str, team_id: str) -> str:
    """Eindeutige Bundle-ID fuer dieses Team.

    Die Original-ID gehoert meist einem fremden Team (Apple lehnt sie mit
    Fehler 9401 ab), deshalb haengen wir die Team-ID an. Das Ergebnis ist
    stabil - wichtig, weil ein Wechsel beim Refresh die App-Daten verlieren
    wuerde.
    """
    base = _ID_SAFE.sub("-", original or "com.modstaller.app").strip(".")
    # Team-ID in Originalschreibweise anhaengen. Das ist die Konvention, die
    # auch die uebrigen Werkzeuge im Umfeld benutzen - dadurch findet
    # ensure_app_id eine bereits vorhandene App-ID wieder, statt eine neue
    # anzulegen und Kontingent zu verbrauchen.
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
    """Liefert eine PKCS#12-Identitaet fuer zsign.

    Die Reihenfolge ist wichtig, weil Apple pro Account nur sehr wenige
    Development-Zertifikate zulaesst und jedes neue ein altes verdraengt:

    1. Eine lokal fertige Identitaet wiederverwenden.
    2. Sonst pruefen, ob bei Apple schon ein Zertifikat zu *unserem*
       Schluessel liegt - dann nur neu zusammensetzen, ohne Kontingent
       anzufassen.
    3. Erst dann ein neues anfordern.
    """
    existing = csrmod.load_p12(team.team_id)
    if existing:
        expiry = csrmod.certificate_expiry(team.team_id)
        if expiry and expiry > datetime.now(timezone.utc):
            return existing

    keypair = csrmod.load_keypair(team.team_id)

    # Schritt 2: Gehoert ein vorhandenes Zertifikat zu unserem Schluessel?
    if keypair is not None:
        content = _fetch_own_certificate(api, team, keypair)
        if content:
            return csrmod.build_p12(team.team_id, keypair, content)

    # Schritt 3: neues anfordern.
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

    # Apple liefert den Inhalt nicht immer gleich mit - ausgestellt ist es
    # trotzdem, dann steht es in der Liste.
    content = cert.content or _fetch_own_certificate(api, team, keypair)
    if not content:
        raise AppleError(_(
            "Apple issued a certificate but returns its content neither in "
            "the response nor in the list. Check with ‘modstaller certs’ "
            "and try again."))
    return csrmod.build_p12(team.team_id, keypair, content)


def _belongs_to(cert_der: bytes, keypair) -> bool:
    """Passt das Zertifikat zu unserem privaten Schluessel?

    Die Maschinenkennung allein reicht nicht: sie kann sich wiederholen, und
    ein Zertifikat mit fremdem Schluessel erzeugt spaeter eine Signatur, die
    das iPhone wortlos ablehnt. Der Vergleich der oeffentlichen Schluessel
    ist eindeutig.
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
    """Sucht bei Apple das Zertifikat, das zu unserem Schluessel gehoert."""
    for cert in api.list_certificates(team.team_id):
        if cert.content and _belongs_to(bytes(cert.content), keypair):
            return bytes(cert.content)
    return b""


def _revoke_foreign_certificates(api: DeveloperServices, team: Team,
                                 keypair) -> None:
    """Macht Platz fuer ein eigenes Zertifikat.

    Gratis-Accounts duerfen nur ein Development-Zertifikat halten, und ein
    fremdes laesst sich nicht mitbenutzen. Wer mit zwei Werkzeugen
    sideloadet, verdraengt zwangslaeufig das jeweils andere.

    Unser eigenes wird dabei ausgelassen - es zu widerrufen waere genau das
    Gegenteil dessen, was der Aufruf bezweckt.
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
    """Stabile Kennung dieses Rechners gegenueber Apple."""
    import uuid as _uuid
    from .apple.anisette import DEVICE_FILE
    import json
    from .config import read_secret
    if DEVICE_FILE.exists():
        return json.loads(read_secret(DEVICE_FILE))["unique_device_id"]
    return str(_uuid.uuid4()).upper()


def ensure_app_id(api: DeveloperServices, team: Team, identifier: str,
                  name: str, *, reuse_when_exhausted: bool = False,
                  protected: set[str] | None = None) -> AppID:
    """Besorgt die App-ID. Die Rueckgabe kann einen anderen Identifier tragen.

    Apple zaehlt **neu angelegte** App-IDs in einem rollierenden
    Sieben-Tage-Fenster, nicht die vorhandenen. Eine zu loeschen gibt also
    kein Kontingent zurueck - es waere reiner Schaden, weil damit eine fremde
    App die Moeglichkeit verliert, erneuert zu werden.

    Ist das Fenster ausgeschoepft, weichen wir deshalb auf eine vorhandene,
    ungenutzte App-ID aus. Die App laeuft dann unter deren Bundle-ID; fuer
    iOS ist das eine eigenstaendige App, und der Name auf dem Homescreen
    bleibt davon unberuehrt.
    """
    existing = api.list_app_ids(team.team_id)
    for candidate in existing:
        if candidate.identifier == identifier:
            return candidate

    try:
        return api.add_app_id(team.team_id, identifier, name)
    except AppleAPIError as exc:
        if exc.code == APP_ID_UNAVAILABLE:
            # Identifier gehoert einem anderen Account - Suffix variieren.
            return api.add_app_id(team.team_id, f"{identifier}.ms", name)
        if exc.code == APP_ID_QUOTA_EXCEEDED and reuse_when_exhausted:
            spare = spare_app_id(existing, protected or set())
            if spare is not None:
                return spare
        raise


def app_id_in_use(identifier: str, protected: set[str]) -> bool:
    """Gehoert diese App-ID zu einer installierten App?

    Geschuetzt ist auch, was darunter liegt: die App-ID einer Extension
    traegt die der App als Praefix, und ohne sie laesst sich die App nicht
    mehr vollstaendig signieren.
    """
    ident = identifier.lower()
    return any(ident == p.lower() or ident.startswith(p.lower() + ".")
               for p in protected)


def spare_app_id(existing: list[AppID], protected: set[str]) -> AppID | None:
    """Eine vorhandene App-ID, die zu keiner installierten App gehoert.

    ``protected`` sind die Bundle-IDs auf dem Geraet.
    """
    for candidate in existing:
        if not app_id_in_use(candidate.identifier, protected):
            return candidate
    return None


def fetch_profile(api: DeveloperServices, team: Team, app_id: AppID) -> Path:
    """Laedt das Profil und legt es ab. Rueckgabe: Pfad zur Datei."""
    profile = api.download_profile(team.team_id, app_id.app_id_id)
    target = PROFILES_DIR / team.team_id / f"{app_id.app_id_id}.mobileprovision"
    write_secret(target, profile.content)
    return target


def profile_info(path: Path) -> Profile:
    from .apple.devservices import _profile_expiry
    blob = path.read_bytes()
    return Profile(content=blob, expires_at=_profile_expiry(blob))
