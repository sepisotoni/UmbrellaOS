# ADR-0003: Hosting domain — nodes, templates, allocations, servers

**Status:** Accepted, implemented (Phase 2).

## Context

Phase 2 needed a multi-server, multi-node hosting domain in `umbrella-core`, declared through Phase
0's Capability Registry, actually calling umbrella-daemon's HTTP API (Phase 1) to create and control
containers. Two things needed explicit decisions before writing code: how this relates to the
pre-existing `server_control_service.py`, and how core and daemon authenticate to each other in
practice (not just in principle, per Phase 1's ADR-0002).

## Decision

**Coexistence with the legacy single-server control path, not replacement.** `server_control_service.py`
is a shell-command-based, single-server, non-containerized control mechanism built for the original
UmbrellaMC deployment model (one server, tracked via `PluginHeartbeat`). The new `hosting.*` domain is
a completely different mechanism — Docker-orchestrated, multi-server, multi-node, daemon-mediated.
They are **not unified in this phase**: forcing every existing single-server deployment onto the new
Docker/daemon model now would be a breaking migration imposed on users who haven't opted into it. The
two permission namespaces reflect this explicitly — the legacy path keeps its existing `server.control`
permission key; the new domain uses `hosting.server.control`, a distinct key, so a role grant for one
was never accidentally interpreted as a grant for the other. Consolidating the two mechanisms (or
deprecating the legacy one) is left as a future, explicit decision once the hosting domain has real
usage to evaluate migration against — not decided speculatively here.

**Templates are versioned; Servers pin the version they were created with.** `ServerTemplate.version`
increments on every edit (`ServerTemplateService.update_template`); `Server.template_version` is
captured once, at creation, and never changes. Editing a template afterward — a new default memory
size, a different startup command — never silently changes what an already-running server does.

**Core and daemon authenticate via a secret exchanged once, tokens issued per-call.** The daemon's own
Go side (`internal/auth`, ADR-0002) verifies short-lived JWTs; this phase's Python-side counterpart
(`services/node_auth_service.py`) issues them. The two must produce byte-for-byte compatible tokens
despite being different languages and were **verified as genuinely compatible**, not assumed: a token
issued by the Python service was fed into an actual build of the daemon's Go `auth.Issuer` during this
phase's development and confirmed to verify correctly (see PHASE2_CHANGES.md) — a real cross-language
check, not a claim resting on "the field names look right."

`DaemonClient` (`services/daemon_client.py`) issues a fresh token on every request rather than caching
one — tokens are cheap to issue (HMAC signing, no round trip) and short-lived by design, so there's no
meaningful cost to always issuing fresh rather than managing token refresh/expiry logic for a cached
one.

**`Create`/`Remove` were added to the daemon's HTTP API in this phase, not Phase 1.** Phase 1's own
changelog explicitly deferred these two routes because there was no real `ContainerSpec` source yet to
build a request from — this phase is that source (a template + node + allocations), so the routes and
their request/response shapes were added now, informed by an actual caller, rather than guessed at
speculatively a phase earlier.

**Port-to-container-port mapping keeps a simple convention in this phase**: a Server's allocation port
numbers double as the in-container port (e.g. host port 25565 maps to container port 25565). Real
per-allocation container-port remapping (letting a template declare "my game port is container-internal
25565 regardless of which host port it's bound to") is a genuine gap — not built now because no current
template needs it, and building the general case speculatively would be exactly the kind of
premature complexity this project's engineering rules warn against. Flagged here rather than silently
assumed away.

**`ServerService` methods accept an optional `daemon_client` parameter**, defaulting to constructing a
real `DaemonClient` from the server's `Node`. This is the same dependency-injection seam used
throughout the project (umbrella-daemon's `DockerClient` interface, the Capability Registry's
`CallContext`) — production code never passes it explicitly; tests inject a fake implementing the same
public methods, which is how `ServerService`'s orchestration logic (allocation validation, status
transitions, rollback-on-daemon-failure) is verified without a running daemon.

## Consequences

**What this buys:**
- 16 hosting capabilities became reachable via REST and the CLI simultaneously, with zero
  CLI-specific or REST-specific code written for any of them — the Capability Registry's Phase 0
  promise held up under a real, second domain, not just the original proof-of-concept capabilities.
- A daemon crash-recovery/self-healing policy (Phase 4) can reuse the exact same `DaemonClient` and
  `ServerService` methods a human operator's REST call uses — there's no separate "automation path"
  with its own daemon-communication logic to keep in sync.

**Trade-offs accepted, explicitly:**
- No event bus / WebSocket gateway wiring in this phase, despite the master roadmap describing Phase 2
  as where it's "stood up." Nothing yet consumes real-time hosting events (no dashboard exists to
  subscribe to them) — building the publish side without a consumer to validate the message shape
  against would be speculative infrastructure. Deferred to land alongside Phase 3's dashboard, where a
  real consumer exists to design the event shape against.
- The one-container-port-per-allocation-port convention (above) is a real limitation, not a hidden one.

## Alternatives considered

- **Migrating `server_control_service.py`'s users onto the hosting domain immediately**: rejected — a
  breaking change imposed on existing deployments with no opt-in, for a phase whose job was building
  the new capability, not deprecating the old one.
- **A single shared permission key across legacy and hosting server control**: rejected — collapsing
  `server.control` and `hosting.server.control` into one key would mean a role grant intended for one
  single legacy server silently also grants control over the entire new multi-server fleet, which is a
  real permission-boundary mistake waiting to happen, not a simplification worth making.
