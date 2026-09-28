"""Windows: checking and setting up the Apple device service.

No Windows here - every call to the outside (PowerShell, winget, the
installer, msiexec) goes through a fake ``run`` that records what it was
asked and answers like Windows would.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from modstaller import winsetup
from modstaller.winsetup import UsbSetupError


class FakeWindows:
    """Answers the commands winsetup issues, one scenario at a time."""

    def __init__(self, *, service=None, winget=0, winget_installs=True,
                 signed=True, msi_signed=True, extract_msi=True, msiexec=0,
                 start=0):
        self.service = service          # None | "Running" | "Stopped"
        self.winget = winget
        self.winget_installs = winget_installs
        self.signed = signed
        self.msi_signed = msi_signed
        self.extract_msi = extract_msi
        self.msiexec = msiexec
        self.start = start
        self.port = service == "Running"
        self.calls: list[str] = []

    def __call__(self, cmd, **kw):
        line = " ".join(map(str, cmd))
        self.calls.append(line)
        out, code = "", 0
        if cmd[0] == "powershell.exe":
            script = cmd[-1]
            if "Get-Service" in script:
                if self.service:
                    out = json.dumps({"Name": "Apple Mobile Device Service",
                                      "Status": self.service})
            elif "Get-AuthenticodeSignature" in script:
                ok = self.msi_signed if ".msi" in script else self.signed
                out = json.dumps({
                    "Status": "Valid" if ok else "HashMismatch",
                    "Subject": "CN=Apple Inc., O=Apple Inc., C=US" if ok else "CN=Evil"})
            elif "msiexec.exe" in script:
                code = self.msiexec
                if code in winsetup.MSI_OK:
                    self.service, self.port = "Running", True
            elif "Start-Service" in script:
                code = self.start
                if code == 0:
                    self.service, self.port = "Running", True
        elif cmd[0].endswith("winget"):
            code = self.winget
            if code in winsetup.WINGET_OK and self.winget_installs:
                self.service, self.port = "Running", True
        elif "/extract" in cmd:
            if self.extract_msi:
                (Path(cmd[-1]) / "AppleMobileDeviceSupport64.msi").write_bytes(b"msi")
        return subprocess.CompletedProcess(cmd, code, out, "")

    def port_open(self):
        return self.port


def fake_fetch(url, target, progress):
    target.write_bytes(b"exe")
    progress(100)


def run_setup(win: FakeWindows, monkeypatch, *, winget=True):
    monkeypatch.setattr(winsetup.shutil, "which",
                        lambda name: "C:/winget" if winget else None)
    steps: list[str] = []
    how = winsetup.setup(steps.append, lambda p: None, run=win, port=win.port_open,
                         fetch=fake_fetch, wait=lambda t: win.port_open(),
                         windows=True)
    return how, steps


def test_a_running_service_needs_nothing(monkeypatch):
    win = FakeWindows(service="Running")
    how, _ = run_setup(win, monkeypatch)
    assert how == "already"
    assert win.calls == []


def test_the_state_tells_stopped_from_missing():
    assert winsetup.service_state(run=FakeWindows(service="Stopped"),
                                  port=lambda: False).state == winsetup.STOPPED
    assert winsetup.service_state(run=FakeWindows(),
                                  port=lambda: False).state == winsetup.MISSING
    assert winsetup.service_state(run=FakeWindows(),
                                  port=lambda: True).state == winsetup.RUNNING


def test_without_powershell_the_service_counts_as_missing():
    def broken(cmd, **kw):
        raise FileNotFoundError("powershell.exe")
    assert winsetup.service_state(run=broken, port=lambda: False).state == winsetup.MISSING


def test_a_stopped_service_is_started_elevated(monkeypatch):
    win = FakeWindows(service="Stopped")
    how, _ = run_setup(win, monkeypatch)
    assert how == "started"
    elevated = [c for c in win.calls if "RunAs" in c]
    assert len(elevated) == 1 and "Start-Service" in elevated[0]
    assert "'Apple Mobile Device Service'" in elevated[0].replace("''", "'")


def test_missing_service_comes_from_the_store_first(monkeypatch):
    win = FakeWindows()
    how, _ = run_setup(win, monkeypatch)
    assert how == "apple-devices"
    winget = next(c for c in win.calls if c.startswith("C:/winget"))
    assert winsetup.APPLE_DEVICES_STORE_ID in winget and "msstore" in winget
    assert not any("/extract" in c for c in win.calls), "no download needed"


def test_already_installed_is_fine_for_winget(monkeypatch):
    win = FakeWindows(winget=0x8A15002B)
    how, _ = run_setup(win, monkeypatch)
    assert how == "apple-devices"


def test_without_winget_only_apples_driver_package_is_installed(monkeypatch):
    win = FakeWindows()
    how, steps = run_setup(win, monkeypatch, winget=False)
    assert how == "driver"
    msi = [c for c in win.calls if "msiexec.exe" in c]
    assert len(msi) == 1 and "AppleMobileDeviceSupport64.msi" in msi[0] and "/qn" in msi[0]
    assert any("winget" in s for s in steps)


def test_a_failing_winget_falls_back_to_the_driver_package(monkeypatch):
    win = FakeWindows(winget=0x8A150014)
    how, steps = run_setup(win, monkeypatch)
    assert how == "driver"
    assert any("0x8a150014" in s for s in steps)


def test_an_unsigned_download_is_never_run(monkeypatch):
    win = FakeWindows(signed=False)
    with pytest.raises(UsbSetupError, match="not signed by Apple"):
        run_setup(win, monkeypatch, winget=False)
    assert not any("/extract" in c or "msiexec" in c for c in win.calls)


def test_an_unsigned_msi_is_never_installed(monkeypatch):
    win = FakeWindows(msi_signed=False)
    with pytest.raises(UsbSetupError, match="not signed by Apple"):
        run_setup(win, monkeypatch, winget=False)
    assert not any("msiexec" in c for c in win.calls)


def test_an_installer_without_the_driver_package_says_so(monkeypatch):
    win = FakeWindows(extract_msi=False)
    with pytest.raises(UsbSetupError, match="AppleMobileDeviceSupport64.msi"):
        run_setup(win, monkeypatch, winget=False)


def test_a_declined_uac_prompt_is_named(monkeypatch):
    win = FakeWindows(msiexec=winsetup.UAC_DECLINED)
    with pytest.raises(UsbSetupError, match="declined"):
        run_setup(win, monkeypatch, winget=False)


def test_restart_recommended_counts_as_success(monkeypatch):
    win = FakeWindows(msiexec=3010)
    how, _ = run_setup(win, monkeypatch, winget=False)
    assert how == "driver"


def test_paths_with_quotes_stay_one_powershell_string():
    assert winsetup._ps_quote("C:/it's here") == "'C:/it''s here'"


def test_only_windows_needs_it():
    with pytest.raises(UsbSetupError):
        winsetup.setup(windows=False)
