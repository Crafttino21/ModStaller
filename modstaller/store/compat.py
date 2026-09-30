"""Does a store app fit the chosen device?

The same rules as before installing (``pipeline.incompatibility``), applied
ahead of time so the store can hide what would fail anyway:

* the platform: Apple TV only takes tvOS apps; the Vision Pro takes its own
  and iPhone/iPad apps ("Designed for iPad");
* the device family: iPad-only apps do not start on an iPhone or iPod touch;
* the OS version: at least ``MinimumOSVersion`` (and at most the source's
  ``maxOSVersion``, where it gives one).

What the IPA itself says (``probe``) wins over what the source says. Three
answers: True, False - and None when nothing is known yet; the store shows
those, marked.
"""

from __future__ import annotations

from .updates import _numbers

IPHONE, IPAD, TV, VISION = 1, 2, 3, 7


def _at_least(version: str, minimum: str) -> bool:
    a, b = _numbers(version), _numbers(minimum)
    if not a or not b:
        return True
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) >= b + (0,) * (width - len(b))


def compatible(app, facts: dict | None, device: dict | None) -> bool | None:
    """``device``: ``{platform, formFactor, osVersion}`` of the chosen device."""
    if not device:
        return True
    platform = device.get("platform") or "ios"
    ipad = device.get("formFactor") == "ipad"
    os_version = device.get("osVersion") or ""
    known = facts is not None and not facts.get("error")

    app_platform = facts.get("platform") if known else None
    if app_platform is None and platform == "tvos":
        # Sources are iOS by nature - a tvOS build only shows by its plist.
        return None
    app_platform = app_platform or "ios"

    if app_platform != platform:
        if not (platform == "xros" and app_platform == "ios"):
            return False
    families = set(facts.get("families") or []) if known else set()
    if platform == "ios" and families == {IPAD} and not ipad:
        return False

    # The OS version only compares within one platform - visionOS 2 says
    # nothing about an iOS app's minimum.
    if app_platform == platform:
        minimum = (facts.get("minOs") if known else "") or getattr(app, "min_os", "")
        if minimum and not _at_least(os_version, minimum):
            return False
        maximum = getattr(app, "max_os", "")
        if maximum and os_version and not _at_least(maximum, os_version):
            return False
    return True if known else None
