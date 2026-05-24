"""测试 archive_updater 模块"""

import pytest
from engine.archive_updater import _extract_json


class TestExtractJson:
    def test_extract_json_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        assert _extract_json(text) == '{"key": "value"}'

    def test_extract_brace_object(self):
        text = '一些前缀文字 {"name": "test", "value": 42} 一些后缀'
        result = _extract_json(text)
        assert result == '{"name": "test", "value": 42}'

    def test_extract_nested_json(self):
        """嵌套 JSON 对象应正确匹配括号"""
        text = '{"outer": {"inner": [1, 2, 3]}, "key": "value"}'
        result = _extract_json(text)
        # 应该返回完整的 JSON
        assert result.startswith("{")
        assert result.endswith("}")
        assert "inner" in result

    def test_no_json_returns_original(self):
        text = "没有 JSON 的纯文本"
        result = _extract_json(text)
        assert result == text

    def test_multiple_objects_returns_first(self):
        text = '{"first": 1} 其他文字 {"second": 2}'
        result = _extract_json(text)
        assert result == '{"first": 1}'

    def test_json_with_string_braces(self):
        """值中包含花括号的 JSON"""
        text = '{"key": "value {with braces}"}'
        result = _extract_json(text)
        assert "with braces" in result
