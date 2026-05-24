"""统一的日志配置"""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """配置根日志器，返回 novel-agent 的 logger"""
    root = logging.getLogger("novel_agent")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        root.addHandler(handler)

    return root
