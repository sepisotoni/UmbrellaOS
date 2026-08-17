package com.umbrellaos.plugin;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Map;
import java.util.logging.Logger;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class ConfigManagerTest {

    @Mock
    CoreApiClient apiClient;

    private ConfigManager configManager;

    @BeforeEach
    void setUp() {
        configManager = new ConfigManager(apiClient);
    }

    @Test
    void apply_parsesFlatSettingsMap() {
        String json = """
                {
                  "settings": {"server.name": "UmbrellaMC", "server.max_players": "50"},
                  "by_category": {}
                }
                """;

        configManager.apply(json);

        assertEquals("UmbrellaMC", configManager.getSetting("server.name"));
        assertEquals("50", configManager.getSetting("server.max_players"));
    }

    @Test
    void apply_parsesByCategoryMap() {
        String json = """
                {
                  "settings": {},
                  "by_category": {
                    "rcon": {"rcon.host": "localhost", "rcon.port": "25575"},
                    "moderation": {"moderation.require_discord_link": "true"}
                  }
                }
                """;

        configManager.apply(json);

        Map<String, String> rcon = configManager.getCategory("rcon");
        assertEquals("localhost", rcon.get("rcon.host"));
        assertEquals("25575", rcon.get("rcon.port"));

        Map<String, String> moderation = configManager.getCategory("moderation");
        assertEquals("true", moderation.get("moderation.require_discord_link"));
    }

    @Test
    void getSetting_returnsNullForUnknownKeyWithNoDefault() {
        configManager.apply("{\"settings\": {}, \"by_category\": {}}");

        assertNull(configManager.getSetting("does.not.exist"));
    }

    @Test
    void getSetting_returnsProvidedDefaultForUnknownKey() {
        configManager.apply("{\"settings\": {}, \"by_category\": {}}");

        assertEquals("fallback", configManager.getSetting("does.not.exist", "fallback"));
    }

    @Test
    void getCategory_returnsEmptyMapForUnknownCategory_notNull() {
        configManager.apply("{\"settings\": {}, \"by_category\": {}}");

        assertNotNull(configManager.getCategory("nonexistent"));
        assertTrue(configManager.getCategory("nonexistent").isEmpty());
    }

    @Test
    void apply_missingTopLevelKeys_doesNotThrow() {
        // Defensive: a future core-side change that omits a key shouldn't
        // NPE the plugin, it should just leave that part empty.
        assertDoesNotThrow(() -> configManager.apply("{}"));
        assertTrue(configManager.getSetting("anything") == null);
    }

    @Test
    void isLoaded_falseUntilRefreshSucceeds() {
        assertFalse(configManager.isLoaded());
    }
}
