# ModStaller

An iOS sideloader for Linux (Windows and Android on the way). It takes an IPA,
signs it with a development certificate obtained through your own Apple account
and installs it on your iPhone - no Mac, no jailbreak.

Tested against: iPhone 16 Pro Max (iPhone17,2), iOS 27.0, CachyOS/Arch.
See [Supported devices](#supported-devices) for the full compatibility list.

## Status

| Milestone | Scope | Status |
|---|---|---|
| M0 | Scaffolding, `doctor`, device connection | working |
| M1 | Anisette + GSA login incl. 2FA | working |
| M2 | Certificate, App ID, provisioning profile | working |
| M3 | Signing and installing | working |
| M4 | `refresh`, `uninstall`, `certs` | built, refresh not yet tested |
| M5 | systemd timer for automatic refresh | open |

First complete run on 2026-09-23: PojavLauncher 2.2 (17 injected dylibs,
4 frameworks) signed and installed on an iPhone 16 Pro Max running iOS 27.0.
Transport: lockdown - so the RSD tunnel is not needed for installation on
iOS 27.

## Roadmap

ModStaller currently runs fully on **Linux**. Planned next:

**Short term**

- [ ] Test `refresh` end to end against a real 7-day expiry (finish M4)
- [ ] systemd timer for automatic refresh (M5)
- [ ] Test on more devices, especially an A13/A14 iPhone without TXM and an
      older iOS version (see [Supported devices](#supported-devices))

**Windows**

- [x] CI builds: installer, CLI zip, auto-update
- [ ] Full test pass on real Windows machines (pairing, install, JIT via RSD tunnel)
- [ ] Automatic refresh via Windows Task Scheduler (counterpart to M5)
- [ ] Declare Windows as officially supported

**Android**

- [ ] Use an Android phone as the host: connect the iPhone via USB-C/OTG and
      sign and install directly from Android - no PC needed
- [ ] Evaluate the USB stack on Android (usbmuxd replacement without root)
- [ ] Android app with the same feature set as the desktop UI

**Later / ideas**

- [ ] Wireless refresh over Wi-Fi once the device is paired
- [ ] Support for multiple Apple accounts and multiple devices

## Supported devices

ModStaller uses the same mechanism as Xcode's free provisioning, so in
principle it works on every iPhone that can run a supported iOS version.
So far only one combination has actually been tested - everything else is
expected to work but unconfirmed. Test reports (issue with model, iOS version
and the output of `modstaller device info`) are very welcome.

**Legend:** ✅ tested · 🟡 expected to work, untested · ❌ not supported

### iPhone

| Model | Chip | TXM/SPTM | Install | JIT | Status |
|---|---|---|---|---|---|
| iPhone 16 Pro Max | A18 Pro | yes | ✅ | 🟡 | ✅ tested on iOS 27.0 |
| iPhone 16 Pro, 16, 16 Plus, 16e | A18 Pro / A18 | yes | 🟡 | 🟡 | 🟡 |
| iPhone 17, 17 Pro, 17 Pro Max, iPhone Air and newer | A19 / A19 Pro and newer | yes | 🟡 | 🟡 | 🟡 |
| iPhone 15 Pro, 15 Pro Max | A17 Pro | yes | 🟡 | 🟡 | 🟡 |
| iPhone 15, 15 Plus, 14 Pro, 14 Pro Max | A16 | yes | 🟡 | 🟡 | 🟡 |
| iPhone 14, 14 Plus, 13 series, SE (3rd gen) | A15 | yes | 🟡 | 🟡 | 🟡 |
| iPhone 12 series | A14 | no | 🟡 | 🟡 ¹ | 🟡 |
| iPhone 11 series, SE (2nd gen) | A13 | no | 🟡 | 🟡 ¹ | 🟡 |
| iPhone XS / XR and older | A12 and older | no | ❌ | ❌ | ❌ no iOS 26/27 |

¹ Without TXM/SPTM, attaching a debugger is enough to unlock JIT (see
[JIT](#jit)), so these devices should actually be the easier case.

iPads running iPadOS use the same mechanism and should work in principle,
but have not been tested at all.

### iOS versions

| iOS | Install | JIT | Status |
|---|---|---|---|
| 27.x | ✅ | 🟡 | ✅ tested on 27.0 |
| 26.x | 🟡 | 🟡 | 🟡 expected |
| 17.4 - 18.x | 🟡 | 🟡 | 🟡 expected, untested |
| 16.0 - 17.3 | 🟡 | ❓ | 🟡 install should work; JIT uses an older tunnel variant and is unverified |
| 15.x and older | ❌ | ❌ | ❌ not supported |

### Apple's requirements for sideloading

These come from Apple's rules for development-signed apps and apply to every
device above, regardless of ModStaller:

* **Developer Mode** must be enabled (iOS 16 and later). ModStaller's iPhone
  check can switch it on for you - see [Usage](#usage).
* **The device must be paired and trusted** with the computer ("Trust This
  Computer", passcode on first connect).
* **The developer certificate must be trusted** once on the iPhone under
  Settings > General > VPN & Device Management.
* **The device is registered to your Apple team** automatically on first
  install. This counts against Apple's device limit for your account.
* **Free accounts:** 7-day profiles, at most 3 sideloaded apps per device,
  10 new App IDs per week - see
  [Limits of free Apple accounts](#limits-of-free-apple-accounts).
  Paid accounts get one-year profiles and don't have the 3-app limit.
* **JIT** additionally requires the app to be development-signed
  (`get-task-allow`) and, on TXM/SPTM devices, to implement the breakpoint
  protocol described under [JIT](#jit).

## Setup

Prebuilt binaries are available under
[Releases](https://github.com/Crafttino21/ModStaller/releases/latest):

| File | For |
|---|---|
| `ModStaller-X.Y.Z-x86_64.AppImage` | Linux, GUI - updates itself |
| `ModStaller-Setup-X.Y.Z.exe` | Windows, GUI - installer without admin rights, updates itself (experimental) |
| `ModStaller-CLI-X.Y.Z-windows-x64.zip` | Windows, command line: `modstaller.exe` + `zsign.exe` (experimental) |

Python, pymobiledevice3 and zsign are bundled in each. The only thing your
machine needs is the service that makes the iPhone reachable over USB:

```bash
sudo pacman -S usbmuxd fuse2              # Arch (fuse2 for AppImages)
sudo apt install usbmuxd libfuse2         # Debian/Ubuntu
```

On **Windows** that is the Apple device service: install the **"Apple
Devices"** app from the Microsoft Store (or iTunes). On first launch
SmartScreen will warn you because the .exe is not signed with a paid
certificate - "More info" > "Run anyway".

To build the AppImage yourself: `./build-appimage.sh` (only needs Docker;
`--run` launches it afterwards). The Windows builds are produced by the GitHub
pipeline.

For development:

```bash
python -m venv .venv
.venv/bin/pip install -e .
paru -S zsign-bin
.venv/bin/modstaller doctor

cd gui && npm install && npm run dev      # GUI with hot reload
```

## Usage

The GUI (AppImage or `npm run dev`) shows up front whether the iPhone is
connected, whether you are signed in and what is about to expire. IPAs can
simply be dragged into the window.

As soon as an iPhone is plugged in, the **iPhone check** runs: pairing, iOS
version, Developer Mode, Developer Disk Image, used app slots and free
storage. Anything that can be fixed automatically gets a button:

* **Request pairing** - then just tap "Trust" on the iPhone.
* **Enable Developer Mode** - fully automatic without a passcode, including
  reboot and confirmation. With a passcode iOS refuses this; ModStaller then
  reveals the otherwise hidden toggle in Settings instead.
* **Load Developer Disk Image** (only needed for JIT) and **remove expired
  profiles**.

"Trust developer" (Settings > General > VPN & Device Management) remains a
manual step - there is no interface for it.

The GUI is a client just like the command line: `gui/` starts
`modstaller serve` and talks to it via JSON-RPC over stdin/stdout
(`modstaller/server.py`).

For scripts and the refresh service, the subcommands remain:

```bash
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

## Releases and updates

Publishing a new version:

```bash
./release.sh 0.2.0            # set version, commit + tag, push
./release.sh 0.3.0-beta.1     # pre-release
```

GitHub takes care of the rest (`.github/workflows/release.yml`): tests on
Linux and Windows, building the AppImage, Windows installer and CLI zip, and
creating a release with the update manifests (`latest-linux.yml`,
`latest.yml`). The AppImage and the installed Windows version check for
updates at startup and every four hours, and show a notice in the bottom-left
corner when something new is available. Downloading and restarting only
happen when you click the button - never during an installation or a JIT
session. Pre-releases are only offered to users who are already running a
pre-release.

## JIT

Java and emulator apps generate machine code at runtime. iOS forbids this -
such apps hang on launch ("Waiting for JIT").

Up to iOS 18 it was enough to attach a debugger: the kernel then set
`CS_DEBUGGED`, and that even survived detaching the debugger.

**On devices with TXM/SPTM - every iPhone with an A15 chip or newer - that is no longer enough.**
There, a memory page only becomes executable when an *attached* debugger
writes to it: one byte per 16 KB page, and that very access grants the
permission. JIT is therefore no longer a switch but a conversation:

    App:      brk #0xf00d, x16=1, x0=address, x1=length   "prepare this"
    Debugger: writes to every page, puts the address into x0
    App:      sets up its compiler memory
    App:      brk #0xf00d, x16=0                          "done, you can go"

`modstaller jit` launches the app suspended, attaches via the RSD tunnel and
serves these requests until the app signs off.

Three limitations:

* **The app has to cooperate.** If it does not trigger this breakpoint, it
  gets no JIT, no matter which debugger is attached.
* The app needs `get-task-allow` - development-signed apps have it, App Store
  apps never do.
* The unlock only applies to *this* launch of the app.

The need only arises once the app actually wants to compile. For a Minecraft
launcher that means: while `modstaller jit` is waiting, you have to start an
instance in the launcher.

With a free account, app extensions are stripped by default: each one costs
an App ID from a quota of ten per week, and the app itself runs fine without
them. Use `--keep-extensions` to keep them.

`refresh` uses the original IPA remembered at install time and keeps the
bundle ID stable - otherwise iOS would treat it as a different app and the
stored data would be gone.

## Three pitfalls solved here

**Apple's 503 smoke screen.** Since the end of August 2026, Apple rejects
every GSA request at the edge with HTTP 503 if its `X-MMe-Client-Info` carries
the identifier `com.apple.dt.Xcode` - which the `anisette` library does by
default. It looks like an Apple outage but isn't one. ModStaller replaces the
identifier with `com.apple.akd` and refuses, in `apple/clientinfo.py`, any
request that doesn't. Verified empirically:

    com.apple.dt.Xcode  ->  HTTP 503, 190 B  (rejected at the edge)
    com.apple.akd/1.0   ->  HTTP 404          (got through)

**Apple's private CA.** `gsa.apple.com` is not signed by a public CA but by
"Apple Server Authentication CA". With the system trust store every
connection fails. The chain lives in
`modstaller/apple/certs/apple-gsa-ca.pem` - we verify against it instead of
disabling verification.

**One request per connection.** Apple's edge only lets the first request on a
TCP connection to `GsService2` through; every further one gets HTTP 429.
Measured:

    Connection reused:   404, 429, 429, 429, 429, 429
    Connection: close:   404, 404, 404, 404, 404, 429

A login consists of two requests (`init`, `complete`) - so with keep-alive
*every* login fails on the second one, and it looks like the account has been
locked. ModStaller forces a fresh connection per request. The remaining
sporadic 429 is a per-IP budget and is retried a limited number of times;
that is harmless because the edge rejects the request before it reaches the
auth service, so the SRP cookie is not consumed.

Diagnosis and measurement method come from the investigations by SideStore
(issue #1557) and OpenTagViewer (issue #226); the implementation here is
original code.

## Limits of free Apple accounts

None of these are bugs in ModStaller; they come from Apple:

* **Profiles expire after 7 days.** After that the app won't launch until
  `modstaller refresh` re-signs it.
* **At most 3 sideloaded apps at a time** per device. The iPhone rejects the
  fourth; `modstaller uninstall <bundle-id>` frees a slot.
* **10 App IDs per week.** What counts is *newly created* ones, not existing
  ones - so deleting one does not give quota back. When the window is full,
  ModStaller falls back to an existing, unused App ID; the app then runs
  under that bundle ID. App IDs of installed apps and their extensions are
  left untouched. Every extension needs its own App ID, which is why they are
  stripped by default on free accounts.
* **Only one development certificate.** Two sideloading tools used in
  parallel will inevitably push each other out, because the private key
  always lives with the tool that requested it.

Apple does not reveal directly whether an account is free: it reports paid
individual accounts as `Individual` too. ModStaller assumes "free" when in
doubt and corrects itself based on the actual lifetime of the first profile -
7 days means free, one year means paid.

## Security

Your Apple password is never stored and never transmitted: SRP-6a proves
knowledge of it without sending it. All secrets are stored under
`~/.local/share/modstaller/` with mode 0600 inside 0700 directories.
