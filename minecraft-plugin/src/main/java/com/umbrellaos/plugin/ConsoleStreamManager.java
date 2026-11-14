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
    private static final String DEFAULT_SERVER_ID = "default";

    private final int capacity;
    private final Deque<BufferedLine> buffer;
    private final Object lock = new Object();
    private final Object pushLock = new Object();
    private Handler logHandler;
    /** The repeating task scheduled by startPushing(), cancelled in stopPushing(). */
    private volatile BukkitTask pushTask;
    private long nextSequence = 0;
    private long nextToSend = 0;

    private record BufferedLine(long sequence, String text) {}

    record Batch(long startSequence, long endSequence, List<String> lines) {
        Batch {
            lines = List.copyOf(lines);
        }
    }

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
                BufferedLine removed = buffer.removeFirst();
                if (removed.sequence() >= nextToSend) {
                    nextToSend = removed.sequence() + 1;
                }
            }
            buffer.addLast(new BufferedLine(nextSequence++, line));
        }
    }

    /**
     * Returns a copy of all recent buffered console log lines in chronological order.
     */
    public List<String> getRecentLines() {
        synchronized (lock) {
            List<String> lines = new ArrayList<>(buffer.size());
            for (BufferedLine line : buffer) {
                lines.add(line.text());
            }
            return lines;
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
            for (BufferedLine line : buffer) {
                if (i >= skip) {
                    result.add(line.text());
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
            nextToSend = nextSequence;
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

    /** Returns the oldest unsent lines without advancing the upload cursor. */
    Batch nextBatch(int maxLines) {
        synchronized (lock) {
            if (maxLines <= 0) {
                return new Batch(nextToSend, nextToSend, Collections.emptyList());
            }
            List<String> result = new ArrayList<>(Math.min(maxLines, buffer.size()));
            long endSequence = nextToSend;
            for (BufferedLine line : buffer) {
                if (line.sequence() < nextToSend) continue;
                if (result.size() == maxLines) break;
                result.add(line.text());
                endSequence = line.sequence() + 1;
            }
            return new Batch(nextToSend, endSequence, result);
        }
    }

    /** Advances the cursor only for a successful upload of the current batch. */
    void confirmUploaded(Batch batch) {
        if (batch == null || batch.lines().isEmpty()) return;
        synchronized (lock) {
            if (nextToSend < batch.endSequence()) {
                nextToSend = Math.max(nextToSend, batch.endSequence());
            }
        }
    }

    /**
     * Schedules a repeating Bukkit task that pushes the oldest unsent console
     * lines to umbrella-core. A batch is marked sent only after core confirms
     * a successful upload.
     *
     * @param plugin        owning plugin (needed for scheduler)
     * @param client        authenticated core API client
     * @param serverId      the server's umbrella-core server_id
     * @param intervalTicks ticks between pushes (100 = 5s at 20 TPS)
     */
    public void startPushing(JavaPlugin plugin, CoreApiClient client, String serverId, long intervalTicks) {
        if (pushTask != null) return; // already started
        String normalizedServerId = normalizeServerId(serverId);
        pushTask = plugin.getServer().getScheduler().runTaskTimerAsynchronously(plugin, () -> {
            synchronized (pushLock) {
                Batch batch = nextBatch(50);
                if (batch.lines().isEmpty()) return;

                // Build JSON array using JSONArray so all control chars are
                // correctly escaped (DESIGN-3 fix — org.json is already shaded in).
                JSONArray arr = new JSONArray(batch.lines());
                String body = "{\"lines\": " + arr.toString() + "}";

                try {
                    HttpResponse<String> resp = client.post(
                            "/api/v1/plugin/servers/" + normalizedServerId + "/console/lines", body);
                    if (resp.statusCode() >= 200 && resp.statusCode() < 300) {
                        confirmUploaded(batch);
                    } else {
                        client.logger().warning("[ConsoleStreamManager] Push returned HTTP "
                                + resp.statusCode() + " — " + resp.body());
                    }
                } catch (IOException | InterruptedException e) {
                    if (e instanceof InterruptedException) Thread.currentThread().interrupt();
                    client.logger().warning("[ConsoleStreamManager] Push failed: " + e.getMessage());
                }
            }
        }, intervalTicks, intervalTicks);
    }

    static String normalizeServerId(String serverId) {
        return serverId == null || serverId.isBlank() ? DEFAULT_SERVER_ID : serverId;
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
