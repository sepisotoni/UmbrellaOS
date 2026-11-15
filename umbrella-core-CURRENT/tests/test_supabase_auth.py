import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from config import get_settings
import services.supabase_auth as supabase_auth


@pytest.fixture
def signing_key(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk["kid"] = "test-key"
    jwks = {"keys": [public_jwk]}

    async def get_test_jwks(_url, *, force_refresh=False):
        return jwks

    monkeypatch.setattr(supabase_auth, "_get_jwks", get_test_jwks)
    monkeypatch.setattr(get_settings(), "supabase_url", "https://example.supabase.co")
    return private_key


def _token(private_key, **overrides):
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
        "iat": now,
        "exp": now + 300,
        "app_metadata": {
            "umbrella_user_id": str(uuid.uuid4()),
            "umbrella_role": "moderator",
            "umbrella_permissions": ["players.view"],
            "umbrella_authz_version": 0,
        },
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


@pytest.mark.asyncio
async def test_valid_supabase_token_returns_verified_claims(signing_key):
    claims = await supabase_auth.validate_access_token(_token(signing_key))

    assert claims["aud"] == "authenticated"
    assert claims["app_metadata"]["umbrella_permissions"] == ["players.view"]


@pytest.mark.asyncio
async def test_invalid_issuer_is_rejected(signing_key):
    token = _token(signing_key, iss="https://attacker.example/auth/v1")

    with pytest.raises(HTTPException) as exc:
        await supabase_auth.validate_access_token(token)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_token_without_server_managed_permissions_is_rejected(signing_key):
    token = _token(
        signing_key,
        app_metadata={"umbrella_user_id": str(uuid.uuid4())},
    )

    with pytest.raises(HTTPException) as exc:
        await supabase_auth.validate_access_token(token)

    assert exc.value.status_code == 403
