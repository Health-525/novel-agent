"""LLM 统一接口 — 支持 Anthropic Claude 和 OpenAI 兼容 API"""

import time
import logging
from anthropic import Anthropic, APIError as AnthropicError, RateLimitError as AnthropicRateLimit
from openai import OpenAI, APIError as OpenAIError, RateLimitError as OpenAIRateLimit

logger = logging.getLogger(__name__)

RETRY_DELAYS = [2, 5, 15]


class LLMClient:
    """统一的 LLM 调用接口"""

    def __init__(self, config: dict):
        provider = config.get("provider", "anthropic")
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "")
        self.model = config.get("model", "claude-opus-4-7")
        self.max_tokens = config.get("max_tokens", 8192)
        self.temperature = config.get("temperature", 0.8)
        self.max_retries = config.get("max_retries", 3)
        self._provider = provider

        if not api_key:
            raise ValueError("LLM API key is required. Set it in config.local.yaml or environment variable.")

        if provider == "anthropic":
            self._client = Anthropic(api_key=api_key)
        elif provider == "openai":
            self._client = OpenAI(api_key=api_key)
        elif provider == "openai-compatible":
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            raise ValueError(f"不支持的 LLM provider: {provider}")

    def _retry(self, fn, *args, **kwargs):
        """带退避重试的调用包装"""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except (AnthropicRateLimit, OpenAIRateLimit) as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                    logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
            except (AnthropicError, OpenAIError, Exception) as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                    logger.warning(f"API error: {e}, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
        raise RuntimeError(f"LLM call failed after {self.max_retries} retries: {last_error}")

    def chat(self, system: str, user: str) -> str:
        """非流式调用，返回完整回复"""
        return self._retry(self._chat_impl, system, user)

    def _chat_impl(self, system: str, user: str) -> str:
        if self._provider == "anthropic":
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
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
        content = resp.choices[0].message.content
        return content if content else ""

    def chat_stream(self, system: str, user: str):
        """流式调用，逐个 yield 文本片段"""
        # 流式调用不做重试（中间已经开始输出）
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
