class AppException(Exception):
    """Base class for all handled application errors."""

    status_code = 400
    error_code = "APP_ERROR"

    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        super().__init__(message)


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"


class UnauthorizedError(AppException):
    status_code = 401
    error_code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    status_code = 403
    error_code = "FORBIDDEN"


class ValidationAppError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class CaptchaRequiredError(AppException):
    status_code = 403
    error_code = "CAPTCHA_REQUIRED"


class InvalidCaptchaError(AppException):
    status_code = 400
    error_code = "INVALID_CAPTCHA"
