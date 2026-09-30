"""Icons and screenshots for the store - fetched here, not in the window.

The interface's content security policy only allows its own images and
``data:`` URLs, and that stays so: the backend fetches the picture, shrinks
it (Pillow comes with pymobiledevice3) and hands it over as a data URL. The
window never talks to a stranger's server, and a big screenshot costs
kilobytes instead of megabytes.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging

from .. import config
from ..i18n import _
from .model import https
from . import sources
from .sources import StoreError

log = logging.getLogger(__name__)

CACHE = config.CACHE_DIR / "store" / "img"
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 20

#: Longest edge: icons are shown small, screenshots at most this high.
SIZES = {"icon": 128, "screenshot": 900}


def _key(url: str, kind: str) -> str:
    return hashlib.sha1(f"{kind}|{url}".encode()).hexdigest()


def _shrink(data: bytes, kind: str) -> tuple[bytes, str]:
    try:
        from PIL import Image
    except ImportError:
        return data, "image/png"
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        limit = SIZES.get(kind, 256)
        if kind == "screenshot":
            if img.height > limit:
                img = img.resize((max(1, img.width * limit // img.height), limit))
        else:
            img.thumbnail((limit, limit))
        out = io.BytesIO()
        if img.mode in ("RGBA", "LA", "P"):
            img.convert("RGBA").save(out, "PNG", optimize=True)
            return out.getvalue(), "image/png"
        img.convert("RGB").save(out, "JPEG", quality=85)
        return out.getvalue(), "image/jpeg"


def image(url: str, kind: str = "icon", *, http=None) -> str:
    """A data URL for the picture at ``url``."""
    url = https(url)
    if not url:
        raise StoreError(_("Only https images are loaded."))
    kind = kind if kind in SIZES else "icon"
    path = CACHE / _key(url, kind)
    try:
        return path.read_text(encoding="ascii")
    except OSError:
        pass
    with (http or sources.session()).get(url, timeout=TIMEOUT, stream=True) as resp:
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if not ctype.startswith("image/"):
            raise StoreError(_("That is not an image."))
        chunks, total = [], 0
        for chunk in resp.iter_content(1 << 16):
            total += len(chunk)
            if total > MAX_BYTES:
                raise StoreError(_("The image is too big."))
            chunks.append(chunk)
    data = b"".join(chunks)
    try:
        data, ctype = _shrink(data, kind)
    except Exception as exc:
        raise StoreError(_("The image cannot be read.")) from exc
    out = f"data:{ctype};base64," + base64.b64encode(data).decode("ascii")
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_text(out, encoding="ascii")
    tmp.replace(path)
    return out
