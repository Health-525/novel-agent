"""LLM 统一接口 — 支持 Anthropic Claude 和 OpenAI 兼容 API"""

from anthropic import Anthropic
from openai import OpenAI


class LLMClient:
    """统一的 LLM 调用接口"""

    def __init__(self, config: dict):
        provider = config.get("provider", "anthropic")
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "")
        self.model = config.get("model", "claude-opus-4-7")
        self.max_tokens = config.get("max_tokens", 8192)
        self.temperature = config.get("temperature", 0.8)
        self._provider = provider

        if provider == "anthropic":
            self._client = Anthropic(api_key=api_key)
        elif provider == "openai":
            self._client = OpenAI(api_key=api_key)
        elif provider == "openai-compatible":
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            raise ValueError(f"不支持的 LLM provider: {provider}")

    def chat(self, system: str, user: str) -> str:
        """非流式调用，返回完整回复"""
        if self._provider == "anthropic":
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            # 从响应中提取文本（跳过 ThinkingBlock）
            for block in resp.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content

    def chat_stream(self, system: str, user: str):
        """流式调用，逐个 yield 文本片段"""
        if self._provider == "anthropic":
            with self._client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        else:
            stream = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
