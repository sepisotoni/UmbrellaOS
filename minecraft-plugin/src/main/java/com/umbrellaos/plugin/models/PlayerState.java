package com.umbrellaos.plugin.models;

import org.bukkit.Location;

public class PlayerState {
    private final java.util.UUID uuid;
    private final String username;
    private final double health;
    private final double maxHealth;
    private final int foodLevel;
    private final int xpLevel;
    private final float xpProgress;
    private final Location location;
    private final String gameMode;
    private final String inventoryJson;
    private final String armorJson;
    private final String offhandJson;

    public PlayerState(java.util.UUID uuid, String username, double health, double maxHealth,
                       int foodLevel, int xpLevel, float xpProgress, Location location,
                       String gameMode, String inventoryJson, String armorJson, String offhandJson) {
        this.uuid = uuid;
        this.username = username;
        this.health = health;
        this.maxHealth = maxHealth;
        this.foodLevel = foodLevel;
        this.xpLevel = xpLevel;
        this.xpProgress = xpProgress;
        this.location = location;
        this.gameMode = gameMode;
        this.inventoryJson = inventoryJson;
        this.armorJson = armorJson;
        this.offhandJson = offhandJson;
    }

    public java.util.UUID getUuid() {
        return uuid;
    }

    public String getUsername() {
        return username;
    }

    public double getHealth() {
        return health;
    }

    public double getMaxHealth() {
        return maxHealth;
    }

    public int getFoodLevel() {
        return foodLevel;
    }

    public int getXpLevel() {
        return xpLevel;
    }

    public float getXpProgress() {
        return xpProgress;
    }

    public Location getLocation() {
        return location;
    }

    public String getGameMode() {
        return gameMode;
    }

    public String getInventoryJson() {
        return inventoryJson;
    }

    public String getArmorJson() {
        return armorJson;
    }

    public String getOffhandJson() {
        return offhandJson;
    }
}
