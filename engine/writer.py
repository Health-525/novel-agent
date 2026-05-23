"""写作引擎 — 调用 LLM 生成小说正文"""

from llm.client import LLMClient
from llm.prompts import WRITER_SYSTEM


def write_chapter(client: LLMClient, context: str, stream: bool = True) -> str:
    """根据上下文生成一章正文

    Args:
        client: LLM 客户端
        context: context_builder.build_chapter_context() 的输出
        stream: 是否流式输出（CLI 模式下流式打印）

    Returns:
        生成的完整正文
    """
    if stream:
        print("\n--- 开始生成 ---\n")
        full_text = ""
        for chunk in client.chat_stream(system=WRITER_SYSTEM, user=context):
            print(chunk, end="", flush=True)
            full_text += chunk
        print("\n--- 生成完毕 ---\n")
        return full_text

    return client.chat(system=WRITER_SYSTEM, user=context)
