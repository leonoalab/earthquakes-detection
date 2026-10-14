import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime

from earthquake_rag.application.ingestion import synchronize_usgs_feed
from earthquake_rag.application.knowledge import index_knowledge, search_knowledge
from earthquake_rag.application.temporal import (
    get_event_history,
    get_latest_events,
    get_latest_ingestions,
)
from earthquake_rag.core.config import get_settings
from earthquake_rag.infrastructure.database import create_schema


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Explore real USGS earthquake data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Create the PostgreSQL tables")
    subparsers.add_parser("sync", help="Download and store the current USGS feed")
    events = subparsers.add_parser("events", help="List the latest event versions")
    events.add_argument("--hours", type=int, default=24)
    events.add_argument("--limit", type=int, default=20)
    events.add_argument("--as-of", help="ISO-8601 knowledge cutoff")
    history = subparsers.add_parser("history", help="Show every version of an event")
    history.add_argument("event_id")
    subparsers.add_parser("ingestions", help="List ingestion snapshots")
    subparsers.add_parser("index", help="Index the educational knowledge base")
    search = subparsers.add_parser("search", help="Run semantic retrieval")
    search.add_argument("question")
    search.add_argument("--limit", type=int, default=4)
    return parser


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()

    if args.command == "init-db":
        create_schema()
        print("Database schema created.")
    elif args.command == "sync":
        summary = synchronize_usgs_feed(settings.feed.url)
        print(json.dumps(asdict(summary), indent=2, default=str))
    elif args.command == "events":
        events = get_latest_events(
            hours=max(1, args.hours),
            limit=max(1, args.limit),
            as_of=parse_datetime(args.as_of),
        )
        print(json.dumps(events, indent=2))
    elif args.command == "history":
        print(json.dumps(get_event_history(args.event_id), indent=2))
    elif args.command == "ingestions":
        print(json.dumps(get_latest_ingestions(), indent=2))
    elif args.command == "index":
        count = index_knowledge(settings)
        print(f"Indexed {count} knowledge chunks.")
    elif args.command == "search":
        hits = search_knowledge(settings, args.question, args.limit)
        print(json.dumps([asdict(hit) for hit in hits], indent=2))


if __name__ == "__main__":
    main()
