package com.umbrellaos.plugin.managers;

import com.umbrellaos.plugin.api.CoreApiClient;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

public class AnticheatManager {
    private final CoreApiClient apiClient;
    private volatile boolean enabled = true;

    public AnticheatManager(CoreApiClient apiClient) {
        this.apiClient = apiClient;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public CompletableFuture<Map<String, Object>> handleFlag(
            UUID uuid, String username, String checkName, String verbose, int vl) {
        if (!enabled) {
            return CompletableFuture.completedFuture(Map.of("processed", false));
        }
        return apiClient.postAnticheatFlag(uuid.toString(), username, checkName, verbose, vl);
    }
}
