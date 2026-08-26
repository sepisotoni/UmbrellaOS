package com.umbrellaos.plugin;

import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.entity.Player;
import org.bukkit.plugin.PluginDescriptionFile;
import org.json.JSONObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.logging.Logger;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class VerificationCommandTest {

    @Mock
    HttpClient httpClient;

    @Mock
    HttpResponse<String> httpResponse;

    @Mock
    Player player;

    @Mock
    ConsoleCommandSender consoleSender;

    @Mock
    Command command;

    @Mock
    UmbrellaPlugin plugin;

    @Mock
    GrimBridge grimBridge;

    private CoreApiClient apiClient;
    private VerificationCommand verificationCommand;

    private final UUID playerUuid = UUID.fromString("11111111-2222-3333-4444-555555555555");
    private final String playerName = "TestPlayer";

    @BeforeEach
    void setUp() {
        apiClient = new CoreApiClient(
                "http://localhost:8000", "test-plugin-key", Logger.getAnonymousLogger(),
                httpClient, Duration.ofSeconds(5));
        verificationCommand = new VerificationCommand(plugin, apiClient, null, grimBridge);
    }

    // ------------------------------------------------------------------
    // Code validation tests
    // ------------------------------------------------------------------

    @Test
    void isValidCode_validLengths() {
        assertTrue(VerificationCommand.isValidCode("123456"));   // 6 chars
        assertTrue(VerificationCommand.isValidCode("ABC1234"));  // 7 chars
        assertTrue(VerificationCommand.isValidCode("12345678")); // 8 chars
    }

    @Test
    void isValidCode_invalidLengths() {
        assertFalse(VerificationCommand.isValidCode(null));
        assertFalse(VerificationCommand.isValidCode(""));
        assertFalse(VerificationCommand.isValidCode("12345"));     // 5 chars
        assertFalse(VerificationCommand.isValidCode("123456789")); // 9 chars
    }

    // ------------------------------------------------------------------
    // Payload generation
    // ------------------------------------------------------------------

    @Test
    void buildVerifyPayload_containsRequiredFields() {
        String payload = VerificationCommand.buildVerifyPayload("123456", playerUuid.toString(), playerName);
        JSONObject json = new JSONObject(payload);

        assertEquals("123456", json.getString("code"));
        assertEquals(playerUuid.toString(), json.getString("minecraft_uuid"));
        assertEquals(playerName, json.getString("minecraft_username"));
        assertEquals(playerUuid.toString(), json.getString("player_uuid"));
        assertEquals(playerName, json.getString("player_username"));
    }

    // ------------------------------------------------------------------
    // Response parsing tests
    // ------------------------------------------------------------------

    @Test
    void parseVerificationResponse_200_defaultTemplate() {
        String body = "{\"success\": true, \"discord_username\": \"DiscordUser#1234\"}";
        VerificationCommand.VerificationResult result =
                VerificationCommand.parseVerificationResponse(200, body, playerName, "123456", null);

        assertTrue(result.success());
        assertEquals(200, result.statusCode());
        assertEquals("DiscordUser#1234", result.discordUsername());
        assertTrue(result.message().contains("linked successfully"));
    }

    @Test
    void parseVerificationResponse_200_alreadyVerified() {
        String body = "{\"already_verified\": true}";
        VerificationCommand.VerificationResult result =
                VerificationCommand.parseVerificationResponse(200, body, playerName, "123456", null);

        assertTrue(result.success());
        assertTrue(result.message().contains("already linked"));
    }

    @Test
    void parseVerificationResponse_200_customTemplateRendered() {
        MessageTemplateManager templateManager = mock(MessageTemplateManager.class);
        when(templateManager.getTemplate(MessageTemplateManager.KEY_INGAME_SUCCESS))
                .thenReturn("Account $PLAYER linked with code $CODE!");
        when(templateManager.render(anyString(), any()))
                .thenReturn("Account TestPlayer linked with code 123456!");

        VerificationCommand.VerificationResult result =
                VerificationCommand.parseVerificationResponse(200, "{\"success\": true}", playerName, "123456", templateManager);

        assertTrue(result.success());
        assertTrue(result.message().contains("Account TestPlayer linked with code 123456!"));
    }

    @Test
    void parseVerificationResponse_400_invalidOrExpired() {
        VerificationCommand.VerificationResult result =
                VerificationCommand.parseVerificationResponse(400, "{\"detail\": \"Code expired\"}", playerName, "123456", null);

        assertFalse(result.success());
        assertEquals(400, result.statusCode());
        assertTrue(result.message().contains("invalid or has expired"));
    }

    @Test
    void parseVerificationResponse_404_notFound() {
        VerificationCommand.VerificationResult result =
                VerificationCommand.parseVerificationResponse(404, "{\"detail\": \"Not found\"}", playerName, "123456", null);

        assertFalse(result.success());
        assertEquals(404, result.statusCode());
        assertTrue(result.message().contains("not found"));
    }

    @Test
    void parseVerificationResponse_409_alreadyLinked() {
        VerificationCommand.VerificationResult result =
                VerificationCommand.parseVerificationResponse(409, "{\"detail\": \"Already linked\"}", playerName, "123456", null);

        assertFalse(result.success());
        assertEquals(409, result.statusCode());
        assertTrue(result.message().contains("already linked to a different Discord account"));
    }

    @Test
    void parseVerificationResponse_500_serverError() {
        VerificationCommand.VerificationResult result =
                VerificationCommand.parseVerificationResponse(500, "Internal error", playerName, "123456", null);

        assertFalse(result.success());
        assertEquals(500, result.statusCode());
        assertTrue(result.message().contains("Verification failed (HTTP 500)"));
    }

    // ------------------------------------------------------------------
    // verifyCode execution & fallback tests
    // ------------------------------------------------------------------

    @Test
    void verifyCode_success_primaryEndpoint() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);
        when(httpResponse.body()).thenReturn("{\"success\": true, \"discord_username\": \"TestUser\"}");

        VerificationCommand.VerificationResult result =
                verificationCommand.verifyCode("123456", playerUuid.toString(), playerName);

        assertTrue(result.success());
        assertEquals("TestUser", result.discordUsername());
        verify(httpClient).send(
                argThat(req -> req.uri().toString().endsWith("/api/v1/verification/verify-code")),
                any(HttpResponse.BodyHandler.class));
    }

    @Test
    void verifyCode_primary404_returnsNotFoundError() throws IOException, InterruptedException {
        // DESIGN-1 fix: fallback endpoint removed. A 404 from /verify-code now returns
        // a user-facing "code not found" error directly — no second HTTP call.
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(404);
        when(httpResponse.body()).thenReturn("{\"detail\": \"Code not found\"}");

        VerificationCommand.VerificationResult result =
                verificationCommand.verifyCode("123456", playerUuid.toString(), playerName);

        assertFalse(result.success());
        assertEquals(404, result.statusCode());
        assertTrue(result.message().contains("not found"));
        // Only ONE network call — no fallback attempt
        verify(httpClient, times(1)).send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void verifyCode_networkException_handledGracefully() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenThrow(new IOException("Connection refused"));

        VerificationCommand.VerificationResult result =
                verificationCommand.verifyCode("123456", playerUuid.toString(), playerName);

        assertFalse(result.success());
        assertEquals(500, result.statusCode());
        assertTrue(result.message().contains("Failed to connect"));
    }

    @Test
    void verifyCode_invalidCode_rejectsImmediatelyWithoutNetwork() throws IOException, InterruptedException {
        VerificationCommand.VerificationResult result =
                verificationCommand.verifyCode("123", playerUuid.toString(), playerName);

        assertFalse(result.success());
        assertEquals(400, result.statusCode());
        verifyNoInteractions(httpClient);
    }

    // ------------------------------------------------------------------
    // checkPlayerVerificationStatus & checkActivePunishmentInfo
    // ------------------------------------------------------------------

    @Test
    void checkPlayerVerificationStatus_verified() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);
        when(httpResponse.body()).thenReturn("{\"verified\": true, \"discord_username\": \"TestDiscord\"}");

        String status = verificationCommand.checkPlayerVerificationStatus(playerUuid.toString());

        assertTrue(status.contains("Linked"));
        assertTrue(status.contains("TestDiscord"));
    }

    @Test
    void checkPlayerVerificationStatus_notVerified() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);
        when(httpResponse.body()).thenReturn("{\"verified\": false}");

        String status = verificationCommand.checkPlayerVerificationStatus(playerUuid.toString());

        assertTrue(status.contains("Not Linked"));
    }

    @Test
    void checkActivePunishmentInfo_activeBan() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);
        when(httpResponse.body()).thenReturn("""
                {
                  "banned": true,
                  "punishment": {
                    "type": "ban",
                    "reason": "Rule violation"
                  }
                }
                """);

        String info = verificationCommand.checkActivePunishmentInfo(playerUuid.toString());

        assertNotNull(info);
        assertTrue(info.contains("BAN"));
        assertTrue(info.contains("Rule violation"));
    }

    @Test
    void checkActivePunishmentInfo_noPunishment() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);
        when(httpResponse.body()).thenReturn("{\"banned\": false, \"punishment\": null}");

        String info = verificationCommand.checkActivePunishmentInfo(playerUuid.toString());

        assertNull(info);
    }

    // ------------------------------------------------------------------
    // Command dispatch tests
    // ------------------------------------------------------------------

    @Test
    void onCommand_verify_consoleSender_rejected() {
        when(command.getName()).thenReturn("verify");

        boolean handled = verificationCommand.onCommand(consoleSender, command, "verify", new String[]{"123456"});

        assertTrue(handled);
        verify(consoleSender).sendMessage(contains("Only in-game players"));
    }

    @Test
    void onCommand_verify_wrongArgCount_showsUsage() {
        when(command.getName()).thenReturn("verify");

        boolean handled = verificationCommand.onCommand(player, command, "verify", new String[]{});

        assertTrue(handled);
        verify(player).sendMessage(contains("Usage: /verify <code>"));
    }

    @Test
    void onCommand_verify_invalidCodeLength_showsError() {
        when(command.getName()).thenReturn("verify");

        boolean handled = verificationCommand.onCommand(player, command, "verify", new String[]{"123"});

        assertTrue(handled);
        verify(player).sendMessage(contains("Invalid verification code"));
    }

    @Test
    void onCommand_umbrella_help() {
        when(command.getName()).thenReturn("umbrella");

        boolean handled = verificationCommand.onCommand(player, command, "umbrella", new String[]{"help"});

        assertTrue(handled);
        verify(player, atLeastOnce()).sendMessage(contains("UmbrellaOS Help"));
    }

    @Test
    void onCommand_umbrella_noArgs_showsHelp() {
        when(command.getName()).thenReturn("umbrella");

        boolean handled = verificationCommand.onCommand(player, command, "umbrella", new String[]{});

        assertTrue(handled);
        verify(player, atLeastOnce()).sendMessage(contains("UmbrellaOS Help"));
    }

    @Test
    void onCommand_umbrella_status() {
        when(command.getName()).thenReturn("umbrella");
        when(plugin.getDescription()).thenReturn(new PluginDescriptionFile("UmbrellaOSPlugin", "1.0.0", "com.umbrellaos.plugin.UmbrellaPlugin"));
        when(grimBridge.isRegistered()).thenReturn(true);
        when(player.getUniqueId()).thenReturn(playerUuid);

        boolean handled = verificationCommand.onCommand(player, command, "umbrella", new String[]{"status"});

        assertTrue(handled);
        verify(player, atLeastOnce()).sendMessage(contains("UmbrellaOS Status"));
    }

    @Test
    void onCommand_umbrella_unknownSubcommand() {
        when(command.getName()).thenReturn("umbrella");

        boolean handled = verificationCommand.onCommand(player, command, "umbrella", new String[]{"invalid"});

        assertTrue(handled);
        verify(player).sendMessage(contains("Unknown subcommand"));
    }

    @Test
    void onCommand_appeal_consoleSender() {
        when(command.getName()).thenReturn("appeal");

        boolean handled = verificationCommand.onCommand(consoleSender, command, "appeal", new String[]{});

        assertTrue(handled);
        verify(consoleSender, atLeastOnce()).sendMessage(contains("Appeal"));
    }

    @Test
    void onCommand_appeal_playerSender() {
        when(command.getName()).thenReturn("appeal");
        when(player.getUniqueId()).thenReturn(playerUuid);

        boolean handled = verificationCommand.onCommand(player, command, "appeal", new String[]{});

        assertTrue(handled);
        verify(player, atLeastOnce()).sendMessage(contains("Appeal"));
    }

    @Test
    void onCommand_unknownCommand_returnsFalse() {
        when(command.getName()).thenReturn("other");

        boolean handled = verificationCommand.onCommand(player, command, "other", new String[]{});

        assertFalse(handled);
    }

    // ------------------------------------------------------------------
    // Tab completion tests
    // ------------------------------------------------------------------

    @Test
    void onTabComplete_umbrella_suggestsSubcommands() {
        when(command.getName()).thenReturn("umbrella");

        List<String> suggestions = verificationCommand.onTabComplete(player, command, "umbrella", new String[]{""});

        assertNotNull(suggestions);
        assertTrue(suggestions.contains("status"));
        assertTrue(suggestions.contains("help"));
    }

    @Test
    void onTabComplete_umbrella_filtersByPrefix() {
        when(command.getName()).thenReturn("umbrella");

        List<String> suggestions = verificationCommand.onTabComplete(player, command, "umbrella", new String[]{"st"});

        assertNotNull(suggestions);
        assertTrue(suggestions.contains("status"));
        assertFalse(suggestions.contains("help"));
    }

    @Test
    void onTabComplete_verify_returnsEmpty() {
        when(command.getName()).thenReturn("verify");

        List<String> suggestions = verificationCommand.onTabComplete(player, command, "verify", new String[]{""});

        assertNotNull(suggestions);
        assertTrue(suggestions.isEmpty());
    }

    @Test
    void onTabComplete_appeal_returnsEmpty() {
        // PLUGIN-BUG-3 fix: /appeal has no subcommands. Tab-completing "status" was dead
        // code — the handler never processed args[0]=="status". Now returns empty list.
        when(command.getName()).thenReturn("appeal");

        List<String> suggestions = verificationCommand.onTabComplete(player, command, "appeal", new String[]{""});

        assertNotNull(suggestions);
        assertTrue(suggestions.isEmpty(), "Expected no tab suggestions for /appeal: " + suggestions);
    }
}
