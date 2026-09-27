from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class DetailResponse(BaseModel):
    detail: str
