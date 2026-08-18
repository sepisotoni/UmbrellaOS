package com.umbrellaos.plugin;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Covers {@link CommandPoller#parsePendingCommands}, the pure/no-Bukkit
 * parsing logic. The scheduling, main-thread dispatch, and network-ack
 * pieces are not unit-testable without a live or mocked Bukkit scheduler —
 * see the Step 2 handback doc for what's verified live instead.
 */
class CommandPollerTest {

    @Test
    void parsePendingCommands_parsesMultipleCommands() {
        String json = """
                [
                  {"id": 1, "command": "say hello world", "status": "pending",
                   "requested_by_username": "TestStaff1", "requested_by_discord_id": "123",
                   "created_at": "2026-08-17T10:00:00Z"},
                  {"id": 2, "command": "gamemode creative Steve", "status": "pending",
                   "requested_by_username": "TestStaff2", "requested_by_discord_id": "456",
                   "created_at": "2026-08-17T10:01:00Z"}
                ]
                """;

        List<CommandPoller.PendingCommand> result = CommandPoller.parsePendingCommands(json);

        assertEquals(2, result.size());
        assertEquals(1L, result.get(0).id());
        assertEquals("say hello world", result.get(0).command());
        assertEquals(2L, result.get(1).id());
        assertEquals("gamemode creative Steve", result.get(1).command());
    }

    @Test
    void parsePendingCommands_emptyArray_returnsEmptyList() {
        List<CommandPoller.PendingCommand> result = CommandPoller.parsePendingCommands("[]");

        assertTrue(result.isEmpty());
    }

    @Test
    void parsePendingCommands_ignoresExtraResponseFields() {
        // Only id/command are consumed — status, requester info, and
        // created_at are real fields on MCCommandResponse but not needed by
        // the poller itself, so extra/unknown fields shouldn't break parsing.
        String json = """
                [{"id": 7, "command": "op Alex", "status": "pending",
                  "requested_by_username": "Staff", "requested_by_discord_id": "999",
                  "created_at": "2026-08-17T10:00:00Z", "unexpected_future_field": 42}]
                """;

        List<CommandPoller.PendingCommand> result = CommandPoller.parsePendingCommands(json);

        assertEquals(1, result.size());
        assertEquals(7L, result.get(0).id());
        assertEquals("op Alex", result.get(0).command());
    }
}

