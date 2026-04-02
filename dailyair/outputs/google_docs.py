"""Google Docs output adapter."""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]


def _get_credentials(credentials_file: str):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    token_path = Path("token.json")
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    return creds


def _find_or_create_folder(drive_service, folder_name: str) -> str:
    results = drive_service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    folder = drive_service.files().create(
        body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}, fields="id"
    ).execute()
    return folder["id"]


class GoogleDocsOutput:
    def __init__(self, config: dict):
        self.config = config
        self.gdocs_cfg = config.get("output", {}).get("google_docs", {})

    def create_doc(self, briefing_script: str, summaries: list[dict]) -> str:
        if not self.gdocs_cfg.get("enabled", False):
            return ""
        try:
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError("Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

        creds = _get_credentials(self.gdocs_cfg.get("credentials_file", "credentials.json"))
        docs_service = build("docs", "v1", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        date_str = datetime.now().strftime("%A, %B %d, %Y")
        doc = docs_service.documents().create(body={"title": f"DailyAir Briefing — {date_str}"}).execute()
        doc_id = doc["documentId"]

        content = f"DailyAir Morning Briefing — {date_str}\n\n{briefing_script}\n\n" + "─" * 40 + "\n\nDetailed Summaries\n\n"
        for s in summaries:
            content += f"{s['title']}\nSource: {s['source_name']} | {s.get('url', '')}\n\n{s['summary']}\n"
            if s.get("quote"):
                content += f'"{s["quote"]}"\n'
            content += "\n"

        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        ).execute()

        folder_id = _find_or_create_folder(drive_service, self.gdocs_cfg.get("folder_name", "DailyAir Briefings"))
        drive_service.files().update(fileId=doc_id, addParents=folder_id, removeParents="root", fields="id, parents").execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        logger.info(f"Google Doc created: {doc_url}")
        return doc_url
