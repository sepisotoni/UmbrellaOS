package com.umbrellaos.plugin;

import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.json.JSONObject;

import java.net.InetSocketAddress;
import java.net.http.HttpResponse;
import java.util.UUID;
import java.util.logging.Level;

/**
 * Listens to player join and quit events, capturing telemetry such as IP address,
 * client brand, ping, and protocol version. Sends this as an analytics event to
 * umbrella-core via {@code POST /api/v1/analytics/events}, and alt tracking via
 * {@code POST /api/v1/alts/track}.
 *
 * <p>FIX ([PLUGIN] subsystem audit): previously posted to
 * {@code /api/v1/players/{uuid}/snapshot} — a URL that has never existed in
 * core (that router is mounted at {@code /api/v1/snapshots}, takes no uuid
 * path segment, and expects a completely different payload shape: in-game
 * position/health/inventory for forensic incident replay, not connection
 * telemetry). Every post from this listener therefore received a 404,
 * silently swallowed (logged at FINE, which most server log configurations
 * don't even surface) — this "snapshot" feature has likely never actually
 * delivered a single event to core in any real deployment.
 *
 * <p>Retargeted at analytics.py's {@code /events} endpoint instead, which is
 * the actual intended destination: services/analytics_service.py's own
 * event-type alias table already maps "player_join"/"player_quit"/"snapshot"
 * (plugin-side naming) to the canonical "join"/"quit" types, with a comment
 * explicitly naming this class as the intended caller. The payload shape is
 * now {@code {event_type, minecraft_uuid, data: {name, ip, brand, ping,
 * protocol_version}}}, matching that endpoint's AnalyticsEventRequest schema
 * exactly, rather than the old flat structure that endpoint never expected.
 *
 * All network operations run asynchronously off the main thread.
 */
public class PlayerTelemetryListener implements Listener {

    private static final String ANALYTICS_EVENT_PATH = "/api/v1/analytics/events";
    private static final String ALT_TRACK_PATH = "/api/v1/alts/track";

    private final UmbrellaPlugin plugin;
    private final CoreApiClient apiClient;

    public PlayerTelemetryListener(UmbrellaPlugin plugin, CoreApiClient apiClient) {
        this.plugin = plugin;
        this.apiClient = apiClient;
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerJoin(PlayerJoinEvent event) {
        Player player = event.getPlayer();
        if (player == null) return;
        recordAndSendTelemetry(player, "join");
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
        if (player == null) return;
        recordAndSendTelemetry(player, "quit");
    }

    /**
     * Extracts telemetry info from the player, creates the payloads, and sends them asynchronously.
     */
    void recordAndSendTelemetry(Player player, String eventType) {
        if (plugin != null && !plugin.getConfig().getBoolean("telemetry.enabled", true)) {
            return;
        }

        UUID uuid = player.getUniqueId();
        String name = player.getName();
        String ip = extractIp(player);
        String brand = extractBrand(player);
        int ping = extractPing(player);
        int protocolVersion = extractProtocolVersion(player);

        String eventPayload = buildAnalyticsEventPayload(uuid, name, ip, brand, ping, protocolVersion, eventType);
        String altPayload = buildAltTrackPayload(uuid, name, ip, brand);

        sendTelemetryAsync(uuid, eventPayload, altPayload);
    }

    private void sendTelemetryAsync(UUID uuid, String eventPayload, String altPayload) {
        if (plugin != null && plugin.isEnabled() && plugin.getServer() != null) {
            plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> dispatchTelemetry(uuid, eventPayload, altPayload));
        } else {
            dispatchTelemetry(uuid, eventPayload, altPayload);
        }
    }

    void dispatchTelemetry(UUID uuid, String eventPayload, String altPayload) {
        // Send analytics event payload
        try {
            HttpResponse<String> resp = apiClient.post(ANALYTICS_EVENT_PATH, eventPayload);
            if (resp.statusCode() >= 400) {
                apiClient.logger().warning("[PlayerTelemetry] Analytics event post returned HTTP " + resp.statusCode() + " for " + uuid);
            }
        } catch (Exception e) {
            apiClient.logger().log(Level.FINE, "[PlayerTelemetry] Failed to post analytics event for " + uuid, e);
        }

        // Send alt tracking payload
        try {
            HttpResponse<String> resp = apiClient.post(ALT_TRACK_PATH, altPayload);
            if (resp.statusCode() >= 400) {
                apiClient.logger().warning("[PlayerTelemetry] Alt track post returned HTTP " + resp.statusCode() + " for " + uuid);
            }
        } catch (Exception e) {
            apiClient.logger().log(Level.FINE, "[PlayerTelemetry] Failed to post alt track for " + uuid, e);
        }
    }

    public static String buildAnalyticsEventPayload(UUID uuid, String name, String ip, String brand,
                                              int ping, int protocolVersion, String eventType) {
        // FIX ([PLUGIN] subsystem audit): renamed from buildSnapshotPayload
        // and restructured — the flat {uuid, name, ip, ..., event_type}
        // shape this used to build never matched any real endpoint's schema.
        // analytics.py's AnalyticsEventRequest expects event_type and
        // minecraft_uuid at the top level, with everything else nested
        // under "data" — matches record_event's actual signature
        // (event_type, minecraft_uuid, data: dict).
        JSONObject data = new JSONObject();
        data.put("name", name != null ? name : "unknown");
        data.put("ip", ip != null ? ip : "127.0.0.1");
        data.put("brand", brand != null && !brand.isBlank() ? brand : "vanilla");
        data.put("ping", ping);
        data.put("protocol_version", protocolVersion);

        JSONObject obj = new JSONObject();
        obj.put("event_type", eventType != null ? eventType : "snapshot");
        obj.put("minecraft_uuid", uuid.toString());
        obj.put("data", data);
        return obj.toString();
    }

    public static String buildAltTrackPayload(UUID uuid, String name, String ip, String brand) {
        JSONObject obj = new JSONObject();
        obj.put("uuid", uuid.toString());
        obj.put("name", name != null ? name : "unknown");
        obj.put("ip", ip != null ? ip : "127.0.0.1");
        obj.put("brand", brand != null && !brand.isBlank() ? brand : "vanilla");
        return obj.toString();
    }

    public static String extractIp(Player player) {
        if (player == null) return "127.0.0.1";
        try {
            InetSocketAddress addr = player.getAddress();
            if (addr != null && addr.getAddress() != null) {
                return addr.getAddress().getHostAddress();
            }
        } catch (Exception ignored) {}
        return "127.0.0.1";
    }

    public static String extractBrand(Player player) {
        if (player == null) return "vanilla";
        try {
            String brand = player.getClientBrandName();
            return (brand != null && !brand.isBlank()) ? brand : "vanilla";
        } catch (Throwable ignored) {
            return "vanilla";
        }
    }

    public static int extractPing(Player player) {
        if (player == null) return 0;
        try {
            return player.getPing();
        } catch (Throwable ignored) {
            return 0;
        }
    }

    public static int extractProtocolVersion(Player player) {
        if (player == null) return -1;
        try {
            return player.getProtocolVersion();
        } catch (Throwable ignored) {
            return -1;
        }
    }
}
