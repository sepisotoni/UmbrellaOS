package com.umbrellaos.plugin.commands;

import com.umbrellaos.plugin.api.CoreApiClient;
import com.umbrellaos.plugin.managers.BridgeManager;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

public class DiscCommand implements CommandExecutor {
    private final CoreApiClient apiClient;
    private final BridgeManager bridgeManager;

    public DiscCommand(CoreApiClient apiClient, BridgeManager bridgeManager) {
        this.apiClient = apiClient;
        this.bridgeManager = bridgeManager;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage("§cThis command can only be used by players.");
            return true;
        }

        Player player = (Player) sender;
        String bridgeMode = bridgeManager.getBridgeMode();

        if ("off".equalsIgnoreCase(bridgeMode)) {
            player.sendMessage("§cDiscord bridge is currently disabled.");
            return true;
        }

        if (args.length == 0) {
            player.sendMessage("§cUsage: /disc <message>");
            return true;
        }

        String message = String.join(" ", args);
        String uuid = player.getUniqueId().toString();

        apiClient.postBridgeMessage("minecraft", uuid, message).thenRun(() -> {
            player.sendMessage("§a[→ Discord] " + message);
        }).exceptionally(e -> {
            player.sendMessage("§cFailed to send message to Discord.");
            e.printStackTrace();
            return null;
        });

        return true;
    }
}
