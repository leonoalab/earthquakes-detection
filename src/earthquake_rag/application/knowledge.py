from pathlib import Path

from earthquake_rag.core.config import Settings
from earthquake_rag.domain.entities import KnowledgeHit
from earthquake_rag.infrastructure.vector_store import KnowledgeStore


def default_knowledge_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "knowledge"


def index_knowledge(settings: Settings) -> int:
    store = KnowledgeStore(settings.ai, settings.qdrant)
    try:
        return store.index_directory(default_knowledge_path())
    finally:
        store.close()


def search_knowledge(
    settings: Settings, question: str, limit: int = 4
) -> list[KnowledgeHit]:
    store = KnowledgeStore(settings.ai, settings.qdrant)
    try:
        return store.search(question, limit)
    finally:
        store.close()
