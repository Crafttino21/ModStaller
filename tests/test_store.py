"""The IPA store: reading sources, searching, downloading, updates."""

from __future__ import annotations

import hashlib
import os
import io
import json
import pathlib
import plistlib
import zipfile

import pytest

from modstaller import config
from modstaller.store import catalog, download, images, sources, updates
from modstaller.store.model import parse_source

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


FLAT = {  # the flat dialect: one version at the app, own field names
    "name": "Flat Repo", "META": {"repoName": "Flat Repo", "repoIcon": "https://x.test/r.png"},
    "apps": [
        {"name": "Emu", "bundleID": "org.example.emu", "version": "2.1", "versionDate": "2026-01-02",
         "size": 1234, "down": "https://x.test/emu.ipa", "icon": "https://x.test/emu.png",
         "localizedDescription": "An emulator"},
        {"name": "Plain http", "bundleID": "org.example.http", "version": "1",
         "down": "http://x.test/insecure.ipa"},
        {"name": "", "bundleID": "org.example.noname", "version": "1", "down": "https://x.test/a.ipa"},
        "garbage",
    ],
}


# -- Parsing --------------------------------------------------------------------


def test_altstore_source():
    src = parse_source(_fixture("store_altstore.json"), "https://apps.altstore.io/")
    delta = next(a for a in src.apps if a.bundle_id == "com.rileytestut.Delta")
    assert src.name == "AltStore"
    assert delta.version == delta.versions[0].version
    assert delta.download_url.startswith("https://")
    assert delta.size > 0 and delta.icon_url.startswith("https://")
    assert len(delta.versions) == 2


def test_sidestore_source():
    src = parse_source(_fixture("store_sidestore.json"), "https://community-apps.sidestore.io/x.json")
    ppsspp = next(a for a in src.apps if a.bundle_id == "org.ppsspp.ppsspp")
    assert ppsspp.name == "PPSSPP" and ppsspp.version and ppsspp.screenshots


def test_flat_source_and_broken_entries_are_skipped():
    src = parse_source(FLAT, "https://x.test/")
    assert src.name == "Flat Repo" and src.icon_url == "https://x.test/r.png"
    assert [a.bundle_id for a in src.apps] == ["org.example.emu"]
    emu = src.apps[0]
    assert (emu.version, emu.size, emu.download_url, emu.icon_url) == (
        "2.1", 1234, "https://x.test/emu.ipa", "https://x.test/emu.png")


def test_not_a_source():
    with pytest.raises(ValueError):
        parse_source({"hello": "world"}, "https://x.test/")


# -- Sources list and fetching ------------------------------------------------


def test_defaults_until_changed_and_only_https():
    assert [e["url"] for e in sources.configured()] == list(sources.DEFAULT_SOURCES)
    sources.add("example.org/repo.json")
    assert sources.configured()[-1]["url"] == "https://example.org/repo.json"
    with pytest.raises(sources.StoreError):
        sources.add("http://example.org/repo.json")
    sources.set_enabled("https://example.org/repo.json", False)
    assert sources.configured()[-1]["enabled"] is False
    sources.remove("https://example.org/repo.json")
    assert len(sources.configured()) == len(sources.DEFAULT_SOURCES)


class _Resp:
    def __init__(self, body=b"", status=200, headers=None, url="https://x.test/"):
        self._body, self.status_code, self.headers, self.url = body, status, headers or {}, url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, size):
        for i in range(0, len(self._body), 7):
            yield self._body[i:i + 7]


class _Http:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url, headers=None, timeout=None, stream=False):
        self.requests.append((url, headers or {}))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_fetch_caches_and_asks_with_etag():
    body = json.dumps(FLAT).encode()
    http = _Http(_Resp(body, headers={"ETag": '"v1"'}))
    src = sources.fetch("https://x.test/", http=http)
    assert len(src.apps) == 1 and not src.error
    # Fresh: no network at all.
    assert len(sources.fetch("https://x.test/", http=_Http()).apps) == 1
    # Forced: asks with the ETag, 304 keeps the cache.
    http2 = _Http(_Resp(status=304))
    assert len(sources.fetch("https://x.test/", force=True, http=http2).apps) == 1
    assert http2.requests[0][1]["If-None-Match"] == '"v1"'


def test_offline_falls_back_to_the_cache():
    sources.fetch("https://x.test/", http=_Http(_Resp(json.dumps(FLAT).encode())))
    src = sources.fetch("https://x.test/", force=True, http=_Http(OSError("offline")))
    assert len(src.apps) == 1 and "offline" in src.error
    with pytest.raises(sources.StoreError):
        sources.fetch("https://y.test/", http=_Http(OSError("offline")))


def test_a_redirect_to_http_is_refused():
    http = _Http(_Resp(json.dumps(FLAT).encode(), url="http://evil.test/"))
    with pytest.raises(sources.StoreError, match="https"):
        sources.fetch("https://x.test/", http=http)


# -- Catalog --------------------------------------------------------------------


def _catalog():
    sources_by_url = {
        "https://a.test/": parse_source(_fixture("store_altstore.json"), "https://a.test/"),
        "https://b.test/": parse_source(_fixture("store_sidestore.json"), "https://b.test/"),
    }
    sources._save([{"url": u, "enabled": True} for u in sources_by_url])
    cat = catalog.Catalog(fetch=lambda url, force=False: sources_by_url[url])
    cat.load()
    return cat


def test_search_pages_and_filters():
    cat = _catalog()
    everything = cat.search()
    assert everything["total"] == 6
    names = [a.name for a, _ in everything["items"]]
    assert names == sorted(names, key=str.lower)
    assert [a.bundle_id for a, _ in cat.search("delta")["items"]] == ["com.rileytestut.Delta"]
    assert cat.search("", source="https://b.test/")["total"] == 3
    page = cat.search(offset=4, limit=5)
    assert page["total"] == 6 and len(page["items"]) == 2


def test_a_broken_source_does_not_hide_the_others():
    good = parse_source(FLAT, "https://good.test/")
    sources._save([{"url": "https://good.test/", "enabled": True},
                   {"url": "https://bad.test/", "enabled": True}])

    def fetch(url, force=False):
        if url == "https://bad.test/":
            raise sources.StoreError("down")
        return good
    cat = catalog.Catalog(fetch=fetch)
    cat.load()
    assert cat.search()["total"] == 1
    bad = next(s for s in cat.sources() if s["url"] == "https://bad.test/")
    assert bad["error"] == "down"


def test_find_prefers_the_source_it_came_from():
    cat = _catalog()
    assert cat.find("org.ppsspp.ppsspp").source_url == "https://b.test/"
    assert cat.find("com.rileytestut.Delta", "https://a.test/").name == "Delta"
    assert cat.find("nope") is None


# -- Download -----------------------------------------------------------------


def _ipa_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Payload/Emu.app/Info.plist", plistlib.dumps({
            "CFBundleIdentifier": "org.example.emu", "CFBundleName": "Emu"}))
        zf.writestr("Payload/Emu.app/Emu", b"\xcf\xfa\xed\xfe")
    return buf.getvalue()


def _app(size=None, sha=""):
    data = _ipa_bytes()
    src = parse_source(FLAT, "https://x.test/")
    app = src.apps[0]
    app.versions[0].size = len(data) if size is None else size
    app.versions[0].sha256 = sha
    return app, data


def test_download_keeps_the_ipa_and_does_not_repeat():
    app, data = _app(sha=hashlib.sha256(_ipa_bytes()).hexdigest())
    seen = []
    path = download.download(app, http=_Http(_Resp(data, url="https://x.test/emu.ipa")),
                             progress=seen.append)
    assert path.read_bytes() == data and path.parent.parent == config.IPA_CACHE_DIR
    assert seen[-1] == 100
    assert not list(path.parent.glob("*.part"))
    # Already there and matching: no second download.
    assert download.download(app, http=_Http()) == path


@pytest.mark.parametrize("change, message", [
    ({"sha": "0" * 64}, "checksum"),
    ({"size": 10}, "bigger"),
    ({"size": 10 ** 6}, "incomplete"),
])
def test_a_bad_download_leaves_nothing_behind(change, message):
    app, data = _app(**change)
    with pytest.raises(sources.StoreError, match=message):
        download.download(app, http=_Http(_Resp(data)))
    assert not list(config.IPA_CACHE_DIR.rglob("*.ipa"))
    assert not list(config.IPA_CACHE_DIR.rglob("*.part"))


def test_not_an_ipa_is_refused():
    app, _ = _app(size=0)
    with pytest.raises(sources.StoreError, match="not a valid IPA"):
        download.download(app, http=_Http(_Resp(b"<html>not found</html>")))
    assert not list(config.IPA_CACHE_DIR.rglob("*.ipa"))


def test_file_names_stay_in_the_folder():
    assert download._safe("../../etc/passwd") == "etc_passwd"
    assert download._safe("") == "app"


# -- Updates ------------------------------------------------------------------


@pytest.mark.parametrize("installed, offered, expected", [
    ("1.9", "1.10", True), ("1.10", "1.9", False), ("1.2", "1.2.0", False),
    ("v1.13.2", "1.14", True), ("2.0", "2.0", False),
    ("", "1.0", False),      # unknown installed version: better no update than a wrong one
])
def test_version_comparison(installed, offered, expected):
    assert updates.newer(installed, offered) is expected


def test_same_numbers_newer_date_counts():
    assert updates.newer("1.0b1", "1.0b2", installed_date="2026-01-01",
                         offered_date="2026-02-01") is True


def test_available_updates_for_installed_store_apps():
    from types import SimpleNamespace
    cat = _catalog()
    delta = cat.find("com.rileytestut.Delta")
    recs = [SimpleNamespace(bundle_id="com.rileytestut.Delta.T1", name="Delta",
                            store_source="https://a.test/", store_bundle_id=delta.bundle_id,
                            store_version="0.1"),
            SimpleNamespace(bundle_id="x", name="x", store_source="", store_bundle_id="",
                            store_version="")]
    [upd] = updates.available(recs, cat.find)
    assert (upd["bundleId"], upd["offered"]) == ("com.rileytestut.Delta.T1", delta.version)


# -- Images -------------------------------------------------------------------


def _png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", (512, 512), (255, 0, 0, 255)).save(buf, "PNG")
    return buf.getvalue()


def test_images_become_small_cached_data_urls():
    http = _Http(_Resp(_png(), headers={"Content-Type": "image/png"}))
    url = images.image("https://x.test/i.png", "icon", http=http)
    assert url.startswith("data:image/png;base64,")
    from PIL import Image
    import base64
    img = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    assert max(img.size) <= 128
    assert images.image("https://x.test/i.png", "icon", http=_Http()) == url   # cached


def test_only_https_images():
    with pytest.raises(sources.StoreError):
        images.image("http://x.test/i.png")
    with pytest.raises(sources.StoreError, match="not an image"):
        images.image("https://x.test/i.png", http=_Http(_Resp(b"<html>", headers={"Content-Type": "text/html"})))


# -- Cache cleanup ------------------------------------------------------------


def test_clearing_keeps_what_installed_apps_need(monkeypatch):
    from types import SimpleNamespace

    from modstaller.store import cache
    keep = config.IPA_CACHE_DIR / "org.example.emu" / "2.1.ipa"
    old = config.IPA_CACHE_DIR / "org.example.emu" / "2.0.ipa"
    gone = config.IPA_CACHE_DIR / "org.gone" / "1.ipa"
    for p in (keep, old, gone):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * 10)
    monkeypatch.setattr("modstaller.state.store.all_installs",
                        lambda: [SimpleNamespace(source_ipa=str(keep))])
    out = cache.clear()
    assert keep.exists() and not old.exists() and not gone.exists()
    assert not (config.IPA_CACHE_DIR / "org.gone").exists()
    assert out["removedIpas"] == 2


# -- Wiring: server and renewal --------------------------------------------------


async def test_store_install_downloads_then_installs_with_the_origin(monkeypatch):
    from modstaller import pipeline
    from modstaller import server as srv
    from modstaller.pipeline import InstallOutcome
    from modstaller.store import catalog as catalog_mod
    from test_server import Wire

    app, data = _app()
    cat = catalog.Catalog(fetch=lambda url, force=False: parse_source(FLAT, url))
    sources._save([{"url": "https://x.test/", "enabled": True}])
    cat.load()
    cat.get("https://x.test/", "org.example.emu").versions[0].size = len(data)
    monkeypatch.setattr(catalog_mod, "CATALOG", cat)
    monkeypatch.setattr(sources, "session", lambda: _Http(_Resp(data)))
    seen = {}

    async def fake_install(path, **kw):
        seen["path"], seen["origin"] = path, kw["store_origin"]
        return InstallOutcome("org.example.emu.T", "Emu", "lockdown", 7.0, False)
    monkeypatch.setattr(pipeline, "install", fake_install)

    w = Wire()
    w.call(1, "store.install", source="https://x.test/", bundleId="org.example.emu")
    reply = await w.reply_to(1)
    assert reply["result"]["bundleId"] == "org.example.emu.T"
    assert seen["path"].read_bytes() == data
    assert seen["origin"] == {"source": "https://x.test/", "bundleId": "org.example.emu",
                              "version": "2.1"}
    assert srv


async def test_renewing_updates_a_store_app(monkeypatch, tmp_path):
    from modstaller import pipeline
    from modstaller.apple import session as session_mod
    from modstaller.pipeline import InstallOutcome
    from modstaller.state import store as store_mod
    from modstaller.store import catalog as catalog_mod

    session_mod.Session(adsid="a", idms_token="i", identity_token="t",
                        created_at=0.0, app_token="x").save()
    old_ipa = tmp_path / "old.ipa"
    old_ipa.write_bytes(b"old")
    rec = store_mod.InstallRecord(
        bundle_id="org.example.emu.T", original_bundle_id="org.example.emu", name="Emu",
        team_id="T", udid="U", source_ipa=str(old_ipa), app_id_id="1", profile_path="",
        expires_at=0.0, adsid="a", store_source="https://x.test/",
        store_bundle_id="org.example.emu", store_version="2.0")
    monkeypatch.setattr(store_mod, "all_installs", lambda: [rec])

    app, data = _app()
    cat = catalog.Catalog(fetch=lambda url, force=False: parse_source(FLAT, url))
    sources._save([{"url": "https://x.test/", "enabled": True}])
    cat.load()
    cat.get("https://x.test/", "org.example.emu").versions[0].size = len(data)
    monkeypatch.setattr(catalog_mod, "CATALOG", cat)
    monkeypatch.setattr(sources, "session", lambda: _Http(_Resp(data)))
    calls = []

    async def fake_install(path, **kw):
        calls.append((path, kw))
        return InstallOutcome(kw["bundle_id"], "Emu", "lockdown", 7.0, False)
    monkeypatch.setattr(pipeline, "install", fake_install)

    [out] = await pipeline.refresh(only=rec.bundle_id, store_updates=True, on_step=lambda m: None)
    path, kw = calls[0]
    assert path != old_ipa and path.read_bytes() == data
    assert kw["bundle_id"] == "org.example.emu.T", "same ID on the device - data stays"
    assert kw["store_origin"]["version"] == "2.1"
    assert out.updated_to == "2.1"

    # Without store updates the installed IPA is used as it is.
    calls.clear()
    await pipeline.refresh(only=rec.bundle_id, on_step=lambda m: None)
    assert calls[0][0] == old_ipa and calls[0][1]["store_origin"] is None


async def test_an_unreachable_store_never_stops_a_renewal(monkeypatch, tmp_path):
    from modstaller import pipeline
    from modstaller.apple import session as session_mod
    from modstaller.pipeline import InstallOutcome
    from modstaller.state import store as store_mod

    session_mod.Session(adsid="a", idms_token="i", identity_token="t",
                        created_at=0.0, app_token="x").save()
    old_ipa = tmp_path / "old.ipa"
    old_ipa.write_bytes(b"old")
    rec = store_mod.InstallRecord(
        bundle_id="b.T", original_bundle_id="b", name="B", team_id="T", udid="U",
        source_ipa=str(old_ipa), app_id_id="1", profile_path="", expires_at=0.0, adsid="a",
        store_source="https://down.test/", store_bundle_id="b", store_version="1")
    monkeypatch.setattr(store_mod, "all_installs", lambda: [rec])
    sources._save([{"url": "https://down.test/", "enabled": True}])
    monkeypatch.setattr(sources, "session", lambda: _Http(OSError("offline")))
    calls = []

    async def fake_install(path, **kw):
        calls.append(path)
        return InstallOutcome("b.T", "B", "lockdown", 7.0, False)
    monkeypatch.setattr(pipeline, "install", fake_install)
    await pipeline.refresh(only="b.T", store_updates=True, on_step=lambda m: None)
    assert calls == [old_ipa]


def test_new_defaults_reach_existing_lists_once(monkeypatch):
    """The first version of sources.json was a bare list with two defaults.
    Sources that became defaults later are added once - and one the user
    removes stays removed."""
    sources.SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    sources.SOURCES_FILE.write_text(json.dumps([
        {"url": sources.DEFAULT_SOURCES[0], "enabled": True},
        {"url": "https://mine.test/", "enabled": False},
    ]))
    urls = [e["url"] for e in sources.configured()]
    # The old default the user had removed stays gone, the new ones arrive.
    assert sources.DEFAULT_SOURCES[1] not in urls
    assert "https://mine.test/" in urls
    assert all(u in urls for u in sources.DEFAULT_SOURCES[2:])

    sources.remove(sources.DEFAULT_SOURCES[3])
    assert sources.DEFAULT_SOURCES[3] not in [e["url"] for e in sources.configured()]


def test_removing_a_default_on_a_fresh_list_keeps_it_removed():
    sources.remove(sources.DEFAULT_SOURCES[0])
    assert sources.DEFAULT_SOURCES[0] not in [e["url"] for e in sources.configured()]
    assert len(sources.configured()) == len(sources.DEFAULT_SOURCES) - 1


def test_defaults_are_https_and_unique():
    assert len(set(sources.DEFAULT_SOURCES)) == len(sources.DEFAULT_SOURCES)
    assert all(u.startswith("https://") for u in sources.DEFAULT_SOURCES)


# -- One app, several sources ---------------------------------------------------


def _dup_catalog():
    def src(url, version, date):
        return parse_source({"name": url, "apps": [
            {"name": "Emu", "bundleIdentifier": "org.example.emu",
             "versions": [{"version": version, "date": date, "downloadURL": f"{url}emu.ipa", "size": 1}]},
            {"name": "Only here", "bundleIdentifier": f"org.example.{url[8]}",
             "versions": [{"version": "1", "downloadURL": f"{url}x.ipa"}]},
        ]}, url)
    by_url = {"https://a.test/": src("https://a.test/", "1.9", "2026-01-01"),
              "https://b.test/": src("https://b.test/", "1.10", "2026-02-01"),
              "https://c.test/": src("https://c.test/", "1.10", "2026-02-01")}
    sources._save([{"url": u, "enabled": True} for u in by_url])
    cat = catalog.Catalog(fetch=lambda url, force=False: by_url[url])
    cat.load()
    return cat


def test_the_same_app_from_several_sources_shows_once():
    cat = _dup_catalog()
    emus = [a for a, _ in cat.search("emu")["items"] if a.bundle_id == "org.example.emu"]
    assert len(emus) == 1
    # The newest version speaks for the group; on a tie the source higher up.
    assert (emus[0].source_url, emus[0].version) == ("https://b.test/", "1.10")
    offers = cat.offers("org.example.emu")
    assert [o.source_url for o in offers] == ["https://b.test/", "https://a.test/", "https://c.test/"]
    assert cat.search()["total"] == 4


def test_filtering_by_source_shows_that_sources_entry():
    cat = _dup_catalog()
    [emu] = [a for a, _ in cat.search(source="https://a.test/")["items"]
             if a.bundle_id == "org.example.emu"]
    assert emu.version == "1.9"


def test_find_falls_back_to_the_best_offer():
    cat = _dup_catalog()
    assert cat.find("org.example.emu", "https://gone.test/").source_url == "https://b.test/"
    assert cat.find("ORG.EXAMPLE.EMU").version == "1.10"


# -- Warnings -----------------------------------------------------------------


def test_jailbreak_tools_are_marked():
    from modstaller.store import risk
    src = parse_source({"name": "Q", "apps": [
        {"name": "unc0ver", "bundleIdentifier": "science.xnu.undecimus",
         "versions": [{"version": "8", "downloadURL": "https://q.test/u.ipa"}]},
        {"name": "NewJB", "bundleIdentifier": "org.new.jb", "subtitle": "A jailbreak for iOS 17",
         "versions": [{"version": "1", "downloadURL": "https://q.test/n.ipa"}]},
        {"name": "Emu", "bundleIdentifier": "org.emu", "localizedDescription": "Works without jailbreak.",
         "versions": [{"version": "1", "downloadURL": "https://q.test/e.ipa"}]},
        {"name": "appdb", "bundleIdentifier": "it.ned.appdb-ios",
         "versions": [{"version": "1", "downloadURL": "https://q.test/a.ipa"}]},
    ]}, "https://q.test/")
    warn = {a.name: a.warning for a in src.apps}
    assert warn == {"unc0ver": risk.JAILBREAK, "NewJB": risk.JAILBREAK, "Emu": "",
                    "appdb": risk.THIRD_PARTY_STORE}
    assert src.apps[0].as_dict()["warning"] == risk.JAILBREAK


def test_quantum_is_a_default_with_a_note():
    from modstaller.store import risk
    url = "https://quarksources.github.io/dist/quantumsource.min.json"
    assert url in sources.DEFAULT_SOURCES
    assert risk.SOURCE_NOTES[url] == risk.JAILBREAK


# -- Fits the device? -----------------------------------------------------------


class _RangeHttp:
    """Serves bytes with HTTP ranges, like GitHub's release CDN."""

    def __init__(self, data: bytes, ranges=True):
        self.data, self.ranges, self.calls = data, ranges, 0

    def get(self, url, headers=None, timeout=None, stream=False):
        self.calls += 1
        rng = (headers or {}).get("Range", "")
        if not self.ranges or not rng.startswith("bytes=") or rng.startswith("bytes=-"):
            return _Resp(self.data, status=200 if self.ranges else 200, url=url)
        a, b = rng[6:].split("-")
        a, b = int(a), min(int(b), len(self.data) - 1)
        body = self.data[a:b + 1]
        return _RangeResp(body, url, f"bytes {a}-{b}/{len(self.data)}")


class _RangeResp(_Resp):
    def __init__(self, body, url, content_range):
        super().__init__(body, status=206, headers={"Content-Range": content_range}, url=url)
        self.raw = io.BytesIO(body)
        self.raw.read = lambda n=-1, decode_content=True, _r=self.raw: io.BytesIO.read(_r, n)


def _big_ipa(info: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Payload/Big.app/Big", os.urandom(300_000))     # makes ranges matter
        zf.writestr("Payload/Big.app/Info.plist", plistlib.dumps(info))
        zf.writestr("Payload/Big.app/PlugIns/X.appex/Info.plist", plistlib.dumps({"x": 1}))
    return buf.getvalue()


def test_the_info_plist_is_read_with_a_few_ranges():
    from modstaller.store import probe
    data = _big_ipa({"CFBundleIdentifier": "b", "UIDeviceFamily": [2],
                     "MinimumOSVersion": "16.0", "CFBundleSupportedPlatforms": ["iPhoneOS"]})
    http = _RangeHttp(data)
    facts = probe.facts("https://cdn.test/big.ipa", http=http)
    assert facts["families"] == [2] and facts["minOs"] == "16.0" and facts["platform"] == "ios"
    assert http.calls <= 5, "a few blocks - not the whole IPA"
    # Cached: no second look.
    assert probe.facts("https://cdn.test/big.ipa", http=_RangeHttp(b"")) == facts


def test_no_range_support_means_unknown_not_an_error():
    from modstaller.store import probe
    facts = probe.facts("https://cdn.test/plain.ipa", http=_RangeHttp(b"x", ranges=False))
    assert "error" in facts


def _dev(platform="ios", form="island", os_version="18.0"):
    return {"platform": platform, "formFactor": form, "osVersion": os_version}


def _probed(platform="ios", families=(1, 2), min_os="14.0"):
    return {"platform": platform, "families": list(families), "minOs": min_os}


@pytest.mark.parametrize("facts, device, expected", [
    (_probed(), _dev(), True),
    (_probed(min_os="19.0"), _dev(), False),                          # iOS too old
    (_probed(families=[2]), _dev(), False),                           # iPad-only on iPhone
    (_probed(families=[2]), _dev(form="ipad"), True),
    (_probed(families=[1]), _dev(form="ipad"), True),                 # iPhone app on iPad
    (_probed(), _dev("tvos", "tv", "18.0"), False),                   # iOS app on Apple TV
    (_probed("tvos", [3], "17.0"), _dev("tvos", "tv", "18.0"), True),
    (_probed(), _dev("xros", "vision", "2.4"), True),                 # Designed for iPad
    (_probed("xros", [7], "1.0"), _dev(), False),
    (None, _dev(), None),                                             # not read yet
    (None, _dev("tvos", "tv"), None),
    ({"error": "no ranges"}, _dev(), None),
])
def test_compatibility_rules(facts, device, expected):
    from types import SimpleNamespace

    from modstaller.store.compat import compatible
    app = SimpleNamespace(min_os="", max_os="")
    assert compatible(app, facts, device) is expected


def test_the_sources_os_limits_count_while_nothing_is_read():
    from types import SimpleNamespace

    from modstaller.store.compat import compatible
    assert compatible(SimpleNamespace(min_os="19.0", max_os=""), None, _dev()) is False
    assert compatible(SimpleNamespace(min_os="", max_os="15.0"), None, _dev()) is False


def test_the_store_picks_the_offer_that_fits_and_hides_the_rest():
    cat = _dup_catalog()                       # emu 1.10 in b and c, 1.9 in a
    new = [o for o in cat.offers("org.example.emu") if o.version == "1.10"]
    old = next(o for o in cat.offers("org.example.emu") if o.version == "1.9")
    for o in new:
        cat._facts[o.download_url] = _probed(min_os="18.0")
    cat._facts[old.download_url] = _probed(min_os="15.0")
    for bundle in ("org.example.a", "org.example.b", "org.example.c"):
        for o in cat.offers(bundle):
            cat._facts[o.download_url] = _probed(families=[2])        # iPad-only

    found = cat.search(device=_dev(os_version="16.0"))
    [(emu, fits)] = [(a, f) for a, f in found["items"] if a.bundle_id == "org.example.emu"]
    assert (emu.version, fits) == ("1.9", True), "the older version still runs on iOS 16"
    assert found["total"] == 1 and found["hidden"] == 3

    everything = cat.search(device=_dev(os_version="16.0"), only_compatible=False)
    assert everything["total"] == 4
