"""RSS / Atom feed fetcher. Handles Substack, blogs, news sites."""

import feedparser
import requests
import time
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from typing import Optional

from .base import BaseFetcher, ContentItem

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "DailyAir/1.0 (+https://github.com/yourusername/dailyair) RSS Reader"}
COMMON_RSS_PATHS = ["/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml", "/index.xml"]


def discover_rss_feed(url: str) -> Optional[str]:
    try:
        if not url.startswith("http"):
            url = "https://" + url
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for link in soup.find_all("link", type=["application/rss+xml", "application/atom+xml"]):
            href = link.get("href", "")
            if href:
                return href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        for path in COMMON_RSS_PATHS:
            try:
                r = requests.head(base + path, headers=HEADERS, timeout=5)
                if r.status_code == 200:
                    return base + path
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"RSS discovery failed for {url}: {e}")
    return None


def substack_rss(substack_url: str) -> str:
    base = substack_url.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base
    return base + "/feed"


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_article_text(url: str, max_chars: int = 6000) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["nav", "footer", "script", "style", "aside", "header"]):
            tag.decompose()
        for selector in ["article", "main", ".post-content", ".entry-content", "body"]:
            el = soup.select_one(selector)
            if el:
                return el.get_text(separator="\n", strip=True)[:max_chars]
    except Exception as e:
        logger.warning(f"Failed to fetch article text from {url}: {e}")
    return ""


class RSSFetcher(BaseFetcher):
    def __init__(self, config: dict, feed_urls: list[str], source_name: str, max_items: int = 3, since_days: int = 1):
        super().__init__(config)
        self.feed_urls = feed_urls
        self.source_name = source_name
        self.max_items = max_items
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

    def fetch(self) -> list[ContentItem]:
        items = []
        for feed_url in self.feed_urls:
            items.extend(self._fetch_feed(feed_url))
        return items[:self.max_items]

    def _fetch_feed(self, feed_url: str) -> list[ContentItem]:
        logger.info(f"Fetching RSS: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            logger.error(f"Failed to parse feed {feed_url}: {e}")
            return []

        items = []
        for entry in feed.entries:
            pub_date = _parse_date(entry)
            if pub_date and pub_date < self.cutoff:
                continue

            url = entry.get("link", "")
            title = entry.get("title", "Untitled")
            author = entry.get("author", "")
            text = ""

            if hasattr(entry, "content") and entry.content:
                text = BeautifulSoup(entry.content[0].get("value", ""), "html.parser").get_text(separator="\n", strip=True)
            elif hasattr(entry, "summary"):
                text = BeautifulSoup(entry.summary, "html.parser").get_text(separator="\n", strip=True)

            if len(text) < 200 and url:
                time.sleep(0.5)
                text = fetch_article_text(url)

            items.append(ContentItem(
                title=title, url=url, source_name=self.source_name,
                source_type="rss", published_at=pub_date, author=author,
                text=self._truncate(text),
            ))
        return items


class PeopleFetcher:
    def __init__(self, config: dict):
        self.config = config
        self.max_items = config.get("briefing", {}).get("max_items_per_source", 3)

    def get_fetchers(self) -> list[RSSFetcher]:
        fetchers = []
        sources = self.config.get("sources", {})

        for person in sources.get("people", []):
            feed_urls = []
            name = person.get("name", "Unknown")
            handles = person.get("handles", {})

            if "substack" in handles:
                feed_urls.append(substack_rss(handles["substack"]))
            if "blog" in handles:
                feed = discover_rss_feed(handles["blog"])
                if feed:
                    feed_urls.append(feed)

            if feed_urls:
                fetchers.append(RSSFetcher(self.config, feed_urls, name, self.max_items))
            else:
                logger.warning(f"No RSS feed found for {name} — skipping")

        for feed_url in sources.get("rss_feeds", []):
            fetchers.append(RSSFetcher(self.config, [feed_url], feed_url, self.max_items))

        return fetchers
