"""
services/mfa_service.py — TOTP-based multi-factor authentication.

Enrollment is a two-step commit, not a single call: `begin_enrollment`
generates and stores a secret but does NOT set `mfa_enabled` — a user must
prove they actually copied the secret into an authenticator app by
submitting one valid code (`confirm_enrollment`) before MFA is considered
active. This avoids a user locking themselves out by "enabling" MFA against
a secret their authenticator app never actually received.
"""
import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.errors import AppException
from models.user import User


class MFAError(AppException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, "MFA_ERROR", status_code)


ISSUER_NAME = "UmbrellaOS"


class MFAService:
    @staticmethod
    async def begin_enrollment(db: AsyncSession, user: User) -> tuple[str, str]:
        """
        Generate and store a new TOTP secret for `user`, without enabling
        MFA yet. Returns (secret, provisioning_uri) — the URI is what a
        dashboard renders as a QR code for the user's authenticator app.
        Overwrites any prior not-yet-confirmed secret if called again
        (e.g. the user's QR code render failed and they retried).
        """
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.mfa_enabled = False
        await db.flush()

        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.username, issuer_name=ISSUER_NAME)
        return secret, uri

    @staticmethod
    async def confirm_enrollment(db: AsyncSession, user: User, code: str) -> None:
        if not user.mfa_secret:
            raise MFAError("no MFA enrollment in progress for this user")
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code, valid_window=1):
            raise MFAError("incorrect verification code", 401)
        user.mfa_enabled = True
        await db.flush()

    @staticmethod
    async def verify_code(user: User, code: str) -> bool:
        """
        Verify a code against an already-enabled MFA setup — used at login,
        not during enrollment. `valid_window=1` tolerates one 30-second step
        of clock drift on either side, matching the standard TOTP practice
        (RFC 6238's own recommendation), not an UmbrellaOS-specific
        loosening of the check.
        """
        if not user.mfa_enabled or not user.mfa_secret:
            return False
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    async def disable(db: AsyncSession, user: User) -> None:
        user.mfa_enabled = False
        user.mfa_secret = None
        await db.flush()
