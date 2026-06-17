package com.umbrellaos.plugin.commands;

import com.umbrellaos.plugin.managers.VerificationManager;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

public class VerifyCommand implements CommandExecutor {
    private final VerificationManager verificationManager;

    public VerifyCommand(VerificationManager verificationManager) {
        this.verificationManager = verificationManager;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage("§cThis command can only be used by players.");
            return true;
        }

        Player player = (Player) sender;

        if (verificationManager.isInLimbo(player.getUniqueId())) {
            // Resend the code
            String code = verificationManager.getCode(player.getUniqueId());
            if (code != null) {
                player.sendMessage("§eDM UmbrellaBot your code: §f" + code);
                player.sendTitle("§cVerify your account!", "§eDM UmbrellaBot your code: " + code, 10, 70, 20);
            }
        } else {
            player.sendMessage("§aYou don't need to verify.");
        }

        return true;
    }
}
