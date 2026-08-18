package com.umbrellaos.plugin;

import net.kyori.adventure.text.Component;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.AsyncPlayerPreLoginEvent;
import org.json.JSONObject;

import java.net.http.HttpResponse;
import java.util.logging.Level;

/**
 * Enforces active bans at connection time via {@link AsyncPlayerPreLoginEvent}
 * — chosen over {@code PlayerLoginEvent}/{@code PlayerJoinEvent} specifically
 * because Paper fires this one off the main thread already, which is
 * required here since the ban check is a blocking HTTP call to core;
 * blocking the main thread on network I/O would freeze the whole server.
 *
 * <p>Uses the new plugin-key-authorized {@code GET
 * /api/v1/plugin/punishments/{player_uuid}/active} endpoint (Phase 13 Step
 * 2) — see that endpoint's docstring in umbrella-core's {@code plugin.py}
 * for why it exists (the plugin has no RBAC identity to use the real
 * {@code punishments.view}-gated {@code GET /api/v1/punishments}).
 *
 * <p><b>Fails open on a core-side/network error</b> — see {@link
 * #onAsyncPreLogin}. This is a real, explicit design choice, not a silent
 * gap; flagged again in the handback doc for Sepiso Toni to confirm.
 */
public class BanEnforcer implements Listener {

    private final CoreApiClient apiClient;

    public BanEnforcer(CoreApiClient apiClient) {
        this.apiClient = apiClient;
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onAsyncPreLogin(AsyncPlayerPreLoginEvent event) {
        // Don't bother checking a connection some higher-priority listener
        // has already rejected (server full, etc.) — nothing to enforce.
        if (event.getLoginResult() != AsyncPlayerPreLoginEvent.Result.ALLOWED) {
            return;
        }

        String playerUuid = event.getUniqueId().toString();
        BanCheckResult result;
        try {
            result = checkActiveBan(playerUuid);
        } catch (Exception e) {
            // Fail open: an unreachable core (or a bad response) should not
            // lock every player out of the server. HeartbeatManager's
            // watchdog path is what's meant to surface core being down, not
            // a login-time hard-fail here. This is the safer default for a
            // community server, but it IS a real choice with a real
            // consequence (a ban silently doesn't apply while core is down)
            // — not defaulted silently, called out in the handback.
            apiClient.logger().log(Level.WARNING,
                    "Ban check failed for " + playerUuid + " — failing open (allowing join)", e);
            return;
        }

        if (result.banned()) {
            event.disallow(AsyncPlayerPreLoginEvent.Result.KICK_BANNED, Component.text(banMessage(result)));
        }
    }

    /** One parsed active-punishment check result. Package-private for tests. */
    record BanCheckResult(boolean banned, String type, String reason, String expiresAt) {}

    /**
     * Calls the ban-check endpoint and parses the response. Split out from
     * the event handler so the network call and the parsing can each be
     * exercised independently in tests — the call via a mocked {@link
     * CoreApiClient}, the parsing via {@link #parseBanCheckResponse} against
     * fixed JSON fixtures.
     */
    BanCheckResult checkActiveBan(String playerUuid) throws Exception {
        HttpResponse<String> response = apiClient.get("/api/v1/plugin/punishments/" + playerUuid + "/active");
        if (response.statusCode() != 200) {
            throw new IllegalStateException(
                    "Ban check endpoint returned HTTP " + response.statusCode() + " — " + response.body());
        }
        return parseBanCheckResponse(response.body());
    }

    /**
     * Parses a raw {@code GET /api/v1/plugin/punishments/{uuid}/active} JSON
     * response body: {@code {"banned": bool, "punishment": {...} | null}}.
     * Package-private, static, and pure (no network call) specifically so
     * this parsing logic is unit-testable against fixed JSON fixtures — same
     * pattern as {@link ConfigManager#apply}.
     */
    static BanCheckResult parseBanCheckResponse(String rawJsonBody) {
        JSONObject root = new JSONObject(rawJsonBody);
        boolean banned = root.optBoolean("banned", false);
        if (!banned) {
            return new BanCheckResult(false, null, null, null);
        }
        JSONObject punishment = root.optJSONObject("punishment");
        if (punishment == null) {
            // Defensive: "banned": true with no punishment object shouldn't
            // happen per the endpoint's real contract, but don't NPE if core
            // ever sends something unexpected — treat as banned with unknown
            // details rather than crashing the login flow.
            return new BanCheckResult(true, "unknown", "No reason provided", null);
        }
        return new BanCheckResult(
                true,
                punishment.optString("type", "ban"),
                punishment.optString("reason", "No reason provided"),
                punishment.isNull("expires_at") ? null : punishment.optString("expires_at", null));
    }

    private static String banMessage(BanCheckResult result) {
        StringBuilder sb = new StringBuilder();
        sb.append("You are banned from this server.\nReason: ").append(result.reason());
        if (result.expiresAt() != null) {
            sb.append("\nExpires: ").append(result.expiresAt());
        } else {
            sb.append("\nThis ban does not expire.");
        }
        return sb.toString();
    }
}

