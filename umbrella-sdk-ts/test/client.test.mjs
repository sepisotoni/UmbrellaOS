import assert from "node:assert/strict";
import { test } from "node:test";
import { UmbrellaApiError, UmbrellaClient } from "../dist/client.js";

test("non-JSON error responses retain their body in one read", async () => {
  const response = new Response("upstream unavailable", {
    status: 502,
    statusText: "Bad Gateway",
  });
  let bodyReads = 0;
  const readText = response.text.bind(response);
  response.text = async () => {
    bodyReads += 1;
    return readText();
  };
  const client = new UmbrellaClient({
    baseUrl: "https://umbrella.example.test",
    apiKey: "test-key",
    fetchFn: async () => response,
  });

  await assert.rejects(client.invoke("example.action"), (error) => {
    assert.ok(error instanceof UmbrellaApiError);
    assert.equal(error.status, 502);
    assert.equal(error.body, "upstream unavailable");
    assert.match(error.message, /502 Bad Gateway — upstream unavailable/);
    return true;
  });
  assert.equal(bodyReads, 1);
});
