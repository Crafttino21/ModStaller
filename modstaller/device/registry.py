"""Devices ModStaller knows - also when they are not plugged in.

Over USB, usbmuxd tells us which device is there and hands out its pairing.
Over the network nobody does: a device in the same Wi-Fi only shows up as
an anonymous Bonjour advert. To recognise it, and to talk to it at all, we
keep what we learned while it was on the cable (or while an Apple TV was
paired by PIN):

* name, model, OS version and platform - for the interface, without having
  to connect first;
* the Wi-Fi MAC address - it names the device in its ``_apple-mobdev2``
  advert;
* the lockdown pair record - lockdown over TCP needs it passed in
  explicitly (pymobiledevice3 looks it up by IP otherwise and finds none);
* the identifier of a RemotePairing record. The record itself stays where
  pymobiledevice3 keeps it (``remote_<id>.plist`` in its home folder): only
  there does its own Bonjour matching find it.

Deliberately a plain JSON file, like ``state/store.py``.
"""

from __future__ import annotations

import json
import plistlib
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from ..config import DATA_DIR, SECRETS_DIR, read_secret, write_secret

DEVICES_FILE = DATA_DIR / "devices.json"
PAIRING_DIR = SECRETS_DIR / "pairing"

IOS = "ios"
TVOS = "tvos"


@dataclass
class KnownDevice:
    udid: str
    name: str = ""
    product_type: str = ""
    os_version: str = ""
    #: "ios" or "tvos" - decides the signing platform and the interface.
    platform: str = IOS
    #: As lockdown reports it (``WiFiMACAddress``), lower case.
    wifi_mac: str = ""
    #: Identifier of the RemotePairing record (``remote_<id>.plist``). For a
    #: USB-paired iPhone the UDID, for an Apple TV the advert's identifier.
    remote_identifier: str = ""
    #: The user switched on Wi-Fi for this device in ModStaller.
    wifi_enabled: bool = False
    last_host: str = ""
    last_seen: float = field(default_factory=time.time)

    @property
    def is_tv(self) -> bool:
        return self.platform == TVOS


def platform_for(product_type: str = "", device_class: str = "") -> str:
    """tvOS for anything Apple TV, iOS otherwise (iPhone, iPad, iPod)."""
    if device_class == "AppleTV" or product_type.startswith("AppleTV"):
        return TVOS
    return IOS


def _load_raw() -> dict:
    if not DEVICES_FILE.exists():
        return {}
    try:
        return json.loads(read_secret(DEVICES_FILE))
    except Exception:
        return {}


def _save_raw(data: dict) -> None:
    write_secret(DEVICES_FILE, json.dumps(data, indent=2).encode())


_FIELDS = {f.name for f in fields(KnownDevice)}


def all_devices() -> list[KnownDevice]:
    out = []
    for raw in _load_raw().values():
        try:
            out.append(KnownDevice(**{k: v for k, v in raw.items() if k in _FIELDS}))
        except TypeError:
            continue
    return sorted(out, key=lambda d: d.name.lower())


def get(udid: str) -> KnownDevice | None:
    raw = _load_raw().get(udid)
    if raw is None:
        return None
    try:
        return KnownDevice(**{k: v for k, v in raw.items() if k in _FIELDS})
    except TypeError:
        return None


def by_remote_identifier(identifier: str) -> KnownDevice | None:
    return next((d for d in all_devices() if d.remote_identifier == identifier), None)


def by_wifi_mac(mac: str) -> KnownDevice | None:
    mac = mac.lower()
    return next((d for d in all_devices() if d.wifi_mac and d.wifi_mac == mac), None)


def remember(udid: str, *, clear: tuple[str, ...] = (), **changes) -> KnownDevice:
    """Creates or updates the entry. Empty values never overwrite known ones -
    a network connection may not tell everything the cable did. Fields named
    in ``clear`` are emptied on purpose."""
    data = _load_raw()
    current = data.get(udid, {"udid": udid})
    for key in clear:
        if key in _FIELDS and key != "udid":
            current[key] = type(getattr(KnownDevice(udid), key))()
    for key, value in changes.items():
        if key not in _FIELDS or key == "udid":
            continue
        if value in ("", None) and current.get(key):
            continue
        current[key] = value.lower() if key == "wifi_mac" and isinstance(value, str) else value
    current["last_seen"] = time.time()
    data[udid] = current
    _save_raw(data)
    return KnownDevice(**{k: v for k, v in current.items() if k in _FIELDS})


def forget(udid: str) -> bool:
    data = _load_raw()
    if udid not in data:
        return False
    del data[udid]
    _save_raw(data)
    pair_record_path(udid).unlink(missing_ok=True)
    return True


# -- Lockdown pair records ---------------------------------------------------


def pair_record_path(udid: str) -> Path:
    # UDIDs are hex with an optional dash - nothing that escapes the folder.
    safe = "".join(c for c in udid if c.isalnum() or c == "-")
    return PAIRING_DIR / f"{safe}.plist"


def save_pair_record(udid: str, record: dict) -> None:
    write_secret(pair_record_path(udid), plistlib.dumps(record))


def load_pair_record(udid: str) -> dict | None:
    path = pair_record_path(udid)
    if not path.exists():
        return None
    try:
        return plistlib.loads(read_secret(path))
    except Exception:
        return None


def all_pair_records() -> dict[str, dict]:
    """udid -> pair record for every device with Wi-Fi switched on."""
    out = {}
    for dev in all_devices():
        if not dev.wifi_enabled:
            continue
        rec = load_pair_record(dev.udid)
        if rec is not None:
            out[dev.udid] = rec
    return out


def as_dict(dev: KnownDevice) -> dict:
    return asdict(dev)
