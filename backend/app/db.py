from sqlalchemy import create_engine
from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.settings import get_settings


def create_session_factory():
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with create_session_factory()() as session:
        yield session
