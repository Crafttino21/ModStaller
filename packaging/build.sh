#!/usr/bin/env bash
# Baut die AppImages:
#   dist/ModStaller-<version>-x86_64.AppImage         portabel, aktualisiert sich selbst
#   dist/ModStaller-Setup-<version>-x86_64.AppImage   installiert nach ~/.local
#
# Braucht nur Docker. Backend und zsign entstehen in einem Debian-11-
# Container (alte glibc = laeuft auf moeglichst vielen Distros), die
# Oberflaeche in einem Node-Container - oder mit lokalem npm, falls da.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/packaging/out"
IMAGE=modstaller-builder
USER_ARGS=(-u "$(id -u):$(id -g)" -e HOME=/tmp)

mkdir -p "$OUT/cache"

echo "==> Builder-Image"
docker build -q -t "$IMAGE" "$ROOT/packaging" >/dev/null

echo "==> Python-Backend (PyInstaller)"
# Als root im Container (pip install), Ergebnis danach dem Nutzer uebergeben.
docker run --rm -v "$ROOT:/src:ro" -v "$OUT:/out" "$IMAGE" \
  bash -c "bash /src/packaging/build-backend.sh && chown -R $(id -u):$(id -g) /out/backend"

# Derselbe Rauchtest wie in der Windows-Pipeline: dasselbe Protokoll, das die
# Oberflaeche spricht, inklusive "doctor" - dem einzigen Kommando, das
# pymobiledevice3, anisette, unicorn und cryptography wirklich anfasst.
echo "==> Backend pruefen"
python3 "$ROOT/packaging/smoke_backend.py" "$OUT/backend/modstaller-backend"

echo "==> zsign"
docker run --rm -v "$ROOT:/src:ro" -v "$OUT:/out" "$IMAGE" \
  bash -c "bash /src/packaging/build-zsign.sh && chown -R $(id -u):$(id -g) /out/bin"

echo "==> Oberflaeche + AppImage"
# install.js holt die Electron-Binary nach, die npm ci hier nicht mitbringt -
# sonst ginge danach "npm run dev" nicht mehr.
# Danach dieselbe App noch einmal als Setup (modstallerVariant=setup) - in
# einen eigenen Ordner, damit ihre latest-linux.yml nicht die der portablen
# AppImage ueberschreibt.
BUILD_GUI='npm ci --no-audit --no-fund && node node_modules/electron/install.js && npm run dist && npm run dist:setup'
if command -v npm >/dev/null; then
  (cd "$ROOT/gui" && ELECTRON_BUILDER_CACHE="$OUT/cache" bash -c "$BUILD_GUI")
else
  docker run --rm "${USER_ARGS[@]}" -v "$ROOT:/src" -w /src/gui \
    -e ELECTRON_BUILDER_CACHE=/src/packaging/out/cache \
    -e ELECTRON_CACHE=/src/packaging/out/cache \
    node:22 bash -c "$BUILD_GUI"
fi

# Setup-AppImage und ihre Update-Metadaten neben die portable legen. Die
# installierte Variante findet ihre Updates ueber latest-linux-setup.yml.
SETUP_OUT="$ROOT/dist/setup-build"
rm -f "$ROOT"/dist/ModStaller-Setup-*.AppImage
cp "$SETUP_OUT"/ModStaller-Setup-*.AppImage "$ROOT/dist/"
cp "$SETUP_OUT/latest-linux.yml" "$ROOT/dist/latest-linux-setup.yml"

echo
ls -lh "$ROOT"/dist/*.AppImage
