package com.umbrellaos.plugin;

import ac.grim.grimac.api.GrimAPIProvider;
import ac.grim.grimac.api.event.events.FlagEvent;
import org.bukkit.Bukkit;
import org.bukkit.plugin.Plugin;

import java.io.IOException;
import java.net.http.HttpResponse;
import java.util.UUID;
import java.util.logging.Logger;

/**
 * GrimAC bridge — registers against GrimAC's EventBus at enable time and
 * forwards every {@link FlagEvent} to {@code POST /api/v1/anticheat/flag}
 * on umbrella-core.
 *
 * <p><b>Soft-dependency:</b> registration only happens when GrimAC is
 * actually present and enabled. If it's absent the plugin loads and runs
 * normally — the bridge is simply inactive, and a single INFO log line
 * says so. The {@code softdepend: [GrimAC]} entry in {@code plugin.yml}
 * ensures Paper classloads GrimAC's API before this plugin if both are
 * installed, which is required for our compile-time import to resolve.
 *
 * <p><b>Why not reflection?</b> The old UmbrellaOS/UmbrellaMC plugin
 * used {@code Class.forName("ac.grim.grimac.api.event.events.PunishmentEvent")}
 * to avoid a compile-time dep — a class that does not exist. That silently
 * no-op'd forever in production. Using a real {@code provided}-scope dep
 * means a wrong class or method name fails the build immediately.
 *
 * <p><b>VL conversion:</b> {@code Check.getViolations()} returns a
 * {@code double}. Core's {@code handle_cheat_flag} takes {@code vl: int}.
 * We round (not truncate) per the dispatch doc: {@code Math.round(check.getViolations())}.
 * This preserves intent — a 1.9-VL flag is a 2, not a 1.
 *
 * <p><b>server_id (P15 Task 5):</b> The {@code server_id} field is read from
 * {@code server.id} in {@code config.yml} (via the constructor) and included
 * in every flag payload sent to core. This allows the dashboard's
 * {@code GET /api/v1/anticheat/violations?server_id=...} filter to work
 * when multiple Minecraft servers report to the same umbrella-core instance.
 * Defaults to {@code "default"} when the config key is blank or absent.
 */
public final class GrimBridge {

    private static final String FLAG_PATH = "/api/v1/anticheat/flag";
    private static final String DEFAULT_SERVER_ID = "default";

    private final Plugin owningPlugin;
    private final CoreApiClient apiClient;
    private final Logger logger;
    private final String serverId;

    private boolean registered = false;

    public GrimBridge(Plugin owningPlugin, CoreApiClient apiClient) {
        this(owningPlugin, apiClient, DEFAULT_SERVER_ID);
    }

    public GrimBridge(Plugin owningPlugin, CoreApiClient apiClient, String serverId) {
        this.owningPlugin = owningPlugin;
        this.apiClient = apiClient;
        this.logger = apiClient.logger();
        // Normalise: blank/null config value → "default"
        this.serverId = (serverId != null && !serverId.isBlank()) ? serverId : DEFAULT_SERVER_ID;
    }

    /**
     * Attempts to register against GrimAC's EventBus. Safe to call
     * unconditionally — guards internally and logs the outcome either way.
     *
     * <p>Must be called <em>after</em> server startup is complete (i.e. from
     * {@link org.bukkit.plugin.java.JavaPlugin#onEnable()}) so that
     * {@link Bukkit#getPluginManager()} reflects the final plugin load order.
     */
    public void register() {
        if (!Bukkit.getPluginManager().isPluginEnabled("GrimAC")) {
            logger.info("[GrimBridge] GrimAC is not enabled — flag bridge inactive. "
                    + "Install GrimAC alongside UmbrellaOSPlugin to activate anticheat reporting.");
            return;
        }

        ac.grim.grimac.api.plugin.GrimPlugin grimPlugin = new ac.grim.grimac.api.plugin.GrimPlugin() {
            @Override
            public ac.grim.grimac.api.plugin.GrimPluginDescription getDescription() {
                return null;
            }

            @Override
            public Logger getLogger() {
                return owningPlugin.getLogger();
            }

            @Override
            public java.io.File getDataFolder() {
                return owningPlugin.getDataFolder();
            }
        };

        GrimAPIProvider.get().getEventBus().subscribe(grimPlugin, FlagEvent.class, event -> {
            UUID uuid = event.getUser().getUniqueId();
            String name = event.getUser().getName();
            String checkName = event.getCheck().getCheckName();
            int vl = (int) Math.round(event.getCheck().getViolations());
            String verbose = event.getVerbose();

            reportFlag(uuid, name, checkName, verbose, vl);
        });

        registered = true;
        logger.info("[GrimBridge] Registered against GrimAC EventBus — "
                + "flag events will be forwarded to " + FLAG_PATH
                + " (server_id=" + serverId + ")");
    }

    /**
     * Whether the bridge successfully registered. Exposed for tests and
     * diagnostic logging — not for branching on in production callers.
     */
    public boolean isRegistered() {
        return registered;
    }

    /**
     * Returns the server ID this bridge will include in flag payloads.
     * Package-private for test assertions.
     */
    String getServerId() {
        return serverId;
    }

    /**
     * Builds the JSON payload and POSTs it to core. Package-private so
     * {@link GrimBridgeTest} can call it directly without needing a real
     * GrimAC EventBus.
     *
     * <p>Failure (network error, non-2xx) is logged and swallowed — a flag
     * that fails to report to core must never crash the Bukkit event dispatch
     * thread, which would bubble up to GrimAC and potentially destabilise the
     * server.
     */
    void reportFlag(UUID playerUuid, String playerName,
                    String checkName, String verbose, int vl) {
        String body = buildFlagPayload(playerUuid, playerName, checkName, verbose, vl, serverId);
        try {
            HttpResponse<String> response = apiClient.post(FLAG_PATH, body);
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                logger.warning("[GrimBridge] core returned HTTP " + response.statusCode()
                        + " for flag report (player=" + playerName
                        + " check=" + checkName + " vl=" + vl + ")");
            }
        } catch (IOException | InterruptedException e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            logger.warning("[GrimBridge] Failed to report flag to core: " + e.getMessage()
                    + " (player=" + playerName + " check=" + checkName + " vl=" + vl + ")");
        }
    }

    /**
     * Constructs the JSON body for {@code POST /api/v1/anticheat/flag} using
     * default server ID.
     */
    static String buildFlagPayload(UUID playerUuid, String playerName,
                                   String checkName, String verbose, int vl) {
        return buildFlagPayload(playerUuid, playerName, checkName, verbose, vl, DEFAULT_SERVER_ID);
    }

    /**
     * Constructs the JSON body for {@code POST /api/v1/anticheat/flag}.
     * Package-private so tests can assert on it without making network calls.
     *
     * <p>Shape verified against {@code api/routers/anticheat.py} in
     * umbrella-core — specifically {@code AnticheatFlagRequest}'s Pydantic
     * model. Using manual string-building here (same pattern as Step 1/2)
     * rather than a JSON library, because {@code verbose} is the only
     * potentially-untrusted string field and we escape it manually.
     *
     * <p>The {@code server_id} field was added in P15 Task 5. Old core
     * versions (pre-P15) will simply ignore the unknown field — Pydantic
     * silently discards extra keys by default.
     */

    static String buildFlagPayload(UUID playerUuid, String playerName,
                                   String checkName, String verbose, int vl,
                                   String serverId) {
        // Escape double-quotes in free-text fields so the JSON body stays valid
        // if GrimAC's verbose string contains them (it sometimes does).
        String safeName    = escapeJson(playerName);
        String safeCheck   = escapeJson(checkName);
        String safeVerbose = verbose != null ? escapeJson(verbose) : "";
        String safeServerId = serverId != null ? escapeJson(serverId) : DEFAULT_SERVER_ID;

        return "{"
                + "\"player_uuid\":\"" + playerUuid + "\","
                + "\"player_name\":\"" + safeName + "\","
                + "\"check_name\":\"" + safeCheck + "\","
                + "\"verbose\":\"" + safeVerbose + "\","
                + "\"vl\":" + vl + ","
                + "\"server_id\":\"" + safeServerId + "\""
                + "}";
    }

    private static String escapeJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
