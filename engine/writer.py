"""写作引擎 — 调用 LLM 生成小说正文"""

import logging
from llm.client import LLMClient
from llm.prompts import WRITER_SYSTEM, REWRITER_SYSTEM

logger = logging.getLogger(__name__)


def write_chapter(client: LLMClient, context: str, stream: bool = True, on_chunk=None) -> str:
    """根据上下文生成一章正文

    Args:
        client: LLM 客户端
        context: context_builder.build_chapter_context() 的输出
        stream: 是否流式输出
        on_chunk: 每个文本块的回调函数，签名 (chunk_text) -> None

    Returns:
        生成的完整正文
    """
    if stream and on_chunk:
        full_text = ""
        for chunk in client.chat_stream(system=WRITER_SYSTEM, user=context):
            on_chunk(chunk)
            full_text += chunk
        return full_text

    logger.info("Generating chapter (non-streaming)...")
    return client.chat(system=WRITER_SYSTEM, user=context)


def rewrite_chapter(client: LLMClient, chapter_text: str, review_report: str,
                    context: str, stream: bool = True, on_chunk=None) -> str:
    """根据审校报告重写章节

    Args:
        client: LLM 客户端
        chapter_text: 当前章节正文
        review_report: 审校报告文本
        context: 原始写作上下文（人物档案等）
        stream: 是否流式输出
        on_chunk: 每个文本块的回调函数

    Returns:
        重写后的完整正文
    """
    prompt = f"""## 原始上下文

{context}

## 当前正文

{chapter_text}

## 审校报告

{review_report}

请根据审校报告重写本章完整正文。"""

    if stream and on_chunk:
        full_text = ""
        for chunk in client.chat_stream(system=REWRITER_SYSTEM, user=prompt):
            on_chunk(chunk)
            full_text += chunk
        return full_text

    logger.info("Rewriting chapter...")
    return client.chat(system=REWRITER_SYSTEM, user=prompt)
