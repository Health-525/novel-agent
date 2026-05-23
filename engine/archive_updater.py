"""档案更新器 — 从新章节中提取信息，写回人物 .md 文件"""

import json
import re
from pathlib import Path
from llm.client import LLMClient
from llm.prompts import ARCHIVE_UPDATER_SYSTEM
from knowledge.character import CharacterManager


def update_archives(
    client: LLMClient,
    chapter_text: str,
    chapter_num: int,
    character_names: list[str],
    character_manager: CharacterManager,
) -> list[dict]:
    """从新章节提取信息并更新人物档案

    Args:
        client: LLM 客户端
        chapter_text: 章节正文
        chapter_num: 章节编号
        character_names: 出场人物名列表
        character_manager: 人物档案管理器

    Returns:
        更新结果列表
    """
    # 收集出场人物的当前档案
    profiles = ""
    for name in character_names:
        data = character_manager.get(name)
        if data:
            profiles += f"\n### {name}\n{json.dumps(data, ensure_ascii=False, indent=2)}"

    prompt = f"""## 新章节（第{chapter_num}章）

{chapter_text}

## 出场人物当前档案

{profiles}"""

    print("\n--- 更新人物档案 ---\n")
    result = client.chat(system=ARCHIVE_UPDATER_SYSTEM, user=prompt)

    # 解析 LLM 返回的 JSON
    try:
        json_text = _extract_json(result)
        updates = json.loads(json_text)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠ JSON 解析失败: {e}")
        print(f"  原始输出: {result[:500]}")
        return []

    # 写回每个人物的档案
    results = []
    for char_update in updates.get("characters", []):
        name = char_update.get("name", "")
        if not name:
            continue

        current = character_manager.get(name)
        if not current:
            print(f"  ⚠ 人物 '{name}' 不在档案中，跳过")
            continue

        # 追加新的 timeline 条目
        timeline = list(current.get("timeline", []))
        for entry in char_update.get("new_timeline_entries", []):
            entry["chapter"] = entry.get("chapter", chapter_num)
            timeline.append(entry)

        # 更新关系状态
        relationships = list(current.get("relationships", []))
        for rel_update in char_update.get("relationship_updates", []):
            target = rel_update.get("target", "")
            new_state = rel_update.get("new_state", "")
            for r in relationships:
                r_target = r.get("target", "")
                if target in r_target or r_target in target:
                    r["state"] = new_state
                    if rel_update.get("reason"):
                        r["history"] = r.get("history", "") + f" → 第{chapter_num}章{rel_update['reason']}"
                    break

        # 更新身份
        identity_update = char_update.get("identity_update", "")
        identity = current.get("identity", "")
        if identity_update and identity_update != identity:
            identity = f"{identity} → {identity_update}"

        # 汇总更新
        updates_dict = {"timeline": timeline, "relationships": relationships}
        if identity_update:
            updates_dict["identity"] = identity

        character_manager.update(name, updates_dict)
        results.append({"name": name, "status": "updated", "changes": char_update})
        print(f"  ✓ {name} 档案已更新")

    print()
    return results


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 块"""
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if json_match:
        return json_match.group(1)
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        return brace_match.group(0)
    return text
