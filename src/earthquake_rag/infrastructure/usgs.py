import json
from datetime import UTC, datetime
from typing import Any

import httpx

from earthquake_rag.domain.entities import Earthquake


class UsgsClient:
    def __init__(self, feed_url: str) -> None:
        self.feed_url = feed_url

    def fetch(self) -> tuple[str, list[Earthquake]]:
        response = httpx.get(self.feed_url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        payload = response.json()

        if payload.get("type") != "FeatureCollection":
            raise ValueError("USGS did not return a valid GeoJSON feature collection")

        events = [self._to_earthquake(feature) for feature in payload["features"]]
        title = payload.get("metadata", {}).get("title", "USGS earthquake feed")
        return title, events

    @staticmethod
    def _to_earthquake(feature: dict[str, Any]) -> Earthquake:
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 3:
            raise ValueError("USGS event has no longitude, latitude and depth")

        occurred_ms = properties.get("time")
        updated_ms = properties.get("updated") or occurred_ms
        if not isinstance(occurred_ms, (int, float)):
            raise TypeError("USGS event has no valid 'time' value")
        if not isinstance(updated_ms, (int, float)):
            raise TypeError("USGS event has no valid 'updated' value")

        return Earthquake(
            event_id=str(feature["id"]),
            source_updated_at=datetime.fromtimestamp(updated_ms / 1000, tz=UTC),
            occurred_at=datetime.fromtimestamp(occurred_ms / 1000, tz=UTC),
            magnitude=float(properties.get("mag") or 0.0),
            place=properties.get("place") or "Unspecified location",
            longitude=float(coordinates[0]),
            latitude=float(coordinates[1]),
            depth_km=float(coordinates[2]),
            url=properties.get("url") or "https://earthquake.usgs.gov/",
            detail_url=properties.get("detail"),
            tsunami=bool(properties.get("tsunami", 0)),
            alert=properties.get("alert"),
            felt_reports=properties.get("felt"),
            status=properties.get("status"),
            raw_json=json.dumps(feature, ensure_ascii=False),
        )
