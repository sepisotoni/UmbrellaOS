package com.umbrellaos.plugin.listeners;

import com.umbrellaos.plugin.api.CoreApiClient;
import com.umbrellaos.plugin.managers.VerificationManager;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerQuitEvent;

public class PlayerQuitListener implements Listener {
    private final CoreApiClient apiClient;
    private final VerificationManager verificationManager;

    public PlayerQuitListener(CoreApiClient apiClient, VerificationManager verificationManager) {
        this.apiClient = apiClient;
        this.verificationManager = verificationManager;
    }

    @EventHandler
    public void onPlayerQuit(PlayerQuitEvent event) {
        String uuid = event.getPlayer().getUniqueId().toString();
        String username = event.getPlayer().getName();

        // Remove from verification limbo if present
        verificationManager.removeFromLimbo(event.getPlayer().getUniqueId());

        // Post leave event
        apiClient.postEvent("player_leave", uuid, username, null).exceptionally(e -> {
            e.printStackTrace();
            return null;
        });
    }
}
