package com.umbrellaos.plugin.tasks;

import com.umbrellaos.plugin.api.CoreApiClient;
import org.bukkit.Bukkit;
import org.bukkit.scheduler.BukkitRunnable;

public class HeartbeatTask extends BukkitRunnable {
    private final CoreApiClient apiClient;

    public HeartbeatTask(CoreApiClient apiClient) {
        this.apiClient = apiClient;
    }

    @Override
    public void run() {
        int onlineCount = Bukkit.getOnlinePlayers().size();
        double tps = Bukkit.getServer().getTPS()[0];
        String serverName = Bukkit.getServer().getName();
        String version = Bukkit.getVersion();
        boolean grim = Bukkit.getPluginManager().getPlugin("GrimAC") != null;

        apiClient.postHeartbeat(onlineCount, tps, serverName, version, grim).exceptionally(e -> {
            e.printStackTrace();
            return null;
        });
    }
}
