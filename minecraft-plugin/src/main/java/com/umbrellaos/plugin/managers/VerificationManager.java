package com.umbrellaos.plugin.managers;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class VerificationManager {
    private final Map<UUID, String> pendingCodes = new ConcurrentHashMap<>();
    private final Map<UUID, Long> pendingExpiry = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    public VerificationManager() {
        // Check for expired pending players every 30 seconds
        scheduler.scheduleAtFixedRate(this::removeExpired, 30, 30, TimeUnit.SECONDS);
    }

    public boolean isInLimbo(UUID uuid) {
        return pendingCodes.containsKey(uuid);
    }

    public void addToLimbo(UUID uuid, String code) {
        pendingCodes.put(uuid, code);
        pendingExpiry.put(uuid, System.currentTimeMillis() + TimeUnit.MINUTES.toMillis(10));
    }

    public void removeFromLimbo(UUID uuid) {
        pendingCodes.remove(uuid);
        pendingExpiry.remove(uuid);
    }

    public String getCode(UUID uuid) {
        return pendingCodes.get(uuid);
    }

    public void verifyPlayer(UUID uuid) {
        Player player = Bukkit.getPlayer(uuid);
        if (player != null) {
            // Remove limbo effects
            player.removePotionEffect(PotionEffectType.BLINDNESS);
            player.removePotionEffect(PotionEffectType.SLOW);
            
            // Send success message
            player.sendMessage("§a✅ Verified! Welcome to the server.");
        }
        removeFromLimbo(uuid);
    }

    public void putInLimbo(UUID uuid, String code) {
        Player player = Bukkit.getPlayer(uuid);
        if (player != null) {
            // Teleport to spawn
            player.teleport(player.getWorld().getSpawnLocation());
            
            // Apply limbo effects
            player.addPotionEffect(new PotionEffect(PotionEffectType.BLINDNESS, Integer.MAX_VALUE, 1, false, false));
            player.addPotionEffect(new PotionEffect(PotionEffectType.SLOW, Integer.MAX_VALUE, 2, false, false));
            
            // Send title and actionbar
            player.sendTitle("§cVerify your account!", "§eDM UmbrellaBot your code: " + code, 10, 70, 20);
            player.spigot().sendMessage(
                net.md_5.bungee.api.chat.TextComponent.fromLegacyText("§eDM UmbrellaBot your code: §f" + code)
            );
        }
        addToLimbo(uuid, code);
    }

    private void removeExpired() {
        long now = System.currentTimeMillis();
        pendingExpiry.entrySet().removeIf(entry -> {
            if (entry.getValue() < now) {
                UUID uuid = entry.getKey();
                pendingCodes.remove(uuid);
                Player player = Bukkit.getPlayer(uuid);
                if (player != null) {
                    player.removePotionEffect(PotionEffectType.BLINDNESS);
                    player.removePotionEffect(PotionEffectType.SLOW);
                    player.kickPlayer("§cVerification expired. Please rejoin to verify.");
                }
                return true;
            }
            return false;
        });
    }

    public void shutdown() {
        scheduler.shutdown();
    }
}
