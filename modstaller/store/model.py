"""What a source says about an app - and reading it from the JSON.

Three dialects of the same format are in the wild:

* **AltStore** (``apps.altstore.io``): ``versions[]`` with ``version``,
  ``date``, ``downloadURL``, ``size``, ``minOSVersion`` and ``sha256``;
* **SideStore** (``community-apps.sidestore.io``): the same, without
  ``sha256``;
* **flat** (AppTesters and friends): one version at the app itself, with
  their own field names (``bundleID``, ``down``, ``icon``).

The newest version (``versions[0]``) wins over the flat fields. Entries that
lack a name, a bundle ID or an https download are skipped - one broken app
must not cost the whole source.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

#: Versions kept per app for the version list in the interface.
MAX_VERSIONS = 10


@dataclass
class StoreVersion:
    version: str
    date: str = ""
    download_url: str = ""
    size: int = 0
    min_os: str = ""
    max_os: str = ""
    sha256: str = ""
    notes: str = ""


@dataclass
class StoreApp:
    source_url: str
    name: str
    bundle_id: str
    version: str
    download_url: str
    developer: str = ""
    date: str = ""
    size: int = 0
    icon_url: str = ""
    subtitle: str = ""
    description: str = ""
    screenshots: list[str] = field(default_factory=list)
    min_os: str = ""
    max_os: str = ""
    sha256: str = ""
    category: str = ""
    tint: str = ""
    versions: list[StoreVersion] = field(default_factory=list)
    #: "jailbreak", "exploit", "store" - or empty (see risk.py).
    warning: str = ""

    @property
    def key(self) -> str:
        return f"{self.source_url}|{self.bundle_id}"

    def as_dict(self, *, full: bool = False) -> dict:
        d = {"source": self.source_url, "name": self.name, "bundleId": self.bundle_id,
             "version": self.version, "developer": self.developer, "date": self.date,
             "size": self.size, "iconUrl": self.icon_url, "subtitle": self.subtitle,
             "category": self.category, "minOs": self.min_os, "tint": self.tint,
             "warning": self.warning}
        if full:
            d.update(description=self.description, screenshots=self.screenshots,
                     versions=[asdict(v) for v in self.versions])
        return d


@dataclass
class Source:
    url: str
    name: str = ""
    identifier: str = ""
    icon_url: str = ""
    subtitle: str = ""
    apps: list[StoreApp] = field(default_factory=list)
    fetched_at: float = 0.0
    #: Why the last fetch failed - the apps are then from the cache.
    error: str = ""


def https(url) -> str:
    """The URL if it is https, else empty - nothing is fetched in plain text."""
    return url.strip() if isinstance(url, str) and url.strip().lower().startswith("https://") else ""


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _screenshots(app: dict) -> list[str]:
    raw = app.get("screenshotURLs") or app.get("screenshots") or []
    if isinstance(raw, dict):                       # {"iphone": [...], "ipad": [...]}
        raw = raw.get("iphone") or next(iter(raw.values()), [])
    out = []
    for item in raw if isinstance(raw, list) else []:
        url = https(item.get("imageURL") if isinstance(item, dict) else item)
        if url:
            out.append(url)
    return out[:12]


def _versions(app: dict) -> list[StoreVersion]:
    out = []
    for v in app.get("versions") or []:
        if not isinstance(v, dict):
            continue
        url = https(v.get("downloadURL"))
        version = _text(v.get("version"))
        if not url or not version:
            continue
        out.append(StoreVersion(
            version=version, date=_text(v.get("date")), download_url=url,
            size=_int(v.get("size")), min_os=_text(v.get("minOSVersion")),
            max_os=_text(v.get("maxOSVersion")),
            sha256=_text(v.get("sha256")).lower(),
            notes=_text(v.get("localizedDescription"))))
        if len(out) >= MAX_VERSIONS:
            break
    return out


def parse_app(raw: dict, source_url: str) -> StoreApp | None:
    if not isinstance(raw, dict):
        return None
    name = _text(raw.get("name"))
    bundle_id = _text(raw.get("bundleIdentifier") or raw.get("bundleID"))
    versions = _versions(raw)
    if versions:
        newest = versions[0]
    else:
        url = https(raw.get("downloadURL") or raw.get("down"))
        version = _text(raw.get("version"))
        if not url or not version:
            return None
        newest = StoreVersion(version=version, date=_text(raw.get("versionDate")),
                              download_url=url, size=_int(raw.get("size")),
                              min_os=_text(raw.get("minOSVersion")),
                              max_os=_text(raw.get("maxOSVersion")),
                              sha256=_text(raw.get("sha256")).lower(),
                              notes=_text(raw.get("versionDescription")))
        versions = [newest]
    if not name or not bundle_id:
        return None
    from .risk import classify
    description = _text(raw.get("localizedDescription"))
    return StoreApp(
        warning=classify(bundle_id, name, _text(raw.get("subtitle")), description),
        source_url=source_url, name=name, bundle_id=bundle_id,
        version=newest.version, download_url=newest.download_url,
        developer=_text(raw.get("developerName")), date=newest.date,
        size=newest.size or _int(raw.get("size")),
        icon_url=https(raw.get("iconURL") or raw.get("icon")),
        subtitle=_text(raw.get("subtitle")),
        description=description,
        screenshots=_screenshots(raw), min_os=newest.min_os, max_os=newest.max_os,
        sha256=newest.sha256, category=_text(raw.get("category")),
        tint=_text(raw.get("tintColor")).lstrip("#")[:6], versions=versions)


def parse_source(data: dict, url: str) -> Source:
    if not isinstance(data, dict) or not isinstance(data.get("apps"), list):
        raise ValueError("not a source: no app list")
    apps, seen = [], set()
    for raw in data["apps"]:
        app = parse_app(raw, url)
        if app is None or app.bundle_id in seen:
            continue
        seen.add(app.bundle_id)
        apps.append(app)
    meta = data.get("META") if isinstance(data.get("META"), dict) else {}
    return Source(url=url, name=_text(data.get("name") or meta.get("repoName")) or url,
                  identifier=_text(data.get("identifier")),
                  icon_url=https(data.get("iconURL") or meta.get("repoIcon")),
                  subtitle=_text(data.get("subtitle")), apps=apps)
