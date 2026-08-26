package com.umbrellaos.plugin;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link MaintenanceEnforcer} (TEST-2).
 *
 * <p>Tests isMaintenanceEnabled() with the canonical key (BUG-7 fix),
 * the bypass checker, and the maintenance override mechanism.
 */
@ExtendWith(MockitoExtension.class)
class MaintenanceEnforcerTest {

    @Mock
    ConfigManager configManager;

    @Mock
    UmbrellaPlugin plugin;

    @Mock
    org.bukkit.configuration.file.FileConfiguration config;

    private MaintenanceEnforcer enforcer;

    @BeforeEach
    void setUp() {
        when(plugin.getConfig()).thenReturn(config);
        when(config.getBoolean("maintenance.enabled", false)).thenReturn(false);
        enforcer = new MaintenanceEnforcer(plugin, configManager, null);
    }

    // ------------------------------------------------------------------
    // isMaintenanceEnabled — canonical key (BUG-7 fix)
    // ------------------------------------------------------------------

    @Test
    void isMaintenanceEnabled_false_whenKeyNotSet() {
        when(configManager.getSetting("server.maintenance_mode")).thenReturn(null);
        assertFalse(enforcer.isMaintenanceEnabled());
    }

    @Test
    void isMaintenanceEnabled_true_whenCanonicalKeyIsTrue() {
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("true");
        assertTrue(enforcer.isMaintenanceEnabled());
    }

    @Test
    void isMaintenanceEnabled_true_whenCanonicalKeyIs1() {
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("1");
        assertTrue(enforcer.isMaintenanceEnabled());
    }

    @Test
    void isMaintenanceEnabled_true_whenCanonicalKeyIsYes() {
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("yes");
        assertTrue(enforcer.isMaintenanceEnabled());
    }

    @Test
    void isMaintenanceEnabled_false_whenCanonicalKeyIsFalse() {
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("false");
        assertFalse(enforcer.isMaintenanceEnabled());
    }

    @Test
    void isMaintenanceEnabled_false_whenCanonicalKeyIsEmpty() {
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("");
        assertFalse(enforcer.isMaintenanceEnabled());
    }

    @Test
    void isMaintenanceEnabled_true_whenLocalConfigIsTrue() {
        // Local config.yml fallback path
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("false");
        when(config.getBoolean("maintenance.enabled", false)).thenReturn(true);
        assertTrue(enforcer.isMaintenanceEnabled());
    }

    @Test
    void isMaintenanceEnabled_doesNotCheckOldKeys() {
        // BUG-7: old keys (server.maintenance, maintenance.enabled from core,
        // maintenance_mode) must NOT be checked — only the canonical key
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("false");
        assertTrue(enforcer.isMaintenanceEnabled() == false);

        // Verify only the canonical key was queried
        verify(configManager, times(1)).getSetting("server.maintenance_mode");
        verify(configManager, never()).getSetting("server.maintenance");
        verify(configManager, never()).getSetting("maintenance.enabled");
        verify(configManager, never()).getSetting("maintenance_mode");
    }

    // ------------------------------------------------------------------
    // Override mechanism
    // ------------------------------------------------------------------

    @Test
    void setMaintenanceOverride_true_overridesConfigManager() {
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("false");
        enforcer.setMaintenanceOverride(true);
        assertTrue(enforcer.isMaintenanceEnabled());
        // ConfigManager should not be queried when override is set
        verify(configManager, never()).getSetting(anyString());
    }

    @Test
    void setMaintenanceOverride_false_overridesConfigManager() {
        enforcer.setMaintenanceOverride(false);
        assertFalse(enforcer.isMaintenanceEnabled());
        verify(configManager, never()).getSetting(anyString());
    }

    @Test
    void setMaintenanceOverride_null_clearsOverride() {
        enforcer.setMaintenanceOverride(true);
        enforcer.setMaintenanceOverride(null);
        when(configManager.getSetting("server.maintenance_mode")).thenReturn("false");
        assertFalse(enforcer.isMaintenanceEnabled());
    }

    // ------------------------------------------------------------------
    // Bypass checker
    // ------------------------------------------------------------------

    @Test
    void hasBypass_customChecker_used() {
        UUID uuid = UUID.randomUUID();
        enforcer.setBypassChecker((u, name) -> u.equals(uuid));
        assertTrue(enforcer.hasBypass(uuid, "Admin"));
        assertFalse(enforcer.hasBypass(UUID.randomUUID(), "Other"));
    }

    @Test
    void hasBypass_nullChecker_setToDefault() {
        enforcer.setBypassChecker(null);
        // Default checker checks Bukkit OP status — always false in unit tests
        // since Bukkit.getOfflinePlayer() returns a non-OP stub in test context.
        // Just verify it doesn't throw.
        assertDoesNotThrow(() -> enforcer.hasBypass(UUID.randomUUID(), "Player"));
    }
}
