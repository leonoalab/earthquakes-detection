from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from earthquake_rag.infrastructure.database import Base


class EventVersionModel(Base):
    __tablename__ = "earthquake_event_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    place: Mapped[str] = mapped_column(String, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    detail_url: Mapped[str | None] = mapped_column(String)
    tsunami: Mapped[bool] = mapped_column(Boolean, nullable=False)
    alert: Mapped[str | None] = mapped_column(String(16))
    felt_reports: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(32))
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)


Index(
    "uq_earthquake_event_source_version",
    EventVersionModel.event_id,
    EventVersionModel.source_updated_at,
    unique=True,
)
Index("ix_earthquake_occurred_at", EventVersionModel.occurred_at.desc())
Index("ix_earthquake_ingested_at", EventVersionModel.ingested_at.desc())


class IngestionRunModel(Base):
    __tablename__ = "earthquake_ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    feed_title: Mapped[str] = mapped_column(String, nullable=False)
    received_events: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted_versions: Mapped[int] = mapped_column(Integer, nullable=False)
