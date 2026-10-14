from dataclasses import asdict
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from earthquake_rag.domain.entities import Earthquake, IngestionSummary
from earthquake_rag.infrastructure.models import EventVersionModel, IngestionRunModel


class EarthquakeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_versions(
        self, events: list[Earthquake], *, ingested_at: datetime
    ) -> int:
        inserted = 0
        for event in events:
            values = asdict(event)
            values["ingested_at"] = ingested_at
            statement = (
                insert(EventVersionModel)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["event_id", "source_updated_at"]
                )
                .returning(EventVersionModel.id)
            )
            result = self.session.execute(statement)
            inserted += int(result.scalar_one_or_none() is not None)
        return inserted

    def record_ingestion(self, summary: IngestionSummary, source_url: str) -> None:
        self.session.add(
            IngestionRunModel(
                fetched_at=summary.fetched_at,
                source_url=source_url,
                feed_title=summary.feed_title,
                received_events=summary.received_events,
                inserted_versions=summary.inserted_versions,
            )
        )
