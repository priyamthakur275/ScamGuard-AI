from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app_service.core.config import get_settings

settings = get_settings()

database_url = settings.get_sqlalchemy_database_url
connect_args = {}
if make_url(database_url).drivername.startswith("postgresql"):
    connect_args = {"connect_timeout": 5}
elif make_url(database_url).drivername.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine_kwargs: dict = {
    "pool_pre_ping": True,
    "future": True,
    "connect_args": connect_args,
}

if make_url(database_url).drivername.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
    })

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
