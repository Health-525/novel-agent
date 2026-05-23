"""CLI 命令行界面 — novel-agent 的主入口"""

import os
from pathlib import Path
import yaml

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from llm.client import LLMClient
from knowledge.character import CharacterManager
from knowledge.worldview import WorldviewManager
from knowledge.chapter import ChapterManager
from knowledge.vector_store import VectorStore
from engine.context_builder import build_chapter_context
from engine.writer import write_chapter
from engine.reviewer import review_chapter
from engine.archive_updater import update_archives

app = typer.Typer(help="novel-agent - AI driven novel writing assistant")
console = Console(force_terminal=False)

project_cmd = typer.Typer(help="Project management")
character_cmd = typer.Typer(help="Character profile management")
chapter_cmd = typer.Typer(help="Chapter management")
app.add_typer(project_cmd, name="project")
app.add_typer(character_cmd, name="character")
app.add_typer(chapter_cmd, name="chapter")


def _load_config() -> dict:
    for name in ["config.local.yaml", "config.yaml"]:
        if Path(name).exists():
            with open(name, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    return {}


def _get_client() -> LLMClient:
    config = _load_config()
    llm_config = config.get("llm", {})
    if not llm_config.get("api_key"):
        llm_config["api_key"] = os.environ.get("ANTHROPIC_API_KEY", "")
        if not llm_config["api_key"]:
            llm_config["api_key"] = os.environ.get("OPENAI_API_KEY", "")
    return LLMClient(llm_config)


def _get_data_root() -> Path:
    config = _load_config()
    return Path(config.get("data", {}).get("root", "./data"))


# ------------------------------------------------------------------
# Project commands
# ------------------------------------------------------------------

@project_cmd.command()
def create(name: str, genre: str = typer.Option("", help="Genre, e.g. xuanhuan, xianxia, quanmou")):
    """Create a new novel project"""
    project_dir = _get_data_root() / name
    if project_dir.exists():
        console.print(f"[red]Project '{name}' already exists: {project_dir}[/red]")
        raise typer.Exit(1)

    project_dir.mkdir(parents=True)

    overview = f"""---
name: {name}
type: 长篇小说
genre: {genre}
target_words: 200000
current_chapter: 0
total_chapters_planned: 0
created: {_today()}
tags: []
---

# {name}

## 一句话梗概
（在这里写一句话的故事梗概）

## 章节规划
"""
    (project_dir / "project.md").write_text(overview, encoding="utf-8")
    (project_dir / "characters").mkdir(exist_ok=True)
    (project_dir / "chapters").mkdir(exist_ok=True)

    WorldviewManager(project_dir).create(genre or "待设定")

    outline = """---
chapters: []
---

# 章节大纲规划

## 第一卷
（在此规划每一章的内容概要）
"""
    (project_dir / "outline.md").write_text(outline, encoding="utf-8")

    console.print(f"[green][OK] Project '{name}' created[/green]")
    console.print(f"  Path: {project_dir}")
    console.print(f"  Open this folder as an Obsidian Vault to manage characters")


@project_cmd.command()
def info(name: str):
    """Show project information"""
    project_dir = _get_data_root() / name
    if not project_dir.exists():
        console.print(f"[red]Project '{name}' not found[/red]")
        raise typer.Exit(1)

    cm = CharacterManager(project_dir, _get_vector_store(project_dir))
    chm = ChapterManager(project_dir)

    console.print(Panel(f"[bold]{name}[/bold]", title="Project Info"))
    console.print(f"Characters: {len(cm.list_all())}")
    console.print(f"Chapters: {len(chm.list_all())}")

    chars = cm.list_all()
    if chars:
        table = Table(title="Characters")
        table.add_column("Name")
        table.add_column("Age")
        table.add_column("Identity")
        for c in chars:
            table.add_row(str(c["name"]), str(c.get("age", "")), str(c.get("identity", "")))
        console.print(table)

    chaps = chm.list_all()
    if chaps:
        table = Table(title="Chapters")
        table.add_column("Ch")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Words")
        for ch in chaps:
            table.add_row(
                str(ch["chapter"]),
                str(ch.get("title", "")),
                str(ch.get("status", "")),
                str(ch.get("word_count", 0)),
            )
        console.print(table)


# ------------------------------------------------------------------
# Character commands
# ------------------------------------------------------------------

@character_cmd.command()
def add(project: str, name: str):
    """Add a new character to the project"""
    project_dir = _get_data_root() / project
    if not project_dir.exists():
        console.print(f"[red]Project '{project}' not found[/red]")
        raise typer.Exit(1)

    cm = CharacterManager(project_dir, _get_vector_store(project_dir))
    filepath = cm.create(name)
    console.print(f"[green][OK] Character '{name}' created[/green]")
    console.print(f"  File: {filepath}")
    console.print(f"  Edit this file in Obsidian to fill in details")


@character_cmd.command()
def list(project: str):
    """List all characters in the project"""
    project_dir = _get_data_root() / project
    cm = CharacterManager(project_dir, _get_vector_store(project_dir))
    chars = cm.list_all()
    if not chars:
        console.print("[yellow]No characters yet[/yellow]")
        return
    table = Table(title="Characters")
    table.add_column("Name")
    table.add_column("Age")
    table.add_column("Gender")
    table.add_column("Identity")
    table.add_column("Tags")
    for c in chars:
        table.add_row(
            str(c["name"]),
            str(c.get("age", "")),
            str(c.get("gender", "")),
            str(c.get("identity", "")),
            ", ".join(c.get("tags", [])),
        )
    console.print(table)


@character_cmd.command()
def show(project: str, name: str):
    """Show full character profile"""
    project_dir = _get_data_root() / project
    cm = CharacterManager(project_dir, _get_vector_store(project_dir))
    char = cm.get(name)
    if not char:
        console.print(f"[red]Character '{name}' not found[/red]")
        raise typer.Exit(1)

    console.print(Panel(char.get("body", ""), title=f"Character: {name}"))
    console.print(f"Age: {char.get('age')} | Gender: {char.get('gender')}")
    console.print(f"Identity: {char.get('identity')}")
    console.print(f"Appearance: {char.get('appearance')}")

    personality = char.get("personality", {})
    if isinstance(personality, dict):
        console.print(f"Traits: {', '.join(personality.get('traits', []))}")
        console.print(f"Motivation: {personality.get('core_motivation', '')}")

    speech = char.get("speech", {})
    if isinstance(speech, dict) and speech.get("habits"):
        console.print(f"Catchphrases: {', '.join(speech['habits'])}")

    timeline = char.get("timeline", [])
    if timeline:
        console.print("\n[bold]Timeline:[/bold]")
        for t in timeline:
            console.print(f"  [Ch.{t.get('chapter', '?')}] {t.get('event', '')}")


# ------------------------------------------------------------------
# Chapter commands
# ------------------------------------------------------------------

@chapter_cmd.command()
def create(project: str, num: int, title: str = ""):
    """Create chapter outline file"""
    project_dir = _get_data_root() / project
    chm = ChapterManager(project_dir)
    filepath = chm.create(num)
    if title:
        from knowledge.obsidian_utils import update_frontmatter
        update_frontmatter(filepath, {"title": title})
    console.print(f"[green][OK] Chapter {num} outline created[/green]")
    console.print(f"  File: {filepath}")


@chapter_cmd.command()
def write(project: str, num: int, stream: bool = True):
    """Generate chapter content using AI"""
    project_dir = _get_data_root() / project
    if not project_dir.exists():
        console.print(f"[red]Project '{project}' not found[/red]")
        raise typer.Exit(1)

    vs = _get_vector_store(project_dir)
    cm = CharacterManager(project_dir, vs)
    wm = WorldviewManager(project_dir)
    chm = ChapterManager(project_dir)
    client = _get_client()

    console.print(f"[bold]Writing Chapter {num}...[/bold]")
    context = build_chapter_context(project_dir, num, cm, wm, chm)
    console.print(f"  Context length: {len(context)} chars")

    chapter_text = write_chapter(client, context, stream=stream)

    if not chapter_text.strip():
        console.print("[red]Generation failed: empty output[/red]")
        raise typer.Exit(1)

    review_chapter(client, chapter_text, context)

    chapter_data = chm.get(num)
    char_names = chapter_data.get("characters", [])
    update_archives(client, chapter_text, num, char_names, cm)

    chm.save(num, chapter_data.get("title", f"Chapter {num}"), chapter_text,
             characters=char_names, pov=chapter_data.get("pov", ""))

    console.print(f"[green][OK] Chapter {num} saved[/green]")
    console.print(f"  Words: {len(chapter_text)}")
    console.print(f"  File: {project_dir / 'chapters' / f'ch{num:02d}.md'}")


@chapter_cmd.command()
def list(project: str):
    """List all chapters"""
    project_dir = _get_data_root() / project
    chm = ChapterManager(project_dir)
    chaps = chm.list_all()
    if not chaps:
        console.print("[yellow]No chapters yet[/yellow]")
        return
    table = Table(title="Chapters")
    table.add_column("Ch")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Words")
    for ch in chaps:
        status = "[green]done[/green]" if ch["status"] == "written" else "draft"
        table.add_row(str(ch["chapter"]), ch["title"], status, str(ch["word_count"]))
    console.print(table)


# ------------------------------------------------------------------
# Utils
# ------------------------------------------------------------------

def _get_vector_store(project_dir: Path) -> VectorStore:
    chroma_dir = project_dir / ".chroma"
    chroma_dir.mkdir(exist_ok=True)
    return VectorStore(chroma_dir)


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


if __name__ == "__main__":
    app()
