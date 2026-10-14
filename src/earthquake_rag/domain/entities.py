from dataclasses import dataclass
from datetime import datetime
from typing import Any


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


@dataclass(frozen=True)
class KnowledgeHit:
    text: str
    title: str
    source: str
    score: float


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    hits: list[KnowledgeHit]


@dataclass
class ToolEvidence:
    name: str
    arguments: dict[str, Any]
    output: str = ""


@dataclass
class AgentRun:
    answer: str
    tools: list[ToolEvidence]
    message_count: int


@dataclass(frozen=True)
class AgentContext:
    user_id: str
    user_name: str = "Student"
    expertise: str = "intermediate"
    default_hours: int = 24
    as_of: str | None = None
