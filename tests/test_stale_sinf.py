"""FairPlay leftovers in decrypted IPAs.

The App Store's ``SC_Info/Manifest.plist`` tells installd which bundles get
a copy of the app's SINF - and installd creates those paths on install,
folders included. Modded IPAs often have extensions taken out while the
manifest still names them; iOS 27 then finds a ``.appex`` without an
Info.plist and refuses the install ("Failed to unarchive journal entry
data"). Measured on an iPhone with iOS 27.0.1 (installd log).
"""

from __future__ import annotations

import plistlib
import zipfile

from modstaller.signing.prepare import stale_sinf_paths, unpack_without

APP = "Payload/YouTube.app/"
MANIFEST = {
    "SinfPaths": ["SC_Info/YouTube.sinf"],
    "SinfReplicationPaths": [
        "Frameworks/widevine.framework/SC_Info/widevine.sinf",
        "PlugIns/IntentsExtension.appex/SC_Info/IntentsExtension.sinf",
        "PlugIns/ShareExtension.appex/SC_Info/ShareExtension.sinf",
        "Watch/YouTubeWatch.app/SC_Info/YouTubeWatch.sinf",
        "SC_Info/YouTube.sinf",
    ],
}


def _ipa(tmp_path, manifest=MANIFEST, *, share=True, watch=False):
    ipa = tmp_path / "in.ipa"
    with zipfile.ZipFile(ipa, "w") as zf:
        zf.writestr(APP + "Info.plist", plistlib.dumps({}))
        zf.writestr(APP + "YouTube", b"bin")
        zf.writestr(APP + "SC_Info/YouTube.sinf", b"sinf")
        if manifest is not None:
            zf.writestr(APP + "SC_Info/Manifest.plist", plistlib.dumps(manifest))
        zf.writestr(APP + "Frameworks/widevine.framework/Info.plist", b"p")
        zf.writestr(APP + "Frameworks/widevine.framework/SC_Info/widevine.sinf", b"s")
        if share:
            zf.writestr(APP + "PlugIns/ShareExtension.appex/Info.plist", b"p")
            zf.writestr(APP + "PlugIns/ShareExtension.appex/ShareExtension", b"x")
        if watch:
            zf.writestr(APP + "Watch/YouTubeWatch.app/Info.plist", b"p")
        # Only its SINF is left of this one - as installd would make it.
        zf.writestr(APP + "PlugIns/IntentsExtension.appex/SC_Info/IntentsExtension.sinf", b"s")
    return ipa


def test_bundles_that_are_gone_are_named(tmp_path):
    assert stale_sinf_paths(_ipa(tmp_path), "YouTube.app", []) == [
        "PlugIns/IntentsExtension.appex/SC_Info/IntentsExtension.sinf",
        "Watch/YouTubeWatch.app/SC_Info/YouTubeWatch.sinf",
    ]


def test_bundles_removed_while_signing_count_as_gone(tmp_path):
    stale = stale_sinf_paths(_ipa(tmp_path, watch=True), "YouTube.app",
                             ["PlugIns/ShareExtension.appex", "Watch"])
    assert "PlugIns/ShareExtension.appex/SC_Info/ShareExtension.sinf" in stale
    assert "Watch/YouTubeWatch.app/SC_Info/YouTubeWatch.sinf" in stale
    assert not any(p.startswith(("SC_Info/", "Frameworks/")) for p in stale), \
        "the app's own SINF and present frameworks stay"


def test_a_clean_ipa_needs_nothing(tmp_path):
    clean = {"SinfPaths": ["SC_Info/YouTube.sinf"],
             "SinfReplicationPaths": ["SC_Info/YouTube.sinf",
                                      "PlugIns/ShareExtension.appex/SC_Info/ShareExtension.sinf"]}
    assert stale_sinf_paths(_ipa(tmp_path, clean), "YouTube.app", []) == []
    assert stale_sinf_paths(_ipa(tmp_path, None), "YouTube.app", []) == []


def test_an_unreadable_manifest_is_left_alone(tmp_path):
    ipa = tmp_path / "in.ipa"
    with zipfile.ZipFile(ipa, "w") as zf:
        zf.writestr(APP + "SC_Info/Manifest.plist", b"not a plist")
    assert stale_sinf_paths(ipa, "YouTube.app", []) == []


def test_unpacking_clears_the_stale_paths_from_the_manifest(tmp_path):
    ipa = _ipa(tmp_path)
    drop = ["PlugIns/ShareExtension.appex"]
    stale = stale_sinf_paths(ipa, "YouTube.app", drop)
    out = unpack_without(ipa, "YouTube.app", drop, tmp_path / "w", stale_sinf=stale)
    app = out / "Payload" / "YouTube.app"
    manifest = plistlib.loads((app / "SC_Info" / "Manifest.plist").read_bytes())
    assert manifest == {
        "SinfPaths": ["SC_Info/YouTube.sinf"],
        "SinfReplicationPaths": ["Frameworks/widevine.framework/SC_Info/widevine.sinf",
                                 "SC_Info/YouTube.sinf"],
    }
    assert (app / "SC_Info" / "YouTube.sinf").read_bytes() == b"sinf"
    assert not (app / "PlugIns" / "ShareExtension.appex").exists()
    assert not (app / "PlugIns" / "IntentsExtension.appex").exists(), \
        "a bundle reduced to its SINF goes too"
    assert (app / "Frameworks" / "widevine.framework" / "SC_Info" / "widevine.sinf").exists()
