package com.umbrellaos.plugin;

import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

import org.json.JSONArray;

import java.io.IOException;
import java.net.http.HttpResponse;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.List;
import java.util.logging.Formatter;
import java.util.logging.Handler;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.logging.SimpleFormatter;

/**
 * Thread-safe manager for capturing and buffering server console log lines.
 * Uses a ring buffer (bounded Deque) with a configurable capacity (default 500 lines)
 * and attaches a logging Handler to capture live server console output.
 */
public class ConsoleStreamManager {

    public static final int DEFAULT_CAPACITY = 500;

    private final int capacity;
    private final Deque<String> buffer;
    private final Object lock = new Object();
    private Handler logHandler;
    /** The repeating task scheduled by startPushing(), cancelled in stopPushing(). */
    private volatile BukkitTask pushTask;
    /** Total lines ever appended — used for delta tracking so we only push new lines. */
    private long totalAppended = 0;
    /** Total lines that have been pushed to core — only send lines after this index. */
    private long totalPushed = 0;

    public ConsoleStreamManager() {
        this(DEFAULT_CAPACITY);
    }

    public ConsoleStreamManager(int capacity) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("Capacity must be positive");
        }
        this.capacity = capacity;
        this.buffer = new ArrayDeque<>(capacity);
    }

    /**
     * Appends a log line to the ring buffer. If the buffer has reached maximum capacity,
     * the oldest line is discarded. Thread-safe.
     */
    public void appendLine(String line) {
        if (line == null) return;
        synchronized (lock) {
            while (buffer.size() >= capacity) {
                buffer.removeFirst();
            }
            buffer.addLast(line);
            totalAppended++;
        }
    }

    /**
     * Returns a copy of all recent buffered console log lines in chronological order.
     */
    public List<String> getRecentLines() {
        synchronized (lock) {
            return new ArrayList<>(buffer);
        }
    }

    /**
     * Returns up to {@code maxLines} of the most recent console log lines in chronological order.
     */
    public List<String> getRecentLines(int maxLines) {
        if (maxLines <= 0) {
            return Collections.emptyList();
        }
        synchronized (lock) {
            int count = Math.min(maxLines, buffer.size());
            List<String> result = new ArrayList<>(count);
            int skip = buffer.size() - count;
            int i = 0;
            for (String line : buffer) {
                if (i >= skip) {
                    result.add(line);
                }
                i++;
            }
            return result;
        }
    }

    /**
     * Returns the current number of buffered lines.
     */
    public int getLineCount() {
        synchronized (lock) {
            return buffer.size();
        }
    }

    /**
     * Returns the maximum buffer capacity.
     */
    public int getCapacity() {
        return capacity;
    }

    /**
     * Clears all buffered console lines.
     */
    public void clear() {
        synchronized (lock) {
            buffer.clear();
        }
    }

    /**
     * Attaches a logging handler to the root logger to capture console log records automatically.
     */
    public synchronized void startCapture() {
        if (logHandler != null) return;
        logHandler = new Handler() {
            private final Formatter formatter = new SimpleFormatter();

            @Override
            public void publish(LogRecord record) {
                if (record == null || record.getMessage() == null) return;
                try {
                    String msg = formatter.formatMessage(record);
                    String level = record.getLevel() != null ? record.getLevel().getName() : "INFO";
                    String line = "[" + level + "] " + msg;
                    appendLine(line);
                } catch (Exception ignored) {}
            }

            @Override
            public void flush() {}

            @Override
            public void close() throws SecurityException {}
        };

        try {
            Logger.getLogger("").addHandler(logHandler);
        } catch (Exception ignored) {}
    }

    /**
     * Schedules a repeating Bukkit task that pushes the most recent console
     * lines to umbrella-core every {@code intervalTicks} ticks (100 ticks = 5s).
     *
     * <p>The task sends the last {@code batchSize} lines each cycle. Core
     * stores them capped at 500 per server and the dashboard polls the GET
     * endpoint to display them when WebSocket is unavailable.
     *
     * @param plugin        owning plugin (needed for scheduler)
     * @param client        authenticated core API client
     * @param serverId      the server's umbrella-core server_id
     * @param intervalTicks ticks between pushes (100 = 5s at 20 TPS)
     */
    /**
     * Returns lines appended since the last push call (delta only), capped at
     * {@code maxLines}. Advances {@code totalPushed} so subsequent calls don't
     * resend already-sent lines.
     */
    /** Package-private for testing. Production callers use startPushing(). */
    List<String> drainNewLines(int maxLines) {
        synchronized (lock) {
            long newCount = totalAppended - totalPushed;
            if (newCount <= 0) return Collections.emptyList();
            int take = (int) Math.min(newCount, maxLines);
            // Lines are in the buffer oldest-first; we want the newest `take` that haven't been sent.
            // totalPushed tracks how many have been sent; buffer may have evicted oldest under capacity.
            List<String> all = new ArrayList<>(buffer);
            int fromIndex = Math.max(0, all.size() - take);
            List<String> result = new ArrayList<>(all.subList(fromIndex, all.size()));
            totalPushed += result.size();
            return result;
        }
    }

    public void startPushing(JavaPlugin plugin, CoreApiClient client, String serverId, long intervalTicks) {
        if (pushTask != null) return; // already started
        pushTask = plugin.getServer().getScheduler().runTaskTimerAsynchronously(plugin, () -> {
            // Only send lines we haven't sent yet (delta tracking).
            List<String> lines = drainNewLines(50);
            if (lines.isEmpty()) return;

            // Build JSON array using JSONArray so all control chars are
            // correctly escaped (DESIGN-3 fix — org.json is already shaded in).
            JSONArray arr = new JSONArray(lines);
            String body = "{\"lines\": " + arr.toString() + "}";

            try {
                HttpResponse<String> resp = client.post(
                        "/api/v1/plugin/servers/" + serverId + "/console/lines", body);
                if (resp.statusCode() != 200) {
                    client.logger().warning("[ConsoleStreamManager] Push returned HTTP "
                            + resp.statusCode() + " — " + resp.body());
                }
            } catch (IOException | InterruptedException e) {
                if (e instanceof InterruptedException) Thread.currentThread().interrupt();
                client.logger().warning("[ConsoleStreamManager] Push failed: " + e.getMessage());
            }
        }, intervalTicks, intervalTicks);
    }

    /**
     * Cancels the repeating push task. Safe to call if startPushing() was never called.
     * Called from UmbrellaPlugin.onDisable() so the task doesn't outlive the plugin.
     */
    public void stopPushing() {
        if (pushTask != null) {
            pushTask.cancel();
            pushTask = null;
        }
    }

    /**
     * Removes the logging handler from the root logger.
     */
    public synchronized void stopCapture() {
        if (logHandler != null) {
            try {
                Logger.getLogger("").removeHandler(logHandler);
            } catch (Exception ignored) {}
            logHandler = null;
        }
    }

    public synchronized boolean isCapturing() {
        return logHandler != null;
    }
}
