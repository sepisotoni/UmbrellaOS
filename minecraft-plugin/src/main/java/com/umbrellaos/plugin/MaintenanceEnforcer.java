package com.umbrellaos.plugin;

import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.AsyncPlayerPreLoginEvent;

import java.util.Map;
import java.util.UUID;

/**
 * Enforces maintenance mode at pre-login time.
 * If maintenance is enabled in ConfigManager or local configuration, players without
 * the bypass permission ({@value #BYPASS_PERMISSION} or OP) are disallowed from joining
 * with a customizable kick message rendered by {@link MessageTemplateManager}.
 */
public class MaintenanceEnforcer implements Listener {

    public static final String BYPASS_PERMISSION = "umbrellaos.maintenance.bypass";
    public static final String DEFAULT_KICK_MESSAGE = "The server is currently under maintenance. Please try again later.";

    @FunctionalInterface
    public interface BypassChecker {
        boolean hasBypass(UUID uuid, String name);
    }

    private final UmbrellaPlugin plugin;
    private final ConfigManager configManager;
    private final MessageTemplateManager templateManager;
    private BypassChecker bypassChecker;
    private Boolean maintenanceOverride = null;

    public MaintenanceEnforcer(UmbrellaPlugin plugin, ConfigManager configManager, MessageTemplateManager templateManager) {
        this.plugin = plugin;
        this.configManager = configManager;
        this.templateManager = templateManager;
        this.bypassChecker = defaultBypassChecker();
    }

    private BypassChecker defaultBypassChecker() {
        return (uuid, name) -> {
            try {
                OfflinePlayer op = Bukkit.getOfflinePlayer(uuid);
                if (op != null && op.isOp()) {
                    return true;
                }
            } catch (Throwable ignored) {}
            return false;
        };
    }

    @EventHandler(priority = EventPriority.NORMAL)
    public void onAsyncPreLogin(AsyncPlayerPreLoginEvent event) {
        // Do not alter decision if already disallowed by higher priority listener (e.g. server full or ban)
        if (event.getLoginResult() != AsyncPlayerPreLoginEvent.Result.ALLOWED) {
            return;
        }

        if (!isMaintenanceEnabled()) {
            return;
        }

        UUID uuid = event.getUniqueId();
        String name = event.getName();

        if (hasBypass(uuid, name)) {
            return;
        }

        String serverName = (plugin != null && plugin.getConfig() != null)
                ? plugin.getConfig().getString("server.name", "Minecraft Server")
                : "Minecraft Server";

        String template = (templateManager != null)
                ? templateManager.getTemplate(MessageTemplateManager.KEY_MAINTENANCE_KICK)
                : DEFAULT_KICK_MESSAGE;

        if (template == null || template.isBlank()) {
            template = DEFAULT_KICK_MESSAGE;
        }

        Map<String, String> vars = Map.of(
                "PLAYER", name != null ? name : "Player",
                "SERVER", serverName
        );

        String kickMessage = (templateManager != null)
                ? templateManager.render(template, vars)
                : template.replace("$PLAYER", vars.get("PLAYER")).replace("$SERVER", vars.get("SERVER"));

        event.disallow(AsyncPlayerPreLoginEvent.Result.KICK_OTHER, Component.text(kickMessage));
    }

    /**
     * Checks if maintenance mode is enabled via override, config manager, or local config.
     *
     * <p>Canonical config key is {@code server.maintenance_mode} (BUG-7 fix — previously
     * checked 4 different keys which caused ambiguity; anyone configuring maintenance mode
     * had to know which key took precedence). The local {@code config.yml} key
     * {@code maintenance.enabled} is kept as a secondary fallback for operators who set
     * it directly in the file, but the dashboard and all docs should point to
     * {@code server.maintenance_mode} in core settings.
     */
    public boolean isMaintenanceEnabled() {
        if (maintenanceOverride != null) {
            return maintenanceOverride;
        }

        if (configManager != null) {
            // Single canonical key — set this via the dashboard settings panel.
            String serverMaintMode = configManager.getSetting("server.maintenance_mode");
            if (isTruthy(serverMaintMode)) return true;
        }

        // Fallback: local config.yml allows operators to force maintenance mode
        // without a network call to core (e.g. during a core outage).
        if (plugin != null && plugin.getConfig() != null) {
            if (plugin.getConfig().getBoolean("maintenance.enabled", false)) {
                return true;
            }
        }

        return false;
    }

    public boolean hasBypass(UUID uuid, String name) {
        if (bypassChecker != null) {
            return bypassChecker.hasBypass(uuid, name);
        }
        return false;
    }

    public void setBypassChecker(BypassChecker bypassChecker) {
        this.bypassChecker = bypassChecker != null ? bypassChecker : defaultBypassChecker();
    }

    public void setMaintenanceOverride(Boolean override) {
        this.maintenanceOverride = override;
    }

    private static boolean isTruthy(String val) {
        if (val == null) return false;
        String trimmed = val.trim().toLowerCase();
        return "true".equals(trimmed) || "1".equals(trimmed) || "yes".equals(trimmed) || "on".equals(trimmed);
    }
}
