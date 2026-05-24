"""EPUB 导出器 — 将整本小说打包为 epub 电子书"""

import logging
from pathlib import Path
from ebooklib import epub
from knowledge.chapter import ChapterManager
from knowledge.obsidian_utils import parse_frontmatter

logger = logging.getLogger(__name__)


def export_epub(project_dir: Path, output_path: str | None = None) -> Path:
    """导出小说为 EPUB 电子书

    Args:
        project_dir: 小说项目目录
        output_path: 输出路径，默认 project_dir / project_name.epub

    Returns:
        生成的 epub 文件路径
    """
    project_meta, project_body = _read_project(project_dir)
    name = project_meta.get("name", project_dir.name)
    chapters_dir = project_dir / "chapters"

    book = epub.EpubBook()
    book.set_identifier(f"novel-agent-{name}")
    book.set_title(name)
    book.set_language("zh-CN")
    book.add_author(project_meta.get("author", "novel-agent"))

    # 收集章节
    chm = ChapterManager(project_dir)
    chaps = [ch for ch in chm.list_all() if ch.get("status") == "written"]
    if not chaps:
        chaps = chm.list_all()

    # CSS 样式
    style = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content="""body { font-family: serif; line-height: 1.8; margin: 2em; }
h1 { text-align: center; font-size: 2em; margin: 1em 0; }
h2 { text-align: center; font-size: 1.3em; margin: 0.8em 0; }
p { text-indent: 2em; margin: 0.5em 0; }
hr { border: none; text-align: center; margin: 1.5em 0; }
hr::after { content: "＊ ＊ ＊"; }
.character { page-break-before: always; }
.character h3 { font-size: 1.2em; }""",
    )
    book.add_item(style)

    # 书名页
    title_page = epub.EpubHtml(
        title="书名页", file_name="title.xhtml", lang="zh-CN"
    )
    title_page.content = f"""<html><body>
<h1>{name}</h1>
<h2>{project_meta.get('genre', '')}</h2>
<p style="text-align:center;margin-top:3em;">共 {len(chaps)} 章</p>
</body></html>"""
    book.add_item(title_page)

    # 章节
    spine = ["nav", title_page]
    toc = []

    for ch in chaps:
        ch_num = ch["chapter"]
        ch_title = ch.get("title", f"第{ch_num}章")
        _, body = parse_frontmatter(chapters_dir / f"ch{ch_num:02d}.md")

        # 将 markdown 转为简单 HTML
        html_body = _md_to_html(body)
        chapter = epub.EpubHtml(
            title=f"第{ch_num}章 {ch_title}",
            file_name=f"ch{ch_num:02d}.xhtml",
            lang="zh-CN",
        )
        chapter.content = f"""<html><body>
<h1>第{ch_num}章</h1>
<h2>{ch_title}</h2>
{html_body}
</body></html>"""
        book.add_item(chapter)
        spine.append(chapter)
        toc.append(epub.Link(f"ch{ch_num:02d}.xhtml", f"第{ch_num}章 {ch_title}", f"ch{ch_num:02d}"))

    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    if output_path is None:
        output_path = str(project_dir / f"{name}.epub")
    epub.write_epub(output_path, book)

    logger.info("EPUB exported: %s (%d chapters)", output_path, len(chaps))
    return Path(output_path)


def _read_project(project_dir: Path) -> tuple[dict, str]:
    project_file = project_dir / "project.md"
    if project_file.exists():
        return parse_frontmatter(project_file)
    return {}, ""


def _md_to_html(text: str) -> str:
    """将小说 markdown 转为简单 HTML"""
    import re

    # 跳过 frontmatter
    text = re.sub(r"^---\n.*?\n---\n*", "", text, flags=re.DOTALL)

    lines = text.strip().split("\n")
    html_lines = []
    in_para = False

    for line in lines:
        line = line.strip()
        if not line:
            if in_para:
                html_lines.append("</p>")
                in_para = False
            continue

        # 标题
        if line.startswith("# "):
            if in_para:
                html_lines.append("</p>")
                in_para = False
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_para:
                html_lines.append("</p>")
                in_para = False
            html_lines.append(f"<h2>{line[2:]}</h2>")
        elif line.startswith("---"):
            if in_para:
                html_lines.append("</p>")
                in_para = False
            html_lines.append("<hr/>")
        else:
            # 处理内联格式
            line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            line = re.sub(r"\*(.+?)\*", r"<i>\1</i>", line)
            if not in_para:
                html_lines.append("<p>")
                in_para = True
            html_lines.append(line)

    if in_para:
        html_lines.append("</p>")

    return "\n".join(html_lines)
