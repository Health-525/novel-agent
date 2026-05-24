"""TTS 语音合成 — 调用 Edge TTS 将章节文本转为 MP3"""

import re
import subprocess
import sys
from pathlib import Path

import yaml

# 高质量中文声音，按场景推荐
VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",       # 女声 · 活泼自然（默认）
    "xiaoyi":   "zh-CN-XiaoyiNeural",          # 女声 · 温柔
    "yunxi":    "zh-CN-YunxiNeural",           # 男声 · 叙事感强
    "yunjian":  "zh-CN-YunjianNeural",         # 男声 · 沉稳大气
}

VOICE_ALIASES = {
    "nv":   "xiaoxiao",
    "nr":   "yunxi",
    "nv2":  "xiaoyi",
    "nr2":  "yunjian",
}


def _resolve_voice(voice: str) -> str:
    """把中文别名映射到 edge-tts 的 ShortName"""
    key = VOICE_ALIASES.get(voice, voice)
    return VOICES.get(key, voice)


def _strip_markdown(text: str) -> str:
    """去掉 markdown 标记，输出纯文本用于朗读"""
    # 去掉 frontmatter
    text = re.sub(r'^---[\s\S]*?---\n*', '', text)
    # 去掉标题标记
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # 去掉粗体 / 斜体
    text = re.sub(r'\*{1,3}([^*]+?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+?)_{1,3}', r'\1', text)
    # 去掉分割线
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # 去掉行内代码和代码块
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)
    # 去掉链接，保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 去掉引用标记
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    # 合并连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _ensure_edge_tts() -> None:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("正在安装 edge-tts ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts"])


async def _synthesize(text: str, voice: str, output: Path, rate: str = "+10%") -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output))


def read_chapter(chapter_path: Path, output_path: Path,
                 voice: str = "xiaoxiao", rate: str = "+10%") -> Path:
    """将章节 md 文件转为 MP3

    Args:
        chapter_path: 章节 .md 文件路径
        output_path: 输出 .mp3 文件路径
        voice: 声音别名 (nv/nr/nv2/nr2) 或 edge-tts ShortName
        rate: 语速，如 "+10%" / "-10%" / "+0%"

    Returns:
        生成的 mp3 文件路径
    """
    _ensure_edge_tts()

    raw = chapter_path.read_text(encoding="utf-8")
    text = _strip_markdown(raw)

    if not text:
        raise ValueError(f"章节内容为空: {chapter_path}")

    voice_name = _resolve_voice(voice)

    import asyncio
    asyncio.run(_synthesize(text, voice_name, output_path, rate))

    return output_path
