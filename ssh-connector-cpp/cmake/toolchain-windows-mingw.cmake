# CMake Toolchain File for Cross-Compiling to Windows x64 using MinGW-w64
#
# Usage:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchain-windows-mingw.cmake \
#         -DQT_HOST_PATH=/opt/homebrew/opt/qt@6 ..
#
# Prerequisites:
#   - MinGW-w64 installed (brew install mingw-w64)
#   - Windows sysroot at /opt/mingw-sysroot with:
#     - zlib, OpenSSL, libssh cross-compiled
#   - Qt6 for Windows at /opt/qt6-windows (optional, for Qt6 builds)

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# MinGW-w64 toolchain
set(TOOLCHAIN_PREFIX x86_64-w64-mingw32)

# Find MinGW compilers (check both Homebrew locations)
find_program(MINGW_GCC ${TOOLCHAIN_PREFIX}-gcc
    PATHS /opt/homebrew/bin /usr/local/bin
    REQUIRED
)
find_program(MINGW_GXX ${TOOLCHAIN_PREFIX}-g++
    PATHS /opt/homebrew/bin /usr/local/bin
    REQUIRED
)
find_program(MINGW_WINDRES ${TOOLCHAIN_PREFIX}-windres
    PATHS /opt/homebrew/bin /usr/local/bin
    REQUIRED
)

set(CMAKE_C_COMPILER ${MINGW_GCC})
set(CMAKE_CXX_COMPILER ${MINGW_GXX})
set(CMAKE_RC_COMPILER ${MINGW_WINDRES})

# Sysroot paths
set(MINGW_SYSROOT "/opt/mingw-sysroot" CACHE PATH "Path to Windows cross-compile sysroot")
set(QT6_WINDOWS_PATH "/opt/qt6-windows" CACHE PATH "Path to Qt6 Windows installation")

# Search paths for libraries and headers
set(CMAKE_FIND_ROOT_PATH
    ${MINGW_SYSROOT}
    ${QT6_WINDOWS_PATH}
)

# Search behavior
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Qt6 host path (required for moc, rcc, uic)
if(NOT DEFINED QT_HOST_PATH AND DEFINED ENV{QT_HOST_PATH})
    set(QT_HOST_PATH "$ENV{QT_HOST_PATH}" CACHE PATH "Path to host Qt installation")
endif()

# Static linking flags for standalone executable
set(CMAKE_EXE_LINKER_FLAGS_INIT "-static-libgcc -static-libstdc++")

# Windows-specific defines
add_definitions(-DWIN32 -D_WIN32 -D_WINDOWS)
