"""The state at a glance: iPhone, sign-in, what expires soon.

These are the three questions that matter before any action. The interface
answers them first and then puts forward whatever is due right now.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .errors import ModStallerError

#: From here on a profile counts as urgent.
URGENT_DAYS = 2.0

#: Where we look for IPAs when none is given.
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
    """Records what the iPhone says about itself - or that there is none."""
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
        # No device is a state, not an error. A locked or unpaired one is -
        # you need to see that in order to fix it.
        from .errors import DeviceNotFound
        if not isinstance(exc, DeviceNotFound):
            st.error = str(exc)
    except Exception as exc:
        st.error = str(exc)


async def gather_status() -> Status:
    """Only local and over USB - no Apple request.

    The state should be ready immediately. Quotas cost a network call and
    are therefore only fetched on demand.
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
