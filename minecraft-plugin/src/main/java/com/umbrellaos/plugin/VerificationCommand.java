package com.umbrellaos.plugin;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.json.JSONObject;

import java.net.http.HttpResponse;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.stream.Collectors;

/**
 * Handles in-game player commands for UmbrellaOS:
 * <ul>
 *   <li>{@code /verify <code>} — Links a player's Minecraft account to Discord via a verification code</li>
 *   <li>{@code /umbrella <status|help>} — Displays plugin status and general help</li>
 *   <li>{@code /appeal} — Provides appeal portal link, Discord link, and active punishment info</li>
 * </ul>
 *
 * <p>All network I/O operations are dispatched asynchronously off the main server thread
 * to avoid stalling the tick loop.
 */
public class VerificationCommand implements CommandExecutor, TabCompleter {

    private static final String VERIFY_CODE_PATH = "/api/v1/verification/verify-code";
    private static final String VERIFY_FALLBACK_PATH = "/api/v1/verification/verify";
    private static final String VERIFY_STATUS_PATH = "/api/v1/verification/status";
    private static final String PUNISHMENTS_ACTIVE_PATH = "/api/v1/plugin/punishments/%s/active";

    private final Plugin plugin;
    private final CoreApiClient apiClient;
    private final MessageTemplateManager templateManager;
    private final GrimBridge grimBridge;

    public VerificationCommand(Plugin plugin,
                               CoreApiClient apiClient,
                               MessageTemplateManager templateManager,
                               @Nullable GrimBridge grimBridge) {
        this.plugin = plugin;
        this.apiClient = apiClient;
        this.templateManager = templateManager;
        this.grimBridge = grimBridge;
    }

    @Override
    public boolean onCommand(@NotNull CommandSender sender,
                             @NotNull Command command,
                             @NotNull String label,
                             @NotNull String[] args) {
        String cmdName = command.getName().toLowerCase();

        switch (cmdName) {
            case "verify":
                handleVerifyCommand(sender, args);
                return true;
            case "umbrella":
                handleUmbrellaCommand(sender, args);
                return true;
            case "appeal":
                handleAppealCommand(sender, args);
                return true;
            default:
                return false;
        }
    }

    // ------------------------------------------------------------------
    // /verify <code>
    // ------------------------------------------------------------------

    private void handleVerifyCommand(CommandSender sender, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("§cOnly in-game players can verify their account.");
            return;
        }

        if (args.length != 1) {
            player.sendMessage("§eUsage: /verify <code>");
            return;
        }

        String code = args[0].trim();
        if (!isValidCode(code)) {
            player.sendMessage("§cInvalid verification code. Code must be 6 to 8 characters.");
            return;
        }

        player.sendMessage("§eVerifying code with UmbrellaOS...");

        if (plugin != null && plugin.getServer() != null && plugin.getServer().getScheduler() != null) {
            plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
                VerificationResult result = verifyCode(code, player.getUniqueId().toString(), player.getName());
                if (plugin.isEnabled()) {
                    plugin.getServer().getScheduler().runTask(plugin, () -> {
                        if (player.isOnline()) {
                            player.sendMessage(result.message());
                        }
                    });
                }
            });
        } else {
            VerificationResult result = verifyCode(code, player.getUniqueId().toString(), player.getName());
            player.sendMessage(result.message());
        }
    }

    /**
     * Validates verification code format (6 to 8 characters).
     */
    public static boolean isValidCode(String code) {
        if (code == null) {
            return false;
        }
        String trimmed = code.trim();
        return trimmed.length() >= 6 && trimmed.length() <= 8;
    }

    /**
     * Result of a verification attempt.
     */
    public record VerificationResult(
            boolean success,
            String message,
            int statusCode,
            @Nullable String discordUsername
    ) {}

    /**
     * Performs the verification HTTP request and parses the response.
     */
    public VerificationResult verifyCode(String code, String playerUuid, String playerName) {
        if (!isValidCode(code)) {
            return new VerificationResult(false, "§cInvalid verification code. Code must be 6 to 8 characters.", 400, null);
        }

        if (apiClient == null) {
            return new VerificationResult(false, "§cUmbrellaOS API client is not configured.", 500, null);
        }

        String payload = buildVerifyPayload(code, playerUuid, playerName);

        try {
            HttpResponse<String> response = apiClient.post(VERIFY_CODE_PATH, payload);
            if (response.statusCode() == 404) {
                // If primary endpoint not found, attempt fallback endpoint
                try {
                    HttpResponse<String> fallbackResp = apiClient.post(VERIFY_FALLBACK_PATH, payload);
                    if (fallbackResp.statusCode() != 404) {
                        return parseVerificationResponse(fallbackResp.statusCode(), fallbackResp.body(), playerName, code, templateManager);
                    }
                } catch (Exception ignored) {
                    // Fall back to original 404 response
                }
            }
            return parseVerificationResponse(response.statusCode(), response.body(), playerName, code, templateManager);
        } catch (Exception e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            if (apiClient.logger() != null) {
                apiClient.logger().log(Level.WARNING, "Verification failed for " + playerName + " (" + playerUuid + ")", e);
            }
            return new VerificationResult(false, "§cFailed to connect to UmbrellaOS verification service. Please try again later.", 500, null);
        }
    }

    /**
     * Constructs JSON request body for verification.
     */
    public static String buildVerifyPayload(String code, String playerUuid, String playerName) {
        JSONObject json = new JSONObject();
        json.put("code", code);
        json.put("minecraft_uuid", playerUuid);
        json.put("minecraft_username", playerName);
        json.put("player_uuid", playerUuid);
        json.put("player_username", playerName);
        return json.toString();
    }

    /**
     * Parses the verification HTTP response status and body.
     */
    public static VerificationResult parseVerificationResponse(int statusCode,
                                                               String responseBody,
                                                               String playerName,
                                                               String code,
                                                               @Nullable MessageTemplateManager templateManager) {
        if (statusCode >= 200 && statusCode < 300) {
            String discordUsername = null;
            if (responseBody != null && !responseBody.isBlank()) {
                try {
                    JSONObject obj = new JSONObject(responseBody);
                    if (obj.has("already_verified") && obj.getBoolean("already_verified")) {
                        return new VerificationResult(true, "§eYour account is already linked to Discord.", statusCode, null);
                    }
                    if (obj.has("success") && !obj.getBoolean("success")) {
                        String errMsg = obj.optString("message", "Verification failed.");
                        return new VerificationResult(false, "§c" + errMsg, statusCode, null);
                    }
                    discordUsername = obj.optString("discord_username", null);
                } catch (Exception ignored) {
                }
            }

            String message;
            if (templateManager != null) {
                String template = templateManager.getTemplate(MessageTemplateManager.KEY_INGAME_SUCCESS);
                message = templateManager.render(template, Map.of(
                        "PLAYER", playerName != null ? playerName : "",
                        "CODE", code != null ? code : ""
                ));
            } else {
                message = "Your Discord account has been linked successfully!";
            }

            // Ensure colored prefix if not already formatted
            if (!message.startsWith("§")) {
                message = "§a" + message;
            }
            return new VerificationResult(true, message, statusCode, discordUsername);
        } else if (statusCode == 400) {
            return new VerificationResult(false, "§cVerification code is invalid or has expired.", statusCode, null);
        } else if (statusCode == 404) {
            return new VerificationResult(false, "§cVerification code not found. Please ensure you generated a code in Discord.", statusCode, null);
        } else if (statusCode == 409) {
            return new VerificationResult(false, "§cThis account is already linked to a different Discord account.", statusCode, null);
        } else {
            return new VerificationResult(false, "§cVerification failed (HTTP " + statusCode + "). Please try again or contact staff.", statusCode, null);
        }
    }

    // ------------------------------------------------------------------
    // /umbrella <status|help>
    // ------------------------------------------------------------------

    private void handleUmbrellaCommand(CommandSender sender, String[] args) {
        if (args.length == 0 || args[0].equalsIgnoreCase("help")) {
            sendHelp(sender);
            return;
        }

        if (args[0].equalsIgnoreCase("status")) {
            handleStatus(sender);
            return;
        }

        sender.sendMessage("§cUnknown subcommand. Use §e/umbrella help§c for available commands.");
    }

    private void sendHelp(CommandSender sender) {
        sender.sendMessage("§6================= §eUmbrellaOS Help §6=================");
        sender.sendMessage("§e/verify <code> §7- Link your Minecraft account to Discord");
        sender.sendMessage("§e/umbrella status §7- View server & plugin integration status");
        sender.sendMessage("§e/umbrella help §7- Display this help message");
        sender.sendMessage("§e/appeal §7- Information on submitting a punishment appeal");
        sender.sendMessage("§6=================================================");
    }

    private void handleStatus(CommandSender sender) {
        String version = plugin != null && plugin.getDescription() != null ? plugin.getDescription().getVersion() : "0.1.0-SNAPSHOT";
        String grimStatus = (grimBridge != null && grimBridge.isRegistered()) ? "§aACTIVE" : "§7Inactive";

        sender.sendMessage("§6================= §eUmbrellaOS Status §6=================");
        sender.sendMessage("§7Plugin Version: §f" + version);
        sender.sendMessage("§7GrimAC Bridge: " + grimStatus);

        if (sender instanceof Player player) {
            if (plugin != null && plugin.getServer() != null && plugin.getServer().getScheduler() != null) {
                plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
                    String linkStatus = checkPlayerVerificationStatus(player.getUniqueId().toString());
                    if (plugin.isEnabled()) {
                        plugin.getServer().getScheduler().runTask(plugin, () -> {
                            if (player.isOnline()) {
                                player.sendMessage("§7Discord Link: " + linkStatus);
                                player.sendMessage("§6=================================================");
                            }
                        });
                    }
                });
                return;
            } else {
                sender.sendMessage("§7Discord Link: " + checkPlayerVerificationStatus(player.getUniqueId().toString()));
            }
        }
        sender.sendMessage("§6=================================================");
    }

    /**
     * Checks verification status for a specific player UUID against core API.
     */
    public String checkPlayerVerificationStatus(String playerUuid) {
        if (apiClient == null) {
            return "§7Unavailable";
        }
        try {
            JSONObject payload = new JSONObject();
            payload.put("player_uuid", playerUuid);
            HttpResponse<String> resp = apiClient.post(VERIFY_STATUS_PATH, payload.toString());
            if (resp.statusCode() == 200) {
                JSONObject obj = new JSONObject(resp.body());
                if (obj.optBoolean("verified", false)) {
                    String discordUsername = obj.optString("discord_username", "");
                    if (!discordUsername.isEmpty()) {
                        return "§aLinked (§e" + discordUsername + "§a)";
                    }
                    return "§aLinked";
                }
                return "§cNot Linked §7(Use §e/verify <code>§7)";
            }
        } catch (Exception ignored) {
        }
        return "§7Unavailable";
    }

    // ------------------------------------------------------------------
    // /appeal
    // ------------------------------------------------------------------

    private void handleAppealCommand(CommandSender sender, String[] args) {
        String appealUrl = getAppealUrl();
        String discordUrl = getDiscordInviteUrl();

        if (!(sender instanceof Player player)) {
            sender.sendMessage("§6=== UmbrellaOS Appeal Info ===");
            sender.sendMessage("§eAppeal Portal: §b" + appealUrl);
            sender.sendMessage("§eDiscord Server: §b" + discordUrl);
            return;
        }

        if (plugin != null && plugin.getServer() != null && plugin.getServer().getScheduler() != null) {
            plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
                String punishmentInfo = checkActivePunishmentInfo(player.getUniqueId().toString());
                if (plugin.isEnabled()) {
                    plugin.getServer().getScheduler().runTask(plugin, () -> {
                        if (player.isOnline()) {
                            sendAppealMessage(player, appealUrl, discordUrl, punishmentInfo);
                        }
                    });
                }
            });
        } else {
            String punishmentInfo = checkActivePunishmentInfo(player.getUniqueId().toString());
            sendAppealMessage(player, appealUrl, discordUrl, punishmentInfo);
        }
    }

    private void sendAppealMessage(Player player, String appealUrl, String discordUrl, @Nullable String punishmentInfo) {
        player.sendMessage("§6================= §eUmbrellaOS Appeal §6=================");
        if (punishmentInfo != null) {
            player.sendMessage("§cActive Punishment: " + punishmentInfo);
        }
        player.sendMessage("§7To submit a punishment appeal:");
        player.sendMessage("§eAppeal Portal: §b" + appealUrl);
        player.sendMessage("§eDiscord Server: §b" + discordUrl);
        player.sendMessage("§7Your Minecraft UUID: §f" + player.getUniqueId());
        player.sendMessage("§6=================================================");
    }

    /**
     * Checks if a player has an active ban/punishment in Core.
     */
    public String checkActivePunishmentInfo(String playerUuid) {
        if (apiClient == null) {
            return null;
        }
        try {
            String path = String.format(PUNISHMENTS_ACTIVE_PATH, playerUuid);
            HttpResponse<String> resp = apiClient.get(path);
            if (resp.statusCode() == 200) {
                JSONObject obj = new JSONObject(resp.body());
                if (obj.optBoolean("banned", false)) {
                    JSONObject punishment = obj.optJSONObject("punishment");
                    if (punishment != null) {
                        return "§e" + punishment.optString("type", "ban").toUpperCase()
                                + " §7- Reason: §f" + punishment.optString("reason", "No reason provided");
                    }
                    return "§eBANNED";
                }
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    public String getAppealUrl() {
        if (plugin != null && plugin.getConfig() != null) {
            return plugin.getConfig().getString("appeal.url", "https://umbrellaos.net/appeals");
        }
        return "https://umbrellaos.net/appeals";
    }

    public String getDiscordInviteUrl() {
        if (templateManager != null) {
            String invite = templateManager.getTemplate(MessageTemplateManager.KEY_DISCORD_INVITE);
            if (invite != null && !invite.isBlank()) {
                return invite;
            }
        }
        return "https://discord.gg/yourserver";
    }

    // ------------------------------------------------------------------
    // Tab Completion
    // ------------------------------------------------------------------

    @Override
    public List<String> onTabComplete(@NotNull CommandSender sender,
                                      @NotNull Command command,
                                      @NotNull String alias,
                                      @NotNull String[] args) {
        String cmdName = command.getName().toLowerCase();
        if ("umbrella".equals(cmdName)) {
            if (args.length == 1) {
                List<String> subcommands = List.of("status", "help");
                return subcommands.stream()
                        .filter(s -> s.startsWith(args[0].toLowerCase()))
                        .collect(Collectors.toList());
            }
        } else if ("verify".equals(cmdName)) {
            return Collections.emptyList();
        // /appeal has no subcommands — tab-completing "status" was dead code
        // (PLUGIN-BUG-3 fix): handleAppealCommand never handled args[0]=="status",
        // so the tab-complete suggestion produced a no-op subcommand.
        return Collections.emptyList();
    }
}
