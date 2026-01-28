@echo off
setlocal enabledelayedexpansion

echo === SSH Connector Windows Build ===

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set BUILD_DIR=%PROJECT_DIR%\build
set BUILD_TYPE=%1
if "%BUILD_TYPE%"=="" set BUILD_TYPE=Release

echo Project: %PROJECT_DIR%
echo Build type: %BUILD_TYPE%

:: Check for vcpkg
echo.
echo Checking for vcpkg...
if not defined VCPKG_ROOT (
    if exist C:\vcpkg\vcpkg.exe (
        set VCPKG_ROOT=C:\vcpkg
    ) else if exist %USERPROFILE%\vcpkg\vcpkg.exe (
        set VCPKG_ROOT=%USERPROFILE%\vcpkg
    ) else (
        echo Error: vcpkg not found. Please install vcpkg:
        echo   git clone https://github.com/Microsoft/vcpkg.git
        echo   cd vcpkg ^&^& bootstrap-vcpkg.bat
        echo   set VCPKG_ROOT=path\to\vcpkg
        exit /b 1
    )
)
echo Using vcpkg at: %VCPKG_ROOT%

:: Install dependencies via vcpkg
echo.
echo Installing dependencies via vcpkg...
%VCPKG_ROOT%\vcpkg install libssh:x64-windows nlohmann-json:x64-windows

:: Check for Qt
echo.
echo Checking for Qt...
if not defined Qt6_DIR (
    :: Try common Qt installation paths
    for %%Q in (
        "C:\Qt\6.6.0\msvc2019_64"
        "C:\Qt\6.5.0\msvc2019_64"
        "C:\Qt\6.4.0\msvc2019_64"
        "%USERPROFILE%\Qt\6.6.0\msvc2019_64"
    ) do (
        if exist %%Q\lib\cmake\Qt6 (
            set Qt6_DIR=%%Q\lib\cmake\Qt6
            goto :qt_found
        )
    )
    echo Error: Qt6 not found. Please install Qt6 and set Qt6_DIR environment variable.
    echo   Download from: https://www.qt.io/download
    exit /b 1
)
:qt_found
echo Using Qt at: %Qt6_DIR%

:: Clean and create build directory
echo.
echo Preparing build directory...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"
cd /d "%BUILD_DIR%"

:: Configure
echo.
echo Configuring...
cmake .. ^
    -DCMAKE_BUILD_TYPE=%BUILD_TYPE% ^
    -DCMAKE_TOOLCHAIN_FILE=%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake ^
    -DCMAKE_PREFIX_PATH=%Qt6_DIR%\..\..\..

if errorlevel 1 (
    echo Configuration failed!
    exit /b 1
)

:: Build
echo.
echo Building...
cmake --build . --config %BUILD_TYPE% --parallel

if errorlevel 1 (
    echo Build failed!
    exit /b 1
)

:: Deploy Qt DLLs
echo.
echo Deploying Qt runtime...
set EXE_DIR=%BUILD_DIR%\%BUILD_TYPE%
if exist "%EXE_DIR%\ssh-connector.exe" (
    %Qt6_DIR%\..\..\..\bin\windeployqt.exe "%EXE_DIR%\ssh-connector.exe"
)

:: Output
echo.
echo === Build Complete ===
echo Executable: %EXE_DIR%\ssh-connector.exe
echo.
echo To run: %EXE_DIR%\ssh-connector.exe

endlocal
