package com.umbrellaos.plugin;

import org.bukkit.plugin.java.JavaPlugin;

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
import java.util.stream.Collectors;

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
    public void startPushing(JavaPlugin plugin, CoreApiClient client, String serverId, long intervalTicks) {
        plugin.getServer().getScheduler().runTaskTimerAsynchronously(plugin, () -> {
            List<String> lines = getRecentLines(50);
            if (lines.isEmpty()) return;

            // Build JSON array of line strings
            String jsonArray = lines.stream()
                    .map(l -> "\"" + l.replace("\\", "\\\\").replace("\"", "\\\"")
                            .replace("\n", "\\n").replace("\r", "\\r") + "\"")
                    .collect(Collectors.joining(",", "[", "]"));
            String body = "{\"lines\": " + jsonArray + "}";

            try {
                HttpResponse<String> resp = client.post(
                        "/api/v1/plugin/servers/" + serverId + "/console/lines", body);
                if (resp.statusCode() != 200) {
                    client.logger().warning("[ConsoleStreamManager] Push returned HTTP "
                            + resp.statusCode() + " — " + resp.body());
                }
            } catch (IOException | InterruptedException e) {
                client.logger().warning("[ConsoleStreamManager] Push failed: " + e.getMessage());
            }
        }, intervalTicks, intervalTicks);
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
