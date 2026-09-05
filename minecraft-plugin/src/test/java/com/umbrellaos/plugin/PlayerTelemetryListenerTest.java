package com.umbrellaos.plugin;

import org.json.JSONObject;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link PlayerTelemetryListener} static payload-builder methods (TEST-2).
 *
 * <p>These methods are pure functions (no Bukkit dependency) so they can be
 * tested directly without Mockito or a live server.
 *
 * <p>FIX ([PLUGIN] subsystem audit): buildSnapshotPayload was renamed to
 * buildAnalyticsEventPayload and its output shape changed from a flat
 * {uuid, name, ip, ..., event_type} object to {event_type, minecraft_uuid,
 * data: {name, ip, ...}}, matching umbrella-core's actual
 * AnalyticsEventRequest schema (the old shape never matched any real
 * endpoint). Tests below updated to match; assertions on the underlying
 * values (name/ip/brand/ping/protocol_version fallbacks) are unchanged in
 * substance, just re-pointed at the nested "data" object.
 */
class PlayerTelemetryListenerTest {

    private static final UUID UUID_1 = UUID.fromString("11111111-2222-3333-4444-555555555555");

    // ------------------------------------------------------------------
    // buildAnalyticsEventPayload
    // ------------------------------------------------------------------

    @Test
    void buildAnalyticsEventPayload_producesValidJson() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, "Steve", "192.168.1.1", "vanilla", 30, 766, "join");
        assertDoesNotThrow(() -> new JSONObject(json), "Must be valid JSON: " + json);
    }

    @Test
    void buildAnalyticsEventPayload_topLevelShapeMatchesAnalyticsEventRequest() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, "Steve", "192.168.1.1", "vanilla", 30, 766, "join");
        JSONObject obj = new JSONObject(json);

        // Matches api/routers/analytics.py's AnalyticsEventRequest exactly:
        // event_type and minecraft_uuid at top level, everything else in "data".
        assertTrue(obj.has("event_type"), "Must have event_type field: " + json);
        assertTrue(obj.has("minecraft_uuid"), "Must have minecraft_uuid field: " + json);
        assertTrue(obj.has("data"), "Must have data field: " + json);
        assertFalse(obj.has("uuid"), "Must NOT have a top-level 'uuid' field (renamed to minecraft_uuid): " + json);
        assertFalse(obj.has("event"), "Must NOT have 'event' field: " + json);
        assertFalse(obj.has("action"), "Must NOT have 'action' field: " + json);
        assertEquals("join", obj.getString("event_type"));
        assertEquals(UUID_1.toString(), obj.getString("minecraft_uuid"));
    }

    @Test
    void buildAnalyticsEventPayload_nullEventType_defaultsToSnapshot() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, "Steve", "192.168.1.1", "vanilla", 30, 766, null);
        JSONObject obj = new JSONObject(json);
        assertEquals("snapshot", obj.getString("event_type"));
    }

    @Test
    void buildAnalyticsEventPayload_quitEventType() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, "Steve", "10.0.0.1", "fabric", 50, 766, "quit");
        JSONObject obj = new JSONObject(json);
        assertEquals("quit", obj.getString("event_type"));
    }

    @Test
    void buildAnalyticsEventPayload_dataContainsAllTelemetryFields() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, "Alex", "1.2.3.4", "paper", 22, 765, "join");
        JSONObject obj = new JSONObject(json);
        JSONObject data = obj.getJSONObject("data");

        assertEquals("Alex", data.getString("name"));
        assertEquals("1.2.3.4", data.getString("ip"));
        assertEquals("paper", data.getString("brand"));
        assertEquals(22, data.getInt("ping"));
        assertEquals(765, data.getInt("protocol_version"));
    }

    @Test
    void buildAnalyticsEventPayload_nullName_usesUnknown() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, null, "1.2.3.4", "vanilla", 0, 766, "join");
        JSONObject data = new JSONObject(json).getJSONObject("data");
        assertEquals("unknown", data.getString("name"));
    }

    @Test
    void buildAnalyticsEventPayload_nullIp_usesLoopback() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, "Steve", null, "vanilla", 0, 766, "join");
        JSONObject data = new JSONObject(json).getJSONObject("data");
        assertEquals("127.0.0.1", data.getString("ip"));
    }

    @Test
    void buildAnalyticsEventPayload_blankBrand_usesVanilla() {
        String json = PlayerTelemetryListener.buildAnalyticsEventPayload(
                UUID_1, "Steve", "1.2.3.4", "  ", 0, 766, "join");
        JSONObject data = new JSONObject(json).getJSONObject("data");
        assertEquals("vanilla", data.getString("brand"));
    }

    // ------------------------------------------------------------------
    // buildAltTrackPayload — unchanged, still matches /api/v1/alts/track's
    // AltTrackRequest schema exactly (flat uuid/name/ip/brand).
    // ------------------------------------------------------------------

    @Test
    void buildAltTrackPayload_producesValidJson() {
        String json = PlayerTelemetryListener.buildAltTrackPayload(
                UUID_1, "Steve", "192.168.1.1", "vanilla");
        assertDoesNotThrow(() -> new JSONObject(json), "Must be valid JSON: " + json);
    }

    @Test
    void buildAltTrackPayload_containsRequiredFields() {
        String json = PlayerTelemetryListener.buildAltTrackPayload(
                UUID_1, "Steve", "10.0.0.5", "paper");
        JSONObject obj = new JSONObject(json);

        assertEquals(UUID_1.toString(), obj.getString("uuid"));
        assertEquals("Steve", obj.getString("name"));
        assertEquals("10.0.0.5", obj.getString("ip"));
        assertEquals("paper", obj.getString("brand"));
    }

    @Test
    void buildAltTrackPayload_nullValues_useFallbacks() {
        String json = PlayerTelemetryListener.buildAltTrackPayload(UUID_1, null, null, null);
        JSONObject obj = new JSONObject(json);
        assertEquals("unknown", obj.getString("name"));
        assertEquals("127.0.0.1", obj.getString("ip"));
        assertEquals("vanilla", obj.getString("brand"));
    }
}
