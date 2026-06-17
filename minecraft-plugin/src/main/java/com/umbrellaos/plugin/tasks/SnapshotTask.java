package com.umbrellaos.plugin.tasks;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.umbrellaos.plugin.api.CoreApiClient;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.scheduler.BukkitRunnable;

import java.util.HashMap;
import java.util.Map;

public class SnapshotTask extends BukkitRunnable {
    private final CoreApiClient apiClient;
    private final Gson gson = new Gson();

    public SnapshotTask(CoreApiClient apiClient) {
        this.apiClient = apiClient;
    }

    @Override
    public void run() {
        for (Player player : Bukkit.getOnlinePlayers()) {
            try {
                Map<String, Object> snapshotData = collectSnapshotData(player);
                apiClient.postSnapshot(player.getUniqueId().toString(), snapshotData).exceptionally(e -> {
                    e.printStackTrace();
                    return null;
                });
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private Map<String, Object> collectSnapshotData(Player player) {
        Map<String, Object> data = new HashMap<>();
        
        // Basic stats
        data.put("health", player.getHealth());
        data.put("max_health", player.getMaxHealth());
        data.put("food", player.getFoodLevel());
        data.put("xp_level", player.getLevel());
        data.put("xp_progress", player.getExp());
        
        // Location
        data.put("x", player.getLocation().getX());
        data.put("y", player.getLocation().getY());
        data.put("z", player.getLocation().getZ());
        data.put("yaw", player.getLocation().getYaw());
        data.put("pitch", player.getLocation().getPitch());
        data.put("world", player.getWorld().getName());
        data.put("dimension", player.getWorld().getEnvironment().name());
        
        // Game mode
        data.put("game_mode", player.getGameMode().name());
        
        // Inventory
        JsonArray inventory = new JsonArray();
        for (ItemStack item : player.getInventory().getContents()) {
            inventory.add(itemToJson(item));
        }
        data.put("inventory", gson.toJson(inventory));
        
        // Armor
        JsonArray armor = new JsonArray();
        for (ItemStack item : player.getInventory().getArmorContents()) {
            armor.add(itemToJson(item));
        }
        data.put("armor", gson.toJson(armor));
        
        // Offhand
        data.put("offhand", gson.toJson(itemToJson(player.getInventory().getItemInOffHand())));
        
        return data;
    }

    private JsonObject itemToJson(ItemStack item) {
        JsonObject json = new JsonObject();
        if (item == null || item.getType() == Material.AIR) {
            json.addProperty("material", "AIR");
            json.addProperty("amount", 0);
        } else {
            json.addProperty("material", item.getType().name());
            json.addProperty("amount", item.getAmount());
            json.addProperty("display_name", item.hasItemMeta() && item.getItemMeta().hasDisplayName() ? item.getItemMeta().getDisplayName() : "");
        }
        return json;
    }
}
