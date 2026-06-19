package com.umbrellaos.plugin.managers;

import com.umbrellaos.plugin.api.CoreApiClient;

import java.util.*;
import java.util.concurrent.CompletableFuture;

public class PunishmentManager {
    private final CoreApiClient apiClient;
    private final Map<UUID, List<Map<String, Object>>> punishmentCache = new HashMap<>();

    public PunishmentManager(CoreApiClient apiClient) {
        this.apiClient = apiClient;
    }

    public void refresh(UUID uuid) {
        apiClient.getPunishments(uuid.toString()).thenAccept(punishments -> {
            punishmentCache.put(uuid, punishments);
        }).exceptionally(e -> {
            e.printStackTrace();
            return null;
        });
    }

    public boolean isBanned(UUID uuid) {
        List<Map<String, Object>> punishments = punishmentCache.get(uuid);
        if (punishments == null) {
            return false;
        }
        for (Map<String, Object> punishment : punishments) {
            String type = (String) punishment.get("type");
            Boolean active = (Boolean) punishment.get("active");
            if (("ban".equalsIgnoreCase(type) || "tempban".equalsIgnoreCase(type)) && Boolean.TRUE.equals(active)) {
                return true;
            }
        }
        return false;
    }

    public boolean isMuted(UUID uuid) {
        List<Map<String, Object>> punishments = punishmentCache.get(uuid);
        if (punishments == null) {
            return false;
        }
        for (Map<String, Object> punishment : punishments) {
            String type = (String) punishment.get("type");
            Boolean active = (Boolean) punishment.get("active");
            if ("mute".equalsIgnoreCase(type) && Boolean.TRUE.equals(active)) {
                return true;
            }
        }
        return false;
    }

    public String getBanReason(UUID uuid) {
        List<Map<String, Object>> punishments = punishmentCache.get(uuid);
        if (punishments == null) {
            return null;
        }
        for (Map<String, Object> punishment : punishments) {
            String type = (String) punishment.get("type");
            Boolean active = (Boolean) punishment.get("active");
            if (("ban".equalsIgnoreCase(type) || "tempban".equalsIgnoreCase(type)) && Boolean.TRUE.equals(active)) {
                return (String) punishment.get("reason");
            }
        }
        return null;
    }
}
