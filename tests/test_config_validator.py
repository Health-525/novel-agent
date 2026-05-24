"""测试 config_validator 模块"""

import pytest
from engine.config_validator import validate_config


def test_valid_config_passes():
    config = {
        "llm": {"provider": "anthropic", "model": "claude-opus-4-7", "max_tokens": 8192, "temperature": 0.8, "max_retries": 3},
        "data": {"root": "./data"},
    }
    assert validate_config(config) == []


def test_empty_config_passes():
    assert validate_config({}) == []


def test_bad_provider():
    errors = validate_config({"llm": {"provider": "gemini"}})
    assert any("provider" in e for e in errors)


def test_bad_type():
    errors = validate_config({"llm": {"temperature": "hot"}})
    assert any("temperature" in e for e in errors)


def test_out_of_range():
    errors = validate_config({"llm": {"temperature": 3.0}})
    assert any("temperature" in e for e in errors)


def test_section_not_dict():
    errors = validate_config({"llm": "not a dict"})
    assert any("llm" in e for e in errors)


def test_data_root_is_string():
    errors = validate_config({"data": {"root": 123}})
    assert any("root" in e for e in errors)
