"""向量数据库封装 — MVP 阶段降级为内存存储，后续启用 ChromaDB"""

from pathlib import Path


class VectorStore:
    """向量索引的降级实现（MVP 阶段）

    ChromaDB 需要 onnxruntime 或 PyTorch，在部分 Windows 环境有 DLL 问题。
    MVP 阶段核心功能（基于 frontmatter 精确匹配人物）不依赖向量搜索。
    后续环境就绪后替换为 ChromaDB 实现。
    """

    def __init__(self, persist_dir: str | Path, embedding_model: str = ""):
        self.persist_dir = str(persist_dir)
        self._docs: dict[str, str] = {}  # char_id -> full text
        self._meta: dict[str, dict] = {}  # char_id -> metadata

    def index_character(self, char_id: str, text: str, metadata: dict) -> None:
        self._docs[char_id] = text
        self._meta[char_id] = metadata

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """简易关键词匹配搜索（非语义搜索）"""
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
