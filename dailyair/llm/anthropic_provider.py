"""Anthropic Claude LLM provider."""

from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = self.model or "claude-3-haiku-20240307"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model, max_tokens=1500, system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
