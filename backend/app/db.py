from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.settings import get_settings


def create_session_factory():
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)
