package com.umbrellaos.plugin;

import net.md_5.bungee.api.ChatMessageType;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.json.JSONObject;

import java.net.http.HttpResponse;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.Map;
import java.util.logging.Level;

/**
 * Sends a configurable welcome message to players on join.
 *
 * <p>New players (first_seen within 60 seconds of join) receive a title +
 * subtitle on screen and a broadcast in chat. Returning players get a chat
 * message only.
 *
 * <p>Controlled by {@code greeter.enabled} in {@code config.yml}.
 * Message templates are fetched from umbrella-core via
 * {@link MessageTemplateManager} so staff can edit them from the dashboard
 * without a plugin reload.
 *
 * <p>All HTTP calls run asynchronously; the main thread is never blocked.
 * On any API failure the greeter silently skips — a core outage must never
 * break the join experience.
 */
public class GreeterListener implements Listener {

    /** Seconds within which a first_seen timestamp is treated as "new player". */
    private static final long NEW_PLAYER_WINDOW_SECONDS = 60L;

    /** Title stay time in ticks (5 seconds × 20 ticks/sec). */
    private static final int TITLE_STAY_TICKS = 100;

    private final UmbrellaPlugin plugin;
    private final CoreApiClient apiClient;
    private final MessageTemplateManager templateManager;

    public GreeterListener(UmbrellaPlugin plugin,
                           CoreApiClient apiClient,
                           MessageTemplateManager templateManager) {
        this.plugin          = plugin;
        this.apiClient       = apiClient;
        this.templateManager = templateManager;
    }

    @EventHandler
    public void onPlayerJoin(PlayerJoinEvent event) {
        if (!plugin.getConfig().getBoolean("greeter.enabled", true)) {
            return;
        }

        Player player = event.getPlayer();
        String uuid   = player.getUniqueId().toString();
        String serverName = plugin.getConfig().getString("server.name", "Minecraft Server");

        // Run off the main thread — we need an HTTP call to determine new vs returning.
        plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
            boolean isNew = false;
            try {
                HttpResponse<String> resp = apiClient.get("/api/v1/players/" + uuid);
                if (resp.statusCode() == 200) {
                    JSONObject body = new JSONObject(resp.body());
                    String firstSeenStr = body.optString("first_seen", "");
                    if (!firstSeenStr.isEmpty()) {
                        Instant firstSeen = Instant.parse(firstSeenStr);
                        long secondsAgo = Instant.now().getEpochSecond() - firstSeen.getEpochSecond();
                        isNew = secondsAgo <= NEW_PLAYER_WINDOW_SECONDS;
                    }
                } else if (resp.statusCode() == 404) {
                    // Player not in core yet — treat as new.
                    isNew = true;
                } else {
                    plugin.getLogger().warning("Greeter: unexpected HTTP " + resp.statusCode()
                            + " for player " + uuid + " — skipping");
                    return;
                }
            } catch (DateTimeParseException e) {
                plugin.getLogger().log(Level.WARNING,
                        "Greeter: could not parse first_seen for " + uuid + " — skipping", e);
                return;
            } catch (Exception e) {
                plugin.getLogger().log(Level.WARNING,
                        "Greeter: API call failed for " + uuid + " — skipping", e);
                return;
            }

            final boolean playerIsNew = isNew;

            // Fetch templates and send on the main thread (Bukkit title API is not thread-safe).
            plugin.getServer().getScheduler().runTask(plugin, () -> {
                if (!player.isOnline()) return;

                String discordInvite = templateManager.getTemplate("discord.invite_url");
                Map<String, String> vars = Map.of(
                        "PLAYER",         player.getName(),
                        "DISCORD_INVITE", discordInvite.isEmpty() ? "our Discord" : discordInvite,
                        "SERVER",         serverName
                );

                if (playerIsNew) {
                    String msg = templateManager.render(
                            templateManager.getTemplate("greeter.first_join_message"), vars);

                    // Title on screen (fade-in 10, stay 100, fade-out 20 ticks).
                    player.sendTitle(
                            "§aWelcome!",
                            "§7" + player.getName(),
                            10, TITLE_STAY_TICKS, 20
                    );

                    // Broadcast in chat with a leading blank line for visibility.
                    Bukkit.broadcastMessage("");
                    Bukkit.broadcastMessage("§6[Welcome] §f" + msg);
                } else {
                    String template = templateManager.getTemplate("greeter.return_join_message");
                    if (template == null || template.isBlank()) return;

                    String msg = templateManager.render(template, vars);
                    // Chat-only for returning players — no broadcast, just a personal message.
                    player.sendMessage("§7" + msg);
                }
            });
        });
    }
}
