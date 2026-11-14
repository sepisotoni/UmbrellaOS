package com.umbrellaos.plugin;

import org.json.JSONArray;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link ConsoleStreamManager} — buffer behaviour, upload
 * batching, and JSON output validity (TEST-1).
 *
 * <p>The push-task scheduling (which needs a live Bukkit scheduler) is not
 * tested here — only the pure logic methods are.
 */
class ConsoleStreamManagerTest {

    private ConsoleStreamManager manager;

    @BeforeEach
    void setUp() {
        manager = new ConsoleStreamManager(10);
    }

    // ------------------------------------------------------------------
    // Buffer basics
    // ------------------------------------------------------------------

    @Test
    void appendLine_and_getLineCount() {
        assertEquals(0, manager.getLineCount());
        manager.appendLine("line 1");
        manager.appendLine("line 2");
        assertEquals(2, manager.getLineCount());
    }

    @Test
    void appendLine_null_ignored() {
        manager.appendLine(null);
        assertEquals(0, manager.getLineCount());
    }

    @Test
    void capacity_respected_oldest_dropped() {
        ConsoleStreamManager small = new ConsoleStreamManager(3);
        small.appendLine("a");
        small.appendLine("b");
        small.appendLine("c");
        small.appendLine("d"); // should evict "a"
        List<String> lines = small.getRecentLines();
        assertEquals(3, lines.size());
        assertFalse(lines.contains("a"), "Oldest line should have been evicted");
        assertTrue(lines.contains("d"));
    }

    @Test
    void getRecentLines_maxLines_respected() {
        for (int i = 0; i < 8; i++) manager.appendLine("line " + i);
        List<String> lines = manager.getRecentLines(3);
        assertEquals(3, lines.size());
        // Should be the 3 most recent
        assertEquals("line 5", lines.get(0));
        assertEquals("line 6", lines.get(1));
        assertEquals("line 7", lines.get(2));
    }

    @Test
    void getRecentLines_zero_returnsEmpty() {
        manager.appendLine("x");
        assertTrue(manager.getRecentLines(0).isEmpty());
    }

    @Test
    void clear_emptiesBuffer() {
        manager.appendLine("x");
        manager.clear();
        assertEquals(0, manager.getLineCount());
    }

    // ------------------------------------------------------------------
    // Upload batching — cursor advances only after successful upload
    // ------------------------------------------------------------------

    @Test
    void nextBatch_returnsOnlyUnsentLines_afterConfirmation() {
        manager.appendLine("line 1");
        manager.appendLine("line 2");
        ConsoleStreamManager.Batch first = manager.nextBatch(50);
        assertEquals(List.of("line 1", "line 2"), first.lines());

        manager.confirmUploaded(first);
        assertTrue(manager.nextBatch(50).lines().isEmpty());
    }

    @Test
    void nextBatch_preservesOldestUnsentOrderAcrossBatches() {
        for (int i = 0; i < 10; i++) manager.appendLine("line " + i);
        ConsoleStreamManager.Batch first = manager.nextBatch(3);
        assertEquals(List.of("line 0", "line 1", "line 2"), first.lines());
        manager.confirmUploaded(first);

        ConsoleStreamManager.Batch second = manager.nextBatch(3);
        assertEquals(List.of("line 3", "line 4", "line 5"), second.lines());
        manager.confirmUploaded(second);
        assertEquals(List.of("line 6", "line 7", "line 8", "line 9"),
                manager.nextBatch(50).lines());
    }

    @Test
    void failedOrUnconfirmedBatch_isRetriedWithoutSkippingOrDuplicating() {
        manager.appendLine("line 1");
        manager.appendLine("line 2");
        ConsoleStreamManager.Batch attempted = manager.nextBatch(50);

        // A failed HTTP response does not call confirmUploaded().
        assertEquals(attempted.lines(), manager.nextBatch(50).lines());
        manager.confirmUploaded(attempted);
        assertTrue(manager.nextBatch(50).lines().isEmpty());

        manager.appendLine("line 3");
        assertEquals(List.of("line 3"), manager.nextBatch(50).lines());
    }

    @Test
    void ringBufferEviction_dropsOnlyUnavailableLinesAndKeepsOldestAvailableOrder() {
        ConsoleStreamManager small = new ConsoleStreamManager(3);
        small.appendLine("a");
        small.appendLine("b");
        ConsoleStreamManager.Batch staleBatch = small.nextBatch(1);
        small.appendLine("c");
        small.appendLine("d"); // evicts the unsent "a"

        // A stale successful response cannot move the cursor past available lines.
        small.confirmUploaded(staleBatch);
        assertEquals(List.of("b", "c", "d"), small.nextBatch(3).lines());
    }

    @Test
    void successfulInFlightBatchAdvancesPastEvictionsWithinThatBatch() {
        ConsoleStreamManager small = new ConsoleStreamManager(4);
        for (int i = 0; i < 4; i++) small.appendLine("line " + i);
        ConsoleStreamManager.Batch inFlight = small.nextBatch(4);
        assertEquals(List.of("line 0", "line 1", "line 2", "line 3"), inFlight.lines());

        small.appendLine("line 4"); // evicts sequence 0 while the upload is pending
        small.appendLine("line 5"); // evicts sequence 1 and moves the cursor to 2
        small.confirmUploaded(inFlight); // successful response covers sequences 0–3

        assertEquals(List.of("line 4", "line 5"), small.nextBatch(4).lines());
    }

    @Test
    void serverId_blankValuesNormalizeToDefault() {
        assertEquals("default", ConsoleStreamManager.normalizeServerId(null));
        assertEquals("default", ConsoleStreamManager.normalizeServerId(""));
        assertEquals("default", ConsoleStreamManager.normalizeServerId("  "));
        assertEquals("survival", ConsoleStreamManager.normalizeServerId("survival"));
    }

    // ------------------------------------------------------------------
    // JSON output — JSONArray produces valid JSON for all content (DESIGN-3)
    // ------------------------------------------------------------------

    @Test
    void jsonArray_producesValidJson_forPlainLines() {
        List<String> lines = List.of("Server started", "[INFO] Player joined");
        JSONArray arr = new JSONArray(lines);
        String json = "{\"lines\": " + arr.toString() + "}";
        // Must not throw
        assertDoesNotThrow(() -> new org.json.JSONObject(json));
    }

    @Test
    void jsonArray_correctlyEscapes_controlChars() {
        // Tab, newline, carriage return — all must produce valid JSON
        List<String> lines = List.of("line with\ttab", "line with\nnewline", "line with\r\nCRLF");
        JSONArray arr = new JSONArray(lines);
        String json = "{\"lines\": " + arr.toString() + "}";
        assertDoesNotThrow(() -> new org.json.JSONObject(json),
                "Control chars must produce valid JSON: " + json);
    }

    @Test
    void jsonArray_correctlyEscapes_quotes() {
        List<String> lines = List.of("Player said: \"hello\"");
        JSONArray arr = new JSONArray(lines);
        String json = "{\"lines\": " + arr.toString() + "}";
        assertDoesNotThrow(() -> new org.json.JSONObject(json),
                "Quotes in line must produce valid JSON: " + json);
    }

    @Test
    void jsonArray_emptyList_producesEmptyArray() {
        JSONArray arr = new JSONArray(List.of());
        assertEquals("[]", arr.toString());
    }

    // ------------------------------------------------------------------
    // Constructor validation
    // ------------------------------------------------------------------

    @Test
    void constructor_negativeCapacity_throws() {
        assertThrows(IllegalArgumentException.class, () -> new ConsoleStreamManager(0));
        assertThrows(IllegalArgumentException.class, () -> new ConsoleStreamManager(-1));
    }
}
