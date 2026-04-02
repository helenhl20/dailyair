"""DailyAir Curator — main orchestration engine."""

import logging
from datetime import datetime

from .config import load_config
from .fetchers import ContentItem, PeopleFetcher, EmailFetcher, YouTubeFetcher, PodcastFetcher
from .llm import get_provider
from .outputs import (
    MarkdownOutput,
    EmailOutput,
    GoogleDocsOutput,
    TelegramOutput,
    generate_audio,
    play_audio,
    speak,
)

logger = logging.getLogger(__name__)


class Curator:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.llm = get_provider(self.config)
        self.briefing_cfg = self.config.get("briefing", {})
        self.style = self.briefing_cfg.get("style", "conversational")
        self.opening_line = self.briefing_cfg.get(
            "opening_line", "Good morning! Here's your DailyAir briefing for today."
        )

    def run(self, dry_run: bool = False, read_aloud: bool = True) -> dict:
        logger.info("=" * 60)
        logger.info(f"DailyAir starting at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info("=" * 60)

        raw_items = self._fetch_all()
        logger.info(f"Total items fetched: {len(raw_items)}")

        if not raw_items:
            logger.warning("No content found. Check your sources and date range.")
            return {"briefing": "No content found for today.", "outputs": []}

        summaries = self._summarize_all(raw_items)

        if dry_run:
            return {"briefing": "", "summaries": summaries, "outputs": []}

        logger.info("Generating briefing script...")
        briefing_script = self.llm.create_briefing(summaries, self.opening_line)

        # Generate the MP3 before dispatching outputs so Telegram (and any
        # future adapter) can attach it without a second TTS call.
        tts_cfg     = self.config.get("tts", {})
        tts_enabled = tts_cfg.get("enabled", True)
        formats     = self.config.get("output", {}).get("formats", ["markdown"])
        is_system   = tts_cfg.get("provider", "edge").lower() == "system"

        audio_path = None
        needs_audio = tts_enabled and not is_system and (read_aloud or "telegram" in formats)
        if needs_audio:
            logger.info("Generating audio...")
            try:
                audio_path = generate_audio(briefing_script, self.config)
            except Exception as e:
                logger.error(f"Audio generation failed: {e}")

        outputs = self._dispatch_outputs(briefing_script, summaries, audio_path)

        # Open the browser player (skipped automatically on headless VMs since
        # webbrowser.open() is a no-op when no browser is available).
        if read_aloud and tts_enabled:
            if audio_path:
                logger.info("Opening player...")
                play_audio(briefing_script, audio_path, self.config)
            elif is_system:
                speak(briefing_script, self.config)

        logger.info("DailyAir complete.")
        return {"briefing": briefing_script, "summaries": summaries, "outputs": outputs}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_all(self) -> list[ContentItem]:
        items = []
        for fetcher in PeopleFetcher(self.config).get_fetchers():
            try:
                fetched = fetcher.fetch()
                logger.info(f"  [{fetcher.source_name}] {len(fetched)} items")
                items.extend(fetched)
            except Exception as e:
                logger.error(f"Fetch error ({fetcher.source_name}): {e}")

        for cls in [EmailFetcher, YouTubeFetcher, PodcastFetcher]:
            try:
                fetched = cls(self.config).fetch()
                items.extend(fetched)
            except Exception as e:
                logger.error(f"{cls.__name__} error: {e}")

        return items

    def _summarize_all(self, items: list[ContentItem]) -> list[dict]:
        summaries = []
        for i, item in enumerate(items, 1):
            logger.info(f"Summarizing [{i}/{len(items)}]: {item.title[:60]}")
            summary, quote = self.llm.summarize_item(
                title=item.title,
                text=item.text or item.transcript or "",
                source_type=item.source_type,
                style=self.style,
            )
            summaries.append({
                "title":        item.title,
                "url":          item.url,
                "source_name":  item.source_name,
                "source_type":  item.source_type,
                "published_at": item.published_at.isoformat() if item.published_at else "",
                "summary":      summary,
                "quote":        quote,
            })
        return summaries

    def _dispatch_outputs(
        self,
        briefing_script: str,
        summaries: list[dict],
        audio_path=None,
    ) -> list[str]:
        formats = self.config.get("output", {}).get("formats", ["markdown"])
        outputs = []

        if "markdown" in formats:
            try:
                path = MarkdownOutput(self.config).save(briefing_script, summaries)
                outputs.append(str(path))
            except Exception as e:
                logger.error(f"Markdown output failed: {e}")

        if "email" in formats:
            try:
                if EmailOutput(self.config).send(briefing_script, summaries):
                    outputs.append("email:sent")
            except Exception as e:
                logger.error(f"Email output failed: {e}")

        if "google_docs" in formats:
            try:
                url = GoogleDocsOutput(self.config).create_doc(briefing_script, summaries)
                if url:
                    outputs.append(url)
            except Exception as e:
                logger.error(f"Google Docs output failed: {e}")

        if "telegram" in formats:
            try:
                if TelegramOutput(self.config).send(briefing_script, audio_path):
                    outputs.append("telegram:sent")
            except Exception as e:
                logger.error(f"Telegram output failed: {e}")

        return outputs
