#!/usr/bin/env bash
# Laeuft IM Builder-Container. Baut das Python-Backend als eigenstaendiges
# Programm (PyInstaller, onedir) nach $OUT/backend.
set -euo pipefail
SRC=${SRC:-/src}
OUT=${OUT:-/out}
WORK=$(mktemp -d)

# Kopie statt direkt aus /src: pip wuerde sonst egg-info und build/ ins
# Repository schreiben - als root-Dateien des Containers.
cp -r "$SRC/modstaller" "$SRC/pyproject.toml" "$SRC/README.md" "$WORK/"
pip install --no-cache-dir "$WORK"

cat > "$WORK/entry.py" <<'PY'
import sys
from modstaller.cli import main
sys.exit(main())
PY

rm -rf "$OUT/backend"
pyinstaller --noconfirm --clean --onedir \
  --name modstaller-backend \
  --distpath "$WORK/dist" --workpath "$WORK/build" --specpath "$WORK" \
  --collect-submodules modstaller \
  --collect-data modstaller \
  --collect-all pymobiledevice3 \
  --collect-all anisette \
  --collect-all unicorn \
  --copy-metadata modstaller \
  --copy-metadata pymobiledevice3 \
  --copy-metadata anisette \
  --copy-metadata cryptography \
  "$WORK/entry.py"

mkdir -p "$OUT"
mv "$WORK/dist/modstaller-backend" "$OUT/backend"
echo "Backend: $OUT/backend"
