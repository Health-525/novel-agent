"""Obsidian Markdown 兼容工具

处理 YAML frontmatter 的解析/写回 + wiki-link 的解析/生成。
对 Markdown 文件的操作保证不破坏用户的自由描述正文。
"""

import re
import yaml
from pathlib import Path
import frontmatter

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """读取 Obsidian .md 文件，返回 (frontmatter_dict, body_text)"""
    with open(filepath, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    return dict(post.metadata), post.content


def write_frontmatter(filepath: Path, metadata: dict, body: str) -> None:
    """将 metadata 和 body 写回 .md 文件，保持 YAML 格式"""
    post = frontmatter.Post(body, **metadata)
    text = frontmatter.dumps(post)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


def update_frontmatter(filepath: Path, updates: dict) -> None:
    """原地更新 YAML frontmatter 的部分字段，不动正文"""
    metadata, body = parse_frontmatter(filepath)
    metadata.update(updates)
    write_frontmatter(filepath, metadata, body)


def extract_wikilinks(text: str) -> list[str]:
    """提取文本中所有 [[wiki-link]] 的目标名称"""
    return WIKILINK_RE.findall(text)


def render_wikilink(name: str, alias: str = "") -> str:
    """生成 Obsidian 格式的 wiki-link"""
    if alias:
        return f"[[{name}|{alias}]]"
    return f"[[{name}]]"


def build_relationship_graph(characters_dir: Path) -> dict[str, list[str]]:
    """扫描人物目录，从所有人物档案的 wiki-link 中构建关系图

    返回 {人物名: [关联人物名列表]}
    """
    graph: dict[str, list[str]] = {}
    for md_file in characters_dir.glob("*.md"):
        name = md_file.stem
        text = md_file.read_text(encoding="utf-8")
        links = extract_wikilinks(text)
        graph[name] = list(set(links))
    return graph
