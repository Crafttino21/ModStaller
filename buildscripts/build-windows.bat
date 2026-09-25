@echo off
rem  Baut den Windows-Installer: dist\ModStaller-Setup-<version>.exe
rem
rem    buildscripts\build-windows.bat                   alles bauen
rem    buildscripts\build-windows.bat --dir             nur dist\win-unpacked (schneller, zum Testen)
rem    buildscripts\build-windows.bat --rebuild-zsign   zsign.exe neu bauen statt wiederverwenden
rem    buildscripts\build-windows.bat --run             danach starten
rem
rem  Braucht Python 3.12+, Node 22+ und - nur fuer zsign - Visual Studio 2022
rem  mit C++-Werkzeugen. Ein einmal gebautes zsign.exe bleibt liegen und wird
rem  wiederverwendet; ohne Visual Studio kann man es auch aus der CLI-Zip einer
rem  Release nach packaging\out\bin\ legen.
rem
rem  Alles mitschreiben:  buildscripts\build-windows.bat > build.log 2>&1
rem
rem  Das Gegenstueck fuer Linux ist build-appimage.sh daneben. Dieselben
rem  Schritte laufen in .github/workflows/release.yml - wer hier etwas
rem  aendert, sollte dort nachsehen.

setlocal EnableExtensions EnableDelayedExpansion

for %%i in ("%~dp0..") do set "ROOT=%%~fi"
set "OUT=%ROOT%\packaging\out"
set "BUILDENV=%OUT%\buildenv"
set "VENVPY=%BUILDENV%\Scripts\python.exe"
set "ZSIGN=%OUT%\bin\zsign.exe"
rem  Dieselbe Version wie in der Pipeline (ZSIGN_REF in release.yml).
set "ZSIGN_REF=v1.1.1"
rem  Ausserhalb jedes Klammerblocks: der Name enthaelt selbst Klammern.
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"

set "DIRONLY="
set "REBUILD_ZSIGN="
set "RUNAFTER="

:args
if "%~1"=="" goto args_done
set "MATCHED="
if /i "%~1"=="--dir" (set "DIRONLY=1" & set "MATCHED=1")
if /i "%~1"=="--rebuild-zsign" (set "REBUILD_ZSIGN=1" & set "MATCHED=1")
if /i "%~1"=="--run" (set "RUNAFTER=1" & set "MATCHED=1")
if /i "%~1"=="--help" goto usage
if /i "%~1"=="-h" goto usage
if not defined MATCHED (
    echo Unbekannte Option: %~1
    goto usage
)
shift
goto args
:args_done

rem -- Voraussetzungen ---------------------------------------------------------

call :need python "Python 3.12+ von python.org installieren." || goto fail
call :need npm "Node 22+ von nodejs.org installieren." || goto fail

python -c "import sys; sys.exit(sys.version_info[:2] < (3, 12))"
if errorlevel 1 (
    echo Das gefundene Python ist zu alt - ModStaller braucht 3.12 oder neuer.
    goto fail
)

echo ModStaller fuer Windows bauen - das dauert beim ersten Mal ein paar Minuten.
echo.

rem -- Build-Umgebung ----------------------------------------------------------
rem
rem  Eigenes venv statt des System-Python: PyInstaller landet nicht im
rem  Entwicklungs-venv, und der Stand ist reproduzierbar. Bewusst "pip install ."
rem  und nicht "-e .": bei einer editierbaren Installation findet
rem  "--collect-submodules modstaller" die Unterpakete nicht, und das gebaute
rem  Programm bricht beim Start mit ModuleNotFoundError ab.

echo ==^> Build-Umgebung
if not exist "%VENVPY%" (
    python -m venv "%BUILDENV%" || goto fail
)
"%VENVPY%" -m pip install --quiet --upgrade pip
"%VENVPY%" -m pip install --quiet "%ROOT%" "pyinstaller>=6.10" || goto fail
rem  Noch einmal nur ModStaller, erzwungen: pip sieht sonst die unveraenderte
rem  Versionsnummer und laesst den Stand von gestern im venv stehen.
"%VENVPY%" -m pip install --quiet --force-reinstall --no-deps "%ROOT%" || goto fail

rem -- zsign -------------------------------------------------------------------

if exist "%ZSIGN%" if not defined REBUILD_ZSIGN (
    echo ==^> zsign ^(vorhanden, wird wiederverwendet^)
    goto zsign_done
)

echo ==^> zsign bauen ^(%ZSIGN_REF%^)
call :need git "Git for Windows installieren." || goto fail
if not exist "%VSWHERE%" (
    echo Visual Studio 2022 mit C++-Werkzeugen fehlt - zsign braucht das Toolset v143.
    echo Alternative: zsign.exe aus der CLI-Zip einer Release nach
    echo   %OUT%\bin\
    echo legen und erneut ohne --rebuild-zsign starten.
    goto fail
)

set "MSBUILD="
for /f "usebackq delims=" %%i in (`"%VSWHERE%" -latest -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe"`) do (
    if not defined MSBUILD set "MSBUILD=%%i"
)
if not defined MSBUILD (
    echo MSBuild nicht gefunden.
    goto fail
)

set "ZSRC=%TEMP%\modstaller-zsign"
if exist "%ZSRC%" rmdir /s /q "%ZSRC%"
git clone -q --depth 1 --branch %ZSIGN_REF% https://github.com/zhlynn/zsign.git "%ZSRC%" || goto fail
"%MSBUILD%" "%ZSRC%\build\windows\vs2022\zsign.sln" -p:Configuration=Release -p:Platform=x64 -m -nologo -v:minimal || goto fail

set "ZBUILT="
for /r "%ZSRC%\build\windows" %%f in (zsign.exe) do (
    set "CAND=%%~ff"
    echo !CAND! | findstr /i /c:"\Release\" >nul
    if not errorlevel 1 if not defined ZBUILT set "ZBUILT=!CAND!"
)
if not defined ZBUILT (
    echo zsign.exe nach dem Build nicht gefunden.
    goto fail
)
if not exist "%OUT%\bin" mkdir "%OUT%\bin"
copy /y "!ZBUILT!" "%ZSIGN%" >nul || goto fail
rmdir /s /q "%ZSRC%"
:zsign_done

rem -- Backend + CLI -----------------------------------------------------------

echo ==^> Python-Backend und CLI ^(PyInstaller^)
"%VENVPY%" "%ROOT%\packaging\build_backend.py" --out "%OUT%" --cli || goto fail

rem -- Rauchtest ---------------------------------------------------------------
rem
rem  "doctor" ist das einzige Kommando, das pymobiledevice3, anisette, unicorn
rem  und cryptography wirklich anfasst - genau dort sassen die Windows-Fehler,
rem  die ein blosses "startet ohne Absturz" nicht sieht.

echo ==^> Backend pruefen
set "PATH=%OUT%\bin;%PATH%"
"%VENVPY%" "%ROOT%\packaging\smoke_backend.py" "%OUT%\backend\modstaller-backend.exe" || goto fail

rem -- Oberflaeche + Installer -------------------------------------------------
rem
rem  npm und npx sind .cmd-Dateien: ohne "call" endet dieses Skript nach dem
rem  ersten Aufruf, statt weiterzulaufen.

echo ==^> Oberflaeche und Installer ^(electron-builder^)
pushd "%ROOT%\gui" || goto fail
call npm ci --no-audit --no-fund || goto popfail
rem  install.js holt die Electron-Binary nach, die npm ci nicht mitbringt,
rem  wenn ELECTRON_SKIP_BINARY_DOWNLOAD einmal gesetzt war.
call node node_modules\electron\install.js
call npx vite build || goto popfail
if defined DIRONLY (
    call npx electron-builder --win --dir --publish never || goto popfail
) else (
    call npx electron-builder --win nsis --publish never || goto popfail
)
popd

rem -- Ergebnis ----------------------------------------------------------------

set "APP=%ROOT%\dist\win-unpacked\ModStaller.exe"
echo.
echo Fertig:
for %%f in ("%ROOT%\dist\ModStaller-Setup-*.exe") do echo   %%~ff  ^(%%~zf Bytes^)
if exist "%APP%" echo   %APP%

if defined RUNAFTER (
    if not exist "%APP%" (
        echo %APP% gibt es nicht.
        goto fail
    )
    echo.
    echo Starte ModStaller ...
    start "" "%APP%"
)
endlocal
exit /b 0

rem -- Hilfsziele --------------------------------------------------------------

:need
where %~1 >nul 2>nul
if errorlevel 1 (
    echo %~1 fehlt. %~2
    exit /b 1
)
exit /b 0

:usage
echo Baut den Windows-Installer: dist\ModStaller-Setup-^<version^>.exe
echo.
echo   buildscripts\build-windows.bat                   alles bauen
echo   buildscripts\build-windows.bat --dir             nur dist\win-unpacked
echo   buildscripts\build-windows.bat --rebuild-zsign   zsign.exe neu bauen
echo   buildscripts\build-windows.bat --run             danach starten
endlocal
exit /b 2

:popfail
popd
:fail
echo.
echo Build fehlgeschlagen.
endlocal
exit /b 1
