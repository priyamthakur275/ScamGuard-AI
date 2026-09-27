class MlServiceError(Exception):
    """Base class for all handled ML-service errors."""

    status_code = 400
    error_code = "ML_SERVICE_ERROR"

    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        super().__init__(message)


class InvalidRequestError(MlServiceError):
    status_code = 422
    error_code = "INVALID_REQUEST"


class ModelUnavailableError(MlServiceError):
    status_code = 503
    error_code = "MODEL_UNAVAILABLE"


class InferenceFailedError(MlServiceError):
    status_code = 500
    error_code = "INFERENCE_FAILED"
