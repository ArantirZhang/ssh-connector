#include "ConfigManager.h"

#include <QDir>
#include <QFile>
#include <QStandardPaths>
#include <QJsonDocument>
#include <QJsonObject>

#include <fstream>

namespace sshconn {

ConfigManager::ConfigManager(const QString& configDir)
    : m_configDir(configDir.isEmpty() ? getDefaultConfigDir() : configDir)
    , m_configPath(m_configDir + "/" + CONFIG_FILENAME)
{
}

QString ConfigManager::getDefaultConfigDir() const
{
#ifdef Q_OS_WIN
    QString base = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
#elif defined(Q_OS_MACOS)
    QString base = QDir::homePath() + "/Library/Application Support";
#else
    // Linux - use XDG_CONFIG_HOME or fallback to ~/.config
    QString base = QStandardPaths::writableLocation(QStandardPaths::ConfigLocation);
#endif
    return base + "/ssh-connector";
}

QString ConfigManager::expandPath(const QString& path) const
{
    QString result = path;
    if (result.startsWith("~")) {
        result.replace(0, 1, QDir::homePath());
    }
    return result;
}

QString ConfigManager::sshKeyPath() const
{
    return expandPath(ServerConfig::SSH_KEY_PATH);
}

AppConfig ConfigManager::load()
{
    QFile file(m_configPath);
    if (!file.exists()) {
        return m_config;
    }

    if (!file.open(QIODevice::ReadOnly)) {
        qWarning("Failed to open config file: %s", qPrintable(m_configPath));
        return m_config;
    }

    QByteArray data = file.readAll();
    file.close();

    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(data, &parseError);

    if (parseError.error != QJsonParseError::NoError) {
        qWarning("JSON parse error: %s", qPrintable(parseError.errorString()));
        return m_config;
    }

    QJsonObject root = doc.object();

    // Load tunnel config
    if (root.contains("tunnel")) {
        QJsonObject tunnelObj = root["tunnel"].toObject();
        m_config.tunnel.localPort = tunnelObj["local_port"].toInt(m_config.tunnel.localPort);
        m_config.tunnel.remotePort = tunnelObj["remote_port"].toInt(m_config.tunnel.remotePort);
        m_config.tunnel.enabled = tunnelObj["enabled"].toBool(m_config.tunnel.enabled);
    }

    // Load reconnect settings
    if (root.contains("auto_reconnect")) {
        m_config.autoReconnect = root["auto_reconnect"].toBool(m_config.autoReconnect);
    }
    if (root.contains("reconnect_delay")) {
        m_config.reconnectDelay = root["reconnect_delay"].toDouble(m_config.reconnectDelay);
    }
    if (root.contains("max_reconnect_delay")) {
        m_config.maxReconnectDelay = root["max_reconnect_delay"].toDouble(m_config.maxReconnectDelay);
    }

    return m_config;
}

void ConfigManager::save()
{
    // Ensure config directory exists
    QDir dir(m_configDir);
    if (!dir.exists()) {
        dir.mkpath(".");
    }

    QJsonObject tunnelObj;
    tunnelObj["local_port"] = m_config.tunnel.localPort;
    tunnelObj["remote_port"] = m_config.tunnel.remotePort;
    tunnelObj["enabled"] = m_config.tunnel.enabled;

    QJsonObject root;
    root["tunnel"] = tunnelObj;
    root["auto_reconnect"] = m_config.autoReconnect;
    root["reconnect_delay"] = m_config.reconnectDelay;
    root["max_reconnect_delay"] = m_config.maxReconnectDelay;

    QJsonDocument doc(root);

    QFile file(m_configPath);
    if (!file.open(QIODevice::WriteOnly)) {
        qWarning("Failed to save config file: %s", qPrintable(m_configPath));
        return;
    }

    file.write(doc.toJson(QJsonDocument::Indented));
    file.close();
}

} // namespace sshconn
