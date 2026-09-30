"""Clearing what the store downloaded - except what installed apps need.

A downloaded IPA is the original a renewal signs again; it stays as long as
an installed app points to it (``InstallRecord.source_ipa``). Everything
else - older versions, apps removed since, the pictures - can go.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import config
from ..state import store
from . import images


def clear() -> dict:
    needed = set()
    for rec in store.all_installs():
        try:
            needed.add(Path(rec.source_ipa).resolve())
        except OSError:
            continue
    freed, removed = 0, 0
    root = config.IPA_CACHE_DIR
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.resolve() not in needed:
                freed += path.stat().st_size
                path.unlink(missing_ok=True)
                removed += 1
        for folder in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
            try:
                folder.rmdir()          # only if empty
            except OSError:
                pass
    if images.CACHE.is_dir():
        freed += sum(p.stat().st_size for p in images.CACHE.iterdir() if p.is_file())
        shutil.rmtree(images.CACHE, ignore_errors=True)
    return {"removedIpas": removed, "freedBytes": freed}
