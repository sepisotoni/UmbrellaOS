package com.umbrellaos.plugin.listeners;

import com.umbrellaos.plugin.api.CoreApiClient;
import org.bukkit.advancement.Advancement;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerAdvancementDoneEvent;

public class PlayerAchievementListener implements Listener {
    private final CoreApiClient apiClient;

    public PlayerAchievementListener(CoreApiClient apiClient) {
        this.apiClient = apiClient;
    }

    @EventHandler
    public void onPlayerAdvancement(PlayerAdvancementDoneEvent event) {
        Advancement advancement = event.getAdvancement();
        
        // Filter out recipe unlocks (only real advancements)
        if (advancement.getKey().getKey().startsWith("recipes/")) {
            return;
        }

        String uuid = event.getPlayer().getUniqueId().toString();
        String title = advancement.getKey().getKey();

        // Post achievement event
        apiClient.postEvent("achievement", uuid, title, null).exceptionally(e -> {
            e.printStackTrace();
            return null;
        });
    }
}
