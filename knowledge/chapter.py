"""章节文件管理 — 读写 📝 章节/*.md"""

from pathlib import Path
from knowledge.obsidian_utils import parse_frontmatter, write_frontmatter

CHAPTER_TEMPLATE = """---
chapter: {num}
title: ""
pov: ""
characters: []
summary: ""
status: draft
word_count: 0
---

# 第{num_chinese}章 · 章节标题

（正文待生成）
"""

_NUMBERS = list("一二三四五六七八九十")


def _chinese_num(n: int) -> str:
    if n <= 10:
        return _NUMBERS[n - 1]
    return str(n)


class ChapterManager:
    """管理 📝 章节/ 目录下的章节 .md 文件"""

    def __init__(self, project_dir: Path):
        self.dir = project_dir / "chapters"
        self.dir.mkdir(parents=True, exist_ok=True)

    def create(self, num: int) -> Path:
        """创建章节骨架文件"""
        filename = f"ch{num:02d}.md"
        filepath = self.dir / filename
        if filepath.exists():
            raise FileExistsError(f"章节文件已存在: {filepath}")
        content = CHAPTER_TEMPLATE.format(num=num, num_chinese=_chinese_num(num))
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def get(self, num: int) -> dict:
        """读取章节内容"""
        filepath = self._filepath(num)
        metadata, body = parse_frontmatter(filepath)
        return {**metadata, "body": body}

    def save(self, num: int, title: str, body: str,
             characters: list[str] | None = None,
             pov: str = "", summary: str = "") -> None:
        """保存章节正文和元数据"""
        filepath = self._filepath(num)
        existing_meta, _ = parse_frontmatter(filepath)
        existing_meta["title"] = title
        existing_meta["status"] = "written"
        existing_meta["word_count"] = len(body)
        if characters:
            existing_meta["characters"] = characters
        if pov:
            existing_meta["pov"] = pov
        if summary:
            existing_meta["summary"] = summary
        write_frontmatter(filepath, existing_meta, body)

    def get_recent_summaries(self, n: int = 3) -> list[dict]:
        """获取最近 n 章的摘要，用于上下文组装"""
        chapters = sorted(self.dir.glob("ch*.md"))
        summaries = []
        for ch in chapters[-n:]:
            metadata, _ = parse_frontmatter(ch)
            if metadata.get("summary"):
                summaries.append({
                    "chapter": metadata.get("chapter"),
                    "title": metadata.get("title"),
                    "summary": metadata.get("summary"),
                })
        return summaries

    def list_all(self) -> list[dict]:
        chapters = []
        for ch in sorted(self.dir.glob("ch*.md")):
            metadata, _ = parse_frontmatter(ch)
            chapters.append({
                "chapter": metadata.get("chapter"),
                "title": metadata.get("title", ""),
                "status": metadata.get("status", "draft"),
                "word_count": metadata.get("word_count", 0),
            })
        return chapters

    def _filepath(self, num: int) -> Path:
        return self.dir / f"ch{num:02d}.md"
