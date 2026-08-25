package com.umbrellaos.plugin;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.UUID;
import java.util.logging.Logger;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link GrimBridge}.
 *
 * <p>Full in-game registration (GrimAPI.INSTANCE.getEventBus()...) requires a
 * live Paper server and a live GrimAC instance — that can't be unit tested.
 * What <em>can</em> be tested in isolation:
 * <ul>
 *   <li>VL rounding: {@code Math.round(double)} vs truncation — the dispatch
 *       doc called this out explicitly.</li>
 *   <li>JSON payload shape: field names and escaping for free-text fields.</li>
 *   <li>HTTP error-path: non-2xx logged, no exception thrown to caller.</li>
 *   <li>Network error: {@link IOException} swallowed + logged.</li>
 * </ul>
 *
 * <p>The live integration test (actual GrimAC flag → umbrella-core) is
 * described in the Step 3 handback doc; it was not performed by this sub-chat
 * because no live Paper + GrimAC environment is available here.
 */
@ExtendWith(MockitoExtension.class)
class GrimBridgeTest {

    @Mock
    HttpClient httpClient;

    @Mock
    HttpResponse<String> httpResponse;

    private CoreApiClient apiClient;
    private GrimBridge bridge;

    @BeforeEach
    void setUp() {
        apiClient = new CoreApiClient(
                "http://localhost:8000", "test-key", Logger.getAnonymousLogger(),
                httpClient, Duration.ofSeconds(5));
        // null Plugin — only used by GrimBridge.register() which we don't call in
        // these tests (it needs Bukkit.getPluginManager(), unavailable in unit tests).
        bridge = new GrimBridge(null, apiClient);
    }

    // -----------------------------------------------------------------------
    // VL conversion: the dispatch doc says Math.round, not truncate
    // -----------------------------------------------------------------------

    @Test
    void buildFlagPayload_vlRoundsUp() {
        // 1.9 → 2, not 1
        String json = GrimBridge.buildFlagPayload(
                UUID.fromString("00000000-0000-0000-0000-000000000001"),
                "Player", "Speed", "verbose", (int) Math.round(1.9));

        assertTrue(json.contains("\"vl\":2"), "Expected vl=2, got: " + json);
    }

    @Test
    void buildFlagPayload_vlRoundsDown() {
        // 1.4 → 1
        String json = GrimBridge.buildFlagPayload(
                UUID.fromString("00000000-0000-0000-0000-000000000001"),
                "Player", "Speed", "verbose", (int) Math.round(1.4));

        assertTrue(json.contains("\"vl\":1"), "Expected vl=1, got: " + json);
    }

    @Test
    void buildFlagPayload_vlExactInteger_noChange() {
        String json = GrimBridge.buildFlagPayload(
                UUID.fromString("00000000-0000-0000-0000-000000000001"),
                "Player", "Reach", "verbose", (int) Math.round(5.0));

        assertTrue(json.contains("\"vl\":5"), "Expected vl=5, got: " + json);
    }

    // -----------------------------------------------------------------------
    // JSON payload shape
    // -----------------------------------------------------------------------

    @Test
    void buildFlagPayload_containsAllRequiredFields() {
        UUID uuid = UUID.fromString("aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb");
        String json = GrimBridge.buildFlagPayload(uuid, "TestPlayer", "Reach", "dx=0.1", 3);

        assertTrue(json.contains("\"player_uuid\":\"" + uuid + "\""),
                "Missing player_uuid: " + json);
        assertTrue(json.contains("\"player_name\":\"TestPlayer\""),
                "Missing player_name: " + json);
        assertTrue(json.contains("\"check_name\":\"Reach\""),
                "Missing check_name: " + json);
        assertTrue(json.contains("\"verbose\":\"dx=0.1\""),
                "Missing verbose: " + json);
        assertTrue(json.contains("\"vl\":3"),
                "Missing vl: " + json);
    }

    @Test
    void buildFlagPayload_escapesDoubleQuotesInVerbose() {
        // GrimAC verbose strings can contain quotes (e.g. key="value")
        String json = GrimBridge.buildFlagPayload(
                UUID.randomUUID(), "Player", "Check", "key=\"val\"", 1);

        // The JSON string value must have escaped quotes, not raw ones
        assertFalse(json.contains("\"key=\"val\"\""),
                "Raw unescaped quotes in verbose field: " + json);
        assertTrue(json.contains("\\\""), "Expected escaped quotes in json: " + json);
    }

    @Test
    void buildFlagPayload_escapesDoubleQuotesInPlayerName() {
        String json = GrimBridge.buildFlagPayload(
                UUID.randomUUID(), "Play\"er", "Check", "v", 1);

        assertFalse(json.contains("\"Play\"er\""),
                "Raw unescaped quote in player_name: " + json);
    }

    @Test
    void buildFlagPayload_nullVerbose_becomesEmptyString() {
        String json = GrimBridge.buildFlagPayload(
                UUID.randomUUID(), "Player", "Check", null, 1);

        assertTrue(json.contains("\"verbose\":\"\""), "Expected empty verbose: " + json);
    }

    // -----------------------------------------------------------------------
    // HTTP behaviour: non-2xx logged, no exception thrown
    // -----------------------------------------------------------------------

    @Test
    void reportFlag_non2xxResponse_doesNotThrow() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(500);

        // Must not throw — a bad core response must never crash the Bukkit event thread
        assertDoesNotThrow(() -> bridge.reportFlag(
                UUID.randomUUID(), "Player", "Speed", "verbose", 2));
    }

    @Test
    void reportFlag_ioException_doesNotThrow() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenThrow(new IOException("connection refused"));

        assertDoesNotThrow(() -> bridge.reportFlag(
                UUID.randomUUID(), "Player", "Speed", "verbose", 2));
    }

    @Test
    void reportFlag_success_sendsToCorrectPath() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);

        bridge.reportFlag(UUID.randomUUID(), "Player", "Reach", "dx=0.05", 1);

        // Verify the request was sent to the anticheat flag endpoint
        verify(httpClient).send(
                argThat(req -> req.uri().toString().endsWith("/api/v1/anticheat/flag")),
                any(HttpResponse.BodyHandler.class));
    }

    @Test
    void buildFlagPayload_withCustomServerId() {
        UUID uuid = UUID.randomUUID();
        String json = GrimBridge.buildFlagPayload(uuid, "Player", "Fly", "dy=1.2", 4, "lobby-1");

        assertTrue(json.contains("\"server_id\":\"lobby-1\""), "Missing custom server_id: " + json);
    }

    @Test
    void buildFlagPayload_defaultServerId_whenNullOrOmitted() {
        UUID uuid = UUID.randomUUID();
        String jsonNull = GrimBridge.buildFlagPayload(uuid, "Player", "Fly", "dy=1.2", 4, null);
        assertTrue(jsonNull.contains("\"server_id\":\"default\""), "Expected default server_id: " + jsonNull);

        String json5Arg = GrimBridge.buildFlagPayload(uuid, "Player", "Fly", "dy=1.2", 4);
        assertTrue(json5Arg.contains("\"server_id\":\"default\""), "Expected default server_id: " + json5Arg);
    }

    // -----------------------------------------------------------------------
    // Constructor & serverId
    // -----------------------------------------------------------------------

    @Test
    void constructor_customServerId() {
        GrimBridge customBridge = new GrimBridge(null, apiClient, "survival-1");
        assertEquals("survival-1", customBridge.getServerId());
    }

    @Test
    void constructor_defaultServerId_whenNullOrBlank() {
        GrimBridge defaultBridge = new GrimBridge(null, apiClient);
        assertEquals("default", defaultBridge.getServerId());

        GrimBridge nullBridge = new GrimBridge(null, apiClient, null);
        assertEquals("default", nullBridge.getServerId());

        GrimBridge blankBridge = new GrimBridge(null, apiClient, "   ");
        assertEquals("default", blankBridge.getServerId());
    }

    // -----------------------------------------------------------------------
    // isRegistered starts false (register() not called — needs Bukkit)
    // -----------------------------------------------------------------------

    @Test
    void isRegistered_falseBeforeRegister() {
        assertFalse(bridge.isRegistered());
    }
}
