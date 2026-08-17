package com.umbrellaos.plugin;

import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Entry point. Step 1 scope only: scaffold + core plumbing (this class,
 * {@link CoreApiClient}, {@link HeartbeatManager}, {@link ConfigManager}).
 *
 * <p>Deliberately NOT built here (Step 2/3, per the dispatch doc): command
 * polling ({@code GET /mc/commands/pending}), ban enforcement, GrimAC
 * bridge.
 */
public final class UmbrellaPlugin extends JavaPlugin {

    private CoreApiClient apiClient;
    private ConfigManager configManager;
    private HeartbeatManager heartbeatManager;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        FileConfiguration config = getConfig();

        String baseUrl = config.getString("core.base-url", "http://localhost:8000");
        String pluginKey = config.getString("core.plugin-key", "");
        long heartbeatIntervalSeconds = config.getLong("heartbeat.interval-seconds", 30);
        String serverId = config.getString("server.id", "");
        String serverName = config.getString("server.name", "Minecraft Server");

        if (pluginKey == null || pluginKey.isBlank() || pluginKey.equals("CHANGE-ME")) {
            getLogger().severe(
                    "core.plugin-key is not set in config.yml — heartbeat and config sync will fail "
                            + "every request with HTTP 401 until this is set to a real key matching "
                            + "umbrella-core's SECRET_KEY.");
        }

        apiClient = new CoreApiClient(baseUrl, pluginKey, getLogger());
        configManager = new ConfigManager(apiClient);
        heartbeatManager = new HeartbeatManager(this, apiClient, configManager, serverId, serverName);

        // Startup config pull (per scope: "on startup and on reconnect").
        // Off the main thread — this is a blocking HTTP call and must never
        // stall server startup or the main tick loop.
        getServer().getScheduler().runTaskAsynchronously(this, configManager::refresh);

        heartbeatManager.start(heartbeatIntervalSeconds);

        getLogger().info("UmbrellaOS plugin enabled — core: " + baseUrl
                + ", heartbeat every " + heartbeatIntervalSeconds + "s");
    }

    @Override
    public void onDisable() {
        if (heartbeatManager != null) {
            heartbeatManager.stop();
        }
        getLogger().info("UmbrellaOS plugin disabled");
    }

    // Package-private accessors for tests / future managers (Step 2/3 will
    // extend CoreApiClient's usage, not replace it — see handback doc).
    CoreApiClient getApiClient() {
        return apiClient;
    }

    ConfigManager getConfigManager() {
        return configManager;
    }
}
