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
 * client brand, ping, and protocol version. Sends player snapshots to umbrella-core
 * via {@code POST /api/v1/players/{uuid}/snapshot} and alt tracking via
 * {@code POST /api/v1/alts/track}.
 *
 * All network operations run asynchronously off the main thread.
 */
public class PlayerTelemetryListener implements Listener {

    private static final String SNAPSHOT_PATH_PREFIX = "/api/v1/players/";
    private static final String SNAPSHOT_PATH_SUFFIX = "/snapshot";
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

        String snapshotPayload = buildSnapshotPayload(uuid, name, ip, brand, ping, protocolVersion, eventType);
        String altPayload = buildAltTrackPayload(uuid, name, ip, brand);

        sendTelemetryAsync(uuid, snapshotPayload, altPayload);
    }

    private void sendTelemetryAsync(UUID uuid, String snapshotPayload, String altPayload) {
        if (plugin != null && plugin.isEnabled() && plugin.getServer() != null) {
            plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> dispatchTelemetry(uuid, snapshotPayload, altPayload));
        } else {
            dispatchTelemetry(uuid, snapshotPayload, altPayload);
        }
    }

    void dispatchTelemetry(UUID uuid, String snapshotPayload, String altPayload) {
        // Send snapshot payload
        try {
            HttpResponse<String> resp = apiClient.post(SNAPSHOT_PATH_PREFIX + uuid + SNAPSHOT_PATH_SUFFIX, snapshotPayload);
            if (resp.statusCode() >= 400 && resp.statusCode() != 404) {
                apiClient.logger().warning("[PlayerTelemetry] Snapshot post returned HTTP " + resp.statusCode() + " for " + uuid);
            }
        } catch (Exception e) {
            apiClient.logger().log(Level.FINE, "[PlayerTelemetry] Failed to post snapshot for " + uuid, e);
        }

        // Send alt tracking payload
        try {
            HttpResponse<String> resp = apiClient.post(ALT_TRACK_PATH, altPayload);
            if (resp.statusCode() >= 400 && resp.statusCode() != 404) {
                apiClient.logger().warning("[PlayerTelemetry] Alt track post returned HTTP " + resp.statusCode() + " for " + uuid);
            }
        } catch (Exception e) {
            apiClient.logger().log(Level.FINE, "[PlayerTelemetry] Failed to post alt track for " + uuid, e);
        }
    }

    public static String buildSnapshotPayload(UUID uuid, String name, String ip, String brand,
                                              int ping, int protocolVersion, String eventType) {
        JSONObject obj = new JSONObject();
        obj.put("uuid", uuid.toString());
        obj.put("name", name != null ? name : "unknown");
        obj.put("ip", ip != null ? ip : "127.0.0.1");
        obj.put("brand", brand != null && !brand.isBlank() ? brand : "vanilla");
        obj.put("ping", ping);
        obj.put("protocol_version", protocolVersion);
        obj.put("event_type", eventType != null ? eventType : "snapshot");
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
