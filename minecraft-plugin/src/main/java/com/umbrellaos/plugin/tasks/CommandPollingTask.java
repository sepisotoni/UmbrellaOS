package com.umbrellaos.plugin.tasks;

import com.umbrellaos.plugin.UmbrellaPlugin;
import com.umbrellaos.plugin.api.CoreApiClient;
import org.bukkit.Bukkit;
import org.bukkit.scheduler.BukkitRunnable;

import java.util.List;
import java.util.Map;

public class CommandPollingTask extends BukkitRunnable {
    private final CoreApiClient apiClient;
    private final UmbrellaPlugin plugin;

    public CommandPollingTask(CoreApiClient apiClient, UmbrellaPlugin plugin) {
        this.apiClient = apiClient;
        this.plugin = plugin;
    }

    @Override
    public void run() {
        apiClient.getPendingCommands().thenAccept(commands -> {
            if (commands == null || commands.isEmpty()) {
                return;
            }

            for (Map<String, Object> commandData : commands) {
                try {
                    int id = ((Number) commandData.get("id")).intValue();
                    String type = (String) commandData.get("type"); // Assuming a 'type' field for command differentiation

                    if ("plugin_control".equals(type)) {
                        String pluginName = (String) commandData.get("plugin_name");
                        String action = (String) commandData.get("action");

                        plugin.getLogger().info("[UmbrellaOS] Received plugin control command for " + pluginName + ": " + action);

                        Bukkit.getScheduler().runTask(plugin, () -> {
                            String output = "";
                            boolean success = false;
                            try {
                                if ("reload".equals(action)) {
                                    plugin.reloadPlugin(pluginName);
                                    output = "Plugin " + pluginName + " reloaded successfully.";
                                    success = true;
                                } else if ("toggle".equals(action)) {
                                    plugin.togglePlugin(pluginName);
                                    output = "Plugin " + pluginName + " toggled successfully.";
                                    success = true;
                                } else {
                                    output = "Unknown plugin control action: " + action;
                                }
                                apiClient.completeCommand(id, output, success).exceptionally(e -> {
                                    plugin.getLogger().warning("[UmbrellaOS] Failed to complete plugin control command " + id + ": " + e.getMessage());
                                    return null;
                                });
                            } catch (Exception e) {
                                plugin.getLogger().severe("[UmbrellaOS] Error executing plugin control for " + pluginName + ": " + e.getMessage());
                                apiClient.completeCommand(id, "Error: " + e.getMessage(), false).exceptionally(e2 -> null);
                            }
                        });
                    } else {
                        String command = (String) commandData.get("command");
                        plugin.getLogger().info("[UmbrellaOS] Executing console command: " + command);

                        // Execute command on main thread
                        Bukkit.getScheduler().runTask(plugin, () -> {
                            try {
                                boolean success = Bukkit.dispatchCommand(Bukkit.getConsoleSender(), command);
                                String output = success ? "Executed successfully" : "Execution failed";

                                // Complete the command
                                apiClient.completeCommand(id, output, success).exceptionally(e -> {
                                    plugin.getLogger().warning("[UmbrellaOS] Failed to complete command " + id + ": " + e.getMessage());
                                    return null;
                                });
                            } catch (Exception e) {
                                plugin.getLogger().severe("[UmbrellaOS] Error executing command: " + e.getMessage());

                                // Complete with failure
                                apiClient.completeCommand(id, "Error: " + e.getMessage(), false).exceptionally(e2 -> {
                                    return null;
                                });
                            }
                        });
                    }
                } catch (Exception e) {
                    plugin.getLogger().severe("[UmbrellaOS] Error processing command: " + e.getMessage());
                }
            }
        }).exceptionally(e -> {
            plugin.getLogger().warning("[UmbrellaOS] Failed to get pending commands: " + e.getMessage());
            return null;
        });
    }
}
