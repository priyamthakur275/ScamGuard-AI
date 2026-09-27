from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ml_service.core.exceptions import MlServiceError
from ml_service.core.logging_config import get_logger

logger = get_logger("ml_service.errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MlServiceError)
    async def handle_ml_service_error(request: Request, exc: MlServiceError) -> JSONResponse:
        logger.warning(f"MlServiceError: {exc.error_code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        safe_details = jsonable_encoder(exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": safe_details,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception in ML service")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error_code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"},
        )
