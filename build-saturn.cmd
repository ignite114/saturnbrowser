@echo off
rem ===========================================================================
rem  Saturn RELEASE build from a fresh ungoogled-chromium-windows tag.
rem
rem  Usage:   build-saturn.cmd <ungoogled-windows-tag>      e.g. 158.0.1234.56-1.1
rem  Result:  release\<tag>\build\src\out\Default\chrome.exe (+ mini_installer.exe)
rem  Log:     saturn_dev\build-release.log
rem  Watch:   powershell -ExecutionPolicy Bypass -File watch-build.ps1 -Log build-release.log
rem
rem  Steps: clone the tag -> ungoogled build.py (download, prune, ungoogled
rem  patches) -> git base commit + Saturn patches (saturn\patches\series) +
rem  string rebrand -> gn gen -> copy gn.exe to buildtools -> ninja.
rem  If a Saturn patch fails to apply, the build stops; see README.md
rem  "Monthly update" for how to refresh the patch.
rem ===========================================================================
setlocal
if "%~1"=="" (echo Usage: %~nx0 ^<ungoogled-chromium-windows tag^> & exit /b 1)
set "TAG=%~1"
set "ROOT=%~dp0"
set "REL=%ROOT%release\%TAG%"
set "LOG=%ROOT%build-release.log"
set "CACHE=%ROOT%ungoogled-chromium-windows\build\download_cache"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"

if exist "%REL%\build\src\BUILD.gn" (
  echo %REL% already has a source tree. Delete that folder to start fresh.
  exit /b 1
)

echo [saturn] release build of %TAG% started %DATE% %TIME% > "%LOG%"

if not exist "%REL%\build.py" (
  git clone --quiet --depth 1 --recurse-submodules --shallow-submodules --branch "%TAG%" ^
    https://github.com/ungoogled-software/ungoogled-chromium-windows.git "%REL%" >> "%LOG%" 2>&1 ^
    || (echo FAILED: git clone of %TAG% >> "%LOG%" & exit /b 1)
)

rem Share the (multi-GB) download cache between trees.
if not exist "%CACHE%" mkdir "%CACHE%"
if not exist "%REL%\build" mkdir "%REL%\build"
if not exist "%REL%\build\download_cache" mklink /J "%REL%\build\download_cache" "%CACHE%" >> "%LOG%"

set "PATH=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer;%PATH%"
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -no_logo
where cl >nul 2>&1 || (echo VsDevCmd failed: cl.exe not on PATH & exit /b 1)
set DEPOT_TOOLS_WIN_TOOLCHAIN=0

cd /d "%REL%"
python "%ROOT%saturn\scripts\build_saturn.py" --tarball >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
echo [saturn] finished with exit code %RC% at %DATE% %TIME% >> "%LOG%"
if %RC%==0 echo [saturn] output: %REL%\build\src\out\Default\chrome.exe >> "%LOG%"
exit /b %RC%
