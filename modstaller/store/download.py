"""Downloading an IPA from a source - and keeping it.

The file stays in ``IPA_CACHE_DIR/<bundle>/<version>.ipa``: renewing a
sideloaded app signs the original IPA again, so it has to be there in seven
days too. A download that is already complete is not repeated.

On the way in it is checked: https only, not bigger than the source said (or
than :data:`MAX_BYTES`), the ``sha256`` if the source gives one, and finally
that it really is an IPA. Only then does the ``.part`` file get its name.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable

from .. import config
from ..i18n import _
from .model import StoreApp, StoreVersion, https
from . import sources
from .sources import StoreError

MAX_BYTES = 8 * 1024 * 1024 * 1024
TIMEOUT = 60
CHUNK = 1 << 20


def _safe(name: str) -> str:
    """Letters, digits, dot, dash, underscore - nothing that leaves the folder."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned[:120] or "app"


def target(app: StoreApp, version: StoreVersion) -> Path:
    return config.IPA_CACHE_DIR / _safe(app.bundle_id) / f"{_safe(version.version)}.ipa"


def pick_version(app: StoreApp, version: str | None = None) -> StoreVersion:
    if version:
        for v in app.versions:
            if v.version == version:
                return v
        raise StoreError(_("Version {version} is not offered.", version=version))
    return app.versions[0]


def _complete(path: Path, version: StoreVersion) -> bool:
    if not path.is_file():
        return False
    if version.size and path.stat().st_size != version.size:
        return False
    if version.sha256:
        return _sha256(path) == version.sha256
    return True


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(app: StoreApp, version: str | None = None, *,
             progress: Callable[[int], None] | None = None,
             cancelled: Callable[[], bool] = lambda: False, http=None) -> Path:
    """The IPA of ``app`` on disk - downloaded if it is not there yet."""
    from ..signing import ipa as ipa_mod

    ver = pick_version(app, version)
    url = https(ver.download_url)
    if not url:
        raise StoreError(_("Only https downloads are supported."))
    path = target(app, ver)
    if _complete(path, ver):
        if progress:
            progress(100)
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    h = hashlib.sha256()
    try:
        with (http or sources.session()).get(url, timeout=TIMEOUT, stream=True) as resp:
            resp.raise_for_status()
            if not https(resp.url):
                raise StoreError(_("The download redirected to a non-https address."))
            total = ver.size or int(resp.headers.get("Content-Length") or 0)
            if total > MAX_BYTES:
                raise StoreError(_("The IPA is too big."))
            done, last = 0, -1
            with part.open("wb") as out:
                for chunk in resp.iter_content(CHUNK):
                    if cancelled():
                        raise StoreError(_("Download cancelled."))
                    done += len(chunk)
                    if done > MAX_BYTES or (ver.size and done > ver.size):
                        raise StoreError(_("The download is bigger than the source says."))
                    out.write(chunk)
                    h.update(chunk)
                    if progress and total:
                        pct = min(99, done * 100 // total)
                        if pct != last:
                            progress(pct)
                            last = pct
        if ver.size and done != ver.size:
            raise StoreError(_("The download is incomplete ({got} of {want} bytes).",
                               got=done, want=ver.size))
        if ver.sha256 and h.hexdigest() != ver.sha256:
            raise StoreError(_("The download does not match its checksum - it was "
                               "damaged or changed on the way."))
        try:
            ipa_mod.inspect(part)
        except Exception as exc:
            raise StoreError(_("The download is not a valid IPA: {error}", error=exc)) from exc
        part.replace(path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    if progress:
        progress(100)
    return path
