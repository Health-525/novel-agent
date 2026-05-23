"""世界观管理 — 读写 🌍 世界观.md"""

from pathlib import Path
from knowledge.obsidian_utils import parse_frontmatter, write_frontmatter

WORLDVIEW_TEMPLATE = """---
name: ""
era: ""
year_start: ""

locations: []
rules: {{}}
timeline: []
tags: []
---

# 世界观名称

## 时代背景

## 核心矛盾
"""


class WorldviewManager:
    """管理项目世界观设定"""

    def __init__(self, project_dir: Path):
        self.filepath = project_dir / "worldview.md"

    def create(self, name: str) -> Path:
        if self.filepath.exists():
            raise FileExistsError(f"世界观文件已存在: {self.filepath}")
        content = WORLDVIEW_TEMPLATE.replace("世界观名称", name)
        self.filepath.write_text(content, encoding="utf-8")
        return self.filepath

    def get(self) -> dict:
        metadata, body = parse_frontmatter(self.filepath)
        return {**metadata, "body": body}

    def update(self, updates: dict) -> None:
        metadata, body = parse_frontmatter(self.filepath)
        metadata.update(updates)
        write_frontmatter(self.filepath, metadata, body)
