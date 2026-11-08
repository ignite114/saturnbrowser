@echo off
rem Saturn dev build (out\Dev): regenerates args.gn from saturn\dev.gn, runs gn gen
rem and builds the "chrome" target. Output goes to saturn_dev\build-dev.log.
rem Usage: dev-build.cmd [extra ninja targets...]
rem Watch:  powershell -ExecutionPolicy Bypass -File watch-build.ps1 -Log build-dev.log
setlocal
set "ROOT=%~dp0"
set "SRC=%ROOT%ungoogled-chromium-windows\build\src"
set "OUT=%SRC%\out\Dev"
set "LOG=%ROOT%build-dev.log"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"

set "PATH=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer;%PATH%"
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -no_logo
where cl >nul 2>&1 || (echo VsDevCmd failed: cl.exe not on PATH & exit /b 1)
set DEPOT_TOOLS_WIN_TOOLCHAIN=0

rem V8 metagen needs gn.exe in buildtools (ungoogled only puts it in out\Default).
if not exist "%SRC%\buildtools\win\gn.exe" copy /y "%SRC%\out\Default\gn.exe" "%SRC%\buildtools\win\gn.exe" >nul

if not exist "%OUT%" mkdir "%OUT%"
for /f "delims=" %%P in ('python -c "import clang,os;print(os.path.dirname(os.path.dirname(clang.__file__)).replace(chr(92),'/'))"') do set "CLANG_PY=%%P"
set "LIBCLANG=%SRC:\=/%/third_party/llvm-build/Release+Asserts/bin/libclang.dll"
(
  type "%ROOT%saturn\dev.gn"
  echo.
  echo v8_metagen_libclang_so = "%LIBCLANG%"
  echo v8_metagen_libclang_bindings_dir = "%CLANG_PY%"
) > "%OUT%\args.gn.new"
rem Only replace args.gn when it changed, so gn does not force a full re-check.
fc /b "%OUT%\args.gn.new" "%OUT%\args.gn" >nul 2>&1 && del "%OUT%\args.gn.new" || move /y "%OUT%\args.gn.new" "%OUT%\args.gn" >nul

cd /d "%SRC%"
set "TARGETS=chrome %*"
echo [saturn] gn gen out\Dev > "%LOG%"
"%SRC%\buildtools\win\gn.exe" gen out\Dev --fail-on-unused-args >> "%LOG%" 2>&1 || (echo FAILED: gn gen >> "%LOG%" & exit /b 1)
echo [saturn] ninja -C out\Dev %TARGETS% >> "%LOG%"
"%SRC%\third_party\ninja\ninja.exe" -C out\Dev %TARGETS% >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
echo [saturn] ninja exit code %RC% >> "%LOG%"
exit /b %RC%
