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
 */
class PlayerTelemetryListenerTest {

    private static final UUID UUID_1 = UUID.fromString("11111111-2222-3333-4444-555555555555");

    // ------------------------------------------------------------------
    // buildSnapshotPayload
    // ------------------------------------------------------------------

    @Test
    void buildSnapshotPayload_producesValidJson() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, "Steve", "192.168.1.1", "vanilla", 30, 766, "join");
        assertDoesNotThrow(() -> new JSONObject(json), "Must be valid JSON: " + json);
    }

    @Test
    void buildSnapshotPayload_containsEventTypeField_notEventOrAction() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, "Steve", "192.168.1.1", "vanilla", 30, 766, "join");
        JSONObject obj = new JSONObject(json);

        // BUG-6 fix: field must be "event_type", not "event" or "action"
        assertTrue(obj.has("event_type"), "Must have event_type field: " + json);
        assertFalse(obj.has("event"), "Must NOT have 'event' field: " + json);
        assertFalse(obj.has("action"), "Must NOT have 'action' field: " + json);
        assertEquals("join", obj.getString("event_type"));
    }

    @Test
    void buildSnapshotPayload_nullEventType_defaultsToSnapshot() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, "Steve", "192.168.1.1", "vanilla", 30, 766, null);
        JSONObject obj = new JSONObject(json);
        assertEquals("snapshot", obj.getString("event_type"));
    }

    @Test
    void buildSnapshotPayload_quitEventType() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, "Steve", "10.0.0.1", "fabric", 50, 766, "quit");
        JSONObject obj = new JSONObject(json);
        assertEquals("quit", obj.getString("event_type"));
    }

    @Test
    void buildSnapshotPayload_containsAllCoreFields() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, "Alex", "1.2.3.4", "paper", 22, 765, "join");
        JSONObject obj = new JSONObject(json);

        assertEquals(UUID_1.toString(), obj.getString("uuid"));
        assertEquals("Alex", obj.getString("name"));
        assertEquals("1.2.3.4", obj.getString("ip"));
        assertEquals("paper", obj.getString("brand"));
        assertEquals(22, obj.getInt("ping"));
        assertEquals(765, obj.getInt("protocol_version"));
    }

    @Test
    void buildSnapshotPayload_nullName_usesUnknown() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, null, "1.2.3.4", "vanilla", 0, 766, "join");
        JSONObject obj = new JSONObject(json);
        assertEquals("unknown", obj.getString("name"));
    }

    @Test
    void buildSnapshotPayload_nullIp_usesLoopback() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, "Steve", null, "vanilla", 0, 766, "join");
        JSONObject obj = new JSONObject(json);
        assertEquals("127.0.0.1", obj.getString("ip"));
    }

    @Test
    void buildSnapshotPayload_blankBrand_usesVanilla() {
        String json = PlayerTelemetryListener.buildSnapshotPayload(
                UUID_1, "Steve", "1.2.3.4", "  ", 0, 766, "join");
        JSONObject obj = new JSONObject(json);
        assertEquals("vanilla", obj.getString("brand"));
    }

    // ------------------------------------------------------------------
    // buildAltTrackPayload
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
