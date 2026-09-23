#!/usr/bin/env bash
# Laeuft IM Builder-Container. Baut zsign mit statisch gelinktem OpenSSL,
# damit die AppImage nicht von der OpenSSL-Version des Hosts abhaengt.
set -euo pipefail
OUT=${OUT:-/out}
ZSIGN_REF=${ZSIGN_REF:-v1.1.1}
WORK=$(mktemp -d)

git clone -q --depth 1 --branch "$ZSIGN_REF" https://github.com/zhlynn/zsign.git "$WORK/zsign"
make -C "$WORK/zsign/build/linux" -j"$(nproc)" \
  OPENSSL_LIB="-Wl,-Bstatic -lcrypto -Wl,-Bdynamic -ldl -lpthread"

mkdir -p "$OUT/bin"
install -m 755 "$WORK/zsign/bin/zsign" "$OUT/bin/zsign"
strip "$OUT/bin/zsign"

# Nur Bibliotheken, die jedes Linux hat, duerfen uebrig bleiben.
if ldd "$OUT/bin/zsign" | grep -vE 'linux-vdso|libc\.so|libm\.so|libdl\.so|libpthread\.so|libstdc\+\+\.so|libgcc_s\.so|ld-linux'; then
  echo "zsign haengt an Bibliotheken, die nicht ueberall vorhanden sind (siehe oben)." >&2
  exit 1
fi
echo "zsign: $OUT/bin/zsign"
