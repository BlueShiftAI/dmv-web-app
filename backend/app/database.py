"""
SQLAlchemy engine, session factory, and base class.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=(settings.app_env == "development"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a database session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
