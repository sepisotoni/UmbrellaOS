"""
services/node_auth_service.py — Issues the signed node tokens umbrella-core
presents to a node's umbrella-daemon on every request.

This is the Python-side counterpart to the daemon's `internal/auth` package
(see umbrella-daemon's docs/adr/0002-daemon-environment-abstraction.md) —
the two must produce/verify byte-for-byte compatible tokens despite being
different languages, since the daemon is what actually verifies them. The
contract between them is:

    - HS256-signed JWT
    - Claims: {"node_id": <str>, "scope": "node", "iss": "umbrella-core",
               "sub": <node_id>, "iat", "nbf", "exp"} — a flat object,
      matching how Go's embedded `jwt.RegisteredClaims` promotes its fields
      to the same JSON level as `NodeClaims`' own `node_id`/`scope` fields.
    - The signing secret is the Node's own `signing_secret` column
      (exchanged once at registration, never transmitted per-request).

Changing this contract requires changing both sides together — it is
intentionally not something either side can version independently, since
there is exactly one verifier (the daemon) and one issuer (this service).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import jwt

NODE_TOKEN_SCOPE = "node"
DEFAULT_TOKEN_TTL_SECONDS = 300  # short-lived by design — see ADR-0002 on the daemon side


class NodeAuthError(Exception):
    """Raised for any node-token issuance/verification failure."""


@dataclass(frozen=True)
class NodeClaims:
    node_id: str
    scope: str


def issue_node_token(node_id: str, signing_secret: str, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS) -> str:
    """
    Issue a signed token asserting node_id, valid for ttl_seconds.

    Raises NodeAuthError if node_id is empty or signing_secret is too short
    to be a meaningful HMAC key — mirroring the daemon-side Issuer's own
    validation, so a misconfigured node fails loudly here rather than
    producing a token the daemon will reject anyway with a less useful
    error message.
    """
    if not node_id:
        raise NodeAuthError("node_id must not be empty")
    if len(signing_secret) < 32:
        raise NodeAuthError(f"signing_secret must be at least 32 characters, got {len(signing_secret)}")

    now = int(time.time())
    payload = {
        "node_id": node_id,
        "scope": NODE_TOKEN_SCOPE,
        "iss": "umbrella-core",
        "sub": node_id,
        "iat": now,
        "nbf": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, signing_secret, algorithm="HS256")


def verify_node_token(token: str, signing_secret: str) -> NodeClaims:
    """
    Verify a node token issued by this same service (used in tests and by
    any future core-side consumer of node tokens — the daemon is the
    primary verifier in production, but core verifying its own issuance is
    useful for round-trip testing without spinning up the Go daemon).
    """
    try:
        payload = jwt.decode(
            token,
            signing_secret,
            algorithms=["HS256"],
            issuer="umbrella-core",
        )
    except jwt.PyJWTError as exc:
        raise NodeAuthError(f"token invalid: {exc}") from exc

    if payload.get("scope") != NODE_TOKEN_SCOPE:
        raise NodeAuthError(f"unexpected token scope {payload.get('scope')!r}")

    return NodeClaims(node_id=payload["node_id"], scope=payload["scope"])
