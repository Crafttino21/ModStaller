"""Anisette providers: Apple's device attestation for GSA logins.

Without these headers Apple accepts no login. Two sources:

* :class:`LocalProvider` (default) - runs Apple's ADI libraries
  (``libstoreservicescore.so``, ``libCoreADI.so`` from the Apple Music APK)
  locally in an ARM emulation. Nothing leaves the machine. On Windows this
  requires Control Flow Guard to be off - see :func:`local_supported`.
* :class:`RemoteV3Provider` - anisette-v3 protocol against a third-party
  server. Fallback only; device identifiers then go to a third party.

This module corrects two things about the ``anisette`` library's behaviour:

1. Its default ``server_friendly_description`` carries
   ``com.apple.dt.Xcode``, which Apple has rejected with HTTP 503 since
   August 2026. See :mod:`.clientinfo`.
2. Its default device config has *hardcoded* IDs shared by every
   installation of the library. We generate our own stable IDs per
   installation.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import uuid
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

            device = _load_or_create_device()
            # Sanitize the client info right here: then the identity used for
            # provisioning matches the one we talk with later.
            device["server_friendly_description"] = clientinfo.sanitize(
                device["server_friendly_description"]
            )
            self._cfg = AnisetteDeviceConfig(**device)
            self._Anisette = Anisette
            self._ani = self._shared(fresh=False)

    def _shared(self, *, fresh: bool):
        """The process-wide instance - loaded from the saved files once, or
        again after the emulation broke (``fresh``). Call with the lock held."""
        global _shared_ani
        if _shared_ani is None or fresh:
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
        data["X-MMe-Client-Info"] = self.client_info()
        return data

    def _headers_once(self) -> dict[str, str]:
        self._ani = self._shared(fresh=False)
        data = dict(self._ani.get_data())
        self._persist()
        return data

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
