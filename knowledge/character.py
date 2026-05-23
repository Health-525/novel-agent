"""人物档案管理 — 读写 Obsidian .md 文件 + 自动向量化"""

from pathlib import Path
from knowledge.obsidian_utils import parse_frontmatter, write_frontmatter
from knowledge.vector_store import VectorStore

CHARACTER_TEMPLATE = """---
name: {name}
aliases: []
age: 0
gender: ""
identity: ""
appearance: ""
chapter_first_appear: 0

personality:
  traits: []
  core_motivation: ""
  fears: []

speech:
  habits: []
  style: ""
  taboos: []
  typical_lines: []

behavior:
  when_nervous: ""
  when_angry: ""
  when_thinking: ""

relationships: []
timeline: []
tags: []
---

# {name}

## 人物画像
（自由描述，给 AI 做语义理解的补充材料）

## 核心冲突

## 关键细节
"""


class CharacterManager:
    """管理 👤 人物/ 目录下的人物 .md 档案"""

    def __init__(self, project_dir: Path, vector_store: VectorStore):
        self.dir = project_dir / "characters"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = vector_store

    def create(self, name: str) -> Path:
        """创建一个新人物档案，返回文件路径"""
        filepath = self.dir / f"{name}.md"
        if filepath.exists():
            raise FileExistsError(f"人物 '{name}' 已存在: {filepath}")
        content = CHARACTER_TEMPLATE.format(name=name)
        filepath.write_text(content, encoding="utf-8")
        self._reindex(filepath)
        return filepath

    def get(self, name: str) -> dict | None:
        """读取一个人物的 frontmatter 数据"""
        metadata, body = self._read(name)
        if metadata is None:
            return None
        return {**metadata, "body": body}

    def update(self, name: str, updates: dict) -> None:
        """更新人物的 frontmatter 字段"""
        metadata, body = self._read(name)
        metadata.update(updates)
        filepath = self._filepath(name)
        write_frontmatter(filepath, metadata, body)
        self._reindex(filepath)

    def list_all(self) -> list[dict]:
        """列出所有人物的基本信息"""
        characters = []
        for md_file in sorted(self.dir.glob("*.md")):
            metadata, _ = parse_frontmatter(md_file)
            characters.append({
                "name": metadata.get("name", md_file.stem),
                "age": metadata.get("age"),
                "gender": metadata.get("gender"),
                "identity": metadata.get("identity"),
                "tags": metadata.get("tags", []),
            })
        return characters

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索人物"""
        return self.vector_store.search(query, top_k=top_k)

    def _read(self, name: str) -> tuple[dict | None, str]:
        filepath = self._filepath(name)
        if not filepath.exists():
            return None, ""
        return parse_frontmatter(filepath)

    def _filepath(self, name: str) -> Path:
        return self.dir / f"{name}.md"

    def _reindex(self, filepath: Path) -> None:
        """将人物全文重新向量化写入 ChromaDB"""
        metadata, body = parse_frontmatter(filepath)
        char_id = f"char_{metadata['name']}"
        full_text = filepath.read_text(encoding="utf-8")
        self.vector_store.index_character(
            char_id=char_id,
            text=full_text,
            metadata={
                "name": metadata.get("name"),
                "tags": str(metadata.get("tags", [])),
                "identity": str(metadata.get("identity", "")),
            },
        )
