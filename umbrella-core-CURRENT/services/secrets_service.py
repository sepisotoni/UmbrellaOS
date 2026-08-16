"""
services/secrets_service.py — Symmetric encryption for secrets at rest,
closing the gap explicitly flagged (not silently ignored) in Phase 2's
ADR-0003 (`Node.signing_secret` "stored as-is... Phase 4's explicit scope")
and Phase 1's ADR-0002 on the daemon side.

Scope for this phase: `Node.signing_secret` specifically — the clearest,
unambiguous credential in the current schema. `Server.env_overrides` is
deliberately NOT blanket-encrypted here: it's a dict that can hold both
genuine secrets (an API key a plugin needs) and ordinary config (a
difficulty setting), and encrypting the whole blob would make even
non-secret values opaque for no benefit. A per-key "mark this env var as
secret" design is real follow-up work, not something to rush into this
phase's scope just to claim full coverage.
"""
from cryptography.fernet import Fernet, InvalidToken

from api.middleware.errors import AppException
from config import get_settings


class SecretsError(AppException):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, "SECRETS_ERROR", status_code)


def _fernet() -> Fernet:
    settings = get_settings()
    key = getattr(settings, "secrets_encryption_key", None)
    if not key:
        raise SecretsError(
            "SECRETS_ENCRYPTION_KEY is not configured — generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and set it before registering nodes or storing any other encrypted secret."
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise SecretsError(f"SECRETS_ENCRYPTION_KEY is not a valid Fernet key: {exc}") from exc


def encrypt_secret(plaintext: str) -> str:
    """Encrypt plaintext, returning a string safe to store in a normal
    text column. Fernet output is already URL-safe base64, so no further
    encoding is needed at the call site."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise SecretsError(
            "stored value could not be decrypted — wrong SECRETS_ENCRYPTION_KEY, "
            "or the value was never encrypted with this scheme", 500
        ) from exc
