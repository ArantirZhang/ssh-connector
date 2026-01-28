#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include "Config.h"
#include <QString>
#include <memory>

namespace sshconn {

class ConfigManager {
public:
    static constexpr const char* CONFIG_FILENAME = "config.json";

    explicit ConfigManager(const QString& configDir = QString());

    AppConfig load();
    void save();

    QString sshKeyPath() const;
    QString configDir() const { return m_configDir; }
    AppConfig& config() { return m_config; }
    const AppConfig& config() const { return m_config; }

private:
    QString getDefaultConfigDir() const;
    QString expandPath(const QString& path) const;

    QString m_configDir;
    QString m_configPath;
    AppConfig m_config;
};

} // namespace sshconn

#endif // CONFIG_MANAGER_H
