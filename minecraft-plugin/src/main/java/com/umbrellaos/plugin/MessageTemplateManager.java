package com.umbrellaos.plugin;

import org.bukkit.plugin.Plugin;
import org.bukkit.scheduler.BukkitTask;
import org.json.JSONObject;

import java.net.http.HttpResponse;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;

/**
 * Fetches configurable message templates from
 * {@code GET /api/v1/settings/{key}} on startup and refreshes them every
 * 5 minutes so staff can edit wording from the dashboard without a
 * plugin reload.
 *
 * <p>Only the two in-game verification messages are fetched by the plugin:
 * <ul>
 *   <li>{@code verification.ingame_prompt} — shown after {@code /verify}</li>
 *   <li>{@code verification.ingame_success} — shown on successful link</li>
 * </ul>
 *
 * <p>Template variables use {@code $VARIABLE} syntax (uppercase). Call
 * {@link #render(String, Map)} to substitute them before sending to a player.
 *
 * <p>All network I/O runs off the main thread (Bukkit async scheduler).
 * On failure, the previously cached value (or the built-in default) is
 * kept — a transient core outage must never silence in-game messages.
 */
public class MessageTemplateManager {

    // Keys fetched from core.
    public static final String KEY_INGAME_PROMPT   = "verification.ingame_prompt";
    public static final String KEY_INGAME_SUCCESS  = "verification.ingame_success";

    // Greeter templates (P16E)
    public static final String KEY_GREETER_FIRST_JOIN  = "greeter.first_join_message";
    public static final String KEY_GREETER_RETURN_JOIN = "greeter.return_join_message";
    public static final String KEY_DISCORD_INVITE      = "discord.invite_url";

    // Chat responder settings (P16E)
    public static final String KEY_CHAT_RESPONDER_KEYWORDS = "chat_responder.keywords";
    public static final String KEY_CHAT_RESPONDER_COOLDOWN = "chat_responder.cooldown_seconds";
    public static final String KEY_CHAT_RESPONDER_STYLE    = "chat_responder.response_style";

    /** Built-in fallbacks used before the first successful fetch. */
    private static final Map<String, String> DEFAULTS;
    static {
        Map<String, String> d = new HashMap<>();
        d.put(KEY_INGAME_PROMPT,  "Check your Discord DMs to complete verification! Code expires in $EXPIRES.");
        d.put(KEY_INGAME_SUCCESS, "\u2705 Your Discord account has been linked successfully!");
        d.put(KEY_GREETER_FIRST_JOIN,  "Welcome to the server, $PLAYER! Join our Discord: $DISCORD_INVITE");
        d.put(KEY_GREETER_RETURN_JOIN, "Welcome back, $PLAYER!");
        d.put(KEY_DISCORD_INVITE,      "https://discord.gg/yourserver");
        d.put(KEY_CHAT_RESPONDER_KEYWORDS, "[\"how to join\",\"whats the ip\",\"what are the rules\"]");
        d.put(KEY_CHAT_RESPONDER_COOLDOWN, "60");
        d.put(KEY_CHAT_RESPONDER_STYLE,    "friendly and brief, 1-2 sentences max");
        DEFAULTS = Collections.unmodifiableMap(d);
    }

    private static final String[] KEYS = {
        KEY_INGAME_PROMPT, KEY_INGAME_SUCCESS,
        KEY_GREETER_FIRST_JOIN, KEY_GREETER_RETURN_JOIN, KEY_DISCORD_INVITE,
        KEY_CHAT_RESPONDER_KEYWORDS, KEY_CHAT_RESPONDER_COOLDOWN, KEY_CHAT_RESPONDER_STYLE,
    };

    private final Plugin plugin;
    private final CoreApiClient apiClient;

    /** Live template cache — concurrent because reads happen on the main thread
     *  while writes happen on the async refresh task. */
    private final ConcurrentHashMap<String, String> cache = new ConcurrentHashMap<>(DEFAULTS);

    private BukkitTask refreshTask;

    public MessageTemplateManager(Plugin plugin, CoreApiClient apiClient) {
        this.plugin   = plugin;
        this.apiClient = apiClient;
    }

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    /**
     * Perform an initial template fetch (async, off the main thread) and
     * schedule a periodic refresh every 5 minutes.
     * Call from {@link UmbrellaPlugin#onEnable()}.
     */
    public void start() {
        // Initial load — async so it never stalls server startup.
        plugin.getServer().getScheduler().runTaskAsynchronously(plugin, this::fetchAll);

        // 5-minute refresh: 20 ticks/sec × 60 sec × 5 = 6000 ticks.
        long periodTicks = 20L * 60 * 5;
        refreshTask = plugin.getServer().getScheduler()
                .runTaskTimerAsynchronously(plugin, this::fetchAll, periodTicks, periodTicks);
    }

    /** Cancel the refresh task. Call from {@link UmbrellaPlugin#onDisable()}. */
    public void stop() {
        if (refreshTask != null) {
            refreshTask.cancel();
            refreshTask = null;
        }
    }

    // ------------------------------------------------------------------
    // Template access
    // ------------------------------------------------------------------

    /**
     * Return the cached template for {@code key}, falling back to the
     * built-in default if the key has never been fetched successfully.
     */
    public String getTemplate(String key) {
        return cache.getOrDefault(key, DEFAULTS.getOrDefault(key, "[missing template: " + key + "]"));
    }

    /**
     * Replace {@code $VARIABLE} placeholders in {@code template} with
     * the values from {@code vars}.  Keys in {@code vars} are matched
     * case-insensitively (converted to upper-case before comparison).
     *
     * <p>Example:
     * <pre>
     *   Map&lt;String, String&gt; vars = Map.of("EXPIRES", "5 minutes");
     *   String msg = manager.render(manager.getTemplate(KEY_INGAME_PROMPT), vars);
     * </pre>
     *
     * @param template the raw template string (may contain {@code $VARIABLE})
     * @param vars     substitution map; keys should be the variable names
     *                 (e.g. {@code "EXPIRES"} or {@code "expires"})
     * @return the rendered string with all known placeholders replaced
     */
    public String render(String template, Map<String, String> vars) {
        for (Map.Entry<String, String> entry : vars.entrySet()) {
            template = template.replace("$" + entry.getKey().toUpperCase(), entry.getValue());
        }
        return template;
    }

    // ------------------------------------------------------------------
    // Internal fetch logic
    // ------------------------------------------------------------------

    /** Fetch all managed template keys from core. Runs on an async thread. */
    private void fetchAll() {
        for (String key : KEYS) {
            try {
                HttpResponse<String> response = apiClient.get("/api/v1/settings/" + key);
                if (response.statusCode() == 200) {
                    JSONObject body = new JSONObject(response.body());
                    String value = body.optString("value", "").trim();
                    if (!value.isEmpty() && !value.equals("***")) {
                        cache.put(key, value);
                        apiClient.logger().fine("MessageTemplate loaded: " + key);
                    }
                } else {
                    apiClient.logger().warning(
                            "MessageTemplate fetch rejected for " + key
                                    + ": HTTP " + response.statusCode());
                }
            } catch (Exception e) {
                apiClient.logger().log(Level.WARNING,
                        "MessageTemplate fetch failed for " + key + " — keeping cached value", e);
            }
        }
    }
}
