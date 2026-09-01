package com.umbrellaos.plugin;

import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Entry point. Step 1: scaffold + core plumbing ({@link CoreApiClient},
 * {@link HeartbeatManager}, {@link ConfigManager}). Step 2 adds {@link
 * CommandPoller} (command-queue round trip) and {@link BanEnforcer} (join-time
 * ban enforcement). Step 3 adds {@link GrimBridge} — soft-dependency GrimAC
 * EventBus integration that forwards flag events to umbrella-core.
 */
public final class UmbrellaPlugin extends JavaPlugin {

    private CoreApiClient apiClient;
    private ConfigManager configManager;
    private HeartbeatManager heartbeatManager;
    private CommandPoller commandPoller;
    private BanEnforcer banEnforcer;
    private GrimBridge grimBridge;
    private MessageTemplateManager messageTemplateManager;
    private GreeterListener greeterListener;
    private ChatResponderListener chatResponderListener;
    private VerificationCommand verificationCommand;
    private PlayerTelemetryListener telemetryListener;
    private ConsoleStreamManager consoleStreamManager;
    private MaintenanceEnforcer maintenanceEnforcer;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        FileConfiguration config = getConfig();

        String baseUrl = config.getString("core.base-url", "http://localhost:8000");
        String pluginKey = config.getString("core.plugin-key", "");
        long heartbeatIntervalSeconds = config.getLong("heartbeat.interval-seconds", 30);
        long commandPollIntervalSeconds = config.getLong("commands.poll-interval-seconds", 5);
        String serverId = config.getString("server.id", "");
        String serverName = config.getString("server.name", "Minecraft Server");

        if (pluginKey == null || pluginKey.isBlank() || pluginKey.equals("CHANGE-ME")) {
            getLogger().severe(
                    "core.plugin-key is not set in config.yml — heartbeat, config sync, command "
                            + "polling, and ban checks will fail every request with HTTP 401 until this "
                            + "is set to a real key matching umbrella-core's SECRET_KEY.");
        }

        apiClient = new CoreApiClient(baseUrl, pluginKey, getLogger());
        configManager = new ConfigManager(apiClient);
        messageTemplateManager = new MessageTemplateManager(this, apiClient);
        // GrimBridge reference set after grimBridge is created below (DEAD-4 fix).
        heartbeatManager = new HeartbeatManager(this, apiClient, configManager, serverId, serverName);
        commandPoller = new CommandPoller(this, apiClient, serverId);
        banEnforcer = new BanEnforcer(apiClient);
        maintenanceEnforcer = new MaintenanceEnforcer(this, configManager, messageTemplateManager);
        telemetryListener = new PlayerTelemetryListener(this, apiClient);
        consoleStreamManager = new ConsoleStreamManager();

        // Startup config pull (per scope: "on startup and on reconnect").
        // Off the main thread — this is a blocking HTTP call and must never
        // stall server startup or the main tick loop.
        getServer().getScheduler().runTaskAsynchronously(this, configManager::refresh);
        messageTemplateManager.start();

        // Register event listeners
        getServer().getPluginManager().registerEvents(banEnforcer, this);
        getServer().getPluginManager().registerEvents(maintenanceEnforcer, this);
        getServer().getPluginManager().registerEvents(telemetryListener, this);

        // Greeter — welcomes new and returning players on join (P16E).
        greeterListener = new GreeterListener(this, apiClient, messageTemplateManager);
        getServer().getPluginManager().registerEvents(greeterListener, this);

        // Chat keyword responder — AI answers common questions in chat (P16E).
        chatResponderListener = new ChatResponderListener(this, apiClient, messageTemplateManager, serverName);
        getServer().getPluginManager().registerEvents(chatResponderListener, this);

        // Console stream manager — starts capturing console log records, then
        // schedules periodic pushes to core so the dashboard can poll them.
        consoleStreamManager.startCapture();
        consoleStreamManager.startPushing(this, apiClient, serverId, 100L);

        // GrimBridge: soft-dependency — register() checks isPluginEnabled("GrimAC")
        // internally and logs the outcome either way. No extra config needed; if
        // GrimAC is absent the bridge stays inactive and everything else runs normally.
        try {
            grimBridge = new GrimBridge(this, apiClient, serverId);
            grimBridge.register();
        } catch (Throwable t) {
            getLogger().info("GrimAC not found or incompatible — anticheat bridge inactive.");
        }
        // Wire the (possibly null) bridge into HeartbeatManager now that it's
        // initialised — grim_connected in heartbeat payloads will reflect reality
        // instead of being hardcoded false (DEAD-4 fix).
        heartbeatManager.setGrimBridge(grimBridge);

        // Player UX commands: /verify, /umbrella, /appeal
        verificationCommand = new VerificationCommand(this, apiClient, messageTemplateManager, grimBridge);
        registerCommand("verify", verificationCommand);
        registerCommand("umbrella", verificationCommand);
        registerCommand("appeal", verificationCommand);

        heartbeatManager.start(heartbeatIntervalSeconds);
        commandPoller.start(commandPollIntervalSeconds);

        getLogger().info("UmbrellaOS plugin enabled — core: " + baseUrl
                + ", heartbeat every " + heartbeatIntervalSeconds + "s"
                + ", command poll every " + commandPollIntervalSeconds + "s"
                + ((grimBridge != null && grimBridge.isRegistered()) ? ", GrimAC bridge: ACTIVE" : ", GrimAC bridge: inactive"));
    }

    private void registerCommand(String name, VerificationCommand executor) {
        org.bukkit.command.PluginCommand cmd = getCommand(name);
        if (cmd != null) {
            cmd.setExecutor(executor);
            cmd.setTabCompleter(executor);
        } else {
            getLogger().warning("Failed to register command /" + name + " — check plugin.yml");
        }
    }

    @Override
    public void onDisable() {
        if (heartbeatManager != null) {
            heartbeatManager.stop();
        }
        if (commandPoller != null) {
            commandPoller.stop();
        }
        if (messageTemplateManager != null) {
            messageTemplateManager.stop();
        }
        if (consoleStreamManager != null) {
            consoleStreamManager.stopPushing();
            consoleStreamManager.stopCapture();
        }
        getLogger().info("UmbrellaOS plugin disabled");
    }

    // Package-private accessors for tests and diagnostics.
    CoreApiClient getApiClient() {
        return apiClient;
    }

    ConfigManager getConfigManager() {
        return configManager;
    }

    CommandPoller getCommandPoller() {
        return commandPoller;
    }

    BanEnforcer getBanEnforcer() {
        return banEnforcer;
    }

    GrimBridge getGrimBridge() {
        return grimBridge;
    }

    MessageTemplateManager getMessageTemplateManager() {
        return messageTemplateManager;
    }

    VerificationCommand getVerificationCommand() {
        return verificationCommand;
    }

    public PlayerTelemetryListener getTelemetryListener() {
        return telemetryListener;
    }

    public ConsoleStreamManager getConsoleStreamManager() {
        return consoleStreamManager;
    }

    public MaintenanceEnforcer getMaintenanceEnforcer() {
        return maintenanceEnforcer;
    }
}
