"""OpenAI (and OpenAI-compatible) LLM provider."""

from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install openai: pip install openai")

        kwargs = {"api_key": self.api_key}
        base_url = self.llm_config.get("base_url")
        if base_url:
            kwargs["base_url"] = base_url

        self.client = OpenAI(**kwargs)
        self.model = self.model or "gpt-4o-mini"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content or ""
