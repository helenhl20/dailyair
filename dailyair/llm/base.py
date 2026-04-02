"""Provider-agnostic LLM interface for DailyAir."""

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.llm_config = config.get("llm", {})
        self.model = self.llm_config.get("model", "")
        self.api_key = self.llm_config.get("api_key", "")

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...

    def summarize_item(self, title: str, text: str, source_type: str, style: str = "conversational") -> tuple[str, str]:
        briefing_cfg = self.config.get("briefing", {})
        length_map = {"short": "2-3 sentences", "medium": "4-6 sentences", "long": "8-10 sentences"}
        length = length_map.get(briefing_cfg.get("summary_length", "medium"), "4-6 sentences")
        include_quotes = briefing_cfg.get("include_quotes", True)

        style_instructions = {
            "conversational": "Write as if you're telling a friend about it — warm, engaging, and natural.",
            "bullet_points": "Summarize as 3-5 bullet points.",
            "executive": "Be direct and crisp, focus on key insights and implications.",
        }.get(style, "Write naturally.")

        quote_instruction = (
            "\n\nAlso extract one compelling, notable quote from the text (max 30 words). "
            "Return it on a new line prefixed with QUOTE:"
        ) if include_quotes and text else ""

        system = (
            "You are Daisy, a sharp and friendly AI briefing assistant. "
            "You summarize content for a busy professional's morning briefing. "
            f"{style_instructions}"
        )

        user = (
            f"Summarize this {source_type} content in {length}.\n\n"
            f"Title: {title}\n\n"
            f"Content:\n{text or '(No content available — summarize based on the title only.)'}"
            f"{quote_instruction}"
        )

        try:
            response = self.complete(system, user)
            if include_quotes and "QUOTE:" in response:
                parts = response.split("QUOTE:", 1)
                return parts[0].strip(), parts[1].strip().strip('"').strip("'")
            return response.strip(), ""
        except Exception as e:
            logger.error(f"LLM summarization failed for '{title}': {e}")
            return f"(Summary unavailable: {e})", ""

    def create_briefing(self, summaries: list[dict], opening_line: str) -> str:
        if not summaries:
            return "No new content found for today's briefing."

        items_text = "\n\n".join(
            f"### {s['source_name']} — {s['title']}\n{s['summary']}"
            + (f'\n\n> "{s["quote"]}"' if s.get("quote") else "")
            for s in summaries
        )

        system = (
            "You are Daisy, DailyAir's AI morning briefing assistant. "
            "You write engaging, naturally-flowing briefing scripts meant to be read aloud. "
            "Use conversational transitions between topics. Sound like a knowledgeable friend, not a newscaster."
        )

        user = (
            f"Create a morning briefing script from these summaries. "
            f"Open with: '{opening_line}'\n\n"
            f"Weave these items together naturally with smooth transitions. "
            f"End with a brief motivating close.\n\n{items_text}"
        )

        try:
            return self.complete(system, user)
        except Exception as e:
            logger.error(f"Briefing creation failed: {e}")
            return opening_line + "\n\n" + items_text


def get_provider(config: dict) -> BaseLLMProvider:
    from .openai_provider import OpenAIProvider
    from .anthropic_provider import AnthropicProvider
    from .ollama_provider import OllamaProvider

    provider = config.get("llm", {}).get("provider", "openai").lower()
    providers = {"openai": OpenAIProvider, "anthropic": AnthropicProvider, "ollama": OllamaProvider, "gemini": OpenAIProvider}
    cls = providers.get(provider)
    if not cls:
        raise ValueError(f"Unknown LLM provider: '{provider}'. Choose from: {list(providers.keys())}")
    return cls(config)
