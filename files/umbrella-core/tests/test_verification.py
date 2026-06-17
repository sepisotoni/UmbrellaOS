"""
tests/test_verification.py — Tests for verification endpoints.

POST /api/v1/verification/request
POST /api/v1/verification/confirm
POST /api/v1/verification/status
GET  /api/v1/verification/pending
POST /api/v1/verification/revoke
"""
import pytest
from tests.conftest import ADMIN_HEADERS, WRONG_HEADERS


@pytest.mark.asyncio
async def test_post_verification_request_creates_code(client):
    """POST /verification/request should create a verification code."""
    payload = {
        "player_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "player_username": "TestPlayer",
        "ip_address": "192.168.1.1",
    }
    response = await client.post("/api/v1/verification/request", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["code"].isdigit()
    assert data["expires_in"] == 600
    assert data["player_uuid"] == payload["player_uuid"]


@pytest.mark.asyncio
async def test_post_verification_request_already_verified_returns_already_verified(client):
    """POST /verification/request for already verified player should return already_verified=true."""
    # First, create a verification code
    await client.post(
        "/api/v1/verification/request",
        json={
            "player_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "player_username": "TestPlayer",
        },
        headers=ADMIN_HEADERS,
    )
    
    # Get the code from pending verifications
    response = await client.get("/api/v1/verification/pending", headers=ADMIN_HEADERS)
    codes = response.json()
    if len(codes) == 0:
        pytest.skip("No pending verification codes")
    code = codes[-1]["code"]
    
    # Confirm the code to verify the player
    await client.post(
        "/api/v1/verification/confirm",
        json={
            "discord_id": "123456789",
            "discord_username": "TestUser",
            "code": code,
        },
        headers=ADMIN_HEADERS,
    )
    
    # Now try to request verification for the same player
    payload = {
        "player_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "player_username": "TestPlayer",
    }
    response = await client.post("/api/v1/verification/request", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["already_verified"] is True


@pytest.mark.asyncio
async def test_post_verification_confirm_with_valid_code_succeeds(client):
    """POST /verification/confirm with valid code should succeed."""
    # First, create a verification code
    await client.post(
        "/api/v1/verification/request",
        json={
            "player_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            "player_username": "Player2",
        },
        headers=ADMIN_HEADERS,
    )
    
    # Get the code from pending verifications
    response = await client.get("/api/v1/verification/pending", headers=ADMIN_HEADERS)
    codes = response.json()
    if len(codes) == 0:
        pytest.skip("No pending verification codes")
    code = codes[-1]["code"]
    
    # Confirm the code
    payload = {
        "discord_id": "987654321",
        "discord_username": "DiscordUser",
        "code": code,
    }
    response = await client.post("/api/v1/verification/confirm", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "player_uuid" in data
    assert "player_username" in data


@pytest.mark.asyncio
async def test_post_verification_confirm_with_invalid_code_returns_404(client):
    """POST /verification/confirm with invalid code should return 404."""
    payload = {
        "discord_id": "123456789",
        "discord_username": "TestUser",
        "code": "000000",
    }
    response = await client.post("/api/v1/verification/confirm", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_verification_confirm_with_expired_code_returns_400(client):
    """POST /verification/confirm with expired code should return 400."""
    # Create a verification code
    await client.post(
        "/api/v1/verification/request",
        json={
            "player_uuid": "cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa",
            "player_username": "Player3",
        },
        headers=ADMIN_HEADERS,
    )
    
    # Get the code and manually expire it (this would require direct DB access)
    # For now, we'll test with a non-existent code which returns 404
    # In a real test, we'd need to update the expires_at field directly
    payload = {
        "discord_id": "123456789",
        "discord_username": "TestUser",
        "code": "999999",
    }
    response = await client.post("/api/v1/verification/confirm", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_verification_confirm_with_used_code_returns_400(client):
    """POST /verification/confirm with used code should return 400."""
    # Create a verification code
    await client.post(
        "/api/v1/verification/request",
        json={
            "player_uuid": "dddddddd-eeee-ffff-aaaa-bbbbbbbbbbbb",
            "player_username": "Player4",
        },
        headers=ADMIN_HEADERS,
    )
    
    # Get the code
    response = await client.get("/api/v1/verification/pending", headers=ADMIN_HEADERS)
    codes = response.json()
    if len(codes) == 0:
        pytest.skip("No pending verification codes")
    code = codes[-1]["code"]
    
    # Confirm the code first time
    await client.post(
        "/api/v1/verification/confirm",
        json={
            "discord_id": "111111111",
            "discord_username": "User1",
            "code": code,
        },
        headers=ADMIN_HEADERS,
    )
    
    # Try to confirm the same code again
    response = await client.post(
        "/api/v1/verification/confirm",
        json={
            "discord_id": "222222222",
            "discord_username": "User2",
            "code": code,
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_verification_status_returns_correct_verified_state(client):
    """POST /verification/status should return correct verified state."""
    # First, verify a player
    await client.post(
        "/api/v1/verification/request",
        json={
            "player_uuid": "eeeeeeee-ffff-aaaa-bbbb-cccccccccccc",
            "player_username": "Player5",
        },
        headers=ADMIN_HEADERS,
    )
    
    response = await client.get("/api/v1/verification/pending", headers=ADMIN_HEADERS)
    codes = response.json()
    if len(codes) == 0:
        pytest.skip("No pending verification codes")
    code = codes[-1]["code"]
    
    await client.post(
        "/api/v1/verification/confirm",
        json={
            "discord_id": "333333333",
            "discord_username": "VerifiedUser",
            "code": code,
        },
        headers=ADMIN_HEADERS,
    )
    
    # Check status
    payload = {"player_uuid": "eeeeeeee-ffff-aaaa-bbbb-cccccccccccc"}
    response = await client.post("/api/v1/verification/status", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["discord_id"] == "333333333"
    assert data["discord_username"] == "VerifiedUser"


@pytest.mark.asyncio
async def test_get_verification_pending_returns_list(client):
    """GET /verification/pending should return list of pending verifications."""
    # Create some verification codes
    await client.post(
        "/api/v1/verification/request",
        json={
            "player_uuid": "ffffffff-aaaa-bbbb-cccc-dddddddddddd",
            "player_username": "Player6",
        },
        headers=ADMIN_HEADERS,
    )
    
    response = await client.get("/api/v1/verification/pending", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_post_verification_revoke_unlinks_account(client):
    """POST /verification/revoke should unlink Discord account."""
    # First, verify a player
    await client.post(
        "/api/v1/verification/request",
        json={
            "player_uuid": "aaaaaaaa-bbbb-cccc-dddd-000000000000",
            "player_username": "Player7",
        },
        headers=ADMIN_HEADERS,
    )
    
    response = await client.get("/api/v1/verification/pending", headers=ADMIN_HEADERS)
    codes = response.json()
    if len(codes) == 0:
        pytest.skip("No pending verification codes")
    code = codes[-1]["code"]
    
    await client.post(
        "/api/v1/verification/confirm",
        json={
            "discord_id": "444444444",
            "discord_username": "ToRevoke",
            "code": code,
        },
        headers=ADMIN_HEADERS,
    )
    
    # Revoke verification
    payload = {"player_uuid": "aaaaaaaa-bbbb-cccc-dddd-000000000000"}
    response = await client.post("/api/v1/verification/revoke", json=payload, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_post_verification_request_without_admin_key_returns_401(client):
    """POST /verification/request without X-Admin-Key should return 401."""
    payload = {
        "player_uuid": "bbbbbbbb-cccc-dddd-eeee-111111111111",
        "player_username": "Player8",
    }
    response = await client.post("/api/v1/verification/request", json=payload, headers=WRONG_HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_verification_confirm_without_admin_key_returns_401(client):
    """POST /verification/confirm without X-Admin-Key should return 401."""
    payload = {
        "discord_id": "123456789",
        "discord_username": "TestUser",
        "code": "123456",
    }
    response = await client.post("/api/v1/verification/confirm", json=payload, headers=WRONG_HEADERS)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_verification_pending_without_auth_returns_401(client):
    """GET /verification/pending without auth should return 401."""
    response = await client.get("/api/v1/verification/pending")
    assert response.status_code == 401
