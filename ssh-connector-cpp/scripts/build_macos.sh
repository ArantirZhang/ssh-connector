#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
BUILD_TYPE="${1:-Release}"

echo "=== SSH Connector macOS Build ==="
echo "Project: $PROJECT_DIR"
echo "Build type: $BUILD_TYPE"

# Check dependencies
echo ""
echo "Checking dependencies..."

if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew not found. Install from https://brew.sh"
    exit 1
fi

MISSING_DEPS=""
for dep in qt libssh nlohmann-json; do
    if ! brew list "$dep" &> /dev/null; then
        MISSING_DEPS="$MISSING_DEPS $dep"
    fi
done

if [ -n "$MISSING_DEPS" ]; then
    echo "Installing missing dependencies:$MISSING_DEPS"
    brew install $MISSING_DEPS
fi

# Get Qt path
QT_PATH="$(brew --prefix qt)"
echo "Using Qt at: $QT_PATH"

# Clean and create build directory
echo ""
echo "Preparing build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure
echo ""
echo "Configuring..."
cmake .. \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DCMAKE_PREFIX_PATH="$QT_PATH"

# Build
echo ""
echo "Building..."
cmake --build . --parallel "$(sysctl -n hw.ncpu)"

# Output
echo ""
echo "=== Build Complete ==="
echo "App bundle: $BUILD_DIR/ssh-connector.app"
echo ""
echo "To run: open $BUILD_DIR/ssh-connector.app"
echo "To create DMG: hdiutil create -volname 'SSH Connector' -srcfolder $BUILD_DIR/ssh-connector.app -ov -format UDZO ssh-connector.dmg"
