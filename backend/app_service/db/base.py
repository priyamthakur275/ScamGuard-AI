from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# Ensure all ORM models are imported so metadata includes their tables.
# The models are stored in a separate module to avoid circular imports
# inside the package.
from app_service.db.postgres import models  # noqa: F401
