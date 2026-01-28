#!/bin/bash
# Cross-compilation build script for SSH Connector
#
# Usage:
#   ./scripts/cross_build.sh [linux|windows] [Debug|Release]
#
# Prerequisites:
#   Linux build:
#     - LLVM/Clang: brew install llvm lld
#     - Linux sysroot at /opt/linux-sysroot
#     - (Optional) Qt6 for Linux at /opt/qt6-linux
#
#   Windows build:
#     - MinGW-w64: brew install mingw-w64
#     - Windows sysroot at /opt/mingw-sysroot
#     - (Optional) Qt6 for Windows at /opt/qt6-windows
#
# Environment variables:
#   QT_HOST_PATH  - Path to host Qt installation (default: brew --prefix qt@6)

set -e

TARGET="${1:-linux}"
BUILD_TYPE="${2:-Release}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build-$TARGET"

# Set QT_HOST_PATH if not already set
if [ -z "$QT_HOST_PATH" ]; then
    if command -v brew &> /dev/null; then
        QT_HOST_PATH="$(brew --prefix qt@6 2>/dev/null || true)"
    fi
    if [ -z "$QT_HOST_PATH" ] || [ ! -d "$QT_HOST_PATH" ]; then
        echo "Warning: QT_HOST_PATH not set and Qt6 not found via Homebrew"
        echo "Set QT_HOST_PATH to your host Qt installation"
    fi
fi
export QT_HOST_PATH

# Select toolchain file
case "$TARGET" in
    linux)
        TOOLCHAIN="$PROJECT_DIR/cmake/toolchain-linux-clang.cmake"
        SYSROOT_CHECK="/opt/linux-sysroot"
        ;;
    windows)
        TOOLCHAIN="$PROJECT_DIR/cmake/toolchain-windows-mingw.cmake"
        SYSROOT_CHECK="/opt/mingw-sysroot"
        ;;
    *)
        echo "Usage: $0 [linux|windows] [Debug|Release]"
        echo ""
        echo "Targets:"
        echo "  linux    - Cross-compile for Linux x64 using Clang"
        echo "  windows  - Cross-compile for Windows x64 using MinGW-w64"
        echo ""
        echo "Build types:"
        echo "  Debug    - Debug build with symbols"
        echo "  Release  - Optimized release build (default)"
        exit 1
        ;;
esac

# Check prerequisites
if [ ! -f "$TOOLCHAIN" ]; then
    echo "Error: Toolchain file not found: $TOOLCHAIN"
    exit 1
fi

if [ ! -d "$SYSROOT_CHECK" ]; then
    echo "Error: Sysroot not found: $SYSROOT_CHECK"
    echo ""
    echo "Please set up the cross-compilation sysroot first."
    echo "See the project documentation for setup instructions."
    exit 1
fi

echo "========================================"
echo "Cross-compiling SSH Connector"
echo "========================================"
echo "Target:      $TARGET"
echo "Build type:  $BUILD_TYPE"
echo "Toolchain:   $TOOLCHAIN"
echo "Build dir:   $BUILD_DIR"
echo "QT_HOST_PATH: ${QT_HOST_PATH:-<not set>}"
echo "========================================"
echo ""

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure
echo "Configuring..."
cmake "$PROJECT_DIR" \
    -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN" \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE"

# Build
echo ""
echo "Building..."
cmake --build . --parallel "$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"

echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
echo "Output: $BUILD_DIR"

# Show binary info
if [ "$TARGET" = "windows" ]; then
    BINARY="$BUILD_DIR/ssh-connector.exe"
else
    BINARY="$BUILD_DIR/ssh-connector"
fi

if [ -f "$BINARY" ]; then
    echo ""
    echo "Binary info:"
    file "$BINARY"
fi
