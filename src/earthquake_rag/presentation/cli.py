import argparse
import json
from dataclasses import asdict

from earthquake_rag.application.ingestion import synchronize_usgs_feed
from earthquake_rag.core.config import get_settings
from earthquake_rag.infrastructure.database import create_schema


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Explore real USGS earthquake data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Create the PostgreSQL tables")
    subparsers.add_parser("sync", help="Download and store the current USGS feed")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()

    if args.command == "init-db":
        create_schema()
        print("Database schema created.")
    elif args.command == "sync":
        summary = synchronize_usgs_feed(settings.feed.url)
        print(json.dumps(asdict(summary), indent=2, default=str))


if __name__ == "__main__":
    main()
