"""
SQLAlchemy engine + session. Swapping DATABASE_URL to a Postgres URL is the
only change needed to move off SQLite — nothing in app/models.py or the
routers is SQLite-specific.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401  (register models on Base before create_all)
    Base.metadata.create_all(bind=engine)
