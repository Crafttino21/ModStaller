"""IPA hineinschauen, ohne sie zu veraendern.

Wir brauchen vorab drei Dinge: die Bundle-ID (fuer die App-ID bei Apple),
den Anzeigenamen, und ob Extensions drinstecken - denn jede Extension
verbraucht bei einem Gratis-Account eine eigene App-ID aus einem Kontingent
von zehn pro Woche.
"""

from __future__ import annotations

import plistlib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from ..errors import SigningError
from ..i18n import _


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

    @property
    def app_id_demand(self) -> int:
        """Wie viele App-IDs bei Apple noetig waeren: App + jede Extension."""
        return 1 + len(self.extensions)

    def summary(self) -> str:
        lines = [
            f"  Name        {self.name}",
            f"  Bundle-ID   {self.bundle_id}",
            f"  Version     {self.version}",
            f"  min. iOS    {self.minimum_os or '?'}",
        ]
        if self.dylibs:
            lines.append(f"  dylibs      {len(self.dylibs)} injiziert "
                         f"({', '.join(d.rsplit('/', 1)[-1] for d in self.dylibs[:3])}"
                         f"{' …' if len(self.dylibs) > 3 else ''})")
        if self.frameworks:
            lines.append(f"  Frameworks  {len(self.frameworks)}")
        if self.extensions:
            lines.append(f"  Extensions  {len(self.extensions)} "
                         f"(braucht {self.app_id_demand} App-IDs)")
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
        # App Store DRM erkennen: dann ist das Binary verschluesselt und
        # kann nicht neu signiert werden.
        encrypted = any(n.startswith(prefix + "SC_Info/") for n in names)

    return IPAInfo(
        path=path,
        bundle_id=info.get("CFBundleIdentifier", ""),
        name=info.get("CFBundleDisplayName") or info.get("CFBundleName") or app[:-4],
        version=info.get("CFBundleShortVersionString", "?"),
        minimum_os=info.get("MinimumOSVersion", ""),
        app_dir=app,
        extensions=under("PlugIns/", ".appex"),
        frameworks=under("Frameworks/", ".framework"),
        dylibs=dylibs,
        encrypted=encrypted,
    )
