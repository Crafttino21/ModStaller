#!/usr/bin/env bash
# Laeuft IM Builder-Container. Baut das Python-Backend als eigenstaendiges
# Programm nach $OUT/backend. Die PyInstaller-Parameter stehen in
# build_backend.py - dasselbe Skript baut unter Windows die .exe.
set -euo pipefail
SRC=${SRC:-/src}
OUT=${OUT:-/out}
WORK=$(mktemp -d)

# Kopie statt direkt aus /src: pip wuerde sonst egg-info und build/ ins
# Repository schreiben - als root-Dateien des Containers.
cp -r "$SRC/modstaller" "$SRC/pyproject.toml" "$SRC/README.md" "$WORK/"
pip install --no-cache-dir "$WORK"

python "$SRC/packaging/build_backend.py" --out "$OUT"
