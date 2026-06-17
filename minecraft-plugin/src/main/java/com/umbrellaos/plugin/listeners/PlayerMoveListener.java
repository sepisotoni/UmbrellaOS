package com.umbrellaos.plugin.listeners;

import com.umbrellaos.plugin.models.ReplayEvent;
import com.umbrellaos.plugin.tasks.ReplayBufferTask;
import org.bukkit.Location;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerMoveEvent;

public class PlayerMoveListener implements Listener {
    private final ReplayBufferTask replayBufferTask;

    public PlayerMoveListener(ReplayBufferTask replayBufferTask) {
        this.replayBufferTask = replayBufferTask;
    }

    @EventHandler
    public void onPlayerMove(PlayerMoveEvent event) {
        // Only record if the player moved to a different block
        Location from = event.getFrom();
        Location to = event.getTo();
        
        if (to == null || (from.getBlockX() == to.getBlockX() && 
                           from.getBlockY() == to.getBlockY() && 
                           from.getBlockZ() == to.getBlockZ())) {
            return;
        }

        // Add move event to replay buffer
        ReplayEvent replayEvent = new ReplayEvent(
            "move",
            to.getX(),
            to.getY(),
            to.getZ(),
            to.getYaw(),
            to.getPitch(),
            null,
            System.currentTimeMillis()
        );
        
        replayBufferTask.addEvent(event.getPlayer().getUniqueId(), replayEvent);
    }
}
