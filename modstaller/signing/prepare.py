"""Taking single extensions out of an IPA before it is signed.

zsign can only remove *all* extensions (``-E``). To keep some, the IPA is
unpacked without the unwanted ``PlugIns/*.appex`` and zsign signs the
folder - it zips the result itself, so nothing is compressed twice.

The same unpacking also clears stale FairPlay references, see
:func:`stale_sinf_paths`.
"""

from __future__ import annotations

import plistlib
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from ..errors import SigningError
from ..i18n import _

#: Left behind by the App Store in decrypted IPAs: which bundles get a copy of
#: the app's FairPlay SINF on install.
SINF_MANIFEST = "SC_Info/Manifest.plist"
_SINF_KEYS = ("SinfPaths", "SinfReplicationPaths")


def _sinf_bundle(path: str) -> str:
    """The bundle a SINF path belongs to: "PlugIns/Share.appex" for
    "PlugIns/Share.appex/SC_Info/Share.sinf", "" for the app's own."""
    head, sep, _rest = path.rpartition("/SC_Info/")
    return head if sep else ""


def stale_sinf_paths(ipa: Path, app_dir: str, removed: list[str]) -> list[str]:
    """SINF paths in the app's ``SC_Info/Manifest.plist`` whose bundle is not
    in the IPA - or goes when it is signed (``removed``: "PlugIns/Foo.appex",
    "Watch").

    installd creates every listed path on install, folders included. For an
    extension that is gone, that leaves a ``.appex`` holding nothing but
    ``SC_Info`` - no Info.plist. iOS 27 then refuses the install with
    "Failed to unarchive journal entry data". Modded IPAs regularly have
    extensions taken out while the manifest still lists them.
    """
    prefix = f"Payload/{app_dir}/"
    try:
        with zipfile.ZipFile(ipa) as zf:
            manifest = plistlib.loads(zf.read(prefix + SINF_MANIFEST))
            names = zf.namelist()
    except Exception:
        return []           # none, or unreadable: then installd ignores it too
    if not isinstance(manifest, dict):
        return []

    def present(bundle: str) -> bool:
        if any(bundle == r or bundle.startswith(r.rstrip("/") + "/") for r in removed):
            return False
        base = f"{prefix}{bundle}/"
        own_sinf = base + "SC_Info/"
        return any(n.startswith(base) and not n.startswith(own_sinf) for n in names)

    stale: list[str] = []
    for key in _SINF_KEYS:
        for path in manifest.get(key) or []:
            if (isinstance(path, str) and path not in stale
                    and _sinf_bundle(path) and not present(_sinf_bundle(path))):
                stale.append(path)
    return stale


def prune_sinf_manifest(app: Path, stale: list[str]) -> None:
    """Takes ``stale`` out of the manifest in the unpacked ``app``."""
    path = app / SINF_MANIFEST
    manifest = plistlib.loads(path.read_bytes())
    for key in _SINF_KEYS:
        if isinstance(manifest.get(key), list):
            manifest[key] = [p for p in manifest[key] if p not in stale]
    path.write_bytes(plistlib.dumps(manifest))


def unpack_without(ipa: Path, app_dir: str, drop: list[str], work: Path,
                   stale_sinf: list[str] | None = None) -> Path:
    """Unpacks ``ipa`` into a new folder below ``work``, leaving out the
    extensions in ``drop`` ("PlugIns/Foo.appex"). Returns the folder (with
    ``Payload/`` inside) - the caller removes it after signing.
    ``stale_sinf`` (see :func:`stale_sinf_paths`) is taken out of the
    FairPlay manifest on the way.

    File modes come along (executables must stay executable), and no entry
    may leave the folder (``..``, absolute paths).
    """
    target = work / f"ipa-{uuid.uuid4().hex[:12]}"
    target.mkdir(parents=True)
    # What is left of a stale bundle (its SC_Info at most) goes as well -
    # a .appex without Info.plist is exactly what iOS refuses.
    gone = list(drop) + [_sinf_bundle(p) for p in stale_sinf or []]
    skip = tuple(f"Payload/{app_dir}/{d.rstrip('/')}/" for d in gone)
    root = target.resolve()
    try:
        with zipfile.ZipFile(ipa) as zf:
            for entry in zf.infolist():
                name = entry.filename
                if name.startswith(skip) or name.rstrip("/") + "/" in skip:
                    continue
                parts = PurePosixPath(name).parts
                if not parts or name.startswith("/") or ".." in parts:
                    raise SigningError(_("{name} contains an unsafe path: {path}",
                                         name=ipa.name, path=name))
                dest = (target / Path(*parts)).resolve()
                if root not in dest.parents and dest != root:
                    raise SigningError(_("{name} contains an unsafe path: {path}",
                                         name=ipa.name, path=name))
                if entry.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(entry) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out, 1 << 20)
                mode = (entry.external_attr >> 16) & 0o777
                if mode:
                    dest.chmod(mode | 0o600)
        if stale_sinf:
            prune_sinf_manifest(target / "Payload" / app_dir, stale_sinf)
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target
