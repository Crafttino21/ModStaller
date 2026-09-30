"""What an IPA is for - read from the server without downloading it.

Sources say which iOS version an app needs (sometimes), but not whether it
is an iPhone, iPad, Apple TV or Vision Pro app. The app's ``Info.plist``
says so (``UIDeviceFamily``, ``CFBundleSupportedPlatforms``,
``MinimumOSVersion``). An IPA is a zip file whose table of contents sits at
its end - so with HTTP range requests three small reads are enough: the end
of the file, the table of contents, the ``Info.plist``. Kilobytes instead of
the whole IPA.

A download URL belongs to one version and does not change: what was read
once stays cached. Reading fails where a server does not support ranges -
then the app is "unknown" and simply stays visible.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import plistlib
import time
import zipfile

from .. import config
from ..signing.ipa import device_families, platform_of
from . import sources
from .model import https

log = logging.getLogger(__name__)

CACHE = config.CACHE_DIR / "store" / "probe"
BLOCK = 64 * 1024
TIMEOUT = 20
#: An Info.plist is a few kilobytes - anything this big is not one.
MAX_PLIST = 2 * 1024 * 1024
#: A failed read is tried again after this long.
RETRY_AFTER = 24 * 3600


class ProbeError(Exception):
    pass


class RangeFile(io.RawIOBase):
    """A remote file, read in blocks with HTTP range requests - enough of a
    file for :mod:`zipfile`."""

    def __init__(self, url: str, size: int, http) -> None:
        super().__init__()
        self._url, self._size, self._http = url, size, http
        self._pos = 0
        self._blocks: dict[int, bytes] = {}
        self.requests = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}[whence]
        self._pos = max(0, base + offset)
        return self._pos

    def _fetch(self, first: int, last: int) -> None:
        """Blocks ``first``..``last`` in one request."""
        start = first * BLOCK
        end = min(self._size, (last + 1) * BLOCK) - 1
        with self._http.get(self._url, headers={"Range": f"bytes={start}-{end}"},
                            timeout=TIMEOUT, stream=True) as resp:
            if resp.status_code != 206:
                raise ProbeError(f"no range support (HTTP {resp.status_code})")
            data = resp.raw.read(end - start + 1, decode_content=True) if hasattr(resp, "raw") \
                else b"".join(resp.iter_content(BLOCK))
        self.requests += 1
        for i in range(first, last + 1):
            self._blocks[i] = data[(i - first) * BLOCK:(i - first + 1) * BLOCK]

    def read(self, size: int = -1) -> bytes:
        if self._pos >= self._size:
            return b""
        if size is None or size < 0:
            size = self._size - self._pos
        end = min(self._size, self._pos + size)
        first, last = self._pos // BLOCK, (end - 1) // BLOCK
        missing = [i for i in range(first, last + 1) if i not in self._blocks]
        if missing:
            self._fetch(missing[0], missing[-1])
        data = b"".join(self._blocks[i] for i in range(first, last + 1))
        offset = self._pos - first * BLOCK
        out = data[offset:offset + (end - self._pos)]
        self._pos += len(out)
        return out

    def readinto(self, buffer) -> int:
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def read_info_plist(url: str, http=None) -> dict:
    """The app's Info.plist, read from the remote IPA."""
    url = https(url)
    if not url:
        raise ProbeError("not https")
    http = http or sources.session()
    # One byte first: tells the size, follows redirects (GitHub hands out
    # a signed CDN address) and shows whether ranges work at all.
    with http.get(url, headers={"Range": "bytes=0-0"}, timeout=TIMEOUT, stream=True) as resp:
        if resp.status_code != 206:
            raise ProbeError(f"no range support (HTTP {resp.status_code})")
        final = resp.url or url
        total = resp.headers.get("Content-Range", "").rpartition("/")[2]
    if not https(final):
        raise ProbeError("redirected to non-https")
    try:
        size = int(total)
    except ValueError as exc:
        raise ProbeError("size unknown") from exc
    raw = RangeFile(final, size, http)
    with zipfile.ZipFile(io.BufferedReader(raw, BLOCK)) as zf:
        name = next((n for n in zf.namelist() if n.startswith("Payload/") and n.count("/") == 2
                     and n.endswith(".app/Info.plist")), None)
        if name is None:
            raise ProbeError("no Payload/*.app/Info.plist")
        if zf.getinfo(name).file_size > MAX_PLIST:
            raise ProbeError("Info.plist too big")
        return plistlib.loads(zf.read(name))


def _cache_file(url: str):
    return CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")


def cached(url: str) -> dict | None:
    """What is known about ``url`` - None if never read (or a failure that
    is due for another try)."""
    try:
        entry = json.loads(_cache_file(url).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if entry.get("error") and time.time() - entry.get("at", 0) > RETRY_AFTER:
        return None
    return entry


def facts(url: str, http=None) -> dict:
    """``{platform, families, minOs}`` of the IPA at ``url`` - or
    ``{error}``. Cached either way."""
    hit = cached(url)
    if hit is not None:
        return hit
    try:
        info = read_info_plist(url, http)
        entry = {"platform": platform_of(info), "families": device_families(info),
                 "minOs": str(info.get("MinimumOSVersion") or ""), "at": time.time()}
    except Exception as exc:
        log.debug("Probe of %s failed: %s", url, exc)
        entry = {"error": str(exc) or type(exc).__name__, "at": time.time()}
    CACHE.mkdir(parents=True, exist_ok=True)
    _cache_file(url).write_text(json.dumps(entry), encoding="utf-8")
    return entry
