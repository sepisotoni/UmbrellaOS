package com.umbrellaos.plugin;

import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.AsyncPlayerChatEvent;
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
 * <p>All AI calls are made asynchronously — this listener is already on an
 * async thread (fired on {@link AsyncPlayerChatEvent}) so the scheduler wrap
 * uses {@code runTaskAsynchronously} from within a task to keep the HTTP call
 * off the main thread while also being safe when used inside an async event.
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
    public void onPlayerChat(AsyncPlayerChatEvent event) {
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

        String message = event.getMessage();
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

        // The event is already async, but we still schedule an async task so the
        // HTTP call happens on a Bukkit pool thread (not the event's own thread,
        // which may have a tight timeout in some server implementations).
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
                        // Send the reply on the main thread (broadcastMessage is main-thread only).
                        plugin.getServer().getScheduler().runTask(plugin, () ->
                                event.getPlayer().sendMessage(REPLY_PREFIX + aiReply));
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

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /**
     * Parse the JSON array string from the template manager into a list of
     * keyword strings. Falls back to an empty list on parse failure.
     */
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

    /**
     * Parse the cooldown seconds setting and convert to milliseconds.
     * Returns {@link #DEFAULT_COOLDOWN_MS} on parse failure.
     */
    private long parseCooldownMs(String raw) {
        try {
            return Long.parseLong(raw.trim()) * 1000L;
        } catch (NumberFormatException e) {
            return DEFAULT_COOLDOWN_MS;
        }
    }
}
