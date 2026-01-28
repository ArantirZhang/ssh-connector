# SSH Connector (C++ Port)

Cross-platform reverse SSH client with Qt 6 GUI.

## Quick Build

Use the build scripts that automatically install dependencies and build:

```bash
# macOS
./scripts/build_macos.sh

# Linux
./scripts/build_linux.sh

# Windows (run in Developer Command Prompt)
scripts\build_windows.bat
```

## Dependencies

- Qt 6 (Core, Widgets, Network)
- libssh
- nlohmann/json
- CMake 3.16+

### macOS

```bash
brew install qt libssh nlohmann-json
```

### Ubuntu/Debian

```bash
sudo apt install qt6-base-dev libssh-dev nlohmann-json3-dev cmake pkg-config
```

### Fedora

```bash
sudo dnf install qt6-qtbase-devel libssh-devel json-devel cmake
```

### Arch Linux

```bash
sudo pacman -S qt6-base libssh nlohmann-json cmake
```

### Windows

1. Install [vcpkg](https://github.com/Microsoft/vcpkg):
   ```powershell
   git clone https://github.com/Microsoft/vcpkg.git
   cd vcpkg && bootstrap-vcpkg.bat
   ```

2. Install dependencies:
   ```powershell
   vcpkg install libssh:x64-windows nlohmann-json:x64-windows
   ```

3. Install [Qt 6](https://www.qt.io/download)

## Manual Build

### macOS

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$(brew --prefix qt)
cmake --build . --parallel
```

### Linux

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --parallel
```

### Windows

```powershell
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake
cmake --build . --config Release --parallel
```

## Output

| Platform | Output |
|----------|--------|
| macOS | `build/ssh-connector.app` |
| Linux | `build/ssh-connector` |
| Windows | `build/Release/ssh-connector.exe` |

## Configuration

The application stores configuration in platform-specific locations:
- **macOS**: `~/Library/Application Support/ssh-connector/config.json`
- **Linux**: `~/.config/ssh-connector/config.json`
- **Windows**: `%APPDATA%/ssh-connector/config.json`

SSH key should be placed at `~/.ssh/tunnel_key`.
