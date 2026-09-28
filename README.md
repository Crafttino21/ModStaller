# ModStaller

A multi-platform iOS sideloader. ModStaller takes an IPA, signs it with a
development certificate from your own Apple account and installs it on your
iPhone - no Mac, no jailbreak, no paid developer account required. It also
enables JIT for emulators and Java launchers, including on iOS 26/27 devices
with TXM.

| Platform | Status |
|---|---|
| **Linux** | ✅ officially supported (AppImage, CLI) |
| **Windows** | ✅ officially supported (installer, CLI) |
| **Android** | 🛠️ planned - Android phone as the host, iPhone via USB-C/OTG |
| macOS | ➖ not planned - use Xcode or AltStore there |

Tested on: iPhone 16 Pro Max (iPhone17,2), iOS 27.0, CachyOS/Arch and
Windows. See [Supported devices](#supported-devices) for the full list.

**Contents:**
[Features](#features) ·
[Roadmap](#roadmap) ·
[Supported devices](#supported-devices) ·
[Installation](#installation) ·
[Usage](#usage) ·
[JIT](#jit) ·
[Limits of free Apple accounts](#limits-of-free-apple-accounts) ·
[Pitfalls solved here](#pitfalls-solved-here) ·
[Development](#development) ·
[AI disclosure and contributions](#ai-disclosure-and-contributions) ·
[Security](#security) ·
[Credits](#credits) ·
[License](#license)

## Features

- **Sign and install** IPAs with your own Apple ID (free or paid account),
  including 2FA. Drag and drop in the GUI, or `modstaller install app.ipa`.
- **Refresh** before the 7-day expiry of free accounts. The original IPA is
  remembered and the bundle ID stays stable, so app data survives.
- **JIT** through StikDebug's *universal* protocol, including the
  extensions apps send along - works on TXM/SPTM devices (A15 and newer,
  iOS 26/27). See [JIT](#jit).
- **iPhone check**: pairing, Developer Mode, Developer Disk Image, app
  slots and free storage, with one-click fixes where Apple allows them.
- **Account management**: team, quotas, App IDs, certificates.
- **Auto-updates** for the AppImage and the Windows installer.
- **Seven languages**: English, German, French, Spanish, Italian, Portuguese
  (Brazil) and Dutch.
- **GUI and CLI** on the same backend - everything the window can do, a
  script can do too.

## Roadmap

**Done recently**

- [x] Windows: CI builds, installer, CLI zip, auto-update, full test pass on
      real machines
- [x] Windows declared officially supported
- [x] `refresh` tested end to end against a real 7-day expiry
- [x] JIT ported to StikDebug's universal protocol (app extensions run)
- [x] iOS 27: Developer Disk Image installed as a cryptex over the RSD tunnel

**Next**

- [ ] **IPA editor** - change display name, bundle ID, version, icon and
      entitlements before installing, and choose which extensions to keep
- [ ] Automatic refresh: systemd timer (Linux) and Task Scheduler (Windows)
- [ ] Test more devices, especially an A13/A14 iPhone without TXM and older
      iOS versions (see [Supported devices](#supported-devices))
- [ ] Support for other Apple devices (iPad test pass, Apple TV)

**Android**

- [ ] Use an Android phone as the host: connect the iPhone via USB-C/OTG,
      sign and install directly from Android - no PC needed
- [ ] Evaluate the USB stack on Android (usbmuxd replacement without root)
- [ ] Android app with the same feature set as the desktop UI

**Backend rewrite in Rust**

- [ ] Rebuild the backend in Rust - one small native binary per platform
      instead of a bundled Python runtime, and the base for the Android host
- [ ] Keep the JSON-RPC interface, so the GUI and scripts keep working
      unchanged during the migration

**Ideas (maybe)**

- [ ] A small built-in IPA market: curated sources for sideloadable apps,
      installable with one click
- [ ] Wireless refresh over Wi-Fi once the device is paired
- [ ] Multiple Apple accounts and multiple devices

## Supported devices

ModStaller uses the same mechanism as Xcode's free provisioning, so in
principle it works on every iPhone that can run a supported iOS version.
Test reports are very welcome: open an issue with the model, the iOS version
and the output of `modstaller device info`.

**Legend:** ✅ tested · 🟡 expected to work, untested · ❌ not supported

### iPhone

| Model | Chip | TXM/SPTM | Install | JIT |
|---|---|---|---|---|
| iPhone 16 Pro Max | A18 Pro | yes | ✅ | ✅ (iOS 27.0) |
| iPhone 16 Pro, 16, 16 Plus, 16e | A18 Pro / A18 | yes | 🟡 | 🟡 |
| iPhone 17, 17 Pro, 17 Pro Max, iPhone Air and newer | A19 / A19 Pro and newer | yes | 🟡 | 🟡 |
| iPhone 15 Pro, 15 Pro Max | A17 Pro | yes | 🟡 | 🟡 |
| iPhone 15, 15 Plus, 14 Pro, 14 Pro Max | A16 | yes | 🟡 | 🟡 |
| iPhone 14, 14 Plus, 13 series, SE (3rd gen) | A15 | yes | 🟡 | 🟡 |
| iPhone 12 series | A14 | from iOS 27 | 🟡 | 🟡 ¹ |
| iPhone 11 series, SE (2nd gen) | A13 | from iOS 27 | 🟡 | 🟡 ¹ |
| iPhone XS / XR and older | A12 and older | - | ❌ | ❌ |

¹ On iOS 26 and older these devices have no TXM, so attaching a debugger
once is enough for JIT - ModStaller detects that and skips the conversation.
From iOS 27 on, iOS treats every supported device like a TXM device.

iPads use the same mechanism and should work in principle, but have not been
tested yet.

### iOS versions

| iOS | Install | JIT | Notes |
|---|---|---|---|
| 27.x | ✅ | ✅ | tested on 27.0; Developer Disk Image is a cryptex |
| 26.x | 🟡 | 🟡 | expected to work |
| 17.4 - 18.x | 🟡 | 🟡 | expected to work, untested |
| 16.0 - 17.3 | 🟡 | ❓ | install should work; JIT uses an older tunnel variant and is unverified |
| 15.x and older | ❌ | ❌ | not supported |

### Apple's requirements for sideloading

These come from Apple's rules for development-signed apps and apply to every
device above, regardless of ModStaller:

* **Developer Mode** must be enabled (iOS 16 and later). The iPhone check
  can switch it on for you - see [Usage](#usage).
* **The device must be paired and trusted** with the computer ("Trust This
  Computer", passcode on first connect).
* **The developer certificate must be trusted** once on the iPhone under
  Settings › General › VPN & Device Management.
* **The device is registered to your Apple team** automatically on first
  install. This counts against Apple's device limit for your account.
* **Free accounts** get 7-day profiles, at most 3 sideloaded apps per device
  and 10 new App IDs per week - see
  [Limits of free Apple accounts](#limits-of-free-apple-accounts). Paid
  accounts get one-year profiles and don't have the 3-app limit.
* **JIT** additionally requires the app to be development-signed
  (`get-task-allow`) and, on TXM/SPTM devices, to implement the breakpoint
  protocol described under [JIT](#jit).

## Installation

Prebuilt binaries are available under
[Releases](https://github.com/Crafttino21/ModStaller/releases/latest):

| File | For |
|---|---|
| `ModStaller-X.Y.Z-x86_64.AppImage` | Linux, GUI - updates itself |
| `ModStaller-Setup-X.Y.Z.exe` | Windows, GUI - installer without admin rights, updates itself |
| `ModStaller-CLI-X.Y.Z-windows-x64.zip` | Windows, command line: `modstaller.exe` + `zsign.exe` |

Python, pymobiledevice3, QuickJS and zsign are bundled in each. The only
thing your machine needs is the service that makes the iPhone reachable over
USB.

**Linux:**

```bash
sudo pacman -S usbmuxd fuse2              # Arch (fuse2 for AppImages)
sudo apt install usbmuxd libfuse2         # Debian/Ubuntu
sudo dnf install usbmuxd fuse-libs        # Fedora
```

**Windows:** install the **"Apple Devices"** app from the Microsoft Store (or
iTunes) - it brings the Apple device service along. On first launch
SmartScreen warns because the .exe is not signed with a paid certificate:
"More info" › "Run anyway". If the GUI ever reports that the backend is
unreachable, the full log is in `%APPDATA%\ModStaller\logs\main.log`.

`modstaller doctor` (or the system check in the GUI) shows whether
everything is in place.

## Usage

The GUI shows up front whether the iPhone is connected, whether you are
signed in and what is about to expire. IPAs can simply be dragged into the
window.

As soon as an iPhone is plugged in, the **iPhone check** runs: pairing, iOS
version, Developer Mode, Developer Disk Image, used app slots and free
storage. Anything that can be fixed automatically gets a button:

* **Request pairing** - then just tap "Trust" on the iPhone.
* **Enable Developer Mode** - fully automatic without a passcode, including
  reboot and confirmation. With a passcode iOS refuses this; ModStaller then
  reveals the otherwise hidden toggle in Settings instead.
* **Mount Developer Disk Image** (only needed for JIT) and **remove expired
  profiles**.

"Trust developer" (Settings › General › VPN & Device Management) remains a
manual step - there is no interface for it.

**Language:** the interface starts in English; **Settings › Language**
switches it, including system checks and error messages from the backend.

The command line offers the same:

```bash
modstaller doctor                 # system check
modstaller login                  # once, asks for Apple ID + 2FA code
modstaller account                # team, quotas, registered App IDs
modstaller device info            # iPhone, iOS version, Developer Mode

modstaller install app.ipa        # sign and install
modstaller list                   # what is installed and how long it has left
modstaller refresh                # renew before the 7-day expiry
modstaller uninstall <bundle-id>  # remove an app, frees a slot
modstaller certs                  # show/revoke certificates
modstaller jit <bundle-id>        # enable JIT (Java/emulator apps)
```

With a free account, app extensions are stripped by default: each one costs
an App ID from a quota of ten per week, and the app itself runs fine without
them. Use `--keep-extensions` to keep them.

## JIT

Java and emulator apps generate machine code at runtime. iOS forbids this -
such apps hang on launch ("Waiting for JIT").

Up to iOS 18 it was enough to attach a debugger: the kernel then set
`CS_DEBUGGED`, and that even survived detaching the debugger.

**On devices with TXM/SPTM that is no longer enough.** There, a memory page
only becomes executable when an *attached* debugger writes to it: one byte
per 16 KB page, and that very access grants the permission. JIT is therefore
no longer a switch but a conversation:

    App:      brk #0xf00d, x16=1, x0=address, x1=length   "prepare this"
    Debugger: writes to every page, puts the address into x0
    App:      sets up its compiler memory
    App:      brk #0xf00d, x16=0                          "done, you can go"

ModStaller speaks the **universal** protocol that StikDebug established, so
every app that works with StikDebug works here too. Apps can extend the
protocol by sending a piece of JavaScript (`brk #0xf00d` with `x16=2`) that
registers commands of their own - Amethyst does this, for example. ModStaller
really runs these extensions: its side of the protocol
(`modstaller/device/jit_host.js`) runs in an embedded QuickJS engine, with
the same global API an extension expects.

`modstaller jit <bundle-id>` mounts the Developer Disk Image if needed,
launches the app suspended, attaches via the RSD tunnel and serves the app's
requests until it signs off. On devices without TXM it just attaches once.

Limitations:

* **The app has to cooperate.** If it never triggers the breakpoint, it gets
  no JIT on TXM devices, no matter which debugger is attached.
* The app needs `get-task-allow` - development-signed apps have it, App Store
  apps never do.
* The unlock only applies to *this* launch of the app.
* The need only arises once the app actually wants to compile. For a
  Minecraft launcher that means: while ModStaller is waiting, start an
  instance in the launcher.
* The iPhone has to be unlocked while the Developer Disk Image is mounted.
  ModStaller asks for it and waits.

## Limits of free Apple accounts

None of these are bugs in ModStaller; they come from Apple:

* **Profiles expire after 7 days.** After that the app won't launch until
  `modstaller refresh` re-signs it.
* **At most 3 sideloaded apps at a time** per device. The iPhone rejects the
  fourth; `modstaller uninstall <bundle-id>` frees a slot.
* **10 App IDs per week.** What counts is *newly created* ones - deleting one
  does not give quota back. When the window is full, ModStaller falls back
  to an existing, unused App ID; the app then runs under that bundle ID. App
  IDs of installed apps and their extensions are left untouched.
* **Only one development certificate.** Two sideloading tools used in
  parallel will push each other out, because the private key always lives
  with the tool that requested it.

Apple does not reveal directly whether an account is free: it reports paid
individual accounts as `Individual` too. ModStaller assumes "free" when in
doubt and corrects itself based on the lifetime of the first profile - 7 days
means free, one year means paid.

## Pitfalls solved here

**Apple's 503 smoke screen.** Since the end of August 2026, Apple rejects
every GSA request at the edge with HTTP 503 if its `X-MMe-Client-Info`
carries the identifier `com.apple.dt.Xcode` - which the `anisette` library
does by default. It looks like an Apple outage but isn't one. ModStaller
replaces the identifier with `com.apple.akd` and refuses, in
`apple/clientinfo.py`, any request that doesn't:

    com.apple.dt.Xcode  ->  HTTP 503, 190 B  (rejected at the edge)
    com.apple.akd/1.0   ->  HTTP 404          (got through)

**Apple's private CA.** `gsa.apple.com` is signed by "Apple Server
Authentication CA", not a public CA, so the system trust store fails every
connection. The chain lives in `modstaller/apple/certs/apple-gsa-ca.pem` -
we verify against it instead of disabling verification.

**One request per connection.** Apple's edge only lets the first request on
a TCP connection to `GsService2` through; every further one gets HTTP 429:

    Connection reused:   404, 429, 429, 429, 429, 429
    Connection: close:   404, 404, 404, 404, 404, 429

A login consists of two requests, so with keep-alive *every* login fails on
the second one and looks like a locked account. ModStaller forces a fresh
connection per request and retries the remaining per-IP 429s a limited
number of times - harmless, because the edge rejects them before the SRP
cookie is consumed.

**Control Flow Guard kills the Windows build.** The Anisette provider runs
Apple's ADI libraries in an ARM emulation (Unicorn). PyInstaller's bootloader
is linked with Control Flow Guard, `python.exe` is not - and CFG applies to
the whole process. Unicorn `longjmp`s out of JIT-generated code, MSVC's
runtime finds no CFG entry for that target and calls `__fastfail`
(`0xC0000409`): the backend simply vanishes. `packaging/build_backend.py`
clears that flag from the finished binaries; `apple/anisette.py` checks the
policy at runtime as a safety net.

**The universal-script handshake.** Amethyst probes the debugger with
`brk #0x69` and only continues if `x0` then holds `0x690000E0`. StikDebug
answers with `P0=E0000069` - and since the GDB `P` packet takes
little-endian bytes, the register really ends up as `0x690000E0`. Answering
with the "correct" value `0xE0000069` makes the app report a legacy script.

**iOS 27 Developer Disk Image.** From iOS 27 on, pymobiledevice3 installs
the image as a cryptex and refuses plain lockdown with `RSDRequiredError`.
ModStaller mounts over the RSD tunnel from iOS 17 on, and checks the
installed cryptexes as well, since the classic image mounter no longer
lists the image.

The diagnosis of the 503 and 429 findings builds on investigations by
SideStore (issue #1557) and OpenTagViewer (issue #226); the implementation
here is original code.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e . pytest pytest-asyncio
paru -S zsign-bin                         # or build zsign yourself
.venv/bin/modstaller doctor
.venv/bin/python -m pytest -q

cd gui && npm install && npm run dev      # GUI with hot reload
```

The GUI is a client just like the command line: it starts
`modstaller serve` and talks to it via JSON-RPC over stdin/stdout
(`modstaller/server.py`).

**Building:**

| Command | Builds |
|---|---|
| `./buildscripts/build-appimage.sh` | the AppImage - only needs Docker; `--run` launches it afterwards |
| `buildscripts\build-windows.bat` | the Windows installer - needs Python 3.12+, Node 22+ and Visual Studio 2022 with C++ for `zsign.exe`; `--dir` skips the installer, `--run` launches it afterwards |

Both run the same steps as `.github/workflows/release.yml`.

**Releases:** one script sets the version, commits, tags and pushes; GitHub
does the rest (tests on Linux and Windows, AppImage, installer, CLI zip,
update manifests):

```bash
./release.sh 1.3.0            # Linux
release.bat 1.3.0             # Windows
./release.sh 1.3.0-beta.1     # pre-release
```

The AppImage and the Windows installer check for updates at startup and
every four hours. Downloading and restarting only happen when you click the
button - never during an installation or a JIT session. Pre-releases are
only offered to users already running one.

**Translations:** English is the source language in the code, so a missing
translation shows the English sentence rather than a key. A new language is
one catalog on each side plus one line in `gui/src/lib/i18n.svelte.ts`:

| Side | File |
|---|---|
| Interface | `gui/src/lib/locale/<code>.ts` |
| Backend | `modstaller/locale/<code>.json` |

`pytest tests/test_i18n.py` checks every catalog against the source.

## AI disclosure and contributions

**Parts of ModStaller's code were written with the help of AI tools.** This
includes code, tests, comments and documentation. Every AI-generated change
has been reviewed, tested and taken responsibility for by a human
maintainer before it was merged.

Contributions that contain AI-generated code are welcome in commits, branches
and pull requests under the same conditions as any other code:

* **It has been professionally reviewed** by the person submitting it - you
  understand every line and can explain and defend it in review.
* **It follows current best practices and security standards**: no secrets
  in code or logs, input validated, TLS verified, no disabled checks, no
  unexplained dependencies, least privilege for anything touching the
  device or the Apple account.
* **It is tested**: new behavior comes with tests, and `pytest` passes.
* **It matches the codebase**: naming, comment density and structure like
  the surrounding code.
* **Licensing is clean**: no code copied from sources whose license does not
  allow it. The JIT host, for example, is an independent implementation of
  StikDebug's protocol, not a copy of its AGPL-licensed script.

Marking AI assistance in the pull request description (and a
`Co-Authored-By` trailer in the commit where the tool adds one) is
appreciated. Unreviewed, bulk-generated changes will be closed.

## Security

Your Apple password is never stored and never transmitted: SRP-6a proves
knowledge of it without sending it. All secrets are stored under
`~/.local/share/modstaller/` with mode 0600 inside 0700 directories.

ModStaller only talks to Apple's servers and your own devices. JavaScript
that an app sends for JIT runs in an isolated QuickJS context whose only
capabilities are the debugger commands for that app's own process.

Found a security issue? Please report it privately via GitHub's security
advisories instead of a public issue.

## Credits

ModStaller builds on
[pymobiledevice3](https://github.com/doronz88/pymobiledevice3) (device
communication),
[zsign](https://github.com/zhlynn/zsign) (signing),
[anisette](https://pypi.org/project/anisette/) (Apple anisette data) and
[quickjs-ng](https://github.com/quickjs-ng/quickjs) (JIT extensions). The JIT
protocol follows [StikDebug](https://github.com/StikDebug/StikDebug); the
GSA findings build on [SideStore](https://github.com/SideStore) and
[OpenTagViewer](https://github.com/parawanderer/OpenTagViewer).

## License

ModStaller is free software: you can redistribute it and/or modify it under
the terms of the [GNU General Public License](LICENSE) as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

It is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the [LICENSE](LICENSE) file for details.

Contributions are accepted under the same license.
