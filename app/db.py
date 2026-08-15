from sqlmodel import create_engine

from app.config import settings

engine = create_engine(settings.sqlalchemy_url, echo=False, pool_pre_ping=True)
