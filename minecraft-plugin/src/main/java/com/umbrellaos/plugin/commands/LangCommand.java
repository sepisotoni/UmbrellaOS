package com.umbrellaos.plugin.commands;

import com.umbrellaos.plugin.UmbrellaPlugin;
import com.umbrellaos.plugin.api.CoreApiClient;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public class LangCommand implements CommandExecutor {
    private final CoreApiClient apiClient;
    private final UmbrellaPlugin plugin;

    private static final Map<String, String> SUPPORTED_LANGUAGES = new HashMap<>();
    
    static {
        SUPPORTED_LANGUAGES.put("english", "en");
        SUPPORTED_LANGUAGES.put("spanish", "es");
        SUPPORTED_LANGUAGES.put("french", "fr");
        SUPPORTED_LANGUAGES.put("portuguese", "pt");
        SUPPORTED_LANGUAGES.put("german", "de");
        SUPPORTED_LANGUAGES.put("chinese", "zh");
        SUPPORTED_LANGUAGES.put("arabic", "ar");
        SUPPORTED_LANGUAGES.put("russian", "ru");
        SUPPORTED_LANGUAGES.put("japanese", "ja");
        SUPPORTED_LANGUAGES.put("korean", "ko");
    }

    public LangCommand(CoreApiClient apiClient, UmbrellaPlugin plugin) {
        this.apiClient = apiClient;
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage("§cThis command can only be used by players.");
            return true;
        }

        Player player = (Player) sender;
        UUID playerUuid = player.getUniqueId();

        // Handle /lang <language>
        if (label.equals("lang")) {
            if (args.length == 0) {
                player.sendMessage("§cUsage: /lang <language>");
                player.sendMessage("§eSupported languages: §f" + String.join(", ", SUPPORTED_LANGUAGES.keySet()));
                return true;
            }

            String languageName = args[0].toLowerCase();
            String languageCode = SUPPORTED_LANGUAGES.get(languageName);

            if (languageCode == null) {
                player.sendMessage("§cUnknown language. Supported languages:");
                player.sendMessage("§e" + String.join(", ", SUPPORTED_LANGUAGES.keySet()));
                return true;
            }

            // Call API to set player language
            apiClient.setPlayerLanguage(playerUuid.toString(), languageCode, capitalizeFirst(languageName), null)
                .thenRun(() -> {
                    player.sendMessage("§a✅ Language set to " + capitalizeFirst(languageName));
                })
                .exceptionally(e -> {
                    player.sendMessage("§cFailed to set language: " + e.getMessage());
                    return null;
                });

            return true;
        }

        // Handle /translate on|off
        if (label.equals("translate")) {
            if (args.length == 0) {
                player.sendMessage("§cUsage: /translate <on|off>");
                return true;
            }

            String action = args[0].toLowerCase();
            boolean enable;

            if (action.equals("on")) {
                enable = true;
            } else if (action.equals("off")) {
                enable = false;
            } else {
                player.sendMessage("§cUsage: /translate <on|off>");
                return true;
            }

            // Call API to set auto-translate preference
            apiClient.setPlayerLanguage(playerUuid.toString(), null, null, enable)
                .thenRun(() -> {
                    if (enable) {
                        player.sendMessage("§a✅ Auto-translation enabled");
                    } else {
                        player.sendMessage("§a✅ Auto-translation disabled");
                    }
                })
                .exceptionally(e -> {
                    player.sendMessage("§cFailed to update translation preference: " + e.getMessage());
                    return null;
                });

            return true;
        }

        return false;
    }

    private String capitalizeFirst(String str) {
        if (str == null || str.isEmpty()) {
            return str;
        }
        return str.substring(0, 1).toUpperCase() + str.substring(1);
    }
}
