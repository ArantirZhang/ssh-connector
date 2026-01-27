# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SSH Connector is a cross-platform (Windows/Mac/Linux) reverse SSH client with a PyQt6 GUI. It connects to SSH servers using key authentication and establishes remote port forwarding (reverse tunnels) with auto-reconnect capability.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.main

# Build standalone executable (platform-specific)
./build_scripts/build_mac.sh      # macOS
./build_scripts/build_linux.sh    # Linux
build_scripts\build_windows.bat   # Windows
```

## Architecture

The app follows a layered architecture with clear separation between SSH logic, connection management, and UI:

```
Application (main.py)
    │
    ├── ConfigManager ← JSON config in platform-appropriate location
    │
    ├── SSHClient (ssh_client.py)
    │       │
    │       └── paramiko Transport (keepalive, key auth)
    │
    ├── TunnelManager (tunnel_manager.py)
    │       │
    │       └── Remote port forwarding via Transport.request_port_forward()
    │
    ├── ConnectionMonitor (connection_monitor.py)
    │       │
    │       └── Health checks + exponential backoff reconnect
    │
    └── MainWindow (ui/main_window.py)
            │
            ├── SettingsDialog → ConfigManager
            ├── PortForwardWidget → list[PortForwardRule]
            └── ConnectionStatusWidget → state display
```

**Key data flow:**
1. `SSHClient` establishes connection, exposes `Transport`
2. `TunnelManager` receives transport, calls `request_port_forward()` for each rule
3. `ConnectionMonitor` polls `SSHClient.check_connection()`, triggers reconnect on failure
4. On reconnect, monitor stops tunnels, reconnects SSH, restarts tunnels

**State management:** Components use callback registration (e.g., `add_state_callback()`) rather than Qt signals for decoupling from UI.

**Config location:** Platform-specific via `ConfigManager._get_default_config_dir()`:
- macOS: `~/Library/Application Support/ssh-connector/`
- Linux: `~/.config/ssh-connector/`
- Windows: `%APPDATA%/ssh-connector/`

## Dependencies

- **paramiko**: SSH protocol implementation
- **PyQt6**: Cross-platform GUI
- **keyring**: System credential storage (optional)
- **pyinstaller**: Building standalone executables
