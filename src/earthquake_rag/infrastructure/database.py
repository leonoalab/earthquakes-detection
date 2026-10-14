from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from earthquake_rag.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def create_schema() -> None:
    from earthquake_rag.infrastructure import models  # noqa: F401

    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
