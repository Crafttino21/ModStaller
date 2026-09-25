#!/usr/bin/env bash
# Baut eine neue ModStaller-AppImage.
#
#   ./buildscripts/build-appimage.sh          bauen
#   ./buildscripts/build-appimage.sh --run    bauen und danach starten
#
# Braucht nur Docker. Das eigentliche Bauen erledigt packaging/build.sh;
# dieses Skript prueft vorher, ob alles bereitsteht, und haelt die lange
# Ausgabe in einer Log-Datei fest. Das Gegenstueck fuer Windows ist
# build-windows.bat daneben.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOG="$ROOT/packaging/out/build.log"
RUN_AFTER=0

for arg in "$@"; do
  case "$arg" in
    --run) RUN_AFTER=1 ;;
    -h|--help) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unbekannte Option: $arg (siehe --help)" >&2; exit 2 ;;
  esac
done

green() { printf '\033[32m%s\033[0m\n' "$*"; }
red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }

# -- Voraussetzungen ---------------------------------------------------------

if ! command -v docker >/dev/null; then
  red "Docker fehlt. Arch: sudo pacman -S docker && sudo systemctl enable --now docker"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  if ! systemctl is-active --quiet docker 2>/dev/null; then
    red "Der Docker-Dienst laeuft nicht. Starten mit: sudo systemctl start docker"
  else
    red "Kein Zugriff auf Docker. Einmalig: sudo usermod -aG docker $USER  (danach neu anmelden)"
  fi
  exit 1
fi

# -- Bauen -------------------------------------------------------------------

mkdir -p "$(dirname "$LOG")"
echo "ModStaller-AppImage wird gebaut - das dauert beim ersten Mal ein paar Minuten."
echo "Ausfuehrliches Log: $LOG"
echo

START=$(date +%s)
# Die Schritt-Ueberschriften von build.sh ("==> ...") live zeigen, den Rest ins Log.
if ! "$ROOT/packaging/build.sh" 2>&1 | tee "$LOG" | grep --line-buffered '^==>'; then
  echo
  red "Build fehlgeschlagen. Die letzten Zeilen aus dem Log:"
  tail -n 25 "$LOG" >&2
  exit 1
fi

APPIMAGE=$(ls -t "$ROOT"/dist/*.AppImage 2>/dev/null | head -n 1)
if [ -z "$APPIMAGE" ]; then
  red "Build lief durch, aber es liegt keine AppImage in dist/. Siehe $LOG"
  exit 1
fi

echo
green "Fertig in $(( $(date +%s) - START )) s:"
echo "  $APPIMAGE ($(du -h "$APPIMAGE" | cut -f1))"

if [ "$RUN_AFTER" = 1 ]; then
  echo
  echo "Starte ModStaller …"
  exec "$APPIMAGE"
fi
