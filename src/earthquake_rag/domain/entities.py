from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Earthquake:
    event_id: str
    source_updated_at: datetime
    occurred_at: datetime
    magnitude: float
    place: str
    longitude: float
    latitude: float
    depth_km: float
    url: str
    detail_url: str | None
    tsunami: bool
    alert: str | None
    felt_reports: int | None
    status: str | None
    raw_json: str


@dataclass(frozen=True)
class IngestionSummary:
    fetched_at: datetime
    feed_title: str
    received_events: int
    inserted_versions: int
