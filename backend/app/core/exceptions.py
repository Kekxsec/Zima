# backend/app/core/exceptions.py


class ZimaBaseException(Exception):
    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ProviderException(ZimaBaseException):
    pass


class ProviderAuthException(ProviderException):
    pass


class ProviderRateLimitException(ProviderException):
    pass


class ProviderTimeoutException(ProviderException):
    pass


class ModuleException(ZimaBaseException):
    pass


class SignalValidationException(ZimaBaseException):
    pass


class TierPermissionException(ZimaBaseException):
    pass


class EntityNotFoundException(ZimaBaseException):
    pass


# Auth
class AuthTokenInvalidException(ZimaBaseException):
    pass


class AuthTokenExpiredException(ZimaBaseException):
    pass


class AuthTokenAlreadyUsedException(ZimaBaseException):
    pass


class AuthOTPRateLimitException(ZimaBaseException):
    pass


# GDPR
class UserDeletionException(ZimaBaseException):
    pass
