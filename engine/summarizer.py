"""章节摘要生成 — 从正文中提炼核心情节"""

import logging
from llm.client import LLMClient
from llm.prompts import SUMMARIZER_SYSTEM

logger = logging.getLogger(__name__)


def generate_summary(client: LLMClient, chapter_text: str, chapter_num: int) -> str:
    """生成章节中文摘要，用于后续章节的上下文组装

    Args:
        client: LLM 客户端
        chapter_text: 章节正文
        chapter_num: 章节编号

    Returns:
        2-4 句中文摘要（不超过 200 字）
    """
    # 截取前 6000 字作为摘要输入，避免超长章节
    text_sample = chapter_text[:6000]
    prompt = f"第{chapter_num}章正文：\n\n{text_sample}"

    logger.info("Generating summary for chapter %d...", chapter_num)
    summary = client.chat(system=SUMMARIZER_SYSTEM, user=prompt)
    summary = summary.strip().strip('"').strip("'")
    logger.info("Summary: %s", summary[:80])
    return summary
