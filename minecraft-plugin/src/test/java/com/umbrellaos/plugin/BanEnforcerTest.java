package com.umbrellaos.plugin;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.net.http.HttpResponse;
import java.util.logging.Logger;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Covers {@link BanEnforcer#parseBanCheckResponse} (pure) and {@link
 * BanEnforcer#checkActiveBan} (network call via a mocked {@link
 * CoreApiClient}, no real HTTP). The actual {@code AsyncPlayerPreLoginEvent}
 * handler, and the fail-open behavior under a real Bukkit event, are not
 * unit-testable without a live/mocked Bukkit server — see the Step 2
 * handback doc for what's verified live instead.
 */
@ExtendWith(MockitoExtension.class)
class BanEnforcerTest {

    @Mock
    CoreApiClient apiClient;

    @Mock
    HttpResponse<String> httpResponse;

    private BanEnforcer banEnforcer;

    @BeforeEach
    void setUp() {
        banEnforcer = new BanEnforcer(apiClient);
    }

    @Test
    void parseBanCheckResponse_notBanned() {
        String json = "{\"banned\": false, \"punishment\": null}";

        BanEnforcer.BanCheckResult result = BanEnforcer.parseBanCheckResponse(json);

        assertFalse(result.banned());
    }

    @Test
    void parseBanCheckResponse_permanentBan_parsesFields() {
        String json = """
                {
                  "banned": true,
                  "punishment": {
                    "id": "abc-123",
                    "type": "ban",
                    "reason": "Griefing spawn",
                    "staff_id": "staff-1",
                    "created_at": "2026-08-17T10:00:00Z",
                    "expires_at": null
                  }
                }
                """;

        BanEnforcer.BanCheckResult result = BanEnforcer.parseBanCheckResponse(json);

        assertTrue(result.banned());
        assertEquals("ban", result.type());
        assertEquals("Griefing spawn", result.reason());
        assertNull(result.expiresAt());
    }

    @Test
    void parseBanCheckResponse_tempBan_parsesExpiry() {
        String json = """
                {
                  "banned": true,
                  "punishment": {
                    "id": "abc-456",
                    "type": "tempban",
                    "reason": "Spam",
                    "staff_id": null,
                    "created_at": "2026-08-17T10:00:00Z",
                    "expires_at": "2026-08-18T10:00:00Z"
                  }
                }
                """;

        BanEnforcer.BanCheckResult result = BanEnforcer.parseBanCheckResponse(json);

        assertTrue(result.banned());
        assertEquals("tempban", result.type());
        assertEquals("2026-08-18T10:00:00Z", result.expiresAt());
    }

    @Test
    void parseBanCheckResponse_bannedTrueButMissingPunishmentObject_doesNotThrow() {
        // Defensive parsing per the class javadoc — shouldn't happen per the
        // real endpoint contract, but must not crash the login flow if it did.
        String json = "{\"banned\": true}";

        BanEnforcer.BanCheckResult result = assertDoesNotThrow(
                () -> BanEnforcer.parseBanCheckResponse(json));

        assertTrue(result.banned());
        assertNotNull(result.reason());
    }

    @Test
    void checkActiveBan_returnsParsedResultOn200() throws Exception {
        when(apiClient.get("/api/v1/plugin/punishments/some-uuid/active")).thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);
        when(httpResponse.body()).thenReturn("{\"banned\": false, \"punishment\": null}");

        BanEnforcer.BanCheckResult result = banEnforcer.checkActiveBan("some-uuid");

        assertFalse(result.banned());
        verify(apiClient).get("/api/v1/plugin/punishments/some-uuid/active");
    }

    @Test
    void checkActiveBan_non200_throws() throws Exception {
        when(apiClient.get("/api/v1/plugin/punishments/some-uuid/active")).thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(401);
        when(httpResponse.body()).thenReturn("Invalid or missing plugin key");

        assertThrows(IllegalStateException.class, () -> banEnforcer.checkActiveBan("some-uuid"));
    }
}

