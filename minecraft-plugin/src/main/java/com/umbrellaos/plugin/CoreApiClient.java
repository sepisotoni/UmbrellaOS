package com.umbrellaos.plugin;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.logging.Logger;

/**
 * The single chokepoint for every HTTP call this plugin makes to
 * umbrella-core. The {@code X-Plugin-Key} auth header is attached exactly
 * once, here — no call site anywhere else in the plugin should build its
 * own {@link HttpRequest} against core directly.
 *
 * <p>Endpoint paths passed to {@link #get(String)} / {@link #post(String,
 * String)} are the full core-side path, e.g. {@code /api/v1/plugin/heartbeat}
 * — verified directly against {@code api/routers/plugin.py} in umbrella-core
 * (the scoping doc on the {@code archive} branch says {@code /plugin/heartbeat}
 * without the {@code /api/v1} prefix; the real router mounts at
 * {@code /api/v1/plugin}, so callers here use the verified path, not the
 * doc's).
 */
public class CoreApiClient {

    private final String baseUrl;
    private final String pluginKey;
    private final HttpClient httpClient;
    private final Logger logger;
    private final Duration requestTimeout;

    public CoreApiClient(String baseUrl, String pluginKey, Logger logger) {
        this(baseUrl, pluginKey, logger,
                HttpClient.newBuilder()
                        .connectTimeout(Duration.ofSeconds(10))
                        .build(),
                Duration.ofSeconds(10));
    }

    /**
     * Test/advanced-use constructor — allows injecting a fake {@link HttpClient}
     * (unit tests) or a non-default timeout, without touching the real-network
     * constructor above.
     */
    CoreApiClient(String baseUrl, String pluginKey, Logger logger,
                  HttpClient httpClient, Duration requestTimeout) {
        if (baseUrl == null || baseUrl.isBlank()) {
            throw new IllegalArgumentException("core base-url must not be blank");
        }
        if (pluginKey == null || pluginKey.isBlank()) {
            throw new IllegalArgumentException("plugin-key must not be blank");
        }
        this.baseUrl = stripTrailingSlash(baseUrl);
        this.pluginKey = pluginKey;
        this.logger = logger;
        this.httpClient = httpClient;
        this.requestTimeout = requestTimeout;
    }

    private static String stripTrailingSlash(String url) {
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }

    /**
     * Builds a request against {@code baseUrl + path} with the auth header
     * and content type attached. Package-private and side-effect-free
     * (doesn't send anything) specifically so unit tests can assert on the
     * built request without a real or mocked network round trip.
     */
    HttpRequest.Builder buildRequest(String path) {
        String fullPath = path.startsWith("/") ? path : "/" + path;
        return HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + fullPath))
                .timeout(requestTimeout)
                .header("X-Plugin-Key", pluginKey)
                .header("Content-Type", "application/json")
                .header("Accept", "application/json");
    }

    /**
     * POSTs a JSON body to core. Returns the raw response so callers
     * (HeartbeatManager, etc.) decide how to log/react — this class stays
     * transport-only, no business logic about what a given endpoint means.
     */
    public HttpResponse<String> post(String path, String jsonBody)
            throws IOException, InterruptedException {
        HttpRequest request = buildRequest(path)
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();
        return httpClient.send(request, HttpResponse.BodyHandlers.ofString());
    }

    /**
     * GETs from core. Same raw-response contract as {@link #post}.
     */
    public HttpResponse<String> get(String path)
            throws IOException, InterruptedException {
        HttpRequest request = buildRequest(path)
                .GET()
                .build();
        return httpClient.send(request, HttpResponse.BodyHandlers.ofString());
    }

    public Logger logger() {
        return logger;
    }
}
