package com.umbrellaos.plugin.listeners;

import com.umbrellaos.plugin.api.CoreApiClient;
import com.umbrellaos.plugin.tasks.ReplayBufferTask;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.PlayerDeathEvent;

import java.util.HashMap;
import java.util.Map;

public class PlayerDeathListener implements Listener {
    private final CoreApiClient apiClient;
    private final ReplayBufferTask replayBufferTask;

    public PlayerDeathListener(CoreApiClient apiClient, ReplayBufferTask replayBufferTask) {
        this.apiClient = apiClient;
        this.replayBufferTask = replayBufferTask;
    }

    @EventHandler
    public void onPlayerDeath(PlayerDeathEvent event) {
        Player player = event.getEntity();
        String uuid = player.getUniqueId().toString();
        String deathMessage = event.getDeathMessage();

        // Build metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("x", player.getLocation().getX());
        metadata.put("y", player.getLocation().getY());
        metadata.put("z", player.getLocation().getZ());
        metadata.put("world", player.getWorld().getName());

        if (player.getKiller() != null) {
            metadata.put("killer_uuid", player.getKiller().getUniqueId().toString());
            metadata.put("killer_name", player.getKiller().getName());
        }

        // Post death event
        apiClient.postEvent("player_death", uuid, deathMessage, metadata).exceptionally(e -> {
            e.printStackTrace();
            return null;
        });

        // Trigger replay save
        replayBufferTask.saveReplay(player.getUniqueId(), "death", deathMessage).exceptionally(e -> {
            e.printStackTrace();
            return null;
        });
    }
}
