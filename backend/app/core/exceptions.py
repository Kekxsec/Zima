# backend/app/core/exceptions.py


class ZimaBaseError(Exception):
    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ProviderError(ZimaBaseError):
    pass


class ProviderAuthError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ModuleError(ZimaBaseError):
    pass


class SignalValidationError(ZimaBaseError):
    pass


class TierPermissionError(ZimaBaseError):
    pass


class EntityNotFoundError(ZimaBaseError):
    pass


# Auth
class AuthTokenInvalidError(ZimaBaseError):
    pass


class AuthTokenExpiredError(ZimaBaseError):
    pass


class AuthTokenAlreadyUsedError(ZimaBaseError):
    pass


class AuthOTPRateLimitError(ZimaBaseError):
    pass


# GDPR
class UserDeletionError(ZimaBaseError):
    pass
