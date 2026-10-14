from datetime import datetime

from earthquake_rag.infrastructure.database import session_scope
from earthquake_rag.infrastructure.repositories import EarthquakeRepository


def get_latest_events(
    *, hours: int = 24, limit: int = 100, as_of: datetime | None = None
) -> list[dict]:
    with session_scope() as session:
        return EarthquakeRepository(session).latest_events(
            hours=hours,
            limit=limit,
            as_of=as_of,
        )


def get_event_history(event_id: str) -> list[dict]:
    with session_scope() as session:
        return EarthquakeRepository(session).event_history(event_id)


def get_latest_ingestions(limit: int = 20) -> list[dict]:
    with session_scope() as session:
        return EarthquakeRepository(session).latest_ingestions(limit)
