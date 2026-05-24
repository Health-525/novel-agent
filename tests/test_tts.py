"""测试 tts 模块"""

import pytest
from engine.tts import _strip_markdown, _resolve_voice, VOICES


class TestStripMarkdown:
    def test_strip_frontmatter(self):
        text = "---\nkey: value\n---\n\n正文内容"
        result = _strip_markdown(text)
        assert "key" not in result
        assert "正文内容" in result

    def test_strip_headers(self):
        text = "# 标题\n正文"
        assert _strip_markdown(text) == "标题\n正文"

    def test_strip_bold(self):
        text = "**粗体**文字"
        assert _strip_markdown(text) == "粗体文字"

    def test_strip_links(self):
        text = "[链接](https://example.com)"
        assert _strip_markdown(text) == "链接"

    def test_strip_horizontal_rules(self):
        text = "段落一\n---\n段落二"
        result = _strip_markdown(text)
        assert "段落一" in result
        assert "段落二" in result

    def test_strip_html_tags(self):
        text = "<div>内容</div>"
        result = _strip_markdown(text)
        assert "<div>" not in result
        assert "内容" in result

    def test_empty_text(self):
        assert _strip_markdown("") == ""


class TestResolveVoice:
    def test_alias_nv(self):
        result = _resolve_voice("nv")
        assert result == VOICES["xiaoxiao"]

    def test_direct_name(self):
        result = _resolve_voice("xiaoxiao")
        assert result == VOICES["xiaoxiao"]

    def test_unknown_passthrough(self):
        result = _resolve_voice("unknown-voice")
        assert result == "unknown-voice"
