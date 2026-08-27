@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
set "ROOT=%CD%"
set "SOLUTION=%ROOT%\KisKospi200Bridge.sln"
set "PROJECT_DIR=%ROOT%\KisKospi200Bridge"
set "RELEASE_DIR=%PROJECT_DIR%\bin\x86\Release"
set "TARGET_EXE=%ROOT%\KisKospi200Bridge.exe"
set "MSBUILD_EXE="
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"

if /i "%~1"=="--ensure" (
    if exist "%TARGET_EXE%" (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe=Get-Item -LiteralPath '%TARGET_EXE%'; $src=Get-ChildItem -LiteralPath '%PROJECT_DIR%' -Recurse -File | Where-Object { $_.Extension -in '.cs','.csproj','.resx','.config','.manifest','.ico' }; if(($src | Measure-Object LastWriteTimeUtc -Maximum).Maximum -le $exe.LastWriteTimeUtc){exit 0}else{exit 1}" >nul 2>nul
        if not errorlevel 1 (
            if exist "%ROOT%\AxInterop.ITGExpertCtlLib.dll" if exist "%ROOT%\Interop.ITGExpertCtlLib.dll" if exist "%ROOT%\KisKospi200Bridge.exe.config" (
                echo [OK]    KIS Bridge root runtime is up to date.
                exit /b 0
            )
        )
    )
)

echo [BUILD] KIS KOSPI200 Bridge Release x86
echo [INFO]  Solution: %SOLUTION%
echo [INFO]  Searching for MSBuild...

for /f "delims=" %%I in ('where msbuild 2^>nul') do if not defined MSBUILD_EXE set "MSBUILD_EXE=%%I"

if not defined MSBUILD_EXE (
    if exist "!VSWHERE!" (
        echo [INFO]  vswhere: !VSWHERE!
        for /f "usebackq delims=" %%I in (`"!VSWHERE!" -latest -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe 2^>nul`) do if not defined MSBUILD_EXE set "MSBUILD_EXE=%%I"
    ) else (
        echo [INFO]  vswhere.exe not found at: !VSWHERE!
    )
)

if not defined MSBUILD_EXE (
    for %%E in (Community Professional Enterprise BuildTools) do (
        if not defined MSBUILD_EXE if exist "%ProgramFiles%\Microsoft Visual Studio\2022\%%E\MSBuild\Current\Bin\MSBuild.exe" set "MSBUILD_EXE=%ProgramFiles%\Microsoft Visual Studio\2022\%%E\MSBuild\Current\Bin\MSBuild.exe"
        if not defined MSBUILD_EXE if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2022\%%E\MSBuild\Current\Bin\MSBuild.exe" set "MSBUILD_EXE=%ProgramFiles(x86)%\Microsoft Visual Studio\2022\%%E\MSBuild\Current\Bin\MSBuild.exe"
    )
)

if not defined MSBUILD_EXE (
    echo [ERROR] MSBuild was not found.
    echo [ERROR] Checked PATH, vswhere, and Visual Studio 2022 default install paths.
    echo [ACTION] Install Visual Studio 2022 or Build Tools 2022 with '.NET desktop development'.
    echo [ACTION] Then run build-kis-bridge-release.bat again and review the MSBuild output if it still fails.
    exit /b 1
)

echo [OK]    MSBuild: !MSBUILD_EXE!
echo [INFO]  Removing Windows download blocking from Bridge source files...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; Get-Item -LiteralPath '%SOLUTION%' | Unblock-File; Get-ChildItem -LiteralPath '%PROJECT_DIR%' -Recurse -File | Unblock-File; exit 0"
if errorlevel 1 (
    echo [WARN]  Could not fully remove Windows file blocking. Build will still be attempted.
) else (
    echo [OK]    Bridge source files are unblocked.
)
echo [INFO]  Building Release^|x86...
set "VSLANG=1033"

"!MSBUILD_EXE!" "%SOLUTION%" /t:Build /m /p:Configuration=Release /p:Platform=x86 /p:PreferredUILang=en-US /nologo /verbosity:quiet /clp:ErrorsOnly
if errorlevel 1 (
    echo [ERROR] KIS Bridge build failed.
    echo [ACTION] The MSBuild errors above are recorded in start-local-server.log.
    exit /b 1
)

echo [OK]    KIS Bridge build succeeded.

rem The project has an AfterTargets=Build deployment target. Copy manually as a fallback.
if not exist "%TARGET_EXE%" if exist "%RELEASE_DIR%\KisKospi200Bridge.exe" (
    echo [INFO]  Root deployment target did not create the EXE. Applying fallback copy.
    copy /y "%RELEASE_DIR%\KisKospi200Bridge.exe" "%TARGET_EXE%" >nul
    if exist "%RELEASE_DIR%\KisKospi200Bridge.exe.config" copy /y "%RELEASE_DIR%\KisKospi200Bridge.exe.config" "%ROOT%\KisKospi200Bridge.exe.config" >nul
    if exist "%RELEASE_DIR%\AxInterop.ITGExpertCtlLib.dll" copy /y "%RELEASE_DIR%\AxInterop.ITGExpertCtlLib.dll" "%ROOT%\AxInterop.ITGExpertCtlLib.dll" >nul
    if exist "%RELEASE_DIR%\Interop.ITGExpertCtlLib.dll" copy /y "%RELEASE_DIR%\Interop.ITGExpertCtlLib.dll" "%ROOT%\Interop.ITGExpertCtlLib.dll" >nul
)

if not exist "%TARGET_EXE%" (
    echo [ERROR] Build completed but root deployment EXE was not created.
    echo [ERROR] Expected: %TARGET_EXE%
    echo [INFO]  Release output folder: %RELEASE_DIR%
    exit /b 1
)

if not exist "%ROOT%\KisKospi200Bridge.exe.config" (
    echo [ERROR] Missing runtime file: KisKospi200Bridge.exe.config
    exit /b 1
)
if not exist "%ROOT%\AxInterop.ITGExpertCtlLib.dll" (
    echo [ERROR] Missing runtime file: AxInterop.ITGExpertCtlLib.dll
    exit /b 1
)
if not exist "%ROOT%\Interop.ITGExpertCtlLib.dll" (
    echo [ERROR] Missing runtime file: Interop.ITGExpertCtlLib.dll
    exit /b 1
)

echo [OK]    %TARGET_EXE%
echo [OK]    KIS Bridge runtime deployed to market-ai root.
exit /b 0
