"""YouTube and Podcast fetchers."""

import logging
import re
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

from .base import BaseFetcher, ContentItem

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyAir/1.0)"}


def _channel_handle_to_url(handle: str) -> str:
    return f"https://www.youtube.com/@{handle.lstrip('@')}/videos"


def _extract_video_ids_from_channel(channel_url: str, max_videos: int = 5) -> list[dict]:
    try:
        resp = requests.get(channel_url, headers=HEADERS, timeout=15)
        ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"', resp.text)
        seen, videos = set(), []
        for vid_id, title in zip(ids, titles):
            if vid_id not in seen:
                seen.add(vid_id)
                videos.append({"id": vid_id, "title": title, "url": f"https://www.youtube.com/watch?v={vid_id}"})
            if len(videos) >= max_videos:
                break
        return videos
    except Exception as e:
        logger.warning(f"Failed to scrape channel {channel_url}: {e}")
        return []


def _get_transcript(video_id: str, max_chars: int = 6000) -> str:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US"])
        return " ".join(seg["text"] for seg in transcript)[:max_chars]
    except (NoTranscriptFound, TranscriptsDisabled):
        return ""
    except Exception as e:
        logger.warning(f"Transcript fetch failed for {video_id}: {e}")
        return ""


class YouTubeFetcher(BaseFetcher):
    def fetch(self) -> list[ContentItem]:
        channels = self.config.get("sources", {}).get("youtube_channels", [])
        max_items = self.config.get("briefing", {}).get("max_items_per_source", 3)
        items = []
        for channel in channels:
            logger.info(f"Fetching YouTube channel: {channel}")
            videos = _extract_video_ids_from_channel(_channel_handle_to_url(channel), max_videos=max_items)
            for video in videos:
                transcript = _get_transcript(video["id"])
                items.append(ContentItem(
                    title=video["title"], url=video["url"], source_name=channel,
                    source_type="youtube", author=channel, text=transcript,
                    transcript=transcript, media_url=video["url"],
                ))
        return items


class PodcastFetcher(BaseFetcher):
    def fetch(self) -> list[ContentItem]:
        podcasts = self.config.get("sources", {}).get("podcasts", [])
        max_items = self.config.get("briefing", {}).get("max_items_per_source", 2)
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        items = []

        for podcast in podcasts:
            name = podcast.get("name", "Podcast")
            rss_url = podcast.get("rss", "")
            if not rss_url:
                continue
            logger.info(f"Fetching podcast: {name}")
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries[:max_items]:
                    t = getattr(entry, "published_parsed", None)
                    pub_date = datetime(*t[:6], tzinfo=timezone.utc) if t else None
                    if pub_date and pub_date < cutoff:
                        continue

                    desc = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text(separator="\n", strip=True)
                    audio_url = next((e.get("href", "") for e in getattr(entry, "enclosures", []) if e.get("type", "").startswith("audio")), "")

                    items.append(ContentItem(
                        title=entry.get("title", "Episode"), url=entry.get("link", rss_url),
                        source_name=name, source_type="podcast", published_at=pub_date,
                        text=self._truncate(desc), media_url=audio_url,
                    ))
            except Exception as e:
                logger.warning(f"Podcast fetch failed for {name}: {e}")

        return items
