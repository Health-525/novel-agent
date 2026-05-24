"""测试 context_builder 模块"""

import pytest
from pathlib import Path
from engine.context_builder import (
    _format_character_profile,
    _guess_characters,
    build_chapter_context,
)


class TestFormatCharacterProfile:
    def test_complete_profile(self):
        data = {
            "name": "苏墨",
            "age": 19,
            "gender": "男",
            "identity": "杂役",
            "appearance": "瘦削",
            "aliases": ["小苏"],
            "personality": {
                "traits": ["固执", "朴素"],
                "core_motivation": "让所有人能修炼",
                "fears": ["功法被禁"],
            },
            "speech": {
                "habits": ["沉默寡言"],
                "style": "简短",
                "taboos": ["宗门"],
                "typical_lines": ["走吧"],
            },
            "behavior": {"when_nervous": "蹲下画圈"},
            "relationships": [
                {"target": "白芷", "state": "师妹", "type": "师门"}
            ],
            "timeline": [
                {"chapter": 1, "event": "捡到功法"}
            ],
            "body": "一个固执的杂役",
        }
        result = _format_character_profile(data)
        assert "苏墨" in result
        assert "19" in result
        assert "杂役" in result
        assert "固执" in result

    def test_minimal_profile_no_none(self):
        """缺失的字段不应显示 None"""
        data = {"name": "测试"}
        result = _format_character_profile(data)
        assert "None" not in result

    def test_missing_personality(self):
        data = {"name": "测试", "age": 20, "gender": "男"}
        result = _format_character_profile(data)
        assert "None" not in result

    def test_linked_prefix(self):
        data = {"name": "关联人"}
        result = _format_character_profile(data, is_linked=True)
        assert "[关联人物]" in result


class TestGuessCharacters:
    def test_extract_wikilinks(self):
        chapter = {"body": "[[苏墨]]和[[白芷]]一起去了[[苍梧城]]"}
        result = _guess_characters(chapter, {})
        assert "苏墨" in result
        assert "白芷" in result

    def test_empty_body(self):
        result = _guess_characters({}, {})
        assert result == []
