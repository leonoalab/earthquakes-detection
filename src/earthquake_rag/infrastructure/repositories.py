from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

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

    def latest_events(
        self,
        *,
        hours: int = 24,
        limit: int = 100,
        as_of: datetime | None = None,
    ) -> list[dict]:
        reference = as_of or datetime.now(UTC)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        cutoff = reference - timedelta(hours=hours)

        ranked = (
            select(
                EventVersionModel,
                func.row_number()
                .over(
                    partition_by=EventVersionModel.event_id,
                    order_by=(
                        EventVersionModel.ingested_at.desc(),
                        EventVersionModel.id.desc(),
                    ),
                )
                .label("version_rank"),
            )
            .where(
                EventVersionModel.ingested_at <= reference,
                EventVersionModel.occurred_at.between(cutoff, reference),
            )
            .subquery()
        )
        latest = aliased(EventVersionModel, ranked)
        statement = (
            select(latest)
            .where(ranked.c.version_rank == 1)
            .order_by(latest.magnitude.desc(), latest.occurred_at.desc())
            .limit(limit)
        )
        events = self.session.scalars(statement).all()
        return [self._event_to_dict(event) for event in events]

    def event_history(self, event_id: str) -> list[dict]:
        statement = (
            select(EventVersionModel)
            .where(EventVersionModel.event_id == event_id)
            .order_by(EventVersionModel.ingested_at, EventVersionModel.id)
        )
        events = self.session.scalars(statement).all()
        return [self._event_to_dict(event) for event in events]

    def latest_ingestions(self, limit: int = 20) -> list[dict]:
        statement = (
            select(IngestionRunModel)
            .order_by(IngestionRunModel.fetched_at.desc())
            .limit(limit)
        )
        runs = self.session.scalars(statement).all()
        return [
            {
                "id": run.id,
                "fetched_at": run.fetched_at.isoformat(),
                "feed_title": run.feed_title,
                "received_events": run.received_events,
                "inserted_versions": run.inserted_versions,
            }
            for run in runs
        ]

    @staticmethod
    def _event_to_dict(event: EventVersionModel) -> dict:
        return {
            "event_id": event.event_id,
            "source_updated_at": event.source_updated_at.isoformat(),
            "ingested_at": event.ingested_at.isoformat(),
            "occurred_at": event.occurred_at.isoformat(),
            "magnitude": event.magnitude,
            "place": event.place,
            "longitude": event.longitude,
            "latitude": event.latitude,
            "depth_km": event.depth_km,
            "url": event.url,
            "tsunami": event.tsunami,
            "alert": event.alert,
            "felt_reports": event.felt_reports,
            "status": event.status,
        }
