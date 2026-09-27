import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app_service.db.postgres.models import UserRole


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    captcha_token: str
    captcha_answer: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        return value


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    full_name: str | None = None
    avatar_url: str | None = None
    preferences: dict | None = None
    last_login_at: datetime | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    preferences: dict | None = None

class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        return value

class UserUpdateRole(BaseModel):
    role: UserRole
