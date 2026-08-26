package com.umbrellaos.plugin;

import org.json.JSONArray;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link ConsoleStreamManager} — buffer behaviour, delta
 * tracking, and JSON output validity (TEST-1).
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
    // Delta tracking (BUG-5 fix) — drainNewLines()
    // ------------------------------------------------------------------

    @Test
    void drainNewLines_returnsOnlyNewLines() {
        manager.appendLine("line 1");
        manager.appendLine("line 2");
        List<String> first = manager.drainNewLines(50);
        assertEquals(2, first.size());

        // No new lines — second drain should return empty
        List<String> second = manager.drainNewLines(50);
        assertTrue(second.isEmpty(), "Expected no new lines on second drain: " + second);
    }

    @Test
    void drainNewLines_respectsMaxLines() {
        for (int i = 0; i < 10; i++) manager.appendLine("line " + i);
        List<String> drained = manager.drainNewLines(3);
        assertEquals(3, drained.size());
        // After draining 3, 7 are still "pending" — next drain gets them
        List<String> rest = manager.drainNewLines(50);
        assertEquals(7, rest.size());
    }

    @Test
    void drainNewLines_emptyBuffer_returnsEmpty() {
        assertTrue(manager.drainNewLines(50).isEmpty());
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
