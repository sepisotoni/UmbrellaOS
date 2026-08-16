import pytest
from cryptography.fernet import Fernet

from services.secrets_service import SecretsError, decrypt_secret, encrypt_secret


@pytest.mark.asyncio
async def test_encrypt_then_decrypt_round_trip():
    plaintext = "a-very-secret-value-12345"
    ciphertext = encrypt_secret(plaintext)
    assert ciphertext != plaintext
    assert decrypt_secret(ciphertext) == plaintext


@pytest.mark.asyncio
async def test_encrypting_the_same_value_twice_produces_different_ciphertext():
    # Fernet includes a random IV per encryption — this is expected and
    # good (no ciphertext pattern leakage across repeated identical
    # secrets), not a bug to "fix" toward deterministic output.
    a = encrypt_secret("same-value")
    b = encrypt_secret("same-value")
    assert a != b
    assert decrypt_secret(a) == decrypt_secret(b) == "same-value"


@pytest.mark.asyncio
async def test_decrypt_fails_with_wrong_key(monkeypatch):
    from config import get_settings

    settings = get_settings()
    original_key = settings.secrets_encryption_key

    ciphertext = encrypt_secret("secret-value")

    monkeypatch.setattr(settings, "secrets_encryption_key", Fernet.generate_key().decode())
    with pytest.raises(SecretsError):
        decrypt_secret(ciphertext)

    monkeypatch.setattr(settings, "secrets_encryption_key", original_key)


@pytest.mark.asyncio
async def test_missing_key_raises_clear_error(monkeypatch):
    from config import get_settings

    settings = get_settings()
    original_key = settings.secrets_encryption_key
    monkeypatch.setattr(settings, "secrets_encryption_key", None)

    with pytest.raises(SecretsError, match="not configured"):
        encrypt_secret("x")

    monkeypatch.setattr(settings, "secrets_encryption_key", original_key)


@pytest.mark.asyncio
async def test_malformed_key_raises_clear_error(monkeypatch):
    from config import get_settings

    settings = get_settings()
    original_key = settings.secrets_encryption_key
    monkeypatch.setattr(settings, "secrets_encryption_key", "not-a-valid-fernet-key")

    with pytest.raises(SecretsError, match="not a valid Fernet key"):
        encrypt_secret("x")

    monkeypatch.setattr(settings, "secrets_encryption_key", original_key)


@pytest.mark.asyncio
async def test_decrypt_rejects_garbage_ciphertext():
    with pytest.raises(SecretsError):
        decrypt_secret("this-is-not-a-real-fernet-token")
