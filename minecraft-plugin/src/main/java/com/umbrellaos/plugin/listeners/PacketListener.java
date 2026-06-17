package com.umbrellaos.plugin.listeners;

import com.comphenix.protocol.PacketType;
import com.comphenix.protocol.events.ListenerPriority;
import com.comphenix.protocol.events.PacketAdapter;
import com.comphenix.protocol.events.PacketEvent;
import com.google.gson.JsonObject;
import com.umbrellaos.plugin.models.ReplayEvent;
import com.umbrellaos.plugin.tasks.ReplayBufferTask;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;

public class PacketListener extends PacketAdapter {
    private final ReplayBufferTask replayBufferTask;

    public PacketListener(Plugin plugin, ReplayBufferTask replayBufferTask) {
        super(plugin, ListenerPriority.NORMAL, PacketType.Play.Client.USE_ENTITY);
        this.replayBufferTask = replayBufferTask;
    }

    @Override
    public void onPacketReceiving(PacketEvent event) {
        if (event.getPacketType() == PacketType.Play.Client.USE_ENTITY) {
            int entityId = event.getPacket().getIntegers().read(0);
            Entity entity = event.getPlayer().getWorld().getEntities().stream().filter(e -> e.getEntityId() == entityId).findFirst().orElse(null);

            if (entity instanceof Player) {
                Player attacker = event.getPlayer();
                Player target = (Player) entity;

                JsonObject combatData = new JsonObject();
                combatData.addProperty("target_uuid", target.getUniqueId().toString());
                combatData.addProperty("target_name", target.getName());

                ReplayEvent replayEvent = new ReplayEvent(
                    "combat",
                    attacker.getLocation().getX(),
                    attacker.getLocation().getY(),
                    attacker.getLocation().getZ(),
                    attacker.getLocation().getYaw(),
                    attacker.getLocation().getPitch(),
                    combatData.toString(),
                    System.currentTimeMillis()
                );

                replayBufferTask.addEvent(attacker.getUniqueId(), replayEvent);
            }
        }
    }
}

