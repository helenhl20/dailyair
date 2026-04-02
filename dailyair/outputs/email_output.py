"""Email output adapter — sends the briefing via SMTP."""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _build_html(briefing_script: str, summaries: list[dict]) -> str:
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    items_html = "".join(
        f'<div style="margin-bottom:24px;border-bottom:1px solid #eee;padding-bottom:16px;">'
        f'<h3 style="margin:0 0 4px;"><a href="{s.get("url","#")}">{s["title"]}</a></h3>'
        f'<p style="color:#888;font-size:12px;margin:0 0 8px;">{s["source_name"]} • {s.get("source_type","").upper()}</p>'
        f'<p style="margin:0 0 8px;">{s["summary"]}</p>'
        + (f'<blockquote style="border-left:3px solid #ccc;padding-left:12px;color:#555;">{s["quote"]}</blockquote>' if s.get("quote") else "")
        + '</div>'
        for s in summaries
    )
    return f"""<html><body style="font-family:Georgia,serif;max-width:680px;margin:auto;padding:20px;color:#222;">
        <h1 style="font-size:28px;border-bottom:2px solid #000;padding-bottom:8px;">☀️ DailyAir Morning Briefing</h1>
        <p style="color:#888;">{date_str}</p>
        <div style="background:#f9f9f9;border-left:4px solid #000;padding:16px;margin:20px 0;font-style:italic;">
            {briefing_script.replace(chr(10), "<br>")}
        </div>
        <h2>Detailed Summaries</h2>{items_html}
        <hr><p style="font-size:11px;color:#aaa;">Sent by <a href="https://github.com/yourusername/dailyair">DailyAir</a></p>
    </body></html>"""


class EmailOutput:
    def __init__(self, config: dict):
        self.config = config
        self.email_cfg = config.get("output", {}).get("email", {})

    def send(self, briefing_script: str, summaries: list[dict]) -> bool:
        if not self.email_cfg.get("enabled", False):
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"☀️ DailyAir Briefing — {datetime.now().strftime('%B %d, %Y')}"
        msg["From"] = f"DailyAir <{self.email_cfg.get('from_address', '')}>"
        msg["To"] = self.email_cfg.get("to_address", "")
        msg.attach(MIMEText(briefing_script, "plain"))
        msg.attach(MIMEText(_build_html(briefing_script, summaries), "html"))

        try:
            with smtplib.SMTP(self.email_cfg.get("smtp_server", "smtp.gmail.com"), self.email_cfg.get("smtp_port", 587)) as server:
                server.starttls()
                server.login(msg["From"].split("<")[1].rstrip(">"), self.email_cfg.get("password", ""))
                server.sendmail(msg["From"], msg["To"], msg.as_string())
            logger.info(f"Briefing email sent to {msg['To']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
