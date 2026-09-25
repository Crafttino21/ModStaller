@echo off
rem  Neue Version veroeffentlichen.
rem
rem    release.bat 0.2.0          Version setzen, Commit + Tag, pushen
rem    release.bat 0.3.0-beta.1   Vorabversion (nur fuer Beta-Nutzer)
rem
rem  Den Rest macht GitHub: .github/workflows/release.yml testet, baut
rem  AppImage, Windows-Installer und CLI-Zip und legt die Release an.
rem  Installierte Apps finden sie von selbst.
rem
rem  Das Gegenstueck fuer Linux ist release.sh daneben - beide machen
rem  dasselbe in derselben Reihenfolge. Wer hier etwas aendert, sollte dort
rem  nachsehen.

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "VERSION=%~1"
set "TAG=v%VERSION%"

where git >nul 2>nul
if errorlevel 1 (
    echo git fehlt. Git for Windows installieren.
    exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
    echo python fehlt - wird fuer packaging\set-version.py gebraucht.
    exit /b 1
)

rem -- Versionsnummer -----------------------------------------------------
rem
rem  Batch kann keine regulaeren Ausdruecke, und Python steht ohnehin schon
rem  bereit. Dasselbe Muster wie in release.sh.

python -c "import re,sys; sys.exit(0 if re.fullmatch(r'\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?', sys.argv[1]) else 1)" "%VERSION%"
if errorlevel 1 goto usage

rem -- Nichts Unfertiges mitnehmen ----------------------------------------

set "DIRTY="
for /f "delims=" %%i in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo Es gibt uncommittete Aenderungen - erst committen oder verwerfen.
    git status --short
    exit /b 1
)

git rev-parse -q --verify "refs/tags/%TAG%" >nul 2>nul
if not errorlevel 1 (
    echo Tag %TAG% gibt es schon.
    exit /b 1
)

set "BRANCH="
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set "BRANCH=%%b"
if not defined BRANCH (
    echo Kein Branch gefunden - steht HEAD irgendwo losgeloest?
    exit /b 1
)

rem  Ein fehlgeschlagenes fetch ist kein Grund abzubrechen: offline soll man
rem  eine Release vorbereiten koennen. Nur wenn origin nachweislich weiter
rem  ist, waere der Tag am falschen Commit.
git fetch -q origin "%BRANCH%" 2>nul
set "AHEAD="
for /f "delims=" %%c in ('git rev-list HEAD..origin/%BRANCH% 2^>nul') do set "AHEAD=1"
if defined AHEAD (
    echo origin/%BRANCH% ist weiter als dein Stand - erst: git pull
    exit /b 1
)

rem -- Version setzen, committen, taggen ----------------------------------

python packaging\set-version.py "%VERSION%"
if errorlevel 1 goto fail
git add gui/package.json gui/package-lock.json pyproject.toml
if errorlevel 1 goto fail
git commit -q -m "Release %TAG%"
if errorlevel 1 goto fail
git tag -a "%TAG%" -m "ModStaller %VERSION%"
if errorlevel 1 goto fail
echo Commit und Tag %TAG% angelegt (Branch %BRANCH%).
echo.

set "ANSWER="
set /p "ANSWER=Jetzt zu GitHub pushen und die Release bauen lassen? [j/N] "
if /i "!ANSWER!"=="j" goto push
if /i "!ANSWER!"=="y" goto push

echo Nicht gepusht. Spaeter:  git push origin %BRANCH% ^&^& git push origin %TAG%
echo Rueckgaengig:           git tag -d %TAG% ^&^& git reset --hard HEAD~1
endlocal
exit /b 0

:push
git push -q origin "%BRANCH%"
if errorlevel 1 goto fail
git push -q origin "%TAG%"
if errorlevel 1 goto fail
echo Gepusht. Fortschritt: https://github.com/Crafttino21/ModStaller/actions
endlocal
exit /b 0

rem -- Hilfsziele ---------------------------------------------------------

:usage
set "CURRENT="
rem  usebackq mit Backticks: das Python-Schnipsel enthaelt selbst Hochkommas,
rem  die die uebliche 'Befehl'-Schreibweise vorzeitig beenden wuerden.
for /f "usebackq delims=" %%v in (`python -c "import json;print(json.load(open('gui/package.json'))['version'])" 2^>nul`) do set "CURRENT=%%v"
echo Aufruf: release.bat X.Y.Z
if defined CURRENT echo   aktuell: !CURRENT!
echo.
echo   release.bat 0.2.0          Version setzen, Commit + Tag, pushen
echo   release.bat 0.3.0-beta.1   Vorabversion (nur fuer Beta-Nutzer)
endlocal
exit /b 2

:fail
echo.
echo Abgebrochen.
endlocal
exit /b 1
