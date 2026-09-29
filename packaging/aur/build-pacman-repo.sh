#!/usr/bin/env bash
# Builds the pacman repository "modstaller" from a finished AppImage:
#
#   VERSION=1.3.2 GPG_KEY_ID=ABCD1234 packaging/aur/build-pacman-repo.sh <AppImage> <outdir>
#
# Result in <outdir> - uploaded next to the AppImage in every stable release,
# so https://github.com/Crafttino21/ModStaller/releases/latest/download is
# always the current repository:
#
#   modstaller-bin-<version>-1-x86_64.pkg.tar.zst (+ .sig)
#   modstaller.db, modstaller.files (+ .sig)      the repository database
#   modstaller-pacman.asc                         public key for pacman-key
#
# Runs on Arch (the CI uses the archlinux container) as a normal user -
# makepkg refuses root. The PKGBUILD is the one in modstaller-bin/, the AUR
# package; only pkgver and the checksum are filled in here. The AppImage is
# taken from disk, nothing is downloaded.
#
# GPG_KEY_ID must be a secret key in the caller's keyring *without a
# passphrase* (the CI imports it from a secret). Without GPG_KEY_ID the
# repository is built unsigned - only for local tests.
set -euo pipefail

APPIMAGE=$(realpath "${1:?AppImage fehlt}")
OUT=$(realpath -m "${2:?Zielordner fehlt}")
VERSION=${VERSION:?VERSION fehlt}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=modstaller

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/sources" "$OUT"

# PKGBUILD with this version and this AppImage's checksum.
sum=$(sha512sum "$APPIMAGE" | cut -d' ' -f1)
sed -E -e "s/^pkgver=.*/pkgver=${VERSION}/" -e "s/^pkgrel=.*/pkgrel=1/" \
       -e "s/^sha512sums=.*/sha512sums=('${sum}')/" \
       "$HERE/modstaller-bin/PKGBUILD" > "$WORK/PKGBUILD"
# makepkg finds the source in SRCDEST under its download name - no download.
cp "$APPIMAGE" "$WORK/sources/ModStaller-${VERSION}-x86_64.AppImage"

(cd "$WORK" && SRCDEST="$WORK/sources" PKGDEST="$OUT" makepkg -f --noconfirm --nodeps)
PKG=$(ls "$OUT"/modstaller-bin-"${VERSION}"-*-x86_64.pkg.tar.zst)

SIGN=()
if [ -n "${GPG_KEY_ID:-}" ]; then
  gpg --batch --yes --detach-sign --no-armor -u "$GPG_KEY_ID" "$PKG"
  SIGN=(--sign --key "$GPG_KEY_ID")
  gpg --batch --yes --armor --export "$GPG_KEY_ID" > "$OUT/modstaller-pacman.asc"
fi

# A fresh database with just this package: the repository only ever offers
# the current version (older ones stay in their own releases).
rm -f "$OUT/$REPO".{db,files}*
repo-add "${SIGN[@]}" "$OUT/$REPO.db.tar.gz" "$PKG"

# repo-add leaves modstaller.db as a symlink - release assets cannot be
# links, so real files under the names pacman asks for.
for f in db files; do
  for ext in "" .sig; do
    if [ -e "$OUT/$REPO.$f.tar.gz$ext" ]; then
      rm -f "$OUT/$REPO.$f$ext"
      cp "$OUT/$REPO.$f.tar.gz$ext" "$OUT/$REPO.$f$ext"
      rm -f "$OUT/$REPO.$f.tar.gz$ext"
    fi
  done
done
ls -la "$OUT"
