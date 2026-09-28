"""Taking single extensions out of an IPA before it is signed.

zsign can only remove *all* extensions (``-E``). To keep some, the IPA is
unpacked without the unwanted ``PlugIns/*.appex`` and zsign signs the
folder - it zips the result itself, so nothing is compressed twice.
"""

from __future__ import annotations

import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from ..errors import SigningError
from ..i18n import _


def unpack_without(ipa: Path, app_dir: str, drop: list[str], work: Path) -> Path:
    """Unpacks ``ipa`` into a new folder below ``work``, leaving out the
    extensions in ``drop`` ("PlugIns/Foo.appex"). Returns the folder (with
    ``Payload/`` inside) - the caller removes it after signing.

    File modes come along (executables must stay executable), and no entry
    may leave the folder (``..``, absolute paths).
    """
    target = work / f"ipa-{uuid.uuid4().hex[:12]}"
    target.mkdir(parents=True)
    skip = tuple(f"Payload/{app_dir}/{d.rstrip('/')}/" for d in drop)
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
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target
