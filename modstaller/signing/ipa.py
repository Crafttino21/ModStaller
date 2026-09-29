"""Looking inside an IPA without changing it.

We need three things up front: the bundle ID (for the App ID at Apple), the
display name, and whether it contains extensions - because with a free
account every extension uses up an App ID of its own from a quota of ten per
week.
"""

from __future__ import annotations

import plistlib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from ..errors import SigningError
from ..i18n import _


@dataclass
class ExtensionInfo:
    """One app extension (PlugIns/*.appex)."""
    path: str                   # "PlugIns/Share.appex"
    bundle_id: str
    name: str
    #: NSExtensionPointIdentifier - what kind of extension it is
    #: ("com.apple.widgetkit-extension", "com.apple.share-services", ...).
    point: str = ""

    def bundle_id_for(self, app_original: str, app_new: str) -> str | None:
        """The extension's ID once the app is called ``app_new``.

        zsign replaces the app's old ID inside every extension ID
        (ModifyPluginsBundleId) - the same rule here, so the App ID we
        register is exactly the one that gets signed. None: the extension
        does not carry the app's ID as its prefix, so it cannot be moved
        to our team (iOS requires that prefix).
        """
        if not self.bundle_id.startswith(app_original + "."):
            return None
        return self.bundle_id.replace(app_original, app_new)


@dataclass
class IPAInfo:
    path: Path
    bundle_id: str
    name: str
    version: str
    minimum_os: str
    app_dir: str
    extensions: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    dylibs: list[str] = field(default_factory=list)
    encrypted: bool = False
    extension_details: list[ExtensionInfo] = field(default_factory=list)
    has_watch: bool = False
    #: "ios" (iPhone/iPad/iPod touch), "tvos" (Apple TV) or "xros" (Vision
    #: Pro) - they need different binaries, and Apple signs them per platform.
    platform: str = "ios"
    #: UIDeviceFamily: 1 iPhone/iPod touch, 2 iPad, 3 Apple TV, 7 Vision Pro.
    device_families: list[int] = field(default_factory=list)

    @property
    def app_id_demand(self) -> int:
        """How many App IDs Apple would require: the app + every extension."""
        return 1 + len(self.extensions)

    def summary(self) -> str:
        lines = [
            f"  Name        {self.name}",
            f"  Bundle-ID   {self.bundle_id}",
            f"  Version     {self.version}",
            f"  min. {_OS_NAMES.get(self.platform, 'iOS'):<7}{self.minimum_os or '?'}",
        ]
        if self.dylibs:
            lines.append(f"  dylibs      {len(self.dylibs)} injected "
                         f"({', '.join(d.rsplit('/', 1)[-1] for d in self.dylibs[:3])}"
                         f"{' …' if len(self.dylibs) > 3 else ''})")
        if self.frameworks:
            lines.append(f"  Frameworks  {len(self.frameworks)}")
        if self.extensions:
            lines.append(f"  Extensions  {len(self.extensions)} "
                         f"(needs {self.app_id_demand} App IDs)")
        return "\n".join(lines)


def inspect(path: str | Path) -> IPAInfo:
    path = Path(path)
    if not path.is_file():
        raise SigningError(_("IPA not found: {path}", path=path))

    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise SigningError(_("{name} is not a valid IPA archive.",
                             name=path.name)) from exc

    with zf:
        names = zf.namelist()
        app_dirs = sorted({
            n.split("/")[1] for n in names
            if n.startswith("Payload/") and "/" in n[8:]
            and n.split("/")[1].endswith(".app")
        })
        if not app_dirs:
            raise SigningError(_(
                "{name} contains no Payload/*.app - not a valid IPA.",
                name=path.name))
        app = app_dirs[0]
        prefix = f"Payload/{app}/"

        try:
            info = plistlib.loads(zf.read(prefix + "Info.plist"))
        except KeyError as exc:
            raise SigningError(_("Info.plist missing in {app}.",
                                 app=app)) from exc

        def under(sub: str, suffix: str) -> list[str]:
            base = prefix + sub
            out = set()
            for n in names:
                if n.startswith(base) and suffix in n:
                    rest = n[len(base):].split("/")[0]
                    if rest.endswith(suffix):
                        out.add(sub + rest)
            return sorted(out)

        dylibs = sorted({
            n[len(prefix):] for n in names
            if n.startswith(prefix + "Frameworks/") and n.endswith(".dylib")
        })
        # App Store DRM: then the binary is encrypted and cannot be
        # re-signed. The binary says so itself (cryptid) - SC_Info/ does
        # not, decrypted IPAs often keep it (see macho.py).
        encrypted = _main_binary_encrypted(zf, prefix, info, names)

        extensions = under("PlugIns/", ".appex")
        details = [_extension(zf, prefix, ext) for ext in extensions]
        has_watch = any(n.startswith(prefix + "Watch/") for n in names)

    return IPAInfo(
        path=path,
        bundle_id=info.get("CFBundleIdentifier", ""),
        name=info.get("CFBundleDisplayName") or info.get("CFBundleName") or app[:-4],
        version=info.get("CFBundleShortVersionString", "?"),
        minimum_os=info.get("MinimumOSVersion", ""),
        app_dir=app,
        extensions=extensions,
        frameworks=under("Frameworks/", ".framework"),
        dylibs=dylibs,
        encrypted=encrypted,
        extension_details=details,
        has_watch=has_watch,
        platform=platform_of(info),
        device_families=device_families(info),
    )


_OS_NAMES = {"ios": "iOS", "tvos": "tvOS", "xros": "visionOS"}


def device_families(info: dict) -> list[int]:
    family = info.get("UIDeviceFamily") or []
    if isinstance(family, int):
        family = [family]
    out = []
    for f in family:
        try:
            out.append(int(f))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


def platform_of(info: dict) -> str:
    """iOS, tvOS or visionOS (xrOS), from the app's Info.plist.

    ``CFBundleSupportedPlatforms`` says it directly (``AppleTVOS``, ``XROS``
    or ``iPhoneOS``); older or hand-built IPAs may lack it, then the device
    family decides (3 = Apple TV, 7 = Vision Pro)."""
    platforms = info.get("CFBundleSupportedPlatforms") or []
    if isinstance(platforms, str):
        platforms = [platforms]
    names = [str(p).lower() for p in platforms]
    if any(n.startswith("appletv") for n in names):
        return "tvos"
    if any(n.startswith("xr") for n in names):
        return "xros"
    if names:
        return "ios"
    family = device_families(info)
    if family and all(f == 3 for f in family):
        return "tvos"
    if family and all(f == 7 for f in family):
        return "xros"
    dt = str(info.get("DTPlatformName", "")).lower()
    if dt.startswith("appletv"):
        return "tvos"
    if dt.startswith("xr"):
        return "xros"
    return "ios"


def _main_binary_encrypted(zf: zipfile.ZipFile, prefix: str, info: dict,
                           names: list[str]) -> bool:
    """cryptid of the app's executable. Unreadable counts as *not*
    encrypted: better zsign or iOS name the real problem than a good IPA
    being refused."""
    from .macho import NotMachO, is_encrypted
    exe = info.get("CFBundleExecutable")
    if not isinstance(exe, str) or prefix + exe not in names:
        return False
    try:
        with zf.open(prefix + exe) as f:
            return is_encrypted(f)
    except (NotMachO, OSError, zipfile.BadZipFile, EOFError, ValueError):
        return False


def _extension(zf: zipfile.ZipFile, prefix: str, path: str) -> ExtensionInfo:
    name = path.rsplit("/", 1)[-1].removesuffix(".appex")
    try:
        info = plistlib.loads(zf.read(f"{prefix}{path}/Info.plist"))
    except Exception:
        return ExtensionInfo(path=path, bundle_id="", name=name)
    ns = info.get("NSExtension") if isinstance(info.get("NSExtension"), dict) else {}
    return ExtensionInfo(
        path=path,
        bundle_id=str(info.get("CFBundleIdentifier", "")),
        name=str(info.get("CFBundleDisplayName") or info.get("CFBundleName") or name),
        point=str(ns.get("NSExtensionPointIdentifier", "")),
    )


def icon_png(path: str | Path) -> bytes | None:
    """The app's icon as a standard PNG - None if it only lives in
    Assets.car or the IPA declares none."""
    from .icon import best_icon, icon_names
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        apps = sorted({n.split("/")[1] for n in names
                       if n.startswith("Payload/") and n.count("/") >= 2
                       and n.split("/")[1].endswith(".app")})
        if not apps:
            return None
        prefix = f"Payload/{apps[0]}/"
        try:
            info = plistlib.loads(zf.read(prefix + "Info.plist"))
        except Exception:
            return None
        wanted = icon_names(info)
        if not wanted:
            return None
        # Only files directly in the bundle root - that is where they live.
        files = {n[len(prefix):]: zf.read(n) for n in names
                 if n.startswith(prefix) and "/" not in n[len(prefix):]
                 and n.lower().endswith(".png")
                 and any(n[len(prefix):].startswith(w) for w in wanted)}
    return best_icon(files, wanted)
