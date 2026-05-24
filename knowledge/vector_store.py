"""向量数据库封装 — 优先 ChromaDB，自动降级为内存存储"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStore:
    """向量索引 — 抽象接口，支持内存和 ChromaDB 两种后端"""

    def __init__(self, persist_dir: str | Path, embedding_model: str = ""):
        self.persist_dir = str(persist_dir)
        self._backend = self._init_backend(persist_dir, embedding_model)

    def _init_backend(self, persist_dir, embedding_model):
        """尝试 ChromaDB，失败则降级为内存存储"""
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(persist_dir),
                anonymized_telemetry=False,
            ))
            collection = client.get_or_create_collection("characters")
            logger.info("Using ChromaDB backend")
            return ChromaBackend(client, collection)
        except (ImportError, Exception) as e:
            logger.info("ChromaDB unavailable (%s), using memory backend", e)
            return MemoryBackend()

    def index_character(self, char_id: str, text: str, metadata: dict) -> None:
        self._backend.index(char_id, text, metadata)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        return self._backend.search(query, top_k)

    def delete(self, char_id: str) -> None:
        self._backend.delete(char_id)

    def count(self) -> int:
        return self._backend.count()


class MemoryBackend:
    """内存后端 — 关键词匹配"""

    def __init__(self):
        self._docs: dict[str, str] = {}
        self._meta: dict[str, dict] = {}

    def index(self, char_id: str, text: str, metadata: dict) -> None:
        self._docs[char_id] = text
        self._meta[char_id] = metadata

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        results = []
        query_lower = query.lower()
        for char_id, doc in self._docs.items():
            if query_lower in doc.lower():
                results.append({
                    "id": char_id,
                    "document": doc,
                    "metadata": self._meta.get(char_id, {}),
                    "distance": 0.0,
                })
        return results[:top_k]

    def delete(self, char_id: str) -> None:
        self._docs.pop(char_id, None)
        self._meta.pop(char_id, None)

    def count(self) -> int:
        return len(self._docs)


class ChromaBackend:
    """ChromaDB 后端 — 语义向量搜索"""

    def __init__(self, client, collection):
        self._client = client
        self._collection = collection

    def index(self, char_id: str, text: str, metadata: dict) -> None:
        self._collection.upsert(
            ids=[char_id],
            documents=[text],
            metadatas=[metadata],
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        results = self._collection.query(query_texts=[query], n_results=top_k)
        return [
            {
                "id": ids[0] if ids else "",
                "document": docs[0] if docs else "",
                "metadata": metas[0] if metas else {},
                "distance": dists[0] if dists else 1.0,
            }
            for ids, docs, metas, dists in zip(
                results.get("ids", [[]]),
                results.get("documents", [[""]]),
                results.get("metadatas", [{}]),
                results.get("distances", [[1.0]]),
            )
        ]

    def delete(self, char_id: str) -> None:
        self._collection.delete(ids=[char_id])

    def count(self) -> int:
        return self._collection.count()
