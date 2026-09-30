"""Apps that deserve a warning before they are installed.

Some sources - Quantum Source among the defaults - also list jailbreak tools
and exploits. They are legitimate in the sense that people use them on
purpose, but they attack the system itself: a failed run can mean a boot
loop, a restore, lost data. Such an entry gets a warning and a question
before it is installed.

Sources do not tag this themselves (Quantum has no categories), so the known
ones are listed by bundle ID, and anything that calls itself a jailbreak is
caught by name - also in sources the user adds.
"""

from __future__ import annotations

JAILBREAK = "jailbreak"
#: Uses a kernel/sandbox exploit to change the system, without a jailbreak.
EXPLOIT = "exploit"
#: A store for other apps, mostly cracked ones.
THIRD_PARTY_STORE = "store"

KNOWN: dict[str, str] = {
    "science.xnu.undecimus": JAILBREAK,                     # unc0ver
    "org.coolstar.odyssey": JAILBREAK,
    "org.coolstar.taurine": JAILBREAK,
    "org.coolstar.electra": JAILBREAK,
    "com.dry05.filzaescaped11-12": EXPLOIT,                  # Filza Escaped
    "com.worthdoingbadly.WDBRemoveThreeAppLimit": EXPLOIT,
    "com.ginsudev.WDBFontOverwrite": EXPLOIT,
    "it.ned.appdb-ios": THIRD_PARTY_STORE,                   # appdb client
}


def classify(bundle_id: str, name: str = "", subtitle: str = "", description: str = "") -> str:
    """The warning for an app - or empty."""
    kind = KNOWN.get(bundle_id) or KNOWN.get(bundle_id.lower(), "")
    if kind:
        return kind
    text = f"{name} {subtitle} {description}".lower()
    if "jailbreak" in text and "no jailbreak" not in text and "without jailbreak" not in text \
            and "jailbroken" not in text:
        return JAILBREAK
    return ""


#: Sources that carry such apps among many good ones - a note in the
#: sources list says so.
SOURCE_NOTES: dict[str, str] = {
    "https://quarksources.github.io/dist/quantumsource.min.json": JAILBREAK,
}
