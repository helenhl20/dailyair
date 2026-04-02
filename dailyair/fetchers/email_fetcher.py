"""Email newsletter fetcher via IMAP."""

import logging
import re
from datetime import datetime, timedelta, timezone
from imap_tools import MailBox, AND, MailMessage
from bs4 import BeautifulSoup

from .base import BaseFetcher, ContentItem

logger = logging.getLogger(__name__)


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "img", "a"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _detect_sender_name(msg: MailMessage, newsletter_names: list[str]) -> str:
    from_str = (msg.from_ or "").lower()
    subject = (msg.subject or "").lower()
    for name in newsletter_names:
        if name.lower() in from_str or name.lower() in subject:
            return name
    match = re.match(r'"?([^"<]+)"?\s*<', msg.from_ or "")
    return match.group(1).strip() if match else msg.from_ or "Unknown Newsletter"


class EmailFetcher(BaseFetcher):
    def fetch(self) -> list[ContentItem]:
        email_cfg = self.config.get("email", {})
        if not email_cfg.get("enabled", False):
            return []

        server = email_cfg.get("imap_server", "imap.gmail.com")
        port = email_cfg.get("imap_port", 993)
        username = email_cfg.get("username", "")
        password = email_cfg.get("password", "")
        folder = email_cfg.get("folder", "INBOX")
        max_emails = email_cfg.get("max_emails", 30)
        since_days = email_cfg.get("since_days", 1)
        newsletter_names = self.config.get("sources", {}).get("email_newsletters", [])
        since_date = datetime.now(timezone.utc) - timedelta(days=since_days)
        items = []

        logger.info(f"Connecting to email: {username} @ {server}")
        try:
            with MailBox(server, port).login(username, password) as mailbox:
                mailbox.folder.set(folder)
                messages = list(mailbox.fetch(AND(date_gte=since_date.date()), limit=max_emails, reverse=True))

            for msg in messages:
                text = _html_to_text(msg.html) if msg.html else (msg.text or "")
                if len(text.strip()) < 100:
                    continue

                source_name = _detect_sender_name(msg, newsletter_names)
                pub_date = msg.date.replace(tzinfo=timezone.utc) if msg.date else None

                items.append(ContentItem(
                    title=msg.subject or "(no subject)",
                    url="", source_name=source_name, source_type="email",
                    published_at=pub_date, author=msg.from_,
                    text=self._truncate(text),
                ))
        except Exception as e:
            logger.error(f"Email fetch failed: {e}")

        logger.info(f"Fetched {len(items)} newsletter emails.")
        return items
