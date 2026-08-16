"""
tests/test_node_auth_service.py — Unit tests for services/node_auth_service.py.

Round-trip verification here uses this same service's own verify_node_token
(there's no Go daemon in this test environment) — cross-language
compatibility with the actual daemon verifier was confirmed manually during
development (see PHASE2_CHANGES.md) by issuing a token here and verifying it
against a real build of umbrella-daemon's internal/auth package; that
confirmation isn't re-run automatically by this suite since it would require
a Go toolchain in CI, which is out of scope for umbrella-core's own test
environment.
"""
import time

import jwt
import pytest

from services.node_auth_service import (
    NodeAuthError,
    issue_node_token,
    verify_node_token,
)

SECRET = "a-shared-secret-at-least-32-bytes-long-ok"


def test_issue_and_verify_round_trip():
    token = issue_node_token("node-1", SECRET)
    claims = verify_node_token(token, SECRET)
    assert claims.node_id == "node-1"
    assert claims.scope == "node"


def test_issue_rejects_empty_node_id():
    with pytest.raises(NodeAuthError):
        issue_node_token("", SECRET)


def test_issue_rejects_short_secret():
    with pytest.raises(NodeAuthError):
        issue_node_token("node-1", "too-short")


def test_verify_rejects_expired_token():
    token = issue_node_token("node-1", SECRET, ttl_seconds=-10)
    with pytest.raises(NodeAuthError):
        verify_node_token(token, SECRET)


def test_verify_rejects_token_signed_with_different_secret():
    token = issue_node_token("node-1", SECRET)
    with pytest.raises(NodeAuthError):
        verify_node_token(token, "a-completely-different-secret-value-123")


def test_verify_rejects_garbage_token():
    with pytest.raises(NodeAuthError):
        verify_node_token("not.a.validtoken", SECRET)


def test_verify_rejects_alg_none_token():
    """Regression test for the classic JWT 'alg: none' bypass — mirrors the
    equivalent test on the Go daemon side (internal/auth/node_token_test.go)."""
    forged = jwt.encode(
        {"node_id": "node-1", "scope": "node", "iss": "umbrella-core"},
        key="",
        algorithm="none",
    )
    with pytest.raises(NodeAuthError):
        verify_node_token(forged, SECRET)


def test_verify_rejects_wrong_scope():
    now = int(time.time())
    token = jwt.encode(
        {
            "node_id": "node-1",
            "scope": "something-else",
            "iss": "umbrella-core",
            "sub": "node-1",
            "iat": now,
            "nbf": now,
            "exp": now + 300,
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(NodeAuthError, match="scope"):
        verify_node_token(token, SECRET)


def test_verify_rejects_wrong_issuer():
    now = int(time.time())
    token = jwt.encode(
        {
            "node_id": "node-1",
            "scope": "node",
            "iss": "some-other-issuer",
            "sub": "node-1",
            "iat": now,
            "nbf": now,
            "exp": now + 300,
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(NodeAuthError):
        verify_node_token(token, SECRET)
