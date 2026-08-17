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
import java.util.logging.Logger;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class CoreApiClientTest {

    @Mock
    HttpClient httpClient;

    @Mock
    HttpResponse<String> httpResponse;

    private CoreApiClient client;

    @BeforeEach
    void setUp() {
        client = new CoreApiClient(
                "http://localhost:8000", "test-plugin-key", Logger.getAnonymousLogger(),
                httpClient, Duration.ofSeconds(5));
    }

    @Test
    void buildRequest_attachesPluginKeyHeaderExactlyOnce() {
        HttpRequest request = client.buildRequest("/api/v1/plugin/heartbeat").GET().build();

        assertEquals(1, request.headers().allValues("X-Plugin-Key").size());
        assertEquals("test-plugin-key", request.headers().firstValue("X-Plugin-Key").orElseThrow());
    }

    @Test
    void buildRequest_setsJsonContentType() {
        HttpRequest request = client.buildRequest("/api/v1/plugin/config").GET().build();

        assertEquals("application/json", request.headers().firstValue("Content-Type").orElseThrow());
    }

    @Test
    void buildRequest_joinsBaseUrlAndPathCorrectly_noDoubleSlash() {
        HttpRequest request = client.buildRequest("/api/v1/plugin/heartbeat").GET().build();

        assertEquals("http://localhost:8000/api/v1/plugin/heartbeat", request.uri().toString());
    }

    @Test
    void buildRequest_addsLeadingSlashIfCallerOmitsIt() {
        HttpRequest request = client.buildRequest("api/v1/plugin/config").GET().build();

        assertEquals("http://localhost:8000/api/v1/plugin/config", request.uri().toString());
    }

    @Test
    void constructor_stripsTrailingSlashFromBaseUrl() {
        CoreApiClient trailingSlashClient = new CoreApiClient(
                "http://localhost:8000/", "key", Logger.getAnonymousLogger(),
                httpClient, Duration.ofSeconds(5));

        HttpRequest request = trailingSlashClient.buildRequest("/api/v1/plugin/heartbeat").GET().build();

        assertEquals("http://localhost:8000/api/v1/plugin/heartbeat", request.uri().toString());
    }

    @Test
    void constructor_rejectsBlankPluginKey() {
        assertThrows(IllegalArgumentException.class, () ->
                new CoreApiClient("http://localhost:8000", "  ", Logger.getAnonymousLogger(),
                        httpClient, Duration.ofSeconds(5)));
    }

    @Test
    void constructor_rejectsBlankBaseUrl() {
        assertThrows(IllegalArgumentException.class, () ->
                new CoreApiClient("", "key", Logger.getAnonymousLogger(),
                        httpClient, Duration.ofSeconds(5)));
    }

    @Test
    void post_sendsBodyAndReturnsResponse() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);

        HttpResponse<String> result = client.post("/api/v1/plugin/heartbeat", "{\"online_count\":5}");

        assertEquals(200, result.statusCode());
        verify(httpClient).send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class));
    }

    @Test
    void get_returnsResponse() throws IOException, InterruptedException {
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class)))
                .thenReturn(httpResponse);
        when(httpResponse.statusCode()).thenReturn(200);

        HttpResponse<String> result = client.get("/api/v1/plugin/config");

        assertEquals(200, result.statusCode());
    }
}
