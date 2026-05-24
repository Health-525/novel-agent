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
from knowledge.obsidian_utils import parse_frontmatter
from engine.context_builder import build_chapter_context
from engine.writer import write_chapter, rewrite_chapter
from engine.reviewer import review_chapter
from engine.summarizer import generate_summary
from engine.archive_updater import update_archives
from engine.epub_exporter import export_epub
from engine.config_validator import validate_config
from engine.tts import read_chapter, VOICES, VOICE_ALIASES

__version__ = "0.2.0"

app = typer.Typer(help="novel-agent - AI driven novel writing assistant")
console = Console(force_terminal=True)


def _version_callback(value: bool):
    if value:
        console.print(f"novel-agent v{__version__}")
        raise typer.Exit()


@app.callback()
def main(version: bool = typer.Option(False, "--version", "-V", callback=_version_callback, help="Show version")):
    pass

project_cmd = typer.Typer(help="Project management")
character_cmd = typer.Typer(help="Character profile management")
chapter_cmd = typer.Typer(help="Chapter management")
app.add_typer(project_cmd, name="project")
app.add_typer(character_cmd, name="character")
tts_cmd = typer.Typer(help="Text-to-speech synthesis")
app.add_typer(chapter_cmd, name="chapter")
app.add_typer(tts_cmd, name="tts")


def _load_config() -> dict:
    """加载配置：先读 config.yaml，再用 config.local.yaml 覆盖"""
    config = {}
    for name in ["config.yaml", "config.local.yaml"]:
        path = Path(name)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                overrides = yaml.safe_load(f) or {}
                _deep_merge(config, overrides)
    errors = validate_config(config)
    if errors:
        for err in errors:
            console.print(f"[yellow][WARN][/yellow] {err}")
    return config


def _deep_merge(base: dict, overrides: dict) -> dict:
    """递归合并配置字典"""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


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

    # 读取项目元数据
    project_meta, _ = parse_frontmatter(project_dir / "project.md") if (project_dir / "project.md").exists() else ({}, "")
    target_words = project_meta.get("target_words", 0)
    genre = project_meta.get("genre", "")

    chaps = chm.list_all()
    total_words = sum(ch.get("word_count", 0) for ch in chaps)
    written = sum(1 for ch in chaps if ch.get("status") == "written")
    draft = len(chaps) - written

    # 进度面板
    console.print(Panel(f"[bold]{name}[/bold]" + (f"  ·  {genre}" if genre else ""), title="Project Info"))
    console.print(f"  人物: {len(cm.list_all())}  |  章节: {len(chaps)} ([green]{written} 已完成[/green], [dim]{draft} 草稿[/dim])")
    console.print(f"  总字数: [bold]{total_words:,}[/bold] 字", end="")
    if target_words:
        pct = min(total_words / target_words * 100, 100)
        console.print(f"  |  目标: {target_words:,} 字  |  进度: {pct:.1f}%")
        bar_width = 30
        filled = int(bar_width * total_words / target_words)
        filled = min(filled, bar_width)
        bar = "=" * filled + "-" * (bar_width - filled)
        color = "green" if pct > 10 else "yellow"
        console.print(f"  [{color}][{bar}] {total_words:,}/{target_words:,}[/{color}]")
    else:
        console.print()

    chars = cm.list_all()
    if chars:
        table = Table(title="Characters")
        table.add_column("Name")
        table.add_column("Age")
        table.add_column("Identity")
        for c in chars:
            table.add_row(str(c["name"]), str(c.get("age", "")), str(c.get("identity", "")))
        console.print(table)

    if chaps:
        table = Table(title="Chapters")
        table.add_column("Ch")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Words")
        table.add_column("Summary")
        for ch in chaps:
            status = "[green]written[/green]" if ch.get("status") == "written" else "[dim]draft[/dim]"
            summary = ch.get("summary", "")
            if summary:
                summary = summary[:40] + "..." if len(summary) > 40 else summary
            table.add_row(
                str(ch["chapter"]),
                str(ch.get("title", "")),
                status,
                f"{ch.get('word_count', 0):,}",
                summary,
            )
        console.print(table)


@project_cmd.command()
def export(name: str,
           fmt: str = typer.Option("epub", help="导出格式: epub"),
           output: str = typer.Option("", help="输出路径，默认在项目目录下")):
    """Export novel to ebook format"""
    project_dir = _get_data_root() / name
    if not project_dir.exists():
        console.print(f"[red]Project '{name}' not found[/red]")
        raise typer.Exit(1)

    output_path = output if output else None
    console.print(f"[bold]Exporting '{name}' to {fmt}...[/bold]")
    result = export_epub(project_dir, output_path)
    console.print(f"[green][OK] Exported: {result}[/green]")


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
def write(project: str, num: int,
          stream: bool = typer.Option(True, help="流式输出生成过程"),
          review: bool = typer.Option(True, help="生成后进行 AI 审校"),
          archive: bool = typer.Option(True, help="从新章节自动更新人物档案")):
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

    if stream:
        console.print("\n--- 开始生成 ---\n")
        def on_chunk(chunk: str):
            console.print(chunk, end="", highlight=False)
        chapter_text = write_chapter(client, context, stream=True, on_chunk=on_chunk)
        console.print("\n--- 生成完毕 ---\n")
    else:
        chapter_text = write_chapter(client, context, stream=False)

    if not chapter_text.strip():
        console.print("[red]Generation failed: empty output[/red]")
        raise typer.Exit(1)

    if review:
        console.print("\n--- 审校中 ---\n")
        review_report = review_chapter(client, chapter_text, context)
        console.print(review_report)
        console.print("\n--- 审校完毕 ---\n")

    chapter_data = chm.get(num)

    if archive:
        char_names = chapter_data.get("characters", [])
        console.print("\n--- 更新人物档案 ---")
        results = update_archives(client, chapter_text, num, char_names, cm)
        for r in results:
            console.print(f"  [green]✓[/green] {r['name']} 档案已更新")

    console.print("\n--- 生成摘要 ---")
    summary = generate_summary(client, chapter_text, num)
    console.print(f"  {summary[:80]}...")

    chm.save(num, chapter_data.get("title", f"Chapter {num}"), chapter_text,
             characters=chapter_data.get("characters", []),
             pov=chapter_data.get("pov", ""), summary=summary)

    console.print(f"[green][OK] Chapter {num} saved[/green]")
    console.print(f"  Words: {len(chapter_text)}")
    console.print(f"  File: {project_dir / 'chapters' / f'ch{num:02d}.md'}")


@chapter_cmd.command()
def rewrite(project: str, num: int,
            stream: bool = typer.Option(True, help="流式输出重写过程")):
    """Rewrite chapter based on review feedback"""
    project_dir = _get_data_root() / project
    if not project_dir.exists():
        console.print(f"[red]Project '{project}' not found[/red]")
        raise typer.Exit(1)

    vs = _get_vector_store(project_dir)
    cm = CharacterManager(project_dir, vs)
    wm = WorldviewManager(project_dir)
    chm = ChapterManager(project_dir)
    client = _get_client()

    chapter_data = chm.get(num)
    chapter_text = chapter_data.get("body", "")
    if not chapter_text.strip():
        console.print(f"[red]Chapter {num} is empty, run 'write' first[/red]")
        raise typer.Exit(1)

    # 重建上下文 + 生成审校报告
    context = build_chapter_context(project_dir, num, cm, wm, chm)
    console.print(f"[bold]Reviewing Chapter {num}...[/bold]")
    review_report = review_chapter(client, chapter_text, context)
    console.print(review_report)

    if "无一致性问题" in review_report:
        console.print("[green]Chapter is clean, no rewrite needed[/green]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Rewriting Chapter {num} based on feedback...[/bold]")

    if stream:
        console.print("\n--- 开始重写 ---\n")
        def on_chunk(chunk: str):
            console.print(chunk, end="", highlight=False)
        new_text = rewrite_chapter(client, chapter_text, review_report, context,
                                   stream=True, on_chunk=on_chunk)
        console.print("\n--- 重写完毕 ---\n")
    else:
        new_text = rewrite_chapter(client, chapter_text, review_report, context,
                                   stream=False)

    if not new_text.strip():
        console.print("[red]Rewrite failed: empty output[/red]")
        raise typer.Exit(1)

    # 生成新摘要
    summary = generate_summary(client, new_text, num)

    chm.save(num, chapter_data.get("title", f"Chapter {num}"), new_text,
             characters=chapter_data.get("characters", []),
             pov=chapter_data.get("pov", ""), summary=summary)

    console.print(f"[green][OK] Chapter {num} rewritten and saved[/green]")
    console.print(f"  Words: {len(new_text)}")


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
# TTS commands
# ------------------------------------------------------------------

@tts_cmd.command()
def read(project: str, num: int,
         voice: str = typer.Option("xiaoxiao", help="音色: nv(女活泼)/nr(男叙事)/nv2(女温柔)/nr2(男沉稳)"),
         output: str = typer.Option("", help="输出路径，默认在项目目录下")):
    """将章节文本转为 MP3 语音"""
    project_dir = _get_data_root() / project
    if not project_dir.exists():
        console.print(f"[red]Project '{project}' not found[/red]")
        raise typer.Exit(1)

    chapter_path = project_dir / "chapters" / f"ch{num:02d}.md"
    if not chapter_path.exists():
        console.print(f"[red]Chapter {num} not found: {chapter_path}[/red]")
        raise typer.Exit(1)

    if not output:
        output = str(project_dir / "audiobook" / f"ch{num:02d}.mp3")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Generating audio for Chapter {num}...[/bold]")
    console.print(f"  Voice: {voice}")
    console.print(f"  Output: {output_path}")

    read_chapter(chapter_path, output_path, voice=voice)

    console.print(f"[green][OK] Audio generated: {output_path}[/green]")


@tts_cmd.command()
def voices():
    """列出可用音色"""
    table = Table(title="Available Voices")
    table.add_column("Alias")
    table.add_column("Voice")
    table.add_column("Description")
    table.add_row("nv",  VOICES["xiaoxiao"], "女声 · 活泼自然（默认）")
    table.add_row("nr",  VOICES["yunxi"],    "男声 · 叙事感强")
    table.add_row("nv2", VOICES["xiaoyi"],    "女声 · 温柔")
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
