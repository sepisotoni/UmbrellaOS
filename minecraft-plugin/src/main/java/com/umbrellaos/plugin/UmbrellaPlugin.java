package com.umbrellaos.plugin;

import com.comphenix.protocol.ProtocolLibrary;
import com.comphenix.protocol.ProtocolManager;
import com.umbrellaos.plugin.api.CoreApiClient;
import com.umbrellaos.plugin.commands.DiscCommand;
import com.umbrellaos.plugin.commands.VerifyCommand;
import com.umbrellaos.plugin.config.PluginConfig;
import com.umbrellaos.plugin.listeners.*;
import com.umbrellaos.plugin.managers.BridgeManager;
import com.umbrellaos.plugin.managers.PunishmentManager;
import com.umbrellaos.plugin.managers.VerificationManager;
import com.umbrellaos.plugin.tasks.HeartbeatTask;
import com.umbrellaos.plugin.tasks.ReplayBufferTask;
import com.umbrellaos.plugin.tasks.SnapshotTask;
import org.bukkit.plugin.java.JavaPlugin;

import java.io.File;

public class UmbrellaPlugin extends JavaPlugin {
    private CoreApiClient apiClient;
    private PluginConfig config;
    private VerificationManager verificationManager;
    private PunishmentManager punishmentManager;
    private BridgeManager bridgeManager;
    private HeartbeatTask heartbeatTask;
    private SnapshotTask snapshotTask;
    private ReplayBufferTask replayBufferTask;

    @Override
    public void onEnable() {
        // Load config
        saveDefaultConfig();
        File configFile = new File(getDataFolder(), "config.yml");
        config = new PluginConfig(configFile);

        // Initialize API client
        apiClient = new CoreApiClient(config.getCoreUrl(), config.getAdminKey());

        // Initialize managers
        verificationManager = new VerificationManager();
        punishmentManager = new PunishmentManager(apiClient);
        bridgeManager = new BridgeManager(apiClient, config.getBridgeModeCacheSeconds());
        bridgeManager.start();

        // Initialize tasks
        heartbeatTask = new HeartbeatTask(apiClient);
        snapshotTask = new SnapshotTask(apiClient);
        replayBufferTask = new ReplayBufferTask(apiClient, config.getReplayBufferSeconds());

        // Register listeners
        getServer().getPluginManager().registerEvents(new PlayerJoinListener(apiClient, verificationManager, punishmentManager, config.isVerifyOnJoin()), this);
        getServer().getPluginManager().registerEvents(new PlayerQuitListener(apiClient, verificationManager), this);
        getServer().getPluginManager().registerEvents(new PlayerDeathListener(apiClient, replayBufferTask), this);
        getServer().getPluginManager().registerEvents(new PlayerMoveListener(replayBufferTask), this);
        getServer().getPluginManager().registerEvents(new PlayerChatListener(apiClient, verificationManager, bridgeManager), this);
        getServer().getPluginManager().registerEvents(new PlayerAchievementListener(apiClient), this);

        // Register ProtocolLib packet listener
        if (getServer().getPluginManager().getPlugin("ProtocolLib") != null) {
            ProtocolManager protocolManager = ProtocolLibrary.getProtocolManager();
            protocolManager.addPacketListener(new PacketListener(this, replayBufferTask));
        } else {
            getLogger().warning("ProtocolLib not found! Packet tracking will not work.");
        }

        // Register commands
        getCommand("verify").setExecutor(new VerifyCommand(verificationManager));
        getCommand("disc").setExecutor(new DiscCommand(apiClient, bridgeManager));

        // Start scheduled tasks
        heartbeatTask.runTaskTimerAsynchronously(this, config.getHeartbeatIntervalSeconds() * 20L, config.getHeartbeatIntervalSeconds() * 20L);
        snapshotTask.runTaskTimerAsynchronously(this, config.getSnapshotIntervalSeconds() * 20L, config.getSnapshotIntervalSeconds() * 20L);
        replayBufferTask.runTaskTimerAsynchronously(this, 20L, 20L); // Run every second

        // Post server start event
        apiClient.postEvent("server_start", null, "Server started", null).thenRun(() -> {
            getLogger().info("Server start event posted to Core API");
        }).exceptionally(e -> {
            getLogger().warning("Failed to post server start event: " + e.getMessage());
            return null;
        });

        getLogger().info("UmbrellaOS Plugin enabled");
    }

    @Override
    public void onDisable() {
        // Post server stop event
        apiClient.postEvent("server_stop", null, "Server stopped", null).thenRun(() -> {
            getLogger().info("Server stop event posted to Core API");
        }).exceptionally(e -> {
            getLogger().warning("Failed to post server stop event: " + e.getMessage());
            return null;
        });

        // Cancel tasks
        if (heartbeatTask != null) {
            heartbeatTask.cancel();
        }
        if (snapshotTask != null) {
            snapshotTask.cancel();
        }
        if (replayBufferTask != null) {
            replayBufferTask.cancel();
        }

        // Shutdown managers
        if (verificationManager != null) {
            verificationManager.shutdown();
        }
        if (bridgeManager != null) {
            bridgeManager.shutdown();
        }

        // Shutdown API client
        if (apiClient != null) {
            apiClient.shutdown();
        }

        getLogger().info("UmbrellaOS Plugin disabled");
    }
}
