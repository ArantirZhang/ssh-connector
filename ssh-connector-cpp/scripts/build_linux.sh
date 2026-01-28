#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
BUILD_TYPE="${1:-Release}"

echo "=== SSH Connector Linux Build ==="
echo "Project: $PROJECT_DIR"
echo "Build type: $BUILD_TYPE"

# Detect package manager and install dependencies
echo ""
echo "Checking dependencies..."

install_deps_apt() {
    local DEPS="cmake pkg-config qt6-base-dev libssh-dev nlohmann-json3-dev"
    echo "Using apt to install: $DEPS"
    sudo apt-get update
    sudo apt-get install -y $DEPS
}

install_deps_dnf() {
    local DEPS="cmake pkg-config qt6-qtbase-devel libssh-devel json-devel"
    echo "Using dnf to install: $DEPS"
    sudo dnf install -y $DEPS
}

install_deps_pacman() {
    local DEPS="cmake pkgconf qt6-base libssh nlohmann-json"
    echo "Using pacman to install: $DEPS"
    sudo pacman -S --noconfirm $DEPS
}

if command -v apt-get &> /dev/null; then
    install_deps_apt
elif command -v dnf &> /dev/null; then
    install_deps_dnf
elif command -v pacman &> /dev/null; then
    install_deps_pacman
else
    echo "Warning: Unknown package manager. Please install dependencies manually:"
    echo "  - cmake"
    echo "  - Qt6 (qt6-base-dev or equivalent)"
    echo "  - libssh-dev"
    echo "  - nlohmann-json3-dev"
fi

# Clean and create build directory
echo ""
echo "Preparing build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure
echo ""
echo "Configuring..."
cmake .. -DCMAKE_BUILD_TYPE="$BUILD_TYPE"

# Build
echo ""
echo "Building..."
cmake --build . --parallel "$(nproc)"

# Output
echo ""
echo "=== Build Complete ==="
echo "Executable: $BUILD_DIR/ssh-connector"
echo ""
echo "To run: $BUILD_DIR/ssh-connector"
echo "To install: sudo cmake --install ."
