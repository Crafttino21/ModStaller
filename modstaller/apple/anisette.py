"""Anisette providers: Apple's device attestation for GSA logins.

Without these headers Apple accepts no login. Two sources:

* :class:`LocalProvider` (default) - runs Apple's ADI libraries
  (``libstoreservicescore.so``, ``libCoreADI.so`` from the Apple Music APK)
  locally in an ARM emulation. Nothing leaves the machine. On Windows this
  requires Control Flow Guard to be off - see :func:`local_supported`.
* :class:`RemoteV3Provider` - anisette-v3 protocol against a third-party
  server. Fallback only; device identifiers then go to a third party.

This module corrects three things about the ``anisette`` library's behaviour:

1. Its default ``server_friendly_description`` carries
   ``com.apple.dt.Xcode``, which Apple has rejected with HTTP 503 since
   August 2026. See :mod:`.clientinfo`.
2. Its default device config has *hardcoded* IDs shared by every
   installation of the library. We generate our own stable IDs per
   installation.
3. It takes time zone, locale and client time straight from the OS. On
   Windows that gives a localized, non-ASCII time zone name
   ("Mitteleuropäische Sommerzeit") and a client time with both an offset
   and a ``Z``. These go out as raw HTTP headers during two-factor - see
   :func:`normalize_headers`.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from ..config import (ANISETTE_DIR, CONFIG_FILE, POSIX, read_secret,
                      write_secret)
from ..errors import AppleError
from ..i18n import _
from . import clientinfo

#: Provisioning state (adi.pb). Apple ties the 2FA trust to it. If the file
#: is lost, Apple asks for a code again on every run - which renders the
#: unattended refresh daemon useless.
PROVISIONING_FILE = ANISETTE_DIR / "provisioning.bin"
LIBS_FILE = ANISETTE_DIR / "libs.bin"
DEVICE_FILE = ANISETTE_DIR / "device.json"


#: The local emulation is one ARM VM (Unicorn) over one set of ADI files.
#: Two threads inside it at once corrupt its memory - UC_ERR_READ_UNMAPPED /
#: UC_ERR_WRITE_UNMAPPED, seen on Windows once the install screen asked for
#: a plan on every edit while the status poll ran (1.3.0-rc.2). So: one
#: instance per process, and only one thread in it at a time.
_LOCAL_LOCK = threading.RLock()
_shared_ani = None


class AnisetteProvider(Protocol):
    def headers(self) -> dict[str, str]: ...
    def client_info(self) -> str: ...


def _load_or_create_device() -> dict[str, str]:
    """A stable device identity, unique to this installation.

    Stable, because Apple treats changing identities as suspicious and then
    demands 2FA again. Unique, because the library's defaults are shared by
    all of its users.
    """
    if DEVICE_FILE.exists():
        return json.loads(read_secret(DEVICE_FILE))

    device = {
        "server_friendly_description": clientinfo.DEFAULT_CLIENT_INFO,
        "unique_device_id": str(uuid.uuid4()).upper(),
        "adi_id": secrets.token_hex(8),
        "local_user_uuid": secrets.token_hex(32).upper(),
    }
    write_secret(DEVICE_FILE, json.dumps(device, indent=2).encode())
    return device


def forget_device() -> None:
    """Discards the device identity. Apple treats this machine as a new one
    and asks for a two-factor code on the next sign-in.

    Drops the in-memory copy as well - otherwise the next :meth:`headers`
    call would write the old identity straight back to disk.
    """
    global _shared_ani
    with _LOCAL_LOCK:
        _shared_ani = None
        for f in (PROVISIONING_FILE, DEVICE_FILE):
            f.unlink(missing_ok=True)


# -- Header hygiene ----------------------------------------------------------

#: What Apple's own clients send: an abbreviation ("CEST") or "GMT+2" -
#: NSTimeZone.abbreviation, as AltSign uses it.
_TIMEZONE_OK = re.compile(r"^(?:[A-Z]{2,5}|GMT(?:[+-]\d{1,2}(?::\d{2})?)?)$")
_LOCALE_OK = re.compile(r"^[a-z]{2,3}(?:_[A-Z]{2})?$")
_FALLBACK_LOCALE = "en_US"
_OFFSET_THEN_Z = re.compile(r"[+-]\d{2}:?\d{2}Z$")


def _gmt_abbreviation(offset: timedelta) -> str:
    """NSTimeZone style: "GMT", "GMT+2", "GMT-3:30"."""
    minutes = round(offset.total_seconds() / 60)
    if not minutes:
        return "GMT"
    sign = "+" if minutes > 0 else "-"
    hours, rest = divmod(abs(minutes), 60)
    return f"GMT{sign}{hours}" + (f":{rest:02d}" if rest else "")


def _utc_client_time(value: str, now: datetime) -> str:
    """ISO 8601 in UTC with a trailing ``Z``.

    The library appends ``Z`` to a local time that already carries an
    offset ("…+02:00Z") - neither local time nor UTC.
    """
    raw = str(value).strip()
    if _OFFSET_THEN_Z.search(raw):
        raw = raw[:-1]
    elif raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        parsed = now
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=now.tzinfo)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_headers(data: dict, *, now: datetime | None = None) -> dict:
    """Brings the OS-derived values into the shape Apple's clients send.

    Only what is malformed gets replaced - correct values from a remote
    server pass through. Every value ends up ASCII: during two-factor these
    are raw HTTP headers, which ``http.client`` encodes as latin-1. A time
    zone like "中国标准时间" would not even get out.
    """
    now = now or datetime.now().astimezone()
    out = dict(data)
    if "X-Apple-I-Client-Time" in out:
        out["X-Apple-I-Client-Time"] = _utc_client_time(
            out["X-Apple-I-Client-Time"], now)
    if not _TIMEZONE_OK.match(str(out.get("X-Apple-I-TimeZone", "GMT"))):
        out["X-Apple-I-TimeZone"] = _gmt_abbreviation(
            now.utcoffset() or timedelta(0))
    if not _LOCALE_OK.match(str(out.get("X-Apple-Locale", _FALLBACK_LOCALE))):
        out["X-Apple-Locale"] = _FALLBACK_LOCALE
    return {k: v for k, v in out.items()
            if not isinstance(v, str) or v.isascii()}


#: Escape hatch, in case someone wants to try anyway.
ALLOW_LOCAL_ENV = "MODSTALLER_ALLOW_LOCAL_ANISETTE"

#: ProcessControlFlowGuardPolicy from PROCESS_MITIGATION_POLICY.
_CFG_POLICY = 7


def control_flow_guard_active() -> bool:
    """Whether Control Flow Guard is active for *this* process.

    The main EXE decides that, for the whole process. Measured rather than
    guessed: packaged programs that went through :func:`packaging.build_backend
    .clear_cfg` are clean, older ones are not - and during development it is
    ``python.exe`` running anyway, which never sets CFG.
    """
    if POSIX:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.GetProcessMitigationPolicy.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t]
        k32.GetProcessMitigationPolicy.restype = wintypes.BOOL

        flags = ctypes.c_uint32()
        if not k32.GetProcessMitigationPolicy(
                k32.GetCurrentProcess(), _CFG_POLICY,
                ctypes.byref(flags), ctypes.sizeof(flags)):
            return False
        return bool(flags.value & 1)        # EnableControlFlowGuard
    except Exception:
        # Cannot be determined - then don't get in the way.
        return False


def local_supported() -> bool:
    """Whether the local ADI emulation can run in this process.

    Not with Control Flow Guard active: ``unicorn.dll`` uses ``longjmp`` to
    jump out of JIT-generated code, MSVC's runtime finds no entry for it in
    the CFG table and calls ``__fastfail`` (0xC0000409,
    FAST_FAIL_INVALID_SET_OF_CONTEXT). Not an error one could catch - the
    process is gone instantly, and with it the GUI's backend. The check
    therefore applies *before* ``anisette`` is imported, so that
    ``unicorn.dll`` is never loaded in the first place.
    """
    return (not control_flow_guard_active()
            or os.environ.get(ALLOW_LOCAL_ENV) == "1")


class LocalProvider:
    """ADI emulation on this machine."""

    name = "local"

    def __init__(self) -> None:
        if not local_supported():
            raise AppleError(_(
                "The local Anisette emulation cannot run in this build: "
                "Control Flow Guard is active for the process, and the ARM "
                "emulation (Unicorn) then aborts in native code "
                "(0xC0000409). A current ModStaller build for Windows does "
                "not set that flag - otherwise an Anisette server helps. "
                "In {config}:\n"
                '  anisette_provider = "remote"\n'
                '  anisette_server = "https://ani.sidestore.io"',
                config=CONFIG_FILE))
        from anisette import Anisette
        from anisette._device import AnisetteDeviceConfig

        # Everything under the lock - including the device identity: two
        # first starts at once would otherwise read a half-written
        # device.json, or each create an identity of its own.
        with _LOCAL_LOCK:
            ANISETTE_DIR.mkdir(parents=True, exist_ok=True)
            ANISETTE_DIR.chmod(0o700)

            self._DeviceConfig = AnisetteDeviceConfig
            self._cfg = self._device_config()
            self._Anisette = Anisette
            self._ani = self._shared(fresh=False)

    def _device_config(self):
        """The saved device identity - a new one after :func:`forget_device`."""
        device = _load_or_create_device()
        # Sanitize the client info right here: then the identity used for
        # provisioning matches the one we talk with later.
        device["server_friendly_description"] = clientinfo.sanitize(
            device["server_friendly_description"]
        )
        return self._DeviceConfig(**device)

    def _shared(self, *, fresh: bool):
        """The process-wide instance - loaded from the saved files once, or
        again after the emulation broke or the identity was discarded
        (``fresh``). Call with the lock held."""
        global _shared_ani
        if _shared_ani is None or fresh:
            # Read again: after a forget the old identity must not live on.
            self._cfg = self._device_config()
            existing = [p for p in (LIBS_FILE, PROVISIONING_FILE) if p.exists()]
            if existing:
                _shared_ani = self._Anisette.load(
                    *existing, default_device_config=self._cfg)
            else:
                _shared_ani = self._Anisette.init(default_device_config=self._cfg)
            self._ani = _shared_ani
            self._persist()
        return _shared_ani

    def _persist(self) -> None:
        if not LIBS_FILE.exists():
            self._ani.save_libs(LIBS_FILE)
            LIBS_FILE.chmod(0o600)
        if self._ani.is_provisioned:
            self._ani.save_provisioning(PROVISIONING_FILE)
            PROVISIONING_FILE.chmod(0o600)

    def headers(self) -> dict[str, str]:
        with _LOCAL_LOCK:
            try:
                data = self._headers_once()
            except Exception as exc:
                # A broken emulation (Unicorn's UcError) is not the end: the
                # state on disk is intact - load it again and retry once.
                if type(exc).__name__ != "UcError":
                    raise
                self._ani = self._shared(fresh=True)
                data = self._headers_once()
        data = normalize_headers(data)
        data["X-MMe-Client-Info"] = self.client_info()
        return data

    def _headers_once(self) -> dict[str, str]:
        self._ani = self._shared(fresh=self._forgotten_elsewhere())
        data = dict(self._ani.get_data())
        self._persist()
        return data

    @staticmethod
    def _forgotten_elsewhere() -> bool:
        """Whether another process discarded the identity - say ``logout
        --forget-device`` in a terminal while the GUI runs.

        Every provisioning is saved right away, so a provisioned instance
        whose file is gone means the file was deleted. Saving it again
        would resurrect exactly the identity the user just threw away.
        """
        return (_shared_ani is not None and _shared_ani.is_provisioned
                and not PROVISIONING_FILE.exists())

    def client_info(self) -> str:
        return clientinfo.sanitize(self._cfg.server_friendly_description)


class RemoteV3Provider:
    """anisette-v3 protocol against a third-party server."""

    name = "remote"

    def __init__(self, base_url: str, timeout: float = 20.0) -> None:
        import requests

        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._client_info: str | None = None

    def client_info(self) -> str:
        # *Ask* the server for its client info instead of guessing it -
        # then Apple's next change won't catch us out again.
        if self._client_info is None:
            try:
                r = self._session.get(f"{self._base}/v3/client_info",
                                      timeout=self._timeout)
                r.raise_for_status()
                raw = r.json().get("client_info")
            except Exception:
                raw = None
            self._client_info = clientinfo.sanitize(raw)
        return self._client_info

    def headers(self) -> dict[str, str]:
        try:
            r = self._session.get(f"{self._base}/v3/get_headers",
                                  timeout=self._timeout)
            r.raise_for_status()
            data = {k: v for k, v in r.json().items() if k.lower() != "result"}
        except Exception as exc:
            raise AppleError(_(
                "Anisette server {url} not reachable: {error}",
                url=self._base, error=exc)) from exc
        data = normalize_headers(data)
        data["X-MMe-Client-Info"] = self.client_info()
        return data


def build(provider: str = "local", server: str = "") -> AnisetteProvider:
    """Builds the configured provider. 'local' does not silently fall back to
    'remote' - whoever chose local doesn't want to send data anywhere."""
    if provider == "local":
        return LocalProvider()
    if provider == "remote":
        if not server:
            raise AppleError(_("anisette_provider = ‘remote’, but no "
                               "anisette_server is configured."))
        return RemoteV3Provider(server)
    raise AppleError(_("Unknown anisette_provider: {provider!r}",
                       provider=provider))
