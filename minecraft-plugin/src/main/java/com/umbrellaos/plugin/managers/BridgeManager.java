package com.umbrellaos.plugin.managers;

import com.umbrellaos.plugin.api.CoreApiClient;

import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class BridgeManager {
    private final CoreApiClient apiClient;
    private final int cacheSeconds;
    private String cachedBridgeMode = "off";
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    public BridgeManager(CoreApiClient apiClient, int cacheSeconds) {
        this.apiClient = apiClient;
        this.cacheSeconds = cacheSeconds;
    }

    public void start() {
        // Refresh bridge mode immediately
        refreshBridgeMode();
        // Schedule periodic refresh
        scheduler.scheduleAtFixedRate(this::refreshBridgeMode, cacheSeconds, cacheSeconds, TimeUnit.SECONDS);
    }

    private void refreshBridgeMode() {
        apiClient.asyncGet("/api/v1/settings/bridge.mode").thenAccept(response -> {
            try {
                // Parse the response - expecting JSON like {"value": "full"}
                // For simplicity, we'll just extract the value from the response
                if (response.contains("\"value\"")) {
                    String value = response.split("\"value\"")[1].split("\"")[1];
                    cachedBridgeMode = value;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).exceptionally(e -> {
            e.printStackTrace();
            return null;
        });
    }

    public String getBridgeMode() {
        return cachedBridgeMode;
    }

    public void shutdown() {
        scheduler.shutdown();
    }
}
