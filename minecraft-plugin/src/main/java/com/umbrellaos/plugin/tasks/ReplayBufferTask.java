package com.umbrellaos.plugin.tasks;

import com.umbrellaos.plugin.api.CoreApiClient;
import com.umbrellaos.plugin.models.ReplayEvent;
import org.bukkit.Bukkit;
import org.bukkit.scheduler.BukkitRunnable;

import java.util.*;
import java.util.concurrent.CompletableFuture;

public class ReplayBufferTask extends BukkitRunnable {
    private final CoreApiClient apiClient;
    private final int bufferSeconds;
    private final Map<UUID, Deque<ReplayEvent>> buffers = new HashMap<>();

    public ReplayBufferTask(CoreApiClient apiClient, int bufferSeconds) {
        this.apiClient = apiClient;
        this.bufferSeconds = bufferSeconds;
    }

    @Override
    public void run() {
        // Prune old events from all buffers
        long cutoffTime = System.currentTimeMillis() - (bufferSeconds * 1000L);
        for (Deque<ReplayEvent> buffer : buffers.values()) {
            while (!buffer.isEmpty() && buffer.peekFirst().getTimestamp() < cutoffTime) {
                buffer.pollFirst();
            }
        }
    }

    public void addEvent(UUID playerUuid, ReplayEvent event) {
        buffers.computeIfAbsent(playerUuid, k -> new ArrayDeque<>()).addLast(event);
    }

    public CompletableFuture<String> saveReplay(UUID playerUuid, String triggerType, String triggerReason) {
        Deque<ReplayEvent> buffer = buffers.get(playerUuid);
        if (buffer == null || buffer.isEmpty()) {
            return CompletableFuture.completedFuture(null);
        }

        return apiClient.createReplaySession(playerUuid.toString(), triggerType, triggerReason).thenCompose(sessionId -> {
            // Convert events to maps for API
            List<Map<String, Object>> events = new ArrayList<>();
            for (ReplayEvent event : buffer) {
                Map<String, Object> eventMap = new HashMap<>();
                eventMap.put("type", event.getType());
                eventMap.put("x", event.getX());
                eventMap.put("y", event.getY());
                eventMap.put("z", event.getZ());
                eventMap.put("yaw", event.getYaw());
                eventMap.put("pitch", event.getPitch());
                eventMap.put("timestamp", event.getTimestamp());
                if (event.getData() != null) {
                    eventMap.put("data", event.getData());
                }
                events.add(eventMap);
            }

            // Post events in batches of 500
            CompletableFuture<Void> postFuture = CompletableFuture.completedFuture(null);
            for (int i = 0; i < events.size(); i += 500) {
                int end = Math.min(i + 500, events.size());
                List<Map<String, Object>> batch = events.subList(i, end);
                postFuture = postFuture.thenCompose(v -> apiClient.postReplayEvents(sessionId, batch));
            }

            return postFuture.thenApply(v -> sessionId).thenCompose(sessionIdFinal -> {
                return apiClient.finalizeReplaySession(sessionIdFinal).thenApply(vv -> sessionIdFinal);
            });
        }).whenComplete((sessionId, throwable) -> {
            if (throwable != null) {
                throwable.printStackTrace();
            }
            // Clear buffer after save
            buffers.remove(playerUuid);
        });
    }

    public void clearBuffer(UUID playerUuid) {
        buffers.remove(playerUuid);
    }
}
