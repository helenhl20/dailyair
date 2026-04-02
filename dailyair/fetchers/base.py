"""Base class for all DailyAir content fetchers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ContentItem:
    title: str
    url: str
    source_name: str
    source_type: str          # rss | email | web | youtube | podcast
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    text: str = ""
    summary: str = ""
    notable_quote: str = ""
    media_url: Optional[str] = None
    transcript: Optional[str] = None

    def __repr__(self):
        return f"<ContentItem [{self.source_type}] '{self.title[:60]}'>"


class BaseFetcher(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def fetch(self) -> list[ContentItem]:
        ...

    def _truncate(self, text: str, max_chars: int = 8000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[... content truncated ...]"
