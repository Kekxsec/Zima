# backend/app/auth/service.py
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.models import Asset
from backend.app.auth.models import AuthToken, User
from backend.app.auth.utils import create_access_token
from backend.app.core.exceptions import AuthTokenInvalidException
from backend.app.core.logging import get_logger
from backend.app.db.models.audit import AuditEventType
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.users import UserRepository

logger = get_logger(__name__)

OTP_EXPIRY_MINUTES: int = 15
MAX_ACTIVE_TOKENS_PER_EMAIL: int = 3
OTP_MAX_FAILURES: int = 5  # Lock account after this many consecutive bad codes
OTP_LOCKOUT_MINUTES: int = 15  # Duration of the lockout window


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
        audit_repo: AuditRepository,
    ) -> None:
        self.session = session
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.audit_repo = audit_repo

    @staticmethod
    def _is_otp_locked(user: User | None, *, asset_flow: bool = False) -> bool:
        if user is None:
            return False
        locked_until = (
            user.asset_otp_locked_until if asset_flow else user.otp_locked_until
        )
        return locked_until is not None and locked_until > datetime.now(UTC)

    @staticmethod
    def _record_otp_failure(user: User, *, asset_flow: bool = False) -> bool:
        if asset_flow:
            user.asset_otp_fail_count = (user.asset_otp_fail_count or 0) + 1
            if user.asset_otp_fail_count >= OTP_MAX_FAILURES:
                user.asset_otp_locked_until = datetime.now(UTC) + timedelta(
                    minutes=OTP_LOCKOUT_MINUTES
                )
                return True
            return False

        user.otp_fail_count = (user.otp_fail_count or 0) + 1
        if user.otp_fail_count >= OTP_MAX_FAILURES:
            user.otp_locked_until = datetime.now(UTC) + timedelta(
                minutes=OTP_LOCKOUT_MINUTES
            )
            return True
        return False

    @staticmethod
    def _reset_otp_failures(user: User, *, asset_flow: bool = False) -> None:
        if asset_flow:
            user.asset_otp_fail_count = 0
            user.asset_otp_locked_until = None
            return
        user.otp_fail_count = 0
        user.otp_locked_until = None

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
            logger.warning("security.otp_rate_limit", ip=requesting_ip)
            await self.audit_repo.log(
                event_type=AuditEventType.OTP_RATE_LIMITED,
                ip_address=requesting_ip,
                metadata={"email_domain": email.split("@")[-1]},
            )
            await self.session.commit()
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
        await self.token_repo.create(token)
        await self.audit_repo.log(
            event_type=AuditEventType.SIGN_IN_REQUESTED,
            user_id=user.id,
            ip_address=requesting_ip,
            metadata={"email_domain": email.split("@")[-1]},
        )
        await self.session.commit()

        logger.info("auth.otp_issued", email_domain=email.split("@")[-1])
        return raw_code

    async def verify_otp(self, email: str, code: str) -> tuple[User, str]:
        """
        Verifies a submitted OTP code.

        On success:
        - Marks the token as used (prevents replay)
        - Resets the OTP failure counter
        - Updates user.last_sign_in_at
        - Returns (user, jwt_access_token)

        Raises AuthTokenInvalidException for ALL failure modes (wrong code,
        expired, already used, user not found, account locked). This ensures
        identical error responses regardless of failure reason.

        Does NOT register the email as a verified asset — the API endpoint
        does that after this method returns successfully.
        """
        email = email.lower().strip()
        email_domain = email.split("@")[-1]

        # Look up the user first — needed for lockout check and fail counter.
        # User is always present by this point: request_otp creates them if new.
        user = await self.user_repo.get_by_email(email)

        # Lockout check — block immediately without revealing the token state.
        if self._is_otp_locked(user):
            logger.warning("security.otp_verify_locked", email_domain=email_domain)
            await self.audit_repo.log(
                event_type=AuditEventType.SIGN_IN_FAILED,
                metadata={"email_domain": email_domain, "reason": "locked"},
            )
            await self.session.commit()
            raise AuthTokenInvalidException("Invalid or expired code.")

        # get_valid_token filters: used_at IS NULL, expires_at > now, hash match.
        token = await self.token_repo.get_valid_token(email, _hash_code(code))

        if not token:
            logger.warning("security.otp_verify_failed", email_domain=email_domain)
            # Increment failure counter. On reaching OTP_MAX_FAILURES, lock the
            # account for OTP_LOCKOUT_MINUTES to slow distributed brute-force.
            if user:
                locked = self._record_otp_failure(user)
                if locked:
                    logger.warning(
                        "security.otp_account_locked",
                        email_domain=email_domain,
                        fail_count=user.otp_fail_count,
                    )
            await self.audit_repo.log(
                event_type=AuditEventType.SIGN_IN_FAILED,
                metadata={"email_domain": email_domain},
            )
            await self.session.commit()
            raise AuthTokenInvalidException("Invalid or expired code.")

        # Consume token before any other operation — prevents concurrent replay.
        # Commit immediately so the token is marked used in the DB before we
        # proceed. If an exception occurs after this point the token cannot be
        # replayed because the commit is durable.
        token.used_at = datetime.now(UTC)
        await self.session.commit()

        # Defensive re-check: user should always exist at this point, but guard
        # against the race where a user is deleted between request and verify.
        if not user:
            user = await self.user_repo.get_by_email(email)
        if not user or user.is_deleted:
            await self.audit_repo.log(
                event_type=AuditEventType.SIGN_IN_FAILED,
                metadata={"email_domain": email_domain, "reason": "user_not_found"},
            )
            await self.session.commit()
            raise AuthTokenInvalidException("Invalid or expired code.")

        # Successful verification — reset brute-force counters.
        self._reset_otp_failures(user)
        user.last_sign_in_at = datetime.now(UTC)
        # Record consent timestamp on first successful sign-in if not already set.
        # request_otp sets this when privacy_policy_accepted=True is passed; this
        # is the fallback for users who completed the OTP flow without passing the
        # flag (e.g. legacy sessions or direct API callers).
        if user.privacy_policy_accepted_at is None:
            user.privacy_policy_accepted_at = datetime.now(UTC)
        await self.audit_repo.log(
            event_type=AuditEventType.SIGN_IN_SUCCESS,
            user_id=user.id,
            metadata={"email_domain": email_domain},
        )
        await self.session.commit()

        jwt_token = create_access_token(
            subject=str(user.id),
            tier=user.tier,
        )

        logger.info("security.sign_in_success", user_id=str(user.id))
        return user, jwt_token

    async def request_asset_email_otp(
        self,
        email: str,
        requesting_ip: str,
        user: User,
    ) -> str | None:
        """
        Generates an OTP for verifying an additional email asset.

        Unlike request_otp, this does NOT create or look up a user — it only
        stores a token keyed by email. The authenticated user is identified by
        the session cookie, not by this email.

        Returns the raw code on success, or None if rate limited.
        """
        email = email.lower().strip()
        if self._is_otp_locked(user, asset_flow=True):
            logger.warning(
                "security.asset_otp_request_locked",
                user_id=str(user.id),
                email_domain=email.split("@")[-1],
            )
            return None
        active_count = await self.token_repo.count_active_for_email(email)
        if active_count >= MAX_ACTIVE_TOKENS_PER_EMAIL:
            logger.warning("security.asset_otp_rate_limit", ip=requesting_ip)
            return None
        raw_code = _generate_code()
        token = AuthToken(
            email=email,
            code_hash=_hash_code(raw_code),
            expires_at=datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES),
            requested_from_ip=requesting_ip,
        )
        await self.token_repo.create(token)
        await self.session.commit()
        logger.info("auth.asset_otp_issued", email_domain=email.split("@")[-1])
        return raw_code

    async def verify_asset_email_otp(self, email: str, code: str, user: User) -> bool:
        """
        Verifies an OTP for an additional email asset.

        Returns True on success (token consumed), False on any failure.
        Does not create a session — the caller registers the asset.
        """
        email = email.lower().strip()
        if self._is_otp_locked(user, asset_flow=True):
            logger.warning(
                "security.asset_otp_verify_locked",
                user_id=str(user.id),
                email_domain=email.split("@")[-1],
            )
            return False
        token = await self.token_repo.get_valid_token(email, _hash_code(code))
        if not token:
            locked = self._record_otp_failure(user, asset_flow=True)
            logger.warning(
                "security.asset_otp_verify_failed",
                email_domain=email.split("@")[-1],
                user_id=str(user.id),
                locked=locked,
            )
            await self.session.commit()
            return False
        token.used_at = datetime.now(UTC)
        self._reset_otp_failures(user, asset_flow=True)
        await self.session.commit()
        logger.info("auth.asset_otp_verified", email_domain=email.split("@")[-1])
        return True

    async def request_asset_phone_otp(
        self,
        phone: str,
        requesting_ip: str,
        user: User,
    ) -> str | None:
        """
        Generates an OTP for verifying a phone number asset.

        Reuses the auth_tokens table with the phone number as the key.
        In production this code would be delivered via SMS; for now the
        caller is responsible for delivering it (console-print in dev).

        Returns the raw code on success, or None if rate limited.
        """
        phone = phone.strip()
        if self._is_otp_locked(user, asset_flow=True):
            logger.warning("security.phone_otp_request_locked", user_id=str(user.id))
            return None
        active_count = await self.token_repo.count_active_for_email(phone)
        if active_count >= MAX_ACTIVE_TOKENS_PER_EMAIL:
            logger.warning("security.phone_otp_rate_limit", ip=requesting_ip)
            return None
        raw_code = _generate_code()
        token = AuthToken(
            email=phone,
            code_hash=_hash_code(raw_code),
            expires_at=datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES),
            requested_from_ip=requesting_ip,
        )
        await self.token_repo.create(token)
        await self.session.commit()
        logger.info("auth.phone_otp_issued")
        return raw_code

    async def verify_asset_phone_otp(self, phone: str, code: str, user: User) -> bool:
        """
        Verifies an OTP for a phone number asset.

        Returns True on success (token consumed), False on any failure.
        Does not create a session — the caller registers the asset.
        """
        phone = phone.strip()
        if self._is_otp_locked(user, asset_flow=True):
            logger.warning("security.phone_otp_verify_locked", user_id=str(user.id))
            return False
        token = await self.token_repo.get_valid_token(phone, _hash_code(code))
        if not token:
            locked = self._record_otp_failure(user, asset_flow=True)
            logger.warning(
                "security.phone_otp_verify_failed",
                user_id=str(user.id),
                locked=locked,
            )
            await self.session.commit()
            return False
        token.used_at = datetime.now(UTC)
        self._reset_otp_failures(user, asset_flow=True)
        await self.session.commit()
        logger.info("auth.phone_otp_verified")
        return True

    async def request_asset_domain_otp(
        self,
        domain: str,
        requesting_ip: str,
        user: User,
    ) -> str | None:
        """
        Generates an OTP for verifying a domain asset via admin@<domain>.

        Stores the token keyed by the admin address so that verify_asset_domain_otp
        can look it up. Returns the raw code on success, None if rate-limited.
        """
        admin_email = f"admin@{domain}"
        if self._is_otp_locked(user, asset_flow=True):
            logger.warning("security.domain_otp_request_locked", user_id=str(user.id))
            return None
        active_count = await self.token_repo.count_active_for_email(admin_email)
        if active_count >= MAX_ACTIVE_TOKENS_PER_EMAIL:
            logger.warning("security.domain_otp_rate_limit", ip=requesting_ip)
            return None
        raw_code = _generate_code()
        token = AuthToken(
            email=admin_email,
            code_hash=_hash_code(raw_code),
            expires_at=datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES),
            requested_from_ip=requesting_ip,
        )
        await self.token_repo.create(token)
        await self.session.commit()
        logger.info("auth.domain_otp_issued", domain=domain)
        return raw_code

    async def verify_asset_domain_otp(self, domain: str, code: str, user: User) -> bool:
        """
        Verifies an OTP for a domain asset.

        Returns True on success (token consumed), False on any failure.
        Does not create a session — the caller registers the asset.
        """
        admin_email = f"admin@{domain}"
        if self._is_otp_locked(user, asset_flow=True):
            logger.warning("security.domain_otp_verify_locked", user_id=str(user.id))
            return False
        token = await self.token_repo.get_valid_token(admin_email, _hash_code(code))
        if not token:
            locked = self._record_otp_failure(user, asset_flow=True)
            logger.warning(
                "security.domain_otp_verify_failed",
                user_id=str(user.id),
                locked=locked,
            )
            await self.session.commit()
            return False
        token.used_at = datetime.now(UTC)
        self._reset_otp_failures(user, asset_flow=True)
        await self.session.commit()
        logger.info("auth.domain_otp_verified", domain=domain)
        return True
