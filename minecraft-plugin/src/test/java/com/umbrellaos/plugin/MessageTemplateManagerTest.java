package com.umbrellaos.plugin;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.net.http.HttpResponse;
import java.util.logging.Logger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class MessageTemplateManagerTest {

    @Mock
    CoreApiClient apiClient;

    @Mock
    HttpResponse<String> response;

    private MessageTemplateManager templateManager;

    @BeforeEach
    void setUp() {
        templateManager = new MessageTemplateManager(null, apiClient);
    }

    @Test
    void fetchAll_usesPluginConfigBundleAndAppliesOnlyManagedSettings() throws Exception {
        when(apiClient.get("/api/v1/plugin/config")).thenReturn(response);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("""
                {
                  "settings": {
                    "verification.ingame_prompt": "Verify in Discord: $EXPIRES",
                    "discord.client_secret": "must-not-be-consumed",
                    "unmanaged.setting": "ignored"
                  },
                  "by_category": {}
                }
                """);
        when(apiClient.logger()).thenReturn(Logger.getLogger("MessageTemplateManagerTest"));

        templateManager.fetchAll();

        assertEquals(
                "Verify in Discord: $EXPIRES",
                templateManager.getTemplate(MessageTemplateManager.KEY_INGAME_PROMPT));
        assertEquals(
                "Welcome back, $PLAYER!",
                templateManager.getTemplate(MessageTemplateManager.KEY_GREETER_RETURN_JOIN));
        verify(apiClient).get("/api/v1/plugin/config");
        verify(apiClient, never()).get(contains("/api/v1/settings/"));
    }

    @Test
    void fetchAll_keepsDefaultsForBlankOrMaskedSettings() throws Exception {
        String promptDefault = templateManager.getTemplate(MessageTemplateManager.KEY_INGAME_PROMPT);
        String successDefault = templateManager.getTemplate(MessageTemplateManager.KEY_INGAME_SUCCESS);
        when(apiClient.get("/api/v1/plugin/config")).thenReturn(response);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("""
                {
                  "settings": {
                    "verification.ingame_prompt": " ",
                    "verification.ingame_success": "***"
                  },
                  "by_category": {}
                }
                """);

        templateManager.fetchAll();

        assertEquals(promptDefault, templateManager.getTemplate(MessageTemplateManager.KEY_INGAME_PROMPT));
        assertEquals(successDefault, templateManager.getTemplate(MessageTemplateManager.KEY_INGAME_SUCCESS));
    }
}
