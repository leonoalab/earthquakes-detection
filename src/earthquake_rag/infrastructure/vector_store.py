from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from earthquake_rag.core.config import AISettings, QdrantSettings
from earthquake_rag.domain.entities import KnowledgeHit


class KnowledgeStore:
    def __init__(self, ai: AISettings, qdrant: QdrantSettings) -> None:
        self.collection = qdrant.collection
        self.score_threshold = qdrant.score_threshold
        self.client = QdrantClient(url=qdrant.url)
        self.embeddings = OllamaEmbeddings(
            model=ai.embedding_model,
            base_url=ai.ollama_base_url,
        )

    def index_directory(self, directory: Path) -> int:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
        )
        chunks: list[tuple[str, dict]] = []

        for path in sorted(directory.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = self._extract_title(text, path.stem)
            for index, chunk in enumerate(splitter.split_text(text)):
                chunks.append(
                    (
                        chunk,
                        {
                            "title": title,
                            "source": path.name,
                            "chunk_index": index,
                        },
                    )
                )

        if not chunks:
            raise ValueError(f"No Markdown documents found in {directory}")

        vectors = self.embeddings.embed_documents([text for text, _ in chunks])
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=len(vectors[0]),
                distance=Distance.COSINE,
            ),
        )

        points = []
        for (text, metadata), vector in zip(chunks, vectors, strict=True):
            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{metadata['source']}:{metadata['chunk_index']}:{text}",
                )
            )
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={**metadata, "text": text},
                )
            )

        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def search(self, question: str, limit: int = 4) -> list[KnowledgeHit]:
        vector = self.embeddings.embed_query(question)
        result = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
            score_threshold=self.score_threshold,
        )
        return [
            KnowledgeHit(
                text=str(point.payload.get("text", "")),
                title=str(point.payload.get("title", "Untitled")),
                source=str(point.payload.get("source", "unknown")),
                score=float(point.score),
            )
            for point in result.points
            if point.payload is not None
        ]

    def close(self) -> None:
        self.client.close()

    @staticmethod
    def _extract_title(text: str, fallback: str) -> str:
        first_line = text.splitlines()[0] if text else ""
        return first_line.removeprefix("# ").strip() or fallback
