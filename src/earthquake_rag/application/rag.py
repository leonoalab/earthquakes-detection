from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from earthquake_rag.core.config import Settings
from earthquake_rag.domain.entities import KnowledgeHit, RagAnswer
from earthquake_rag.infrastructure.vector_store import KnowledgeStore

SYSTEM_PROMPT = """
You are an educational assistant specialized in seismology.

Answer using only the retrieved context. Cite supporting passages as
[Source 1], [Source 2], and so on. If the context does not contain enough
evidence, state that limitation instead of using unsupported knowledge.
""".strip()


class RagService:
    def __init__(self, settings: Settings) -> None:
        self.knowledge = KnowledgeStore(settings.ai, settings.qdrant)
        model = ChatOllama(
            model=settings.ai.chat_model,
            base_url=settings.ai.ollama_base_url,
            temperature=0,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    "Retrieved context:\n\n{context}\n\nQuestion:\n{question}",
                ),
            ]
        )
        self.chain = prompt | model | StrOutputParser()

    def answer(self, question: str, limit: int = 4) -> RagAnswer:
        hits = self.knowledge.search(question, limit)
        if not hits:
            return RagAnswer(
                answer="The knowledge base does not contain enough evidence to answer.",
                hits=[],
            )

        return RagAnswer(
            answer=self.chain.invoke(
                {"question": question, "context": self._format_context(hits)}
            ),
            hits=hits,
        )

    def close(self) -> None:
        self.knowledge.close()

    @staticmethod
    def _format_context(hits: list[KnowledgeHit]) -> str:
        sections = []
        for number, hit in enumerate(hits, start=1):
            sections.append(
                f"[Source {number}]\n"
                f"Title: {hit.title}\n"
                f"File: {hit.source}\n"
                f"Similarity: {hit.score:.4f}\n\n"
                f"{hit.text}"
            )
        return "\n\n".join(sections)
