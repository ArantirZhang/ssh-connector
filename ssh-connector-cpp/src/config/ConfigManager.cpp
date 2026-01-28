#include "ConfigManager.h"

#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cstdlib>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace sshconn {

ConfigManager::ConfigManager(const std::string& configDir)
    : m_configDir(configDir.empty() ? getDefaultConfigDir() : configDir)
    , m_configPath(m_configDir + "/" + CONFIG_FILENAME)
{
}

std::string ConfigManager::getDefaultConfigDir() const
{
#ifdef _WIN32
    const char* appdata = std::getenv("APPDATA");
    if (appdata) {
        return std::string(appdata) + "/ssh-connector";
    }
    return "./ssh-connector";
#elif defined(__APPLE__)
    const char* home = std::getenv("HOME");
    if (home) {
        return std::string(home) + "/Library/Application Support/ssh-connector";
    }
    return "./ssh-connector";
#else
    // Linux - use XDG_CONFIG_HOME or fallback to ~/.config
    const char* xdg = std::getenv("XDG_CONFIG_HOME");
    if (xdg) {
        return std::string(xdg) + "/ssh-connector";
    }
    const char* home = std::getenv("HOME");
    if (home) {
        return std::string(home) + "/.config/ssh-connector";
    }
    return "./ssh-connector";
#endif
}

std::string ConfigManager::expandPath(const std::string& path) const
{
    if (path.empty() || path[0] != '~') {
        return path;
    }
    const char* home = std::getenv("HOME");
#ifdef _WIN32
    if (!home) {
        home = std::getenv("USERPROFILE");
    }
#endif
    if (home) {
        return std::string(home) + path.substr(1);
    }
    return path;
}

std::string ConfigManager::sshKeyPath() const
{
    return expandPath(ServerConfig::SSH_KEY_PATH);
}

AppConfig ConfigManager::load()
{
    if (!fs::exists(m_configPath)) {
        return m_config;
    }

    std::ifstream file(m_configPath);
    if (!file.is_open()) {
        std::cerr << "Failed to open config file: " << m_configPath << std::endl;
        return m_config;
    }

    try {
        json root = json::parse(file);

        // Load tunnel config
        if (root.contains("tunnel")) {
            const auto& tunnelObj = root["tunnel"];
            if (tunnelObj.contains("local_port")) {
                m_config.tunnel.localPort = tunnelObj["local_port"].get<int>();
            }
            if (tunnelObj.contains("remote_port")) {
                m_config.tunnel.remotePort = tunnelObj["remote_port"].get<int>();
            }
            if (tunnelObj.contains("enabled")) {
                m_config.tunnel.enabled = tunnelObj["enabled"].get<bool>();
            }
        }

        // Load reconnect settings
        if (root.contains("auto_reconnect")) {
            m_config.autoReconnect = root["auto_reconnect"].get<bool>();
        }
        if (root.contains("reconnect_delay")) {
            m_config.reconnectDelay = root["reconnect_delay"].get<double>();
        }
        if (root.contains("max_reconnect_delay")) {
            m_config.maxReconnectDelay = root["max_reconnect_delay"].get<double>();
        }
    } catch (const json::exception& e) {
        std::cerr << "JSON parse error: " << e.what() << std::endl;
    }

    return m_config;
}

void ConfigManager::save()
{
    // Ensure config directory exists
    fs::path dirPath(m_configDir);
    if (!fs::exists(dirPath)) {
        std::error_code ec;
        fs::create_directories(dirPath, ec);
        if (ec) {
            std::cerr << "Failed to create config directory: " << m_configDir << std::endl;
            return;
        }
    }

    json tunnelObj;
    tunnelObj["local_port"] = m_config.tunnel.localPort;
    tunnelObj["remote_port"] = m_config.tunnel.remotePort;
    tunnelObj["enabled"] = m_config.tunnel.enabled;

    json root;
    root["tunnel"] = tunnelObj;
    root["auto_reconnect"] = m_config.autoReconnect;
    root["reconnect_delay"] = m_config.reconnectDelay;
    root["max_reconnect_delay"] = m_config.maxReconnectDelay;

    std::ofstream file(m_configPath);
    if (!file.is_open()) {
        std::cerr << "Failed to save config file: " << m_configPath << std::endl;
        return;
    }

    file << root.dump(4);
}

} // namespace sshconn
