"""All apps of all active sources - searchable, page by page.

One source can list thousands of apps; the interface asks for sixty at a
time. The index lives in memory for the backend's lifetime and is rebuilt
whenever a source is (re)loaded.

The same app often sits in several sources (Delta in AltStore and in
SideStore's picks, DolphiniOS in its own source and in Quantum). The store
shows it once: all entries with the same bundle ID form a group, and the
entry with the newest version speaks for it - on equal versions the source
higher up in the user's list. The others remain as offers to pick from.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from . import sources as sources_mod
from .model import Source, StoreApp
from . import probe
from .compat import compatible
from .risk import SOURCE_NOTES

#: Sources bigger than this are not probed - thousands of range requests
#: for one collection (AppTesters) would be anything but polite.
PROBE_LIMIT = 1000
PROBE_WORKERS = 4
from .updates import newer


class Catalog:
    def __init__(self, fetch: Callable[..., Source] = sources_mod.fetch) -> None:
        self._fetch = fetch
        self._lock = threading.Lock()
        self._sources: dict[str, Source] = {}
        self._errors: dict[str, str] = {}
        self._apps: list[StoreApp] = []
        self._by_key: dict[str, StoreApp] = {}
        self._groups: dict[str, list[StoreApp]] = {}
        #: download URL -> what the IPA says about itself (probe.facts).
        self._facts: dict[str, dict] = {}
        self._probe_pending = 0
        self._probe_thread: threading.Thread | None = None
        self.loaded = False

    # -- Loading --

    def load(self, *, force: bool = False, only: str | None = None) -> None:
        """Fetches the enabled sources (from the cache while fresh)."""
        enabled = [e["url"] for e in sources_mod.configured() if e["enabled"]]
        wanted = [only] if only else enabled
        fetched: dict[str, Source] = {}
        errors: dict[str, str] = {}

        def one(url: str):
            try:
                return url, self._fetch(url, force=force), ""
            except Exception as exc:
                return url, None, str(exc) or type(exc).__name__

        # Side by side - ten sources one after the other would keep the
        # store waiting for seconds.
        with ThreadPoolExecutor(max_workers=6) as pool:
            for url, source, error in pool.map(one, wanted):
                if source is not None:
                    fetched[url] = source
                else:
                    errors[url] = error
        with self._lock:
            if only:
                self._sources.update(fetched)
                self._errors.pop(only, None)
                self._errors.update(errors)
            else:
                self._sources = fetched
                self._errors = errors
            # Sources switched off or removed drop out of the index.
            self._sources = {u: s for u, s in self._sources.items() if u in enabled}
            self._reindex()
            self.loaded = True
        self._start_probing()

    # -- What the IPAs say about themselves --

    def _to_probe(self) -> list[str]:
        with self._lock:
            urls = []
            for src in self._sources.values():
                if len(src.apps) > PROBE_LIMIT:
                    continue
                for app in src.apps:
                    for v in app.versions[:1]:
                        urls.append(v.download_url)
            return list(dict.fromkeys(urls))

    def _start_probing(self) -> None:
        """Reads what is cached at once, the rest in the background."""
        urls = self._to_probe()
        todo = []
        for url in urls:
            hit = probe.cached(url)
            if hit is not None:
                self._facts[url] = hit
            elif url not in self._facts:
                todo.append(url)
        if not todo or (self._probe_thread and self._probe_thread.is_alive()):
            return
        self._probe_pending = len(todo)

        def run() -> None:
            def one(url: str) -> None:
                try:
                    self._facts[url] = probe.facts(url)
                finally:
                    self._probe_pending = max(0, self._probe_pending - 1)
            with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as pool:
                list(pool.map(one, todo))

        self._probe_thread = threading.Thread(target=run, name="store-probe", daemon=True)
        self._probe_thread.start()

    @property
    def probing(self) -> int:
        """How many IPAs are still being looked at."""
        return self._probe_pending

    def facts_for(self, app: StoreApp) -> dict | None:
        return self._facts.get(app.download_url)

    def compat(self, app: StoreApp, device: dict | None) -> bool | None:
        return compatible(app, self._facts.get(app.download_url), device)

    def ensure_loaded(self) -> None:
        if not self.loaded:
            self.load()

    def _reindex(self) -> None:
        order = {e["url"]: i for i, e in enumerate(sources_mod.configured())}
        apps = [a for s in self._sources.values() for a in s.apps]
        self._by_key = {a.key: a for a in apps}
        groups: dict[str, list[StoreApp]] = {}
        for app in apps:
            groups.setdefault(app.bundle_id.lower(), []).append(app)
        for offers in groups.values():
            offers.sort(key=lambda a: order.get(a.source_url, len(order)))
            best = offers[0]
            for other in offers[1:]:
                if newer(best.version, other.version, installed_date=best.date,
                         offered_date=other.date):
                    best = other
            offers.remove(best)
            offers.insert(0, best)
        self._groups = groups
        # One entry per app, the best offer first.
        self._apps = sorted((g[0] for g in groups.values()), key=lambda a: a.name.lower())

    # -- Reading --

    def sources(self) -> list[dict]:
        with self._lock:
            out = []
            for entry in sources_mod.configured():
                url = entry["url"]
                src = self._sources.get(url)
                out.append({
                    "url": url, "enabled": entry["enabled"],
                    "name": src.name if src else "", "iconUrl": src.icon_url if src else "",
                    "subtitle": src.subtitle if src else "",
                    "apps": len(src.apps) if src else 0,
                    "fetchedAt": src.fetched_at if src else None,
                    "error": self._errors.get(url) or (src.error if src else ""),
                    "notice": SOURCE_NOTES.get(url, ""),
                })
            return out

    def categories(self) -> list[str]:
        with self._lock:
            return sorted({a.category for g in self._groups.values() for a in g if a.category})

    def offers(self, bundle_id: str) -> list[StoreApp]:
        """Every source's entry for this app, the best first."""
        with self._lock:
            return list(self._groups.get(bundle_id.lower(), []))

    def search(self, query: str = "", *, source: str | None = None,
               category: str | None = None, offset: int = 0, limit: int = 60,
               device: dict | None = None, only_compatible: bool = True) -> dict:
        """One hit per app. Filtered by source, the hit is that source's
        entry - so the list shows what that source offers.

        With a ``device``, the hit is the best offer that fits it (an older
        version elsewhere may still run where the newest does not), and apps
        that fit nowhere are left out - unless ``only_compatible`` is off.
        ``items`` are ``(app, compatible)`` pairs; compatible is None where
        nothing is known yet."""
        words = [w for w in (query or "").lower().split() if w]
        with self._lock:
            hits = []
            hidden = 0
            for app in self._apps:
                group = self._groups.get(app.bundle_id.lower(), [app])
                if source:
                    group = [a for a in group if a.source_url == source]
                    if not group:
                        continue
                app, fits = group[0], True
                if device:
                    rated = [(a, self.compat(a, device)) for a in group]
                    fitting = [x for x in rated if x[1] is not False]
                    if fitting:
                        app, fits = fitting[0]
                    else:
                        app, fits = rated[0]
                        if only_compatible:
                            hidden += 1
                            continue
                if category and not any(a.category == category for a in group):
                    continue
                if words:
                    hay = f"{app.name} {app.developer} {app.bundle_id} {app.subtitle}".lower()
                    if not all(w in hay for w in words):
                        continue
                hits.append((app, fits))
        offset = max(0, int(offset))
        limit = max(1, min(200, int(limit)))
        return {"total": len(hits), "items": hits[offset:offset + limit], "hidden": hidden}

    def get(self, source_url: str, bundle_id: str) -> StoreApp | None:
        with self._lock:
            return self._by_key.get(f"{source_url}|{bundle_id}")

    def find(self, bundle_id: str, source_url: str = "") -> StoreApp | None:
        """By bundle ID - in the given source first, else in any."""
        with self._lock:
            if source_url:
                hit = self._by_key.get(f"{source_url}|{bundle_id}")
                if hit is not None:
                    return hit
            group = self._groups.get(bundle_id.lower())
            return group[0] if group else None


#: One catalog per process - the server and the refresh share it.
CATALOG = Catalog()
