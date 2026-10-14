import json
from datetime import UTC, datetime
from typing import Any

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool

from earthquake_rag.application.temporal import get_event_history, get_latest_events
from earthquake_rag.domain.entities import AgentContext
from earthquake_rag.infrastructure.vector_store import KnowledgeStore


def serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def event_for_model(event: dict) -> dict:
    safe_event = dict(event)
    tsunami_flag = safe_event.pop("tsunami", False)
    pager_alert = safe_event.pop("alert", None)
    safe_event["tsunami_processing_flag"] = tsunami_flag
    safe_event["pager_alert"] = pager_alert
    safe_event["source_field_notes"] = {
        "tsunami_processing_flag": (
            f"The raw USGS value is {tsunami_flag}. It does not confirm that a "
            "tsunami occurred and is not an active warning."
        ),
        "pager_alert": (
            f"The raw USGS value is {pager_alert!r}. Do not translate it into "
            "'safe', 'no danger' or a damage prediction."
        ),
    }
    safe_event["answering_constraint"] = (
        "This summary record cannot support claims about expected damage, "
        "personal danger, shaking distance or whether a tsunami occurred."
    )
    return safe_event


def build_earthquake_tools(knowledge: KnowledgeStore) -> list[BaseTool]:
    @tool
    def search_earthquake_knowledge(question: str, limit: int = 4) -> str:
        """Search educational seismology documents.

        Use this for concepts such as magnitude, intensity, aftershocks,
        seismic waves, depth, tsunami indicators, hazard and uncertainty.
        It does not return current earthquake events.
        """
        return serialize(
            [
                {
                    "title": hit.title,
                    "source": hit.source,
                    "score": round(hit.score, 4),
                    "text": hit.text,
                }
                for hit in knowledge.search(question, limit)
            ]
        )

    @tool
    def list_recent_earthquakes(
        runtime: ToolRuntime[AgentContext],
        hours: int | None = None,
        limit: int = 10,
        as_of: str | None = None,
    ) -> str:
        """List real earthquake events stored from the USGS feed.

        Use this for questions about locations, magnitudes, depth, event
        links, tsunami flags, alerts, felt reports or review status.
        """
        selected_hours = hours or runtime.context.default_hours
        selected_as_of = as_of or runtime.context.as_of
        events = get_latest_events(
            hours=max(1, min(selected_hours, 24 * 30)),
            limit=max(1, min(limit, 100)),
            as_of=parse_datetime(selected_as_of),
        )
        return serialize([event_for_model(event) for event in events])

    @tool
    def calculate_earthquake_statistics(
        runtime: ToolRuntime[AgentContext],
        hours: int | None = None,
        as_of: str | None = None,
    ) -> str:
        """Calculate exact statistics for stored USGS earthquakes.

        Returns event count, minimum, maximum and average magnitude, plus
        the strongest event. Use this instead of asking the model to count.
        """
        selected_hours = hours or runtime.context.default_hours
        selected_as_of = as_of or runtime.context.as_of
        events = get_latest_events(
            hours=max(1, min(selected_hours, 24 * 30)),
            limit=10_000,
            as_of=parse_datetime(selected_as_of),
        )
        if not events:
            return serialize({"hours": selected_hours, "event_count": 0})

        magnitudes = [float(event["magnitude"]) for event in events]
        return serialize(
            {
                "hours": selected_hours,
                "as_of": selected_as_of,
                "event_count": len(events),
                "minimum_magnitude": min(magnitudes),
                "maximum_magnitude": max(magnitudes),
                "average_magnitude": round(sum(magnitudes) / len(magnitudes), 2),
                "strongest_event": event_for_model(
                    max(events, key=lambda event: float(event["magnitude"]))
                ),
            }
        )

    @tool
    def get_earthquake_history(event_id: str) -> str:
        """Return every version stored for one USGS earthquake event."""
        return serialize(get_event_history(event_id))

    return [
        search_earthquake_knowledge,
        list_recent_earthquakes,
        calculate_earthquake_statistics,
        get_earthquake_history,
    ]
