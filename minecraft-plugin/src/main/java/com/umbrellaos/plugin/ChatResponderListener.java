package com.umbrellaos.plugin;

import io.papermc.paper.event.player.AsyncChatEvent;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.json.JSONArray;
import org.json.JSONObject;

import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;

/**
 * Listens for chat messages and triggers an AI response when the message
 * contains a known keyword/phrase (e.g. "how to join", "whats the ip").
 *
 * <p>The keyword list and response style are fetched from umbrella-core via
 * {@link MessageTemplateManager}, so they can be changed from the dashboard
 * without a plugin reload.
 *
 * <p>A per-player cooldown prevents the bot from flooding chat if the same
 * player repeatedly asks questions. The cooldown duration is also pulled from
 * core ({@code chat_responder.cooldown_seconds}).
 *
 * <p>Migrated from {@code AsyncPlayerChatEvent} (removed in Paper 1.20.6) to
 * Paper's {@code AsyncChatEvent} with Adventure API message extraction (BUG-4 fix).
 *
 * <p>Controlled by {@code chat_responder.enabled} in {@code config.yml}.
 */
public class ChatResponderListener implements Listener {

    /** Prefix shown before the AI's reply in chat. */
    private static final String REPLY_PREFIX = "§8[§bAssistant§8] §7";

    /** Default cooldown if the setting cannot be read. */
    private static final long DEFAULT_COOLDOWN_MS = 60_000L;

    /** Per-player cooldown expiry timestamps (epoch milliseconds). */
    private final ConcurrentHashMap<UUID, Long> cooldowns = new ConcurrentHashMap<>();

    private final UmbrellaPlugin plugin;
    private final CoreApiClient apiClient;
    private final MessageTemplateManager templateManager;
    private final String serverName;

    public ChatResponderListener(UmbrellaPlugin plugin,
                                 CoreApiClient apiClient,
                                 MessageTemplateManager templateManager,
                                 String serverName) {
        this.plugin          = plugin;
        this.apiClient       = apiClient;
        this.templateManager = templateManager;
        this.serverName      = serverName;
    }

    @EventHandler
    public void onPlayerChat(AsyncChatEvent event) {
        if (!plugin.getConfig().getBoolean("chat_responder.enabled", true)) {
            return;
        }

        UUID playerUuid = event.getPlayer().getUniqueId();
        String playerName = event.getPlayer().getName();

        // Cooldown check — fast path before any network I/O.
        Long expiry = cooldowns.get(playerUuid);
        if (expiry != null && System.currentTimeMillis() < expiry) {
            return;
        }

        // Extract plain text from the Adventure Component message (BUG-4 fix —
        // Paper 1.20.6+ uses AsyncChatEvent whose message() returns a Component).
        String message = PlainTextComponentSerializer.plainText().serialize(event.message());
        String messageLower = message.toLowerCase(Locale.ROOT);

        // Fetch keyword list from template cache.
        List<String> keywords = parseKeywords(
                templateManager.getTemplate(MessageTemplateManager.KEY_CHAT_RESPONDER_KEYWORDS));

        boolean matched = keywords.stream()
                .anyMatch(kw -> messageLower.contains(kw.toLowerCase(Locale.ROOT)));

        if (!matched) {
            return;
        }

        // Compute cooldown duration from settings.
        long cooldownMs = parseCooldownMs(
                templateManager.getTemplate(MessageTemplateManager.KEY_CHAT_RESPONDER_COOLDOWN));

        // Set cooldown immediately so concurrent/rapid messages don't slip through.
        cooldowns.put(playerUuid, System.currentTimeMillis() + cooldownMs);

        String responseStyle = templateManager.getTemplate(
                MessageTemplateManager.KEY_CHAT_RESPONDER_STYLE);

        plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
            try {
                String context = String.format(
                        "Player %s asked this in Minecraft chat on server \"%s\". "
                                + "Answer briefly. Style: %s.",
                        playerName, serverName,
                        responseStyle.isEmpty() ? "friendly and brief, 1-2 sentences max" : responseStyle);

                JSONObject requestBody = new JSONObject();
                requestBody.put("message", message);
                requestBody.put("context", context);

                HttpResponse<String> resp = apiClient.post(
                        "/api/v1/ai/copilot", requestBody.toString());

                if (resp.statusCode() == 200) {
                    JSONObject body = new JSONObject(resp.body());
                    String aiReply = body.optString("response", "").trim();
                    if (!aiReply.isEmpty()) {
                        // Broadcast reply to all so the question+answer are both
                        // visible in chat (DESIGN-5 fix). Prefixed with the asking
                        // player's name for context.
                        Component reply = Component.text(REPLY_PREFIX + playerName + ": " + aiReply);
                        plugin.getServer().getScheduler().runTask(plugin, () ->
                                event.getPlayer().getServer().broadcast(reply));
                    }
                } else {
                    plugin.getLogger().warning("ChatResponder: AI request failed with HTTP "
                            + resp.statusCode() + " — skipping reply for " + playerName);
                }
            } catch (Exception e) {
                plugin.getLogger().log(Level.WARNING,
                        "ChatResponder: AI call threw exception for " + playerName
                                + " — skipping reply", e);
            }
        });
    }

    private List<String> parseKeywords(String raw) {
        List<String> result = new ArrayList<>();
        if (raw == null || raw.isBlank()) return result;
        try {
            JSONArray arr = new JSONArray(raw.trim());
            for (int i = 0; i < arr.length(); i++) {
                String kw = arr.optString(i, "").trim();
                if (!kw.isEmpty()) result.add(kw);
            }
        } catch (Exception e) {
            plugin.getLogger().warning("ChatResponder: could not parse keyword list — "
                    + "check chat_responder.keywords in dashboard settings. Raw: " + raw);
        }
        return result;
    }

    private long parseCooldownMs(String raw) {
        try {
            return Long.parseLong(raw.trim()) * 1000L;
        } catch (NumberFormatException e) {
            return DEFAULT_COOLDOWN_MS;
        }
    }
}
