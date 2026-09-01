package com.umbrellaos.plugin;

import org.bukkit.Bukkit;
import org.bukkit.plugin.Plugin;
import org.bukkit.scheduler.BukkitTask;
import org.json.JSONArray;
import org.json.JSONObject;

import java.net.URLEncoder;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;

/**
 * Periodically polls {@code GET /api/v1/mc/commands/pending}, executes each
 * command on the server's main thread (Bukkit command dispatch is not
 * thread-safe), and acknowledges the result via
 * {@code POST /api/v1/mc/commands/{id}/complete}.
 *
 * <p>Network calls (the poll itself, and the completion ack) run off the
 * main thread via {@link CoreApiClient}; only the actual in-game command
 * dispatch is marshalled onto the main thread — same async-network /
 * sync-Bukkit-API split {@link HeartbeatManager} already established.
 *
 * <p>FIX ([PLUGIN] subsystem audit): the poll previously fetched every
 * pending command globally with no server scoping, despite core already
 * supporting multiple Minecraft servers under one umbrella-core instance
 * (the Node/Server/daemon system). In a real fleet, every plugin instance
 * would execute every OTHER server's queued commands too, since core's
 * mc_commands table had no server_id column at all until this fix.
 * {@link HeartbeatManager} already threads {@code serverId} through from
 * {@link UmbrellaPlugin}; this class previously didn't take it as a
 * constructor argument at all, even though the exact same value was
 * already available at the exact same construction site.
 */
public class CommandPoller {

    /** One pending command as returned by the core endpoint. */
    record PendingCommand(long id, String command) {}

    private final Plugin plugin;
    private final CoreApiClient apiClient;
    private final String serverId;

    private BukkitTask task;

    /**
     * @param serverId this server's configured ID (same value passed to
     *                 {@link HeartbeatManager}), or null/blank if not yet
     *                 configured — in which case the poll omits the
     *                 server_id query param entirely and core's own
     *                 "default" column default applies, preserving
     *                 pre-fix behavior for any deployment that hasn't set
     *                 one.
     */
    public CommandPoller(Plugin plugin, CoreApiClient apiClient, String serverId) {
        this.plugin = plugin;
        this.apiClient = apiClient;
        this.serverId = (serverId == null || serverId.isBlank()) ? null : serverId;
    }

    /** Starts the periodic async poll task. Safe to call once from onEnable. */
    public void start(long intervalSeconds) {
        long periodTicks = Math.max(1, intervalSeconds) * 20L; // 20 ticks/sec
        task = Bukkit.getScheduler().runTaskTimerAsynchronously(
                plugin, this::pollSafely, 0L, periodTicks);
    }

    /** Cancels the scheduled task. Call from onDisable. */
    public void stop() {
        if (task != null) {
            task.cancel();
            task = null;
        }
    }

    private void pollSafely() {
        try {
            poll();
        } catch (Exception e) {
            // Same rationale as HeartbeatManager.sendHeartbeatSafely: a
            // repeating task that throws is silently de-scheduled by Bukkit
            // and never runs again — never let that happen here.
            apiClient.logger().log(Level.WARNING, "Command poll failed unexpectedly", e);
        }
    }

    private void poll() throws Exception {
        String path = "/api/v1/mc/commands/pending";
        if (serverId != null) {
            path += "?server_id=" + URLEncoder.encode(serverId, StandardCharsets.UTF_8);
        }
        HttpResponse<String> response = apiClient.get(path);
        if (response.statusCode() != 200) {
            apiClient.logger().warning(
                    "Command poll rejected by core: HTTP " + response.statusCode() + " — " + response.body());
            return;
        }

        List<PendingCommand> pending = parsePendingCommands(response.body());
        for (PendingCommand cmd : pending) {
            // Hop onto the main thread to actually run the command — Bukkit
            // command dispatch must happen there. The completion ack (network
            // I/O) hops back off it once execution finishes; see executeAndAck.
            Bukkit.getScheduler().runTask(plugin, () -> executeAndAck(cmd));
        }
    }

    /**
     * Parses a raw {@code GET /api/v1/mc/commands/pending} JSON array body.
     * Package-private, static, and pure (no network, no Bukkit calls)
     * specifically so this parsing logic is unit-testable against fixed JSON
     * fixtures — same pattern as {@link ConfigManager#apply}.
     */
    static List<PendingCommand> parsePendingCommands(String rawJsonBody) {
        List<PendingCommand> result = new ArrayList<>();
        JSONArray array = new JSONArray(rawJsonBody);
        for (int i = 0; i < array.length(); i++) {
            JSONObject obj = array.getJSONObject(i);
            result.add(new PendingCommand(obj.getLong("id"), obj.getString("command")));
        }
        return result;
    }

    private void executeAndAck(PendingCommand cmd) {
        boolean success;
        String output;
        try {
            // dispatchCommand's boolean return means "a command handler was
            // found and ran without throwing" — not "the command's own logic
            // considered itself successful" (Bukkit has no generic way to
            // observe that for an arbitrary third-party command). Good enough
            // signal for the queue's ack; a command that runs but reports its
            // own internal failure (e.g. "player not found") still shows up
            // in server console/logs, just not reflected in this ack.
            success = Bukkit.dispatchCommand(Bukkit.getConsoleSender(), cmd.command());
            output = success
                    ? "Executed via UmbrellaOS command queue"
                    : "Unknown or unrecognized command: " + cmd.command();
        } catch (Exception e) {
            success = false;
            output = "Exception during execution: " + e.getMessage();
            apiClient.logger().log(Level.WARNING, "Command execution threw for id=" + cmd.id(), e);
        }

        boolean finalSuccess = success;
        String finalOutput = output;
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> ack(cmd.id(), finalSuccess, finalOutput));
    }

    private void ack(long commandId, boolean success, String output) {
        JSONObject body = new JSONObject();
        body.put("success", success);
        body.put("output", output);
        try {
            HttpResponse<String> response = apiClient.post(
                    "/api/v1/mc/commands/" + commandId + "/complete", body.toString());
            if (response.statusCode() != 200) {
                apiClient.logger().warning(
                        "Command completion ack rejected by core: HTTP " + response.statusCode()
                                + " — " + response.body());
            }
        } catch (Exception e) {
            apiClient.logger().log(Level.WARNING, "Command completion ack failed for id=" + commandId, e);
        }
    }
}

