"""Der Zustand auf einen Blick: iPhone, Anmeldung, was demnaechst ablaeuft.

Das sind die drei Fragen, die vor jeder Aktion zaehlen. Die Oberflaeche
beantwortet sie zuerst und bietet dann vorrangig an, was gerade dran ist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .errors import ModStallerError

#: Ab hier gilt ein Profil als dringend.
URGENT_DAYS = 2.0

#: Wo wir nach IPAs suchen, wenn keine angegeben wird.
IPA_DIRS = (Path.home() / "Downloads", Path.home() / "Dokumente",
            Path.home() / "Documents", Path.home() / "Desktop",
            Path.home() / "Schreibtisch")


@dataclass
class Status:
    device_name: str | None = None
    udid: str = ""
    ios_version: str = ""
    product_type: str = ""
    developer_mode: bool = True
    battery: object = None      # device.connection.Battery
    logged_in: bool = False
    apps: list = field(default_factory=list)
    error: str = ""

    @property
    def has_device(self) -> bool:
        return self.device_name is not None

    @property
    def urgent(self) -> list:
        return [a for a in self.apps if a.days_left <= URGENT_DAYS]


async def device_status(st: Status) -> None:
    """Traegt ein, was das iPhone ueber sich sagt - oder dass keins da ist."""
    try:
        from .device.connection import ServiceProvider, battery, device_info
        async with ServiceProvider() as sp:
            info = await device_info(sp.lockdown)
            st.device_name = info.name
            st.udid = info.udid
            st.ios_version = info.ios_version
            st.product_type = info.product_type
            st.developer_mode = info.developer_mode
            st.battery = await battery(sp.lockdown)
    except ModStallerError as exc:
        # Kein Geraet ist ein Zustand, kein Fehler. Ein gesperrtes oder
        # ungepairtes schon - das muss man sehen, um es zu beheben.
        from .errors import DeviceNotFound
        if not isinstance(exc, DeviceNotFound):
            st.error = str(exc)
    except Exception as exc:
        st.error = str(exc)


async def gather_status() -> Status:
    """Nur lokal und ueber USB - keine Apple-Abfrage.

    Der Zustand soll sofort stehen. Kontingente kosten einen Netzaufruf und
    werden deshalb erst auf Nachfrage geholt.
    """
    from .apple.session import Session
    from .state import store

    st = Status(apps=store.all_installs(), logged_in=Session.load() is not None)
    await device_status(st)
    return st


def find_ipas() -> list[Path]:
    seen: list[Path] = []
    for d in IPA_DIRS:
        if d.is_dir():
            seen.extend(sorted(d.glob("*.ipa")))
    return seen
