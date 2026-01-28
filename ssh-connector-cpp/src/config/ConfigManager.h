#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include "Config.h"
#include <string>
#include <memory>

namespace sshconn {

class ConfigManager {
public:
    static constexpr const char* CONFIG_FILENAME = "config.json";

    explicit ConfigManager(const std::string& configDir = std::string());

    AppConfig load();
    void save();

    std::string sshKeyPath() const;
    std::string configDir() const { return m_configDir; }
    AppConfig& config() { return m_config; }
    const AppConfig& config() const { return m_config; }

private:
    std::string getDefaultConfigDir() const;
    std::string expandPath(const std::string& path) const;

    std::string m_configDir;
    std::string m_configPath;
    AppConfig m_config;
};

} // namespace sshconn

#endif // CONFIG_MANAGER_H
