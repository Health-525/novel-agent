"""配置校验 — 启动时验证 config.yaml 结构和值"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = {
    "llm": {
        "required": False,
        "type": dict,
        "keys": {
            "provider":       {"type": str, "values": ["anthropic", "openai", "openai-compatible"]},
            "model":          {"type": str},
            "api_key":        {"type": str},
            "base_url":       {"type": str},
            "max_tokens":     {"type": int, "min": 100, "max": 200000},
            "temperature":    {"type": (int, float), "min": 0.0, "max": 2.0},
            "max_retries":    {"type": int, "min": 0, "max": 10},
        },
    },
    "data": {
        "required": False,
        "type": dict,
        "keys": {
            "root": {"type": str},
        },
    },
    "chroma": {
        "required": False,
        "type": dict,
        "keys": {
            "persist_dir":      {"type": str},
            "embedding_model":  {"type": str},
        },
    },
}


def validate_config(config: dict) -> list[str]:
    """校验配置字典，返回错误消息列表

    Args:
        config: _load_config() 返回的合并后配置

    Returns:
        错误列表，空列表表示通过
    """
    errors = []

    for section, schema in SCHEMA.items():
        if section not in config:
            if schema["required"]:
                errors.append(f"缺少必需配置节: [{section}]")
            continue

        value = config[section]
        if not isinstance(value, schema["type"]):
            errors.append(f"[{section}] 应为字典，实际为 {type(value).__name__}")
            continue

        for key, rules in schema["keys"].items():
            if key not in value:
                continue
            v = value[key]
            expected = rules["type"]
            if not isinstance(v, expected):
                type_name = expected.__name__ if isinstance(expected, type) else " | ".join(t.__name__ for t in expected)
                errors.append(f"[{section}] {key}: 期望 {type_name}，实际 {type(v).__name__}")
                continue
            if "values" in rules and v and v not in rules["values"]:
                errors.append(f"[{section}] {key}: '{v}' 不在支持的值中 ({', '.join(rules['values'])})")
            if "min" in rules and isinstance(v, (int, float)):
                if v < rules["min"]:
                    errors.append(f"[{section}] {key}: {v} < 最小值 {rules['min']}")
            if "max" in rules and isinstance(v, (int, float)):
                if v > rules["max"]:
                    errors.append(f"[{section}] {key}: {v} > 最大值 {rules['max']}")

    return errors
