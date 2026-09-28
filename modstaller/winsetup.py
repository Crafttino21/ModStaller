"""Windows: the Apple device service - check it and set it up.

pymobiledevice3 does not talk to the USB device itself on Windows. It talks
to Apple's device service on ``127.0.0.1:27015`` (the Windows counterpart of
usbmuxd), and Apple's USB driver comes with that service. Without it, Windows
binds the iPhone to its own photo import driver: Explorer shows it,
ModStaller never can.

The service comes with the "Apple Devices" app (Microsoft Store) or with
iTunes. :func:`setup` installs it without anyone having to look for either:

1. the "Apple Devices" app through ``winget`` from the Microsoft Store -
   official, updates itself;
2. otherwise only Apple's driver package (Apple Mobile Device Support),
   taken from the iTunes installer that is downloaded from apple.com. Its
   Authenticode signature must name Apple before anything runs elevated.

An installed but stopped service is simply started. Everything that needs
administrator rights goes through one UAC prompt each.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .errors import ModStallerError
from .i18n import _

#: Where the Apple device service listens (usbmuxd protocol over TCP).
APPLE_MOBILE_DEVICE = ("127.0.0.1", 27015)

#: The "Apple Devices" app in the Microsoft Store.
APPLE_DEVICES_STORE_ID = "9NP83LWLPZ9K"
STORE_URL = f"https://apps.microsoft.com/detail/{APPLE_DEVICES_STORE_ID}"

#: Apple's permanent link to the current 64-bit iTunes installer.
ITUNES_URL = "https://www.apple.com/itunes/download/win64"
DRIVER_MSI = "AppleMobileDeviceSupport64.msi"

#: The service is called differently depending on where it came from
#: (iTunes: "Apple Mobile Device Service", the Store app packages its own).
SERVICE_FILTER = ("$_.Name -like '*AppleMobileDevice*' -or "
                  "$_.DisplayName -like '*Apple Mobile Device*'")

#: winget: "already installed" / "no newer version" are fine, too.
WINGET_OK = {0, 0x8A15002B, 0x8A150061}
#: msiexec: 3010 = done, restart recommended.
MSI_OK = {0, 3010}
#: What ShellExecute reports when the UAC prompt is declined.
UAC_DECLINED = 1223

RUNNING, STOPPED, MISSING = "running", "stopped", "missing"

Run = Callable[..., subprocess.CompletedProcess]
Step = Callable[[str], None]
Progress = Callable[[int], None]


class UsbSetupError(ModStallerError):
    exit_code = 4


@dataclass(frozen=True)
class ServiceState:
    state: str          # RUNNING, STOPPED or MISSING
    name: str = ""      # service name, if there is one


def port_open(timeout: float = 1.0) -> bool:
    try:
        socket.create_connection(APPLE_MOBILE_DEVICE, timeout=timeout).close()
        return True
    except OSError:
        return False


def _no_window() -> int:
    # Without it a console window flashes up for every PowerShell call.
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def powershell(script: str, *, run: Run = subprocess.run,
               timeout: float = 60) -> subprocess.CompletedProcess:
    return run(["powershell.exe", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-Command", script],
               capture_output=True, text=True, timeout=timeout,
               creationflags=_no_window())


def service_state(*, run: Run = subprocess.run,
                  port: Callable[[], bool] = port_open) -> ServiceState:
    """Is the service there, and does it run?"""
    if port():
        return ServiceState(RUNNING)
    try:
        r = powershell(
            f"Get-Service | Where-Object {{ {SERVICE_FILTER} }} | "
            "Select-Object -First 1 Name, @{n='Status';e={[string]$_.Status}} | "
            "ConvertTo-Json -Compress", run=run, timeout=30)
        found = json.loads(r.stdout) if r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError, ValueError):
        found = None
    if not isinstance(found, dict) or not found.get("Name"):
        return ServiceState(MISSING)
    # Running according to Windows but the port is closed: it is still
    # starting, or hanging - both are fixed by (re)starting it.
    return ServiceState(STOPPED, str(found["Name"]))


def run_elevated(exe: str, args: str, *, run: Run = subprocess.run,
                 timeout: float = 1800) -> int:
    """Runs ``exe`` with administrator rights (one UAC prompt), waits for it
    and returns its exit code - :data:`UAC_DECLINED` if declined."""
    script = (f"try {{ $p = Start-Process -FilePath {_ps_quote(exe)} "
              f"-ArgumentList {_ps_quote(args)} -Verb RunAs -Wait -PassThru "
              f"-WindowStyle Hidden; exit $p.ExitCode }} "
              f"catch {{ exit {UAC_DECLINED} }}")
    return powershell(script, run=run, timeout=timeout).returncode


def signed_by_apple(path: Path, *, run: Run = subprocess.run) -> bool:
    """Valid Authenticode signature whose signer is Apple Inc."""
    r = powershell(
        f"$s = Get-AuthenticodeSignature -LiteralPath {_ps_quote(str(path))}; "
        "@{Status=[string]$s.Status; Subject=[string]$s.SignerCertificate.Subject}"
        " | ConvertTo-Json -Compress", run=run, timeout=120)
    try:
        sig = json.loads(r.stdout)
    except ValueError:
        return False
    return sig.get("Status") == "Valid" and "O=Apple Inc." in sig.get("Subject", "")


def wait_for_service(timeout: float, *, port: Callable[[], bool] = port_open,
                     sleep: Callable[[float], None] = time.sleep) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        if port():
            return True
        if time.monotonic() >= deadline:
            return False
        sleep(2)


def download(url: str, target: Path, on_progress: Progress) -> None:
    import requests
    with requests.get(url, stream=True, timeout=60,
                      headers={"User-Agent": "ModStaller"}) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        with open(target, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    on_progress(min(100, done * 100 // total))


# -- The two ways in -----------------------------------------------------------


def _via_winget(on_step: Step, *, run: Run) -> bool:
    winget = shutil.which("winget")
    if not winget:
        on_step(_("winget is not available - taking Apple's driver package "
                  "instead."))
        return False
    on_step(_("Installing “Apple Devices” from the Microsoft Store (winget) …"))
    try:
        r = run([winget, "install", "--id", APPLE_DEVICES_STORE_ID,
                 "--source", "msstore", "--exact", "--silent",
                 "--accept-package-agreements", "--accept-source-agreements",
                 "--disable-interactivity"],
                capture_output=True, text=True, timeout=1800,
                creationflags=_no_window())
    except (OSError, subprocess.SubprocessError) as exc:
        on_step(_("winget failed: {error}", error=exc))
        return False
    code = r.returncode & 0xFFFFFFFF
    if code not in WINGET_OK:
        last = (r.stdout or r.stderr or "").strip().splitlines()[-1:] or [""]
        on_step(_("winget failed (code {code:#x}): {detail}",
                  code=code, detail=last[0]))
        return False
    return True


def _via_driver_package(on_step: Step, on_progress: Progress, *, run: Run,
                        fetch: Callable[[str, Path, Progress], None]) -> None:
    with tempfile.TemporaryDirectory(prefix="modstaller-usb-") as tmp:
        work = Path(tmp)
        setup_exe = work / "iTunes64Setup.exe"
        on_step(_("Downloading Apple's driver package from apple.com …"))
        fetch(ITUNES_URL, setup_exe, lambda p: on_progress(10 + p * 6 // 10))

        if not signed_by_apple(setup_exe, run=run):
            raise UsbSetupError(_(
                "The download from apple.com is not signed by Apple - "
                "it was not run."))

        # Only the driver package is taken out - iTunes itself stays out.
        on_step(_("Unpacking the driver package …"))
        extract = work / "extract"
        extract.mkdir()
        run([str(setup_exe), "/extract", str(extract)], cwd=str(extract),
            capture_output=True, timeout=600, creationflags=_no_window())
        msi = next(iter(sorted(extract.rglob(DRIVER_MSI))), None) \
            or next(iter(sorted(work.rglob(DRIVER_MSI))), None)
        if msi is None:
            raise UsbSetupError(_(
                "Apple's installer did not contain {file}.", file=DRIVER_MSI))
        if not signed_by_apple(msi, run=run):
            raise UsbSetupError(_(
                "{file} is not signed by Apple - it was not installed.",
                file=DRIVER_MSI))
        on_progress(75)

        on_step(_("Installing Apple's USB driver - please confirm the "
                  "Windows prompt …"))
        code = run_elevated("msiexec.exe", f'/i "{msi}" /qn /norestart', run=run)
        if code == UAC_DECLINED:
            raise UsbSetupError(_("The Windows prompt was declined - nothing "
                                  "was installed."))
        if code not in MSI_OK:
            raise UsbSetupError(_("Apple's driver package could not be "
                                  "installed (msiexec {code}).", code=code))


def _start(name: str, on_step: Step, *, run: Run) -> None:
    on_step(_("Starting the Apple device service - please confirm the "
              "Windows prompt …"))
    code = run_elevated(
        "powershell.exe",
        f"-NoProfile -Command Set-Service -Name {_ps_quote(name)} "
        f"-StartupType Automatic; Start-Service -Name {_ps_quote(name)}",
        run=run, timeout=300)
    if code == UAC_DECLINED:
        raise UsbSetupError(_("The Windows prompt was declined - the "
                              "service was not started."))


def setup(on_step: Step = lambda s: None, on_progress: Progress = lambda p: None,
          *, run: Run = subprocess.run, port: Callable[[], bool] = port_open,
          fetch: Callable[[str, Path, Progress], None] = download,
          wait: Callable[[float], bool] | None = None,
          windows: bool = os.name == "nt") -> str:
    """Makes the Apple device service available.

    Returns what was done: ``"already"``, ``"started"``, ``"apple-devices"``
    (Store app via winget) or ``"driver"`` (Apple's driver package).
    """
    if not windows:
        raise UsbSetupError(_("Only needed on Windows."))
    if wait is None:
        def wait(timeout: float) -> bool:
            return wait_for_service(timeout, port=port)

    on_progress(0)
    state = service_state(run=run, port=port)
    if state.state == RUNNING:
        on_progress(100)
        on_step(_("The Apple device service is already running."))
        return "already"

    if state.state == STOPPED:
        _start(state.name, on_step, run=run)
        if wait(60):
            on_progress(100)
            return "started"
        raise UsbSetupError(_("The Apple device service does not start. "
                              "Restarting Windows usually helps."))

    on_progress(5)
    if _via_winget(on_step, run=run):
        on_step(_("Waiting for the Apple device service …"))
        if wait(120):
            on_progress(100)
            return "apple-devices"
        # Installed but not running (yet) - start it once, then give up
        # on this way and take the driver package.
        again = service_state(run=run, port=port)
        if again.state == STOPPED:
            _start(again.name, on_step, run=run)
            if wait(60):
                on_progress(100)
                return "apple-devices"

    _via_driver_package(on_step, on_progress, run=run, fetch=fetch)
    on_step(_("Waiting for the Apple device service …"))
    if wait(120):
        on_progress(100)
        return "driver"
    again = service_state(run=run, port=port)
    if again.state == STOPPED:
        _start(again.name, on_step, run=run)
        if wait(60):
            on_progress(100)
            return "driver"
    raise UsbSetupError(_("The driver is installed, but the Apple device "
                          "service does not answer yet. Restart Windows and "
                          "plug the iPhone in again."))
