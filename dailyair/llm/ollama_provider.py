"""Ollama provider — run LLMs locally for free."""

import requests
from .base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = self.llm_config.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = self.model or "llama3"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
