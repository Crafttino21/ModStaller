"""Signieren mit zsign.

zsign nimmt uns die heikle Arbeit ab: es signiert nested Frameworks und
injizierte dylibs von innen nach aussen, entfernt alte Signaturen und legt
das ``embedded.mobileprovision`` an der richtigen Stelle ab. Genau die Punkte,
an denen handgeschriebene Signierer typischerweise scheitern.

Die Entitlements ziehen wir bewusst *nicht* selbst zusammen: ohne ``-e`` nimmt
zsign die aus dem Provisioning-Profil - und das ist per Definition genau das,
was Apple dem Account tatsaechlich gewaehrt hat.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..errors import SigningError
from ..i18n import _

#: Wie zsign aufgerufen wird - an beiden Aufrufstellen gleich.
#:
#: ``encoding``: ohne Angabe dekodiert ``text=True`` mit der Codepage des
#: Systems (cp1252 auf deutschem Windows); ein Sonderzeichen in zsigns Ausgabe
#: wuerde dann mitten in ``subprocess.run`` einen UnicodeDecodeError werfen.
#:
#: ``creationflags``: zsign ist ein Konsolenprogramm. Das ``windowsHide`` der
#: Oberflaeche gilt nur fuer das Backend, nicht fuer dessen Kindprozesse -
#: ohne CREATE_NO_WINDOW blitzt bei jedem Signieren ein Fenster auf.
RUN_KWARGS: dict = {
    "capture_output": True,
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}
if os.name == "nt":
    RUN_KWARGS["creationflags"] = subprocess.CREATE_NO_WINDOW


@dataclass
class SignRequest:
    ipa: Path
    output: Path
    p12: Path
    p12_password: str
    profile: Path
    bundle_id: str | None = None
    display_name: str | None = None
    #: Extensions entfernen. Bei Gratis-Accounts fast immer sinnvoll: jede
    #: Extension braucht eine eigene App-ID aus dem Wochenkontingent.
    strip_extensions: bool = False
    strip_watch: bool = False


def _redact(cmd: list[str], password: str) -> str:
    return " ".join("***" if a == password else a for a in cmd)


def sign(req: SignRequest, *, timeout: float = 900.0,
         zsign: str = "zsign") -> Path:
    if not req.ipa.is_file():
        raise SigningError(_("IPA not found: {path}", path=req.ipa))
    if not req.profile.is_file():
        raise SigningError(_("Provisioning profile not found: {path}",
                             path=req.profile))

    req.output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        zsign,
        "-k", str(req.p12),
        "-p", req.p12_password,
        "-m", str(req.profile),
        "-o", str(req.output),
        "-z", "1",          # leichte Kompression: deutlich schneller, kaum groesser
        "-f",               # Cache umgehen - sonst ueberlebt eine alte Signatur
    ]
    if req.bundle_id:
        cmd += ["-b", req.bundle_id]
    if req.display_name:
        cmd += ["-n", req.display_name]
    if req.strip_extensions:
        cmd += ["-E"]
    if req.strip_watch:
        cmd += ["-W"]
    cmd.append(str(req.ipa))

    try:
        proc = subprocess.run(cmd, timeout=timeout, **RUN_KWARGS)
    except FileNotFoundError as exc:
        raise SigningError(_(
            "zsign not found. Install it with: paru -S zsign-bin"
        )) from exc
    except subprocess.TimeoutExpired as exc:
        raise SigningError(_("zsign did not finish within {seconds:.0f}s.",
                             seconds=timeout)) from exc

    if proc.returncode != 0 or not req.output.exists():
        detail = (proc.stderr or proc.stdout or "").strip()
        raise SigningError(_(
            "Signing failed (exit {code}).\nCall: {call}\n{detail}",
            code=proc.returncode, call=_redact(cmd, req.p12_password),
            detail=detail[-1200:]))
    return req.output


def check_identity(p12: Path, password: str, zsign: str = "zsign") -> str:
    """Prueft die Identitaet und gibt zsigns Beschreibung zurueck."""
    proc = subprocess.run(
        [zsign, "-C", "-k", str(p12), "-p", password],
        timeout=120, **RUN_KWARGS,
    )
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        raise SigningError(_("Certificate or key unusable:\n{detail}",
                             detail=out[-800:]))
    return out


def subject_of(output: str) -> str:
    m = re.search(r"SubjectCN:\s*(.+)", output)
    return m.group(1).strip() if m else ""
