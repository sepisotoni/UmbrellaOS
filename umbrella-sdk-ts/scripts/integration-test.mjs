/**
 * integration-test.mjs — Task A verification: exercises the built
 * `@umbrellaos/sdk` package against a real, running local umbrella-core
 * instance (SQLite-backed, started by run-integration-test.sh), not a
 * mock. Confirms `listCapabilities()` sees the real registry and that
 * `invoke()` can drive one full real capability round-trip
 * (marketplace.install.list) through the generated client.
 *
 * Not run as part of `npm run typecheck`/`build` — this is a one-off
 * verification script for the Phase 7 completion dispatch's handback,
 * run manually against a locally-booted backend (see
 * run-integration-test.sh in the same handback for how that backend is
 * started).
 */
import { UmbrellaClient } from "../dist/index.js";

const baseUrl = process.env.UMBRELLA_BASE_URL ?? "http://127.0.0.1:8123";
const apiKey = process.env.UMBRELLA_API_KEY;

if (!apiKey) {
  console.error("UMBRELLA_API_KEY env var is required");
  process.exit(1);
}

const client = new UmbrellaClient({ baseUrl, apiKey });

let failures = 0;

function assert(condition, message) {
  if (!condition) {
    failures += 1;
    console.error(`FAIL: ${message}`);
  } else {
    console.log(`PASS: ${message}`);
  }
}

// 1. GET /api/v1/capabilities — real registry introspection.
const capabilities = await client.listCapabilities();
assert(Array.isArray(capabilities), "listCapabilities() returns an array");
assert(capabilities.length > 50, `listCapabilities() returns a real, populous registry (got ${capabilities.length})`);
const marketplaceInstallList = capabilities.find((c) => c.name === "marketplace.install.list");
assert(!!marketplaceInstallList, "registry includes marketplace.install.list");
assert(
  marketplaceInstallList?.required_permission === "marketplace.install.view",
  "marketplace.install.list reports its real required_permission",
);

// 2. POST /api/v1/capabilities/marketplace.install.list/invoke — a real
// capability round-trip through the generic invoke path. Empty install
// list is a valid, real response (no plugins installed in this fresh
// SQLite DB) — the point is the request completed and typed correctly,
// not that any particular plugin is installed.
const installs = await client.invoke("marketplace.install.list", {});
assert(Array.isArray(installs), "invoke('marketplace.install.list') returns an array");

// 3. A real write + read round-trip: create a webhook subscription, list
// it back, then delete it — proves invoke() handles params, a
// server-generated id, and a 3-call sequence, not just a single
// read-only GET-shaped call.
const created = await client.invoke("webhooks.subscription.create", {
  topic: "sdk.integration_test",
  url: "https://example.com/umbrella-sdk-integration-test",
});
assert(typeof created.id === "string" && created.id.length > 0, "webhooks.subscription.create returns a real generated id");
assert(typeof created.secret === "string" && created.secret.length > 0, "webhooks.subscription.create returns a signing secret on creation");

const listed = await client.invoke("webhooks.subscription.list", { topic: "sdk.integration_test" });
assert(
  Array.isArray(listed) && listed.some((s) => s.id === created.id),
  "webhooks.subscription.list reflects the just-created subscription",
);
assert(
  Array.isArray(listed) && listed.every((s) => s.secret === undefined || s.secret === null),
  "webhooks.subscription.list never includes the signing secret",
);

const deleted = await client.invoke("webhooks.subscription.delete", { subscription_id: created.id });
assert(deleted.deleted === true, "webhooks.subscription.delete confirms deletion");

// 4. Error path: an invalid capability name should surface as a real
// UmbrellaApiError, not throw something unstructured.
let sawExpectedError = false;
try {
  await client.invoke("this.capability.does_not_exist", {});
} catch (err) {
  sawExpectedError = err && err.name === "UmbrellaApiError" && typeof err.status === "number";
}
assert(sawExpectedError, "invoking an unknown capability raises a structured UmbrellaApiError");

console.log(`\n${failures === 0 ? "ALL PASSED" : `${failures} FAILURE(S)`}`);
process.exit(failures === 0 ? 0 : 1);
