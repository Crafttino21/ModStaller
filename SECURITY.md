# Security Policy

ModStaller handles sensitive things: your Apple ID session, development
certificates and their private keys, and debugger access to your iPhone. We
take reports about any of that seriously and are grateful for them.

## Supported versions

Security fixes land in the latest release. Older versions are not patched -
the AppImage and the Windows installer update themselves, so please stay
current.

| Version | Supported |
|---|---|
| Latest stable release (1.2.x) | ✅ |
| Latest pre-release (beta) | ✅ |
| Older releases | ❌ |

## Reporting a vulnerability

**Please do not open a public issue, discussion or pull request for a
security problem.**

Report it privately through GitHub instead:

1. Go to the [Security tab](https://github.com/Crafttino21/ModStaller/security)
   of this repository.
2. Click **"Report a vulnerability"**
   ([direct link](https://github.com/Crafttino21/ModStaller/security/advisories/new)).
3. Describe the issue. Only the maintainers can see the report.

Helpful to include:

- the affected version (shown in the app, or in the name of the AppImage or
  installer you downloaded) and your platform (Linux distribution or
  Windows version)
- the component, if you know it (for example the Apple sign-in in
  `modstaller/apple/`, the JIT host in `modstaller/device/jit_host.js`, the
  JSON-RPC backend, or the Electron app in `gui/`)
- steps to reproduce, and what an attacker could achieve
- a proof of concept, if you have one

**Never include real credentials** - no Apple ID passwords, session tokens,
anisette data, certificates or private keys. Redact them from logs before
attaching anything.

## What happens next

This is a volunteer project, so these are goals rather than guarantees:

- **Acknowledgement** within 7 days.
- **Assessment** - whether we can reproduce it and how severe it is - within
  14 days, with updates as we go.
- **Fix and release** as soon as practical; critical issues get priority
  over everything else.
- **Disclosure**: once a fix is released, we publish a GitHub Security
  Advisory and credit you by name or handle - unless you prefer to stay
  anonymous. Please give us a reasonable window (90 days by default) before
  disclosing details yourself.

## Scope

**In scope** - issues in ModStaller's own code, for example:

- leaking or insecurely storing the Apple session, certificates, private keys
  or anisette data
- the Apple password being stored, logged or transmitted in clear text
- TLS verification being bypassable when talking to Apple
- a way for an app's JIT extension script to escape its QuickJS context or
  reach beyond the debugger commands for its own process
- the Electron interface executing untrusted content, or its bridge
  (`gui/electron/preload.cjs`) being abusable
- IPA handling that lets a crafted IPA write outside its working directory
  or execute code on the host
- supply-chain problems in how releases are built or updated

**Out of scope:**

- vulnerabilities in dependencies such as pymobiledevice3, zsign, anisette,
  QuickJS or Electron - please report those upstream (a heads-up to us is
  still welcome if ModStaller is affected)
- Apple's services, iOS itself, or the limits Apple imposes on free
  developer accounts
- attacks that require an already compromised computer or an unlocked,
  trusted device in the attacker's hands
- IPAs from untrusted sources doing what apps do - ModStaller signs and
  installs what you give it; judging an app is up to you

## Safe harbor

We will not pursue legal action against anyone who researches and reports
security issues in good faith under this policy: test only against your own
accounts and devices, avoid harming other users or Apple's services, and
give us a chance to fix the issue before going public.
