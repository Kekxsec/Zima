# backend/app/auth/service.py
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.models import Asset
from backend.app.auth.models import AuthToken, User
from backend.app.core.exceptions import AuthTokenInvalidException
from backend.app.core.logging import get_logger
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.users import UserRepository

logger = get_logger(__name__)

OTP_EXPIRY_MINUTES: int = 15
MAX_ACTIVE_TOKENS_PER_EMAIL: int = 3


def _generate_code() -> str:
    """
    Cryptographically secure 6-digit numeric OTP.
    Range: 100000–999999 inclusive.
    Uses secrets.randbelow which is CSPRNG-backed.
    """
    return str(secrets.randbelow(900000) + 100000)


def _hash_code(code: str) -> str:
    """SHA-256 hash of the raw OTP code. Only the hash is stored."""
    return hashlib.sha256(code.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        token_repo: AuthTokenRepository,
    ) -> None:
        self.session = session
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def request_otp(
        self,
        email: str,
        requesting_ip: str,
        privacy_policy_accepted: bool = False,
    ) -> str | None:
        """
        Generates and stores an OTP for the given email.

        Returns the raw 6-digit code string if successful.
        Returns None silently if rate limit is hit.
        The caller ALWAYS returns the same HTTP response regardless of return value
        to prevent account enumeration.

        Creates a new User row on first ever sign-in for this email.
        """
        email = email.lower().strip()

        active_count = await self.token_repo.count_active_for_email(email)
        if active_count >= MAX_ACTIVE_TOKENS_PER_EMAIL:
            logger.warning("auth.otp_rate_limit", ip=requesting_ip)
            return None

        # Find existing user via their primary email asset
        user = await self.user_repo.get_by_email(email)
        if not user:
            # First sign-in — create user row and a placeholder email asset.
            # The asset is unverified here; AssetService.register_verified_email()
            # marks it verified after OTP confirmation. The asset must exist now
            # so verify_otp can look up the user by email via the Asset join.
            user = User(
                privacy_policy_accepted_at=(
                    datetime.now(UTC) if privacy_policy_accepted else None
                )
            )
            self.session.add(user)
            await self.session.flush()  # Assigns user.id without committing
            asset = Asset(
                user_id=user.id,
                entity_type="email",
                value=email,
                is_primary=True,
                is_verified=False,
            )
            self.session.add(asset)
            logger.info("auth.new_user_created", user_id=str(user.id))

        raw_code = _generate_code()
        token = AuthToken(
            email=email,
            code_hash=_hash_code(raw_code),
            expires_at=datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES),
            requested_from_ip=requesting_ip,
        )
        self.session.add(token)
        await self.session.commit()

        logger.info("auth.otp_issued", email_domain=email.split("@")[-1])
        return raw_code

    async def verify_otp(self, email: str, code: str) -> tuple[User, str]:
        """
        Verifies a submitted OTP code.

        On success:
        - Marks the token as used (prevents replay)
        - Updates user.last_sign_in_at
        - Returns (user, jwt_access_token)

        Raises AuthTokenInvalidException for ALL failure modes (wrong code,
        expired, already used, user not found). This ensures identical
        error responses regardless of failure reason.

        Does NOT register the email as a verified asset — the API endpoint
        does that after this method returns successfully.
        """
        email = email.lower().strip()
        token = await self.token_repo.get_valid_token(email, _hash_code(code))

        # Identical exception for all failure modes — no information leakage
        if not token or token.is_expired or token.is_used:
            logger.warning("auth.otp_verify_failed", email_domain=email.split("@")[-1])
            raise AuthTokenInvalidException("Invalid or expired code.")

        # Consume token before any other operation — prevents concurrent replay
        token.used_at = datetime.now(UTC)
        await self.session.flush()

        user = await self.user_repo.get_by_email(email)
        if not user or user.is_deleted:
            raise AuthTokenInvalidException("Invalid or expired code.")

        user.last_sign_in_at = datetime.now(UTC)
        await self.session.commit()

        from backend.app.auth.utils import create_access_token

        jwt_token = create_access_token(
            subject=str(user.id),
            tier=user.tier,
        )

        logger.info("auth.sign_in_success", user_id=str(user.id))
        return user, jwt_token
