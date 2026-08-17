package com.umbrellaos.plugin;

import org.json.JSONObject;

import java.net.http.HttpResponse;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;

/**
 * Pulls the non-sensitive settings bundle from {@code GET
 * /api/v1/plugin/config} and holds it as local plugin state. Called on
 * startup ({@link UmbrellaPlugin#onEnable()}) and again on reconnect (see
 * {@link HeartbeatManager}, which calls {@link #refresh()} when a heartbeat
 * succeeds after a prior failure).
 *
 * <p>Response shape verified against the real
 * {@code api/routers/plugin.py::plugin_config} handler, not just the
 * scoping doc's prose:
 * <pre>
 * {
 *   "settings": {"server.name": "...", ...},
 *   "by_category": {"server": {...}, "rcon": {...}, ...}
 * }
 * </pre>
 * Both maps use string keys and string values on the core side (settings
 * are stored and serialized as strings regardless of logical type) — this
 * class keeps them as strings too and leaves any typed parsing (int, bool,
 * etc.) to whichever future caller needs a specific setting, rather than
 * guessing a type here.
 */
public class ConfigManager {

    private final CoreApiClient apiClient;

    private volatile Map<String, String> flatSettings = Collections.emptyMap();
    private volatile Map<String, Map<String, String>> byCategory = Collections.emptyMap();
    private volatile boolean everLoaded = false;

    public ConfigManager(CoreApiClient apiClient) {
        this.apiClient = apiClient;
    }

    /**
     * Fetches and applies the current config from core. Safe to call
     * repeatedly (startup, and again on every reconnect). On failure, logs
     * and leaves the previously-applied settings in place rather than
     * clearing them — a transient fetch failure shouldn't blank out
     * everything the plugin already knew.
     */
    public void refresh() {
        try {
            HttpResponse<String> response = apiClient.get("/api/v1/plugin/config");
            if (response.statusCode() != 200) {
                apiClient.logger().warning(
                        "Config pull rejected by core: HTTP " + response.statusCode() + " — " + response.body());
                return;
            }
            apply(response.body());
            everLoaded = true;
        } catch (Exception e) {
            apiClient.logger().log(Level.WARNING, "Config pull failed", e);
        }
    }

    /**
     * Parses a raw {@code /api/v1/plugin/config} JSON response body and
     * applies it. Package-private and pure (no network call) specifically
     * so this parsing logic is unit-testable against fixed JSON fixtures.
     */
    void apply(String rawJsonBody) {
        JSONObject root = new JSONObject(rawJsonBody);

        Map<String, String> flat = new HashMap<>();
        JSONObject settingsObj = root.optJSONObject("settings", new JSONObject());
        for (String key : settingsObj.keySet()) {
            flat.put(key, String.valueOf(settingsObj.get(key)));
        }

        Map<String, Map<String, String>> categories = new ConcurrentHashMap<>();
        JSONObject byCategoryObj = root.optJSONObject("by_category", new JSONObject());
        for (String category : byCategoryObj.keySet()) {
            JSONObject categoryObj = byCategoryObj.optJSONObject(category, new JSONObject());
            Map<String, String> categoryMap = new HashMap<>();
            for (String key : categoryObj.keySet()) {
                categoryMap.put(key, String.valueOf(categoryObj.get(key)));
            }
            categories.put(category, Collections.unmodifiableMap(categoryMap));
        }

        this.flatSettings = Collections.unmodifiableMap(flat);
        this.byCategory = Collections.unmodifiableMap(categories);
    }

    /** Returns a setting's raw string value, or {@code null} if unknown. */
    public String getSetting(String key) {
        return flatSettings.get(key);
    }

    /** Same as {@link #getSetting(String)} but with a fallback default. */
    public String getSetting(String key, String defaultValue) {
        return flatSettings.getOrDefault(key, defaultValue);
    }

    public Map<String, String> getCategory(String category) {
        return byCategory.getOrDefault(category, Collections.emptyMap());
    }

    /** Whether a successful config pull has ever completed since plugin start. */
    public boolean isLoaded() {
        return everLoaded;
    }
}
