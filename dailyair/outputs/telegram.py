"""
Telegram output — sends the daily briefing text and MP3 audio to a Telegram chat.

Setup (one-time):
  1. Message @BotFather on Telegram → /newbot → copy the token
  2. Start a chat with your new bot, then visit:
       https://api.telegram.org/bot<TOKEN>/getUpdates
     and copy your numeric chat_id from the response.
  3. Add both to config.yaml under the `telegram:` key.
"""

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Telegram caps plain messages at 4096 chars
_MAX_MSG_LEN = 4000


class TelegramOutput:
    def __init__(self, config: dict):
        tg = config.get("telegram", {})
        self.bot_token  = tg.get("bot_token", "")
        self.chat_id    = str(tg.get("chat_id", ""))
        self.send_text  = tg.get("send_text", True)
        self.send_audio = tg.get("send_audio", True)
        self._base      = f"https://api.telegram.org/bot{self.bot_token}"

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def send(self, briefing_script: str, audio_path: Path | None = None) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.error(
                "Telegram: bot_token and chat_id must be set in config.yaml. "
                "See the 'telegram' section for setup instructions."
            )
            return False

        ok = True

        if self.send_text:
            ok &= self._send_text(briefing_script)

        if self.send_audio:
            if audio_path and audio_path.exists():
                ok &= self._send_audio(audio_path)
            else:
                logger.warning(
                    "Telegram: send_audio is enabled but no MP3 was found. "
                    "Make sure tts.enabled is true and a non-system provider is configured."
                )

        return ok

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self._base}/{endpoint}"
        resp = requests.post(url, timeout=120, **kwargs)
        if not resp.ok:
            logger.error(f"Telegram {endpoint} failed ({resp.status_code}): {resp.text[:300]}")
        return resp

    def _send_text(self, text: str) -> bool:
        """Send the briefing as one or more messages (respects the 4 000-char limit)."""
        chunks = [text[i : i + _MAX_MSG_LEN] for i in range(0, len(text), _MAX_MSG_LEN)]
        for chunk in chunks:
            resp = self._post(
                "sendMessage",
                json={"chat_id": self.chat_id, "text": chunk},
            )
            if not resp.ok:
                return False
        return True

    def _send_audio(self, audio_path: Path) -> bool:
        """Upload the MP3 so it appears as a playable audio file in Telegram."""
        logger.info(f"Telegram: uploading {audio_path.name} …")
        with audio_path.open("rb") as fh:
            resp = self._post(
                "sendAudio",
                data={
                    "chat_id":   self.chat_id,
                    "title":     "DailyAir Morning Briefing",
                    "performer": "DailyAir",
                },
                files={"audio": (audio_path.name, fh, "audio/mpeg")},
            )
        return resp.ok
