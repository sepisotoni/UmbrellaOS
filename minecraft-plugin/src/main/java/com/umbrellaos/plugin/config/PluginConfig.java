package com.umbrellaos.plugin.config;

import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;

public class PluginConfig {
    private final File configFile;
    private FileConfiguration config;

    public PluginConfig(File configFile) {
        this.configFile = configFile;
        this.config = YamlConfiguration.loadConfiguration(configFile);
    }

    public void reload() {
        config = YamlConfiguration.loadConfiguration(configFile);
    }

    public void save() {
        try {
            config.save(configFile);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public String getCoreUrl() {
        return config.getString("umbrella.core_url", "http://localhost:8765");
    }

    public String getAdminKey() {
        return config.getString("umbrella.admin_key", "changeme");
    }

    public boolean isVerifyOnJoin() {
        return config.getBoolean("umbrella.verify_on_join", true);
    }

    public int getBridgeModeCacheSeconds() {
        return config.getInt("umbrella.bridge_mode_cache_seconds", 30);
    }

    public int getSnapshotIntervalSeconds() {
        return config.getInt("umbrella.snapshot_interval_seconds", 300);
    }

    public int getReplayBufferSeconds() {
        return config.getInt("umbrella.replay_buffer_seconds", 300);
    }

    public int getHeartbeatIntervalSeconds() {
        return config.getInt("umbrella.heartbeat_interval_seconds", 30);
    }
}
