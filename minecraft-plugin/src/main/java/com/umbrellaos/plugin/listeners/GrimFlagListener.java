package com.umbrellaos.plugin.listeners;

import com.umbrellaos.plugin.UmbrellaPlugin;
import com.umbrellaos.plugin.api.CoreApiClient;
import com.umbrellaos.plugin.managers.AnticheatManager;
import com.umbrellaos.plugin.managers.PunishmentManager;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.Event;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;

import java.lang.reflect.Method;
import java.util.UUID;

/** Listens to GrimAC PunishmentEvent via reflection (soft dependency). */
public class GrimFlagListener implements Listener {
    private final AnticheatManager anticheatManager;
    private final PunishmentManager punishmentManager;

    public GrimFlagListener(AnticheatManager anticheatManager, PunishmentManager punishmentManager) {
        this.anticheatManager = anticheatManager;
        this.punishmentManager = punishmentManager;
    }

    public static void register(UmbrellaPlugin plugin, AnticheatManager anticheatManager,
                                PunishmentManager punishmentManager) {
        if (Bukkit.getPluginManager().getPlugin("GrimAC") == null) {
            plugin.getLogger().info("GrimAC not found — anticheat bridge disabled");
            return;
        }
        try {
            Class<?> eventClass = Class.forName("ac.grim.grimac.api.event.events.PunishmentEvent");
            GrimFlagListener listener = new GrimFlagListener(anticheatManager, punishmentManager);
            Bukkit.getPluginManager().registerEvent(
                    (Class<? extends Event>) eventClass,
                    listener,
                    EventPriority.MONITOR,
                    (l, event) -> ((GrimFlagListener) l).onGrimPunish(event),
                    plugin,
                    false
            );
            plugin.getLogger().info("GrimAC anticheat bridge registered");
        } catch (ClassNotFoundException e) {
            plugin.getLogger().warning("GrimAC API not found: " + e.getMessage());
        }
    }

    public void onGrimPunish(Event event) {
        try {
            Method getPlayer = event.getClass().getMethod("getPlayer");
            Object grimPlayer = getPlayer.invoke(event);
            Method getUuid = grimPlayer.getClass().getMethod("getUniqueId");
            UUID uuid = (UUID) getUuid.invoke(grimPlayer);
            Method getName = grimPlayer.getClass().getMethod("getName");
            String username = String.valueOf(getName.invoke(grimPlayer));

            String checkName = "Unknown";
            try {
                Object check = event.getClass().getMethod("getCheck").invoke(event);
                checkName = String.valueOf(check.getClass().getMethod("getCheckName").invoke(check));
            } catch (ReflectiveOperationException ignored) {
                try {
                    checkName = String.valueOf(event.getClass().getMethod("getSimpleCheckName").invoke(event));
                } catch (ReflectiveOperationException ignored2) { }
            }

            String verbose = "";
            try {
                verbose = String.valueOf(event.getClass().getMethod("getVerbose").invoke(event));
            } catch (ReflectiveOperationException ignored) {
                verbose = checkName;
            }

            int vl = 0;
            try {
                vl = (int) event.getClass().getMethod("getVl").invoke(event);
            } catch (ReflectiveOperationException ignored) { }

            anticheatManager.handleFlag(uuid, username, checkName, verbose, vl).thenAccept(result -> {
                if (Boolean.TRUE.equals(result.get("kick"))) {
                    Bukkit.getScheduler().runTask(Bukkit.getPluginManager().getPlugin("UmbrellaOS"), () -> {
                        punishmentManager.refresh(uuid);
                        Player player = Bukkit.getPlayer(uuid);
                        if (player != null && punishmentManager.isBanned(uuid)) {
                            String reason = punishmentManager.getBanReason(uuid);
                            player.kickPlayer("§c[Anti-Cheat] " + (reason != null ? reason : "Cheating detected"));
                        }
                    });
                }
            });
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
