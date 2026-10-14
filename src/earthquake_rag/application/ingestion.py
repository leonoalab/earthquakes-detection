from datetime import UTC, datetime

from earthquake_rag.domain.entities import IngestionSummary
from earthquake_rag.infrastructure.database import session_scope
from earthquake_rag.infrastructure.repositories import EarthquakeRepository
from earthquake_rag.infrastructure.usgs import UsgsClient


def synchronize_usgs_feed(feed_url: str) -> IngestionSummary:
    feed_title, events = UsgsClient(feed_url).fetch()
    fetched_at = datetime.now(UTC)

    with session_scope() as session:
        repository = EarthquakeRepository(session)
        inserted = repository.insert_versions(events, ingested_at=fetched_at)
        summary = IngestionSummary(
            fetched_at=fetched_at,
            feed_title=feed_title,
            received_events=len(events),
            inserted_versions=inserted,
        )
        repository.record_ingestion(summary, feed_url)

    return summary
