from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseModel):
    chat_model: str = "qwen3:8b"
    embedding_model: str = "embeddinggemma"
    ollama_base_url: str = "http://127.0.0.1:11434"


class QdrantSettings(BaseModel):
    url: str = "http://127.0.0.1:6333"
    collection: str = "earthquake_knowledge"
    score_threshold: float = 0.30


class FeedSettings(BaseModel):
    url: str = (
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/"
        "all_day.geojson"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    database_url: str = Field(
        default=(
            "postgresql+psycopg://earthquakes_detection:"
            "earthquakes_detection@localhost:5432/earthquakes_detection"
        ),
        validation_alias="DATABASE_URL",
    )
    checkpoint_database_path: Path = Path("data/checkpoints.db")
    memory_store_url: str = (
        "postgresql://earthquakes_detection:earthquakes_detection@localhost:5432/"
        "earthquakes_detection"
    )
    ai: AISettings = AISettings()
    qdrant: QdrantSettings = QdrantSettings()
    feed: FeedSettings = FeedSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
