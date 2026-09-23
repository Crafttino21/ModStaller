#!/usr/bin/env bash
# Baut die AppImage: dist/ModStaller-<version>-x86_64.AppImage
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

echo "==> zsign"
docker run --rm -v "$ROOT:/src:ro" -v "$OUT:/out" "$IMAGE" \
  bash -c "bash /src/packaging/build-zsign.sh && chown -R $(id -u):$(id -g) /out/bin"

echo "==> Oberflaeche + AppImage"
# install.js holt die Electron-Binary nach, die npm ci hier nicht mitbringt -
# sonst ginge danach "npm run dev" nicht mehr.
BUILD_GUI='npm ci --no-audit --no-fund && node node_modules/electron/install.js && npm run dist'
if command -v npm >/dev/null; then
  (cd "$ROOT/gui" && ELECTRON_BUILDER_CACHE="$OUT/cache" bash -c "$BUILD_GUI")
else
  docker run --rm "${USER_ARGS[@]}" -v "$ROOT:/src" -w /src/gui \
    -e ELECTRON_BUILDER_CACHE=/src/packaging/out/cache \
    -e ELECTRON_CACHE=/src/packaging/out/cache \
    node:22 bash -c "$BUILD_GUI"
fi

echo
ls -lh "$ROOT"/dist/*.AppImage
