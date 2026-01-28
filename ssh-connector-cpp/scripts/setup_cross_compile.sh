#!/bin/bash
# Setup script for cross-compilation sysroots
#
# This script helps set up the cross-compilation environment for building
# SSH Connector for Windows and Linux from macOS.
#
# Usage:
#   ./scripts/setup_cross_compile.sh [phase]
#
# Phases:
#   toolchains  - Install LLVM and MinGW-w64 via Homebrew
#   linux       - Create Linux sysroot from Docker
#   windows     - Cross-compile Windows dependencies
#   qt6-linux   - Cross-compile Qt6 for Linux (advanced)
#   qt6-windows - Cross-compile Qt6 for Windows (advanced)
#   all         - Run all phases (except Qt6)
#
# Note: Qt6 cross-compilation is complex and time-consuming.
# Consider using GitHub Actions for full cross-platform builds instead.

set -e

PHASE="${1:-help}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

check_homebrew() {
    if ! command -v brew &> /dev/null; then
        error "Homebrew not found. Install from https://brew.sh"
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Install Docker Desktop from https://docker.com"
    fi
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker Desktop."
    fi
}

phase_toolchains() {
    info "Installing cross-compilation toolchains..."
    check_homebrew

    info "Installing LLVM with multi-target support..."
    brew install llvm lld

    info "Installing MinGW-w64 for Windows cross-compilation..."
    brew install mingw-w64

    # Verify installations
    LLVM_PATH="/opt/homebrew/opt/llvm"
    if [ -f "$LLVM_PATH/bin/clang" ]; then
        info "LLVM installed at: $LLVM_PATH"
        "$LLVM_PATH/bin/clang" --version | head -1
    else
        warn "LLVM not found at expected path"
    fi

    if command -v x86_64-w64-mingw32-gcc &> /dev/null; then
        info "MinGW-w64 installed:"
        x86_64-w64-mingw32-gcc --version | head -1
    else
        warn "MinGW-w64 not found in PATH"
    fi

    info "Toolchains installation complete!"
}

phase_linux_sysroot() {
    info "Creating Linux sysroot from Docker..."
    check_docker

    SYSROOT="/opt/linux-sysroot"
    TEMP_DIR="/tmp/linux-sysroot-setup"

    if [ -d "$SYSROOT" ]; then
        warn "Linux sysroot already exists at $SYSROOT"
        read -p "Overwrite? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Skipping Linux sysroot creation"
            return
        fi
        sudo rm -rf "$SYSROOT"
    fi

    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"

    info "Pulling Ubuntu 22.04 image..."
    docker pull ubuntu:22.04

    info "Creating container with development packages..."
    docker rm -f sysroot-builder 2>/dev/null || true
    docker run --name sysroot-builder ubuntu:22.04 bash -c "
        apt-get update && \
        apt-get install -y --no-install-recommends \
            build-essential \
            libssh-dev \
            nlohmann-json3-dev \
            libgl1-mesa-dev \
            libxkbcommon-dev \
            libc6-dev \
            linux-libc-dev
    "

    info "Extracting sysroot..."
    docker export sysroot-builder > "$TEMP_DIR/rootfs.tar"

    sudo mkdir -p "$SYSROOT"
    cd "$SYSROOT"

    # Extract only necessary directories
    info "Extracting /lib..."
    sudo tar -xf "$TEMP_DIR/rootfs.tar" lib lib64 2>/dev/null || true

    info "Extracting /usr/lib..."
    sudo tar -xf "$TEMP_DIR/rootfs.tar" usr/lib 2>/dev/null || true

    info "Extracting /usr/include..."
    sudo tar -xf "$TEMP_DIR/rootfs.tar" usr/include 2>/dev/null || true

    # Cleanup
    docker rm -f sysroot-builder
    rm -rf "$TEMP_DIR"

    info "Linux sysroot created at: $SYSROOT"
    du -sh "$SYSROOT"
}

phase_windows_deps() {
    info "Cross-compiling Windows dependencies..."

    SYSROOT="/opt/mingw-sysroot"
    TEMP_DIR="/tmp/mingw-deps-setup"
    JOBS="$(sysctl -n hw.ncpu)"

    if [ ! -d "$SYSROOT" ]; then
        sudo mkdir -p "$SYSROOT"/{include,lib}
    fi

    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"

    # zlib
    info "Cross-compiling zlib..."
    if [ ! -f "$SYSROOT/lib/libz.a" ]; then
        curl -sL https://zlib.net/zlib-1.3.1.tar.gz -o zlib.tar.gz
        tar xzf zlib.tar.gz
        cd zlib-1.3.1
        CC=x86_64-w64-mingw32-gcc ./configure --prefix="$SYSROOT" --static
        make -j"$JOBS"
        sudo make install
        cd "$TEMP_DIR"
    else
        info "zlib already installed, skipping"
    fi

    # OpenSSL
    info "Cross-compiling OpenSSL..."
    if [ ! -f "$SYSROOT/lib/libssl.a" ]; then
        curl -sL https://www.openssl.org/source/openssl-3.2.0.tar.gz -o openssl.tar.gz
        tar xzf openssl.tar.gz
        cd openssl-3.2.0
        ./Configure mingw64 --cross-compile-prefix=x86_64-w64-mingw32- \
            --prefix="$SYSROOT" no-shared
        make -j"$JOBS"
        sudo make install_sw
        cd "$TEMP_DIR"
    else
        info "OpenSSL already installed, skipping"
    fi

    # libssh
    info "Cross-compiling libssh..."
    if [ ! -f "$SYSROOT/lib/libssh.a" ]; then
        git clone --depth 1 https://gitlab.com/libssh/libssh-mirror.git libssh
        cd libssh
        mkdir build && cd build
        cmake .. \
            -DCMAKE_SYSTEM_NAME=Windows \
            -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc \
            -DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ \
            -DCMAKE_INSTALL_PREFIX="$SYSROOT" \
            -DOPENSSL_ROOT_DIR="$SYSROOT" \
            -DZLIB_INCLUDE_DIR="$SYSROOT/include" \
            -DZLIB_LIBRARY="$SYSROOT/lib/libz.a" \
            -DWITH_EXAMPLES=OFF \
            -DBUILD_SHARED_LIBS=OFF
        make -j"$JOBS"
        sudo make install
        cd "$TEMP_DIR"
    else
        info "libssh already installed, skipping"
    fi

    # nlohmann-json (header-only)
    info "Installing nlohmann-json..."
    if [ ! -f "$SYSROOT/include/nlohmann/json.hpp" ]; then
        sudo mkdir -p "$SYSROOT/include/nlohmann"
        curl -sL https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp \
            -o /tmp/json.hpp
        sudo cp /tmp/json.hpp "$SYSROOT/include/nlohmann/"
    else
        info "nlohmann-json already installed, skipping"
    fi

    # Cleanup
    rm -rf "$TEMP_DIR"

    info "Windows dependencies installed at: $SYSROOT"
    ls -la "$SYSROOT/lib/"
}

show_help() {
    echo "Cross-Compilation Setup for SSH Connector"
    echo ""
    echo "Usage: $0 [phase]"
    echo ""
    echo "Phases:"
    echo "  toolchains  - Install LLVM and MinGW-w64 via Homebrew"
    echo "  linux       - Create Linux sysroot from Docker"
    echo "  windows     - Cross-compile Windows dependencies"
    echo "  all         - Run toolchains, linux, and windows phases"
    echo "  help        - Show this help message"
    echo ""
    echo "After setup, use cross_build.sh to build:"
    echo "  ./scripts/cross_build.sh linux"
    echo "  ./scripts/cross_build.sh windows"
    echo ""
    echo "Note: Qt6 cross-compilation is not included in this script."
    echo "The project can still use GitHub Actions for full cross-platform builds."
}

case "$PHASE" in
    toolchains)
        phase_toolchains
        ;;
    linux)
        phase_linux_sysroot
        ;;
    windows)
        phase_windows_deps
        ;;
    all)
        phase_toolchains
        phase_linux_sysroot
        phase_windows_deps
        info "All phases complete!"
        ;;
    help|*)
        show_help
        ;;
esac
