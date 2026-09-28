"""Signing with zsign.

zsign takes the tricky work off our hands: it signs nested frameworks and
injected dylibs from the inside out, removes old signatures and puts the
``embedded.mobileprovision`` in the right place. Exactly the spots where
hand-written signers typically fail.

We deliberately do *not* assemble the entitlements ourselves: without ``-e``
zsign takes them from the provisioning profile - and that is, by definition,
exactly what Apple has actually granted the account.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..errors import SigningError
from ..i18n import _

#: How zsign is invoked - the same at both call sites.
#:
#: ``encoding``: if unset, ``text=True`` decodes with the system code page
#: (cp1252 on German Windows); a special character in zsign's output would
#: then raise a UnicodeDecodeError in the middle of ``subprocess.run``.
#:
#: ``creationflags``: zsign is a console program. The UI's ``windowsHide``
#: only applies to the backend, not to its child processes - without
#: CREATE_NO_WINDOW a window flashes up on every signing run.
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
    #: Remove extensions. Almost always sensible for free accounts: every
    #: extension needs an App ID of its own from the weekly quota.
    strip_extensions: bool = False
    strip_watch: bool = False
    #: Profiles for the extensions. zsign picks the right one per bundle by
    #: its App ID; ``profile`` (the app's) comes first and is the fallback.
    extra_profiles: list[Path] | None = None
    #: A square PNG that replaces the app icon (zsign ``-I``).
    icon: Path | None = None


def _redact(cmd: list[str], password: str) -> str:
    return " ".join("***" if a == password else a for a in cmd)


def sign(req: SignRequest, *, timeout: float = 900.0,
         zsign: str = "zsign") -> Path:
    # A folder is fine too: an IPA unpacked beforehand (Payload/ inside),
    # e.g. with single extensions taken out.
    if not req.ipa.exists():
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
    ]
    for extra in req.extra_profiles or []:
        cmd += ["-m", str(extra)]
    cmd += [
        "-o", str(req.output),
        "-z", "1",          # light compression: much faster, hardly bigger
        "-f",               # skip the cache - else an old signature survives
    ]
    if req.bundle_id:
        cmd += ["-b", req.bundle_id]
    if req.display_name:
        cmd += ["-n", req.display_name]
    if req.strip_extensions:
        cmd += ["-E"]
    if req.strip_watch:
        cmd += ["-W"]
    if req.icon:
        cmd += ["-I", str(req.icon)]
    cmd.append(str(req.ipa))

    try:
        # Signing a folder, zsign keeps a cache (.zsign_cache) in its
        # working directory - there, it goes into the folder that is thrown
        # away afterwards, not wherever the backend happens to run.
        cwd = req.ipa if req.ipa.is_dir() else req.output.parent
        proc = subprocess.run(cmd, timeout=timeout, cwd=str(cwd), **RUN_KWARGS)
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
    """Checks the identity and returns zsign's description of it."""
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
