package com.umbrellaos.plugin.api;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import okhttp3.*;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public class CoreApiClient {
    private final OkHttpClient client;
    private final Gson gson;
    private final String baseUrl;
    private final String adminKey;

    public CoreApiClient(String baseUrl, String adminKey) {
        this.baseUrl = baseUrl;
        this.adminKey = adminKey;
        this.gson = new Gson();
        this.client = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .build();
    }

    public void shutdown() {
        client.dispatcher().executorService().shutdown();
        client.connectionPool().evictAll();
    }

    private Request.Builder buildRequest(String endpoint) {
        return new Request.Builder()
                .url(baseUrl + endpoint)
                .addHeader("X-Admin-Key", adminKey)
                .addHeader("Content-Type", "application/json");
    }

    private CompletableFuture<String> asyncPost(String endpoint, Object body) {
        CompletableFuture<String> future = new CompletableFuture<>();
        RequestBody requestBody = RequestBody.create(toJson(body), MediaType.parse("application/json"));
        Request request = buildRequest(endpoint).post(requestBody).build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                future.completeExceptionally(e);
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try {
                    if (!response.isSuccessful()) {
                        future.completeExceptionally(new ApiException(response.code(), response.body().string()));
                        return;
                    }
                    future.complete(response.body().string());
                } finally {
                    response.close();
                }
            }
        });

        return future;
    }

    public CompletableFuture<String> asyncGet(String endpoint) {
        CompletableFuture<String> future = new CompletableFuture<>();
        Request request = buildRequest(endpoint).get().build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                future.completeExceptionally(e);
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try {
                    if (!response.isSuccessful()) {
                        future.completeExceptionally(new ApiException(response.code(), response.body().string()));
                        return;
                    }
                    future.complete(response.body().string());
                } finally {
                    response.close();
                }
            }
        });

        return future;
    }

    private String toJson(Object obj) {
        return gson.toJson(obj);
    }

    private <T> T parseJson(String json, Class<T> clazz) {
        return gson.fromJson(json, clazz);
    }

    public CompletableFuture<Void> postEvent(String type, String playerUuid, String message, Map<String, Object> metadata) {
        JsonObject body = new JsonObject();
        body.addProperty("type", type);
        body.addProperty("player_uuid", playerUuid);
        body.addProperty("message", message);
        if (metadata != null) {
            JsonObject metaJson = gson.toJsonTree(metadata).getAsJsonObject();
            body.add("metadata", metaJson);
        }
        return asyncPost("/api/v1/bridge/event", body).thenApply(response -> null);
    }

    public CompletableFuture<String> requestVerification(String playerUuid, String username, String ipAddress) {
        JsonObject body = new JsonObject();
        body.addProperty("minecraft_uuid", playerUuid);
        body.addProperty("username", username);
        body.addProperty("ip_address", ipAddress);
        return asyncPost("/api/v1/verification/request", body).thenApply(response -> response);
    }

    public CompletableFuture<Boolean> confirmVerification(String discordId, String code) {
        JsonObject body = new JsonObject();
        body.addProperty("discord_id", discordId);
        body.addProperty("code", code);
        return asyncPost("/api/v1/verification/confirm", body).thenApply(response -> parseJson(response, Boolean.class));
    }

    public CompletableFuture<Boolean> checkVerificationStatus(String playerUuid) {
        return asyncGet("/api/v1/verification/status/" + playerUuid).thenApply(response -> parseJson(response, Boolean.class));
    }

    public CompletableFuture<List<Map<String, Object>>> getPunishments(String playerUuid) {
        return asyncGet("/api/v1/punishments/player/" + playerUuid).thenApply(response -> parseJson(response, List.class));
    }

    public CompletableFuture<Void> postBridgeMessage(String source, String playerUuid, String message) {
        JsonObject body = new JsonObject();
        body.addProperty("source", source);
        body.addProperty("player_uuid", playerUuid);
        body.addProperty("message", message);
        return asyncPost("/api/v1/bridge/message", body).thenApply(response -> null);
    }

    public CompletableFuture<Void> postSnapshot(String playerUuid, Map<String, Object> snapshotData) {
        JsonObject body = gson.toJsonTree(snapshotData).getAsJsonObject();
        body.addProperty("minecraft_uuid", playerUuid);
        return asyncPost("/api/v1/snapshots", body).thenApply(response -> null);
    }

    public CompletableFuture<Void> postReplayEvents(String sessionId, List<Map<String, Object>> events) {
        JsonObject body = new JsonObject();
        body.addProperty("session_id", sessionId);
        body.add("events", gson.toJsonTree(events));
        return asyncPost("/api/v1/replay/sessions/" + sessionId + "/events", body).thenApply(response -> null);
    }

    public CompletableFuture<String> createReplaySession(String playerUuid, String triggerType, String triggerReason) {
        JsonObject body = new JsonObject();
        body.addProperty("player_uuid", playerUuid);
        body.addProperty("trigger", triggerType);
        body.addProperty("trigger_reason", triggerReason);
        return asyncPost("/api/v1/replay/sessions", body).thenApply(response -> parseJson(response, Map.class).get("id").toString());
    }

    public CompletableFuture<Void> finalizeReplaySession(String sessionId) {
        return asyncPost("/api/v1/replay/sessions/" + sessionId + "/finalize", new JsonObject()).thenApply(response -> null);
    }

    public CompletableFuture<Map<String, Object>> checkAltDetection(String playerUuid, String ipAddress, String username) {
        JsonObject body = new JsonObject();
        body.addProperty("minecraft_uuid", playerUuid);
        body.addProperty("ip_address", ipAddress);
        body.addProperty("username", username);
        return asyncPost("/api/v1/alts/check", body).thenApply(response -> parseJson(response, Map.class));
    }

    public CompletableFuture<Void> postHeartbeat(int onlineCount, double tps) {
        JsonObject body = new JsonObject();
        body.addProperty("online_count", onlineCount);
        body.addProperty("tps", tps);
        return asyncPost("/api/v1/plugin/heartbeat", body).thenApply(response -> null);
    }
}
