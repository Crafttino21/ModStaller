"""Which sources the store reads - and fetching them.

The list lives in ``CONFIG_DIR/sources.json``. Out of the box it holds the
official sources of projects whose apps are free to share - AltStore,
SideStore, UTM, PojavLauncher/Amethyst, the emulators (DolphiniOS, Provenance,
Flycast), iSH and StikDebug. Anything else the user adds by URL, on their own
responsibility.

Sources that become defaults later are added once to an existing list - but
a default the user removed stays removed (``seenDefaults``).

Fetched sources are cached (``CACHE_DIR/store/sources``) with their
``ETag``/``Last-Modified``: a source is only asked again after
:data:`MAX_AGE`, and then answers "not modified" when nothing changed. When
the network fails, the last cached copy is used and marked stale.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

from .. import config
from ..errors import ModStallerError
from ..i18n import _
from .model import Source, https, parse_source

log = logging.getLogger(__name__)

SOURCES_FILE = config.CONFIG_DIR / "sources.json"
CACHE = config.CACHE_DIR / "store" / "sources"

#: Official sources of their own projects, each checked by hand: open
#: source or free apps, nothing that unlocks paid ones.
DEFAULT_SOURCES = (
    "https://apps.altstore.io/",                                  # AltStore, Delta, Clip
    "https://community-apps.sidestore.io/sidecommunity.json",     # SideStore Team Picks
    "https://apps.sidestore.io/",                                 # SideStore itself
    "https://alt.getutm.app/",                                    # UTM, UTM SE
    "https://alt.crystall1ne.dev/",                               # PojavLauncher, Amethyst
    "https://altstore.oatmealdome.me/",                           # DolphiniOS
    "https://provenance-emu.com/apps.json",                       # Provenance, iCube
    "https://flyinghead.github.io/flycast-builds/altstore.json",  # Flycast
    "https://ish.app/altstore.json",                              # iSH
    "https://stikdebug.xyz/index.json",                           # StikDebug, StikPair
    # Community source with many emulators - and jailbreak tools, which are
    # marked in the store (risk.py) and ask before installing.
    "https://quarksources.github.io/dist/quantumsource.min.json",
    "https://raw.githubusercontent.com/YTLitePlus/YTLitePlus-Altstore/main/apps.json",
)

#: A cached source is asked again after this long.
MAX_AGE = 6 * 3600
#: Big sources exist (AppTesters: ~10 MB) - but not this big.
MAX_BYTES = 64 * 1024 * 1024
TIMEOUT = 30

USER_AGENT = "ModStaller (+https://github.com/Crafttino21/ModStaller)"


class StoreError(ModStallerError):
    exit_code = 5


def session():
    """Plain HTTP for the store - never the Apple sessions (apple/http.py),
    which carry sign-in headers."""
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


# -- The list -----------------------------------------------------------------


def _load() -> tuple[list[dict], set[str]] | None:
    """``(entries, seen defaults)`` from the file - None without one. The
    first version of the file was a bare list: all its URLs count as seen,
    the two defaults of that time too."""
    try:
        data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, list):
        raw, seen = data, set(DEFAULT_SOURCES[:2])
    elif isinstance(data, dict):
        raw = data.get("sources") or []
        seen = {u for u in data.get("seenDefaults") or [] if isinstance(u, str)}
    else:
        return None
    entries = [{"url": https(e.get("url")), "enabled": bool(e.get("enabled", True))}
               for e in raw if isinstance(e, dict)]
    entries = [e for e in entries if e["url"]]
    return entries, seen | {e["url"] for e in entries}


def configured() -> list[dict]:
    """``[{url, enabled}]`` - the defaults until the user changes anything,
    plus defaults added since that the user has not seen yet."""
    loaded = _load()
    if loaded is None:
        return [{"url": u, "enabled": True} for u in DEFAULT_SOURCES]
    entries, seen = loaded
    new = [u for u in DEFAULT_SOURCES if u not in seen]
    if new:
        entries += [{"url": u, "enabled": True} for u in new]
        _save(entries)
    return entries


def _save(entries: list[dict]) -> None:
    previous = _load()
    seen = (previous[1] if previous else set()) | {e["url"] for e in entries}
    # Defaults shown so far count as seen - removing one keeps it removed.
    seen |= {u for u in DEFAULT_SOURCES if previous is None or u in previous[1]}
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_FILE.write_text(json.dumps(
        {"sources": entries, "seenDefaults": sorted(seen)}, indent=2), encoding="utf-8")


def normalize(url: str) -> str:
    url = (url or "").strip()
    if url and "://" not in url:
        url = "https://" + url
    if not https(url):
        raise StoreError(_("Only https sources are supported."))
    return url


def add(url: str) -> list[dict]:
    url = normalize(url)
    entries = configured()
    if not any(e["url"] == url for e in entries):
        entries.append({"url": url, "enabled": True})
        _save(entries)
    return entries


def remove(url: str) -> list[dict]:
    entries = [e for e in configured() if e["url"] != url]
    _save(entries)
    _cache_file(url).unlink(missing_ok=True)
    return entries


def set_enabled(url: str, enabled: bool) -> list[dict]:
    entries = configured()
    for e in entries:
        if e["url"] == url:
            e["enabled"] = bool(enabled)
    _save(entries)
    return entries


# -- Fetching -----------------------------------------------------------------


def _cache_file(url: str) -> Path:
    return CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")


def _read_cache(url: str) -> dict | None:
    try:
        return json.loads(_cache_file(url).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_cache(url: str, body: bytes, etag: str, modified: str) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    entry = {"url": url, "at": time.time(), "etag": etag, "modified": modified,
             "body": body.decode("utf-8", errors="replace")}
    tmp = _cache_file(url).with_suffix(".part")
    tmp.write_text(json.dumps(entry), encoding="utf-8")
    tmp.replace(_cache_file(url))


def _download(url: str, cached: dict | None, http) -> tuple[bytes | None, str, str]:
    """``(body, etag, last_modified)`` - body None: not modified."""
    headers = {}
    if cached:
        if cached.get("etag"):
            headers["If-None-Match"] = cached["etag"]
        if cached.get("modified"):
            headers["If-Modified-Since"] = cached["modified"]
    with http.get(url, headers=headers, timeout=TIMEOUT, stream=True) as resp:
        if resp.status_code == 304 and cached:
            return None, cached.get("etag", ""), cached.get("modified", "")
        resp.raise_for_status()
        if not https(resp.url):
            raise StoreError(_("The source redirected to a non-https address."))
        chunks, total = [], 0
        for chunk in resp.iter_content(1 << 16):
            total += len(chunk)
            if total > MAX_BYTES:
                raise StoreError(_("The source is too big."))
            chunks.append(chunk)
        return b"".join(chunks), resp.headers.get("ETag", ""), resp.headers.get("Last-Modified", "")


def fetch(url: str, *, force: bool = False, http=None) -> Source:
    """The source at ``url`` - from the cache while it is fresh."""
    url = normalize(url)
    cached = _read_cache(url)
    fresh = cached is not None and time.time() - cached.get("at", 0) < MAX_AGE
    error = ""
    body = None
    if force or not fresh:
        try:
            body, etag, modified = _download(url, cached, http or session())
            if body is None:                     # 304: unchanged, just fresh again
                body = cached["body"].encode()
            _write_cache(url, body, etag, modified)
            fetched_at = time.time()
        except StoreError:
            raise
        except Exception as exc:
            if cached is None:
                raise StoreError(_("The source cannot be loaded: {error}",
                                   error=str(exc) or type(exc).__name__)) from exc
            log.info("Source %s not reachable, using the cache: %s", url, exc)
            error = str(exc) or type(exc).__name__
    if body is None:
        body = cached["body"].encode()
        fetched_at = cached.get("at", 0.0)
    try:
        data = json.loads(body)
        source = parse_source(data, url)
    except ValueError as exc:
        raise StoreError(_("This is not a source in the AltStore format: {error}",
                           error=exc)) from exc
    source.fetched_at = fetched_at
    source.error = error
    return source
