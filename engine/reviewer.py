"""审校器 — 检查人物一致性和情节矛盾"""

from llm.client import LLMClient
from llm.prompts import REVIEWER_SYSTEM


def review_chapter(client: LLMClient, chapter_text: str, context: str) -> str:
    """检查章节正文的人物一致性问题

    Args:
        client: LLM 客户端
        chapter_text: 生成的章节正文
        context: context_builder 的输出（含人物档案信息）

    Returns:
        审校报告文本
    """
    prompt = f"""## 人物档案参考

{context}

## 待审校章节

{chapter_text}"""

    print("\n--- 审校中 ---\n")
    report = client.chat(system=REVIEWER_SYSTEM, user=prompt)
    print(report)
    print("\n--- 审校完毕 ---\n")
    return report
