"""Markdown output adapter."""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MarkdownOutput:
    def __init__(self, config: dict):
        self.config = config
        output_path = config.get("output", {}).get("markdown", {}).get("path", "~/dailyair-briefings/")
        self.output_dir = Path(output_path).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, briefing_script: str, summaries: list[dict]) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = self.output_dir / f"briefing-{date_str}.md"

        seen = {}
        for s in summaries:
            seen.setdefault(s["source_name"], []).append(s["title"])

        sources_section = "## Sources Covered\n\n" + "".join(
            f"- **{source}**: {', '.join(titles[:3])}\n" for source, titles in seen.items()
        )

        detail_section = "---\n\n## Detailed Summaries\n\n" + "".join(
            f"### [{s['title']}]({s.get('url', '#')})\n"
            f"**Source:** {s['source_name']} | **Type:** {s.get('source_type', '')}\n\n"
            f"{s['summary']}\n\n"
            + (f"> \"{s['quote']}\"\n\n" if s.get("quote") else "")
            for s in summaries
        )

        content = (
            f"# DailyAir Morning Briefing — {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
            + sources_section
            + f"\n\n## Today's Briefing\n\n{briefing_script}\n\n"
            + detail_section
        )

        filename.write_text(content, encoding="utf-8")
        logger.info(f"Briefing saved to: {filename}")
        return filename
