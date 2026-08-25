package com.umbrellaos.plugin;

import org.bukkit.Bukkit;
import org.bukkit.plugin.Plugin;
import org.bukkit.scheduler.BukkitTask;
import org.json.JSONObject;

import java.net.http.HttpResponse;
import java.util.logging.Level;

/**
 * Periodically POSTs {@code /api/v1/plugin/heartbeat} to core: online status
 * (implicit — a successful POST means the server is up), player count, real
 * server TPS, and plugin/server version.
 *
 * <p>Body shape is matched against umbrella-core's actual
 * {@code HeartbeatRequest} pydantic model in {@code api/routers/plugin.py}
 * (not just the scoping doc's prose description of it):
 * {@code server_id, server_name, online_count, tps, version, plugin_version,
 * grim_connected}.
 *
 * <p><b>{@code grim_connected} is hardcoded {@code false} in this step.</b>
 * The GrimAC bridge is explicitly Step 3's job (out of scope here) — wiring
 * this field to a real value happens then, not now. Flagged again in the
 * handback doc; not silently defaulted without a note.
 */
public class HeartbeatManager {

    private final Plugin plugin;
    private final CoreApiClient apiClient;
    private final ConfigManager configManager;
    private final String serverId;
    private final String serverName;
    /** Nullable — GrimAC is a soft-dependency; bridge may not be active. */
    private GrimBridge grimBridge;

    private BukkitTask task;
    private volatile boolean lastHeartbeatSucceeded = true;

    /** Legacy constructor — grim_connected will always report false. */
    public HeartbeatManager(Plugin plugin, CoreApiClient apiClient, ConfigManager configManager,
                             String serverId, String serverName) {
        this(plugin, apiClient, configManager, serverId, serverName, null);
    }

    /**
     * Full constructor — pass the GrimBridge so that {@code grim_connected}
     * in the heartbeat payload reflects the real runtime state of the GrimAC
     * integration (DEAD-4 fix). Pass {@code null} if GrimAC is not present.
     */
    public HeartbeatManager(Plugin plugin, CoreApiClient apiClient, ConfigManager configManager,
                             String serverId, String serverName, GrimBridge grimBridge) {
        this.plugin = plugin;
        this.apiClient = apiClient;
        this.configManager = configManager;
        this.serverId = (serverId == null || serverId.isBlank()) ? null : serverId;
        this.serverName = serverName;
        this.grimBridge = grimBridge;
    }

    /** Update the GrimBridge reference after construction (e.g. if GrimAC loads late). */
    public void setGrimBridge(GrimBridge grimBridge) {
        this.grimBridge = grimBridge;
    }

    /** Starts the periodic async heartbeat task. Safe to call once from onEnable. */
    public void start(long intervalSeconds) {
        long periodTicks = Math.max(1, intervalSeconds) * 20L; // 20 ticks/sec
        task = Bukkit.getScheduler().runTaskTimerAsynchronously(
                plugin, this::sendHeartbeatSafely, 0L, periodTicks);
    }

    /** Cancels the scheduled task. Call from onDisable. */
    public void stop() {
        if (task != null) {
            task.cancel();
            task = null;
        }
    }

    private void sendHeartbeatSafely() {
        try {
            sendHeartbeat();
        } catch (Exception e) {
            // Scheduler swallows exceptions from a repeating task and silently
            // stops rescheduling it if one escapes — never let that happen here.
            apiClient.logger().log(Level.WARNING, "Heartbeat failed unexpectedly", e);
            onFailure();
        }
    }

    private void sendHeartbeat() throws Exception {
        JSONObject body = new JSONObject();
        if (serverId != null) {
            body.put("server_id", serverId);
        }
        body.put("server_name", serverName);
        body.put("online_count", Bukkit.getOnlinePlayers().size());
        body.put("tps", realTps());
        body.put("version", Bukkit.getVersion());
        body.put("plugin_version", plugin.getDescription().getVersion());
        // Reflects real GrimAC bridge state (DEAD-4 fix). False when GrimBridge is
        // null (GrimAC absent) or not yet registered (GrimAC present but bridge
        // registration failed). True only when GrimAC is running and the EventBus
        // subscription succeeded.
        body.put("grim_connected", grimBridge != null && grimBridge.isRegistered());

        HttpResponse<String> response = apiClient.post("/api/v1/plugin/heartbeat", body.toString());

        if (response.statusCode() == 200) {
            onSuccess();
        } else {
            apiClient.logger().warning(
                    "Heartbeat rejected by core: HTTP " + response.statusCode() + " — " + response.body());
            onFailure();
        }
    }

    /**
     * Real server tick rate — Paper's {@code Server#getTPS()} rolling
     * average, not a hand-rolled tick-counter estimate. Index 0 is the
     * 1-minute average, the most responsive of the three Paper exposes.
     */
    private double realTps() {
        double[] tps = Bukkit.getServer().getTPS();
        double oneMinute = tps[0];
        // TPS can rarely report fractionally above 20 in Paper's rolling
        // average; core doesn't need to know about that implementation
        // detail, so clamp to the sane 0–20 range.
        return Math.max(0.0, Math.min(20.0, oneMinute));
    }

    private void onSuccess() {
        boolean wasDown = !lastHeartbeatSucceeded;
        lastHeartbeatSucceeded = true;
        if (wasDown) {
            // Reconnect: re-pull config now that core is reachable again,
            // per the scope's "on startup and on reconnect" requirement.
            apiClient.logger().info("Heartbeat succeeded after prior failure — treating as reconnect, refreshing config");
            configManager.refresh();
        }
    }

    private void onFailure() {
        lastHeartbeatSucceeded = false;
    }
}
