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
        // FIX ([PLUGIN] subsystem audit, blocking mvn test module-wide):
        // these two stubs aren't consumed by every test method below (only
        // the ones that actually exercise the legacy config.yml fallback
        // path reach plugin.getConfig()/config.getBoolean(...)) — Mockito's
        // strict-stubs mode (MockitoExtension's default) flags that as
        // UnnecessaryStubbingException on every test that doesn't touch
        // them. lenient() is Mockito's own documented remedy for exactly
        // this shape of shared @BeforeEach fixture used across
        // heterogeneous test methods — doesn't change any test's actual
        // assertions or behavior, just stops strict-stubs treating an
        // under-used shared stub as an error.
        lenient().when(plugin.getConfig()).thenReturn(config);
        lenient().when(config.getBoolean("maintenance.enabled", false)).thenReturn(false);
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
        // FIX ([PLUGIN] audit): removed a stray configManager.getSetting(...)
        // stub here — this test's own assertion below proves configManager
        // is never queried once an override is set, so the stub (likely a
        // copy-paste leftover from the test above) could never be consumed,
        // triggering strict-stubs UnnecessaryStubbingException.
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
