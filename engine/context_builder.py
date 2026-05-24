"""上下文组装器 — 把碎片化的档案信息拼成 LLM 能理解的小说写作 prompt"""

from pathlib import Path
from knowledge.character import CharacterManager
from knowledge.worldview import WorldviewManager
from knowledge.chapter import ChapterManager
from knowledge.obsidian_utils import extract_wikilinks


def build_chapter_context(
    project_dir: Path,
    chapter_num: int,
    character_manager: CharacterManager,
    worldview_manager: WorldviewManager,
    chapter_manager: ChapterManager,
) -> str:
    """组装写一章所需的完整上下文

    返回: 给 LLM 的 user_prompt 文本
    """
    parts = []

    # 1. 世界观设定
    worldview = worldview_manager.get()
    parts.append(_format_worldview(worldview))

    # 2. 本章大纲
    chapter = chapter_manager.get(chapter_num)
    parts.append(f"## 本章任务\n章节: 第{chapter_num}章")
    if chapter.get("title"):
        parts.append(f"标题: {chapter['title']}")
    if chapter.get("pov"):
        parts.append(f"视角人物: {chapter['pov']}")

    # 3. 前情提要
    recent = chapter_manager.get_recent_summaries(n=3)
    if recent:
        parts.append("## 前情提要")
        for s in recent:
            parts.append(f"第{s['chapter']}章 {s['title']}: {s['summary']}")

    # 4. 出场人物档案（最核心）
    char_names = chapter.get("characters", [])
    if not char_names:
        char_names = _guess_characters(chapter, worldview)

    if char_names:
        parts.append("## 出场人物档案")
        for name in char_names:
            char_data = character_manager.get(name)
            if char_data:
                parts.append(_format_character_profile(char_data))
                # 上溯关联人物的档案
                linked = _get_linked_characters(name, char_data, character_manager)
                for linked_data in linked:
                    parts.append(_format_character_profile(linked_data, is_linked=True))

    # 5. 写作指令
    parts.append("## 写作要求")
    parts.append(f"请根据以上设定，撰写第{chapter_num}章的正文。要求：")
    parts.append("- 字数: 3000-5000 字")
    parts.append("- 严格遵循人物档案中的性格、行为模式和语言风格")
    parts.append("- 结尾设置悬念，引出下一章")
    if chapter.get("body") and chapter["body"].strip():
        parts.append(f"\n本章大纲参考:\n{chapter['body']}")

    return "\n\n".join(parts)


def _format_worldview(worldview: dict) -> str:
    lines = ["## 世界观"]
    if worldview.get("name"):
        lines.append(f"### {worldview['name']}")
    if worldview.get("era"):
        lines.append(f"时代: {worldview['era']}")
    if worldview.get("locations"):
        lines.append("### 地点")
        for loc in worldview["locations"]:
            lines.append(f"- {loc['name']}: {loc.get('desc', '')}")
    if worldview.get("rules"):
        rules = worldview["rules"]
        if isinstance(rules, dict):
            for k, v in rules.items():
                if isinstance(v, list):
                    lines.append(f"- {k}: {', '.join(v)}")
                else:
                    lines.append(f"- {k}: {v}")
    if worldview.get("timeline"):
        lines.append("### 世界观时间线")
        for t in worldview["timeline"]:
            label = t.get("year", t.get("era", ""))
            lines.append(f"- {label}: {t.get('event', '')}")
    return "\n".join(lines)


def _format_character_profile(data: dict, is_linked: bool = False) -> str:
    """将人物 frontmatter 格式化为 LLM 友好的文本"""
    prefix = "### [关联人物]" if is_linked else "### [出场人物]"
    name = data.get("name", "") or ""
    lines = [f"{prefix} {name}"]

    aliases = data.get("aliases")
    if aliases:
        lines.append(f"别名: {', '.join(aliases)}")

    age = data.get("age")
    gender = data.get("gender")
    if age or gender:
        lines.append(f"年龄: {age or '?'} | 性别: {gender or '?'}")

    identity = data.get("identity")
    if identity:
        lines.append(f"身份: {identity}")

    appearance = data.get("appearance")
    if appearance:
        lines.append(f"外貌: {appearance}")

    personality = data.get("personality", {})
    if isinstance(personality, dict):
        traits = personality.get("traits", [])
        if traits:
            lines.append(f"性格: {', '.join(traits)}")
        if personality.get("core_motivation"):
            lines.append(f"核心动机: {personality['core_motivation']}")
        if personality.get("fears"):
            lines.append(f"恐惧: {', '.join(personality['fears'])}")

    speech = data.get("speech", {})
    if isinstance(speech, dict):
        if speech.get("habits"):
            lines.append(f"口头禅: {', '.join(speech['habits'])}")
        if speech.get("style"):
            lines.append(f"句式风格: {speech['style']}")
        if speech.get("taboos"):
            lines.append(f"语言禁忌: {', '.join(speech['taboos'])}")
        if speech.get("typical_lines"):
            lines.append(f"典型对话: {'; '.join(speech['typical_lines'])}")

    behavior = data.get("behavior", {})
    if isinstance(behavior, dict):
        for key, val in behavior.items():
            if val:
                label = key.replace("when_", "当")
                lines.append(f"行为模式 — {label}: {val}")

    relationships = data.get("relationships", [])
    if relationships:
        lines.append("当前关系:")
        for r in relationships:
            lines.append(f"  - 与{r.get('target', '')}: {r.get('state', '')} ({r.get('type', '')})")

    timeline = data.get("timeline", [])
    if timeline:
        lines.append("关键经历:")
        for t in timeline:
            lines.append(f"  - [第{t.get('chapter', '?')}章] {t.get('event', '')}")

    if not is_linked and data.get("body"):
        lines.append(f"\n补充描述:\n{data['body'][:500]}")

    return "\n".join(lines)


def _guess_characters(chapter: dict, worldview: dict) -> list[str]:
    """如果没有指定出场人物，根据章节大纲中出现的 [[链接]] 推断"""
    body = chapter.get("body", "")
    if body:
        return extract_wikilinks(body)
    return []


def _get_linked_characters(name: str, data: dict, cm: CharacterManager) -> list[dict]:
    """获取人物档案中 wiki-link 引用的关联人物档案（最多 3 个）"""
    linked = []
    relationships = data.get("relationships", [])
    for r in relationships[:3]:
        target = r.get("target", "")
        target = target.replace("[[", "").replace("]]", "").split("|")[0].strip()
        if target and target != name:
            target_data = cm.get(target)
            if target_data:
                linked.append(target_data)
    return linked
