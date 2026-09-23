#!/usr/bin/env bash
# Neue Version veroeffentlichen.
#
#   ./release.sh 0.2.0          Version setzen, Commit + Tag, pushen
#   ./release.sh 0.3.0-beta.1   Vorabversion (nur fuer Beta-Nutzer)
#
# Den Rest macht GitHub: .github/workflows/release.yml testet, baut die
# AppImage und legt die Release an. Installierte Apps finden sie von selbst.
set -euo pipefail

cd "$(dirname "$0")"
VERSION=${1:-}
TAG="v$VERSION"

red() { printf '\033[31m%s\033[0m\n' "$*" >&2; }

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]]; then
  red "Aufruf: ./release.sh X.Y.Z   (aktuell: $(python3 -c 'import json;print(json.load(open("gui/package.json"))["version"])'))"
  exit 2
fi
if [ -n "$(git status --porcelain)" ]; then
  red "Es gibt uncommittete Aenderungen - erst committen oder verwerfen."
  git status --short >&2
  exit 1
fi
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  red "Tag $TAG gibt es schon."
  exit 1
fi
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git fetch -q origin "$BRANCH" 2>/dev/null || true
if [ -n "$(git rev-list HEAD..origin/"$BRANCH" 2>/dev/null)" ]; then
  red "origin/$BRANCH ist weiter als dein Stand - erst: git pull"
  exit 1
fi

python3 packaging/set-version.py "$VERSION"
git add gui/package.json gui/package-lock.json pyproject.toml
git commit -q -m "Release $TAG"
git tag -a "$TAG" -m "ModStaller $VERSION"
echo "Commit und Tag $TAG angelegt (Branch $BRANCH)."

read -r -p "Jetzt zu GitHub pushen und die Release bauen lassen? [j/N] " answer
if [[ "$answer" =~ ^[jJyY]$ ]]; then
  git push -q origin "$BRANCH"
  git push -q origin "$TAG"
  echo "Gepusht. Fortschritt: https://github.com/Crafttino21/ModStaller/actions"
else
  echo "Nicht gepusht. Spaeter:  git push origin $BRANCH && git push origin $TAG"
  echo "Rueckgaengig:           git tag -d $TAG && git reset --hard HEAD~1"
fi
