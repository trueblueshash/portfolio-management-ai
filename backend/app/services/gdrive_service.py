"""
Google Drive API service for listing and downloading files.
Reuses the same service account credentials as Google Docs.
The Drive folder must be shared with: portfolio-doc-sync@lightspeed-ai-platform.iam.gserviceaccount.com
"""
import logging
import os
import io
import re
from typing import Optional, List, Dict
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_drive_service():
    """Initialize Google Drive API service."""
    credentials_path = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if not credentials_path:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials not found: {credentials_path}")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=[
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/documents.readonly',
        ]
    )
    return build('drive', 'v3', credentials=credentials)


def extract_folder_id(url: str) -> str:
    """Extract folder ID from Google Drive URL."""
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    if '/' not in url and len(url) > 10:
        return url
    raise ValueError(f"Could not extract folder ID from: {url}")


def list_folder_files(folder_id: str) -> List[Dict]:
    """List all files in a Google Drive folder."""
    service = get_drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType, modifiedTime, size)",
        orderBy="modifiedTime desc",
    ).execute()
    return results.get('files', [])


def download_file(file_id: str, destination_path: str) -> str:
    """Download a file from Google Drive to a local path."""
    service = get_drive_service()
    os.makedirs(os.path.dirname(destination_path) or '.', exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    with open(destination_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    logger.info(f"Downloaded {file_id} to {destination_path}")
    return destination_path


def export_google_sheet_as_excel(file_id: str, destination_path: str) -> str:
    """Export a Google Sheet as .xlsx file."""
    service = get_drive_service()
    os.makedirs(os.path.dirname(destination_path) or '.', exist_ok=True)

    request = service.files().export_media(
        fileId=file_id,
        mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    with open(destination_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    logger.info(f"Exported Google Sheet {file_id} to {destination_path}")
    return destination_path


def categorize_files(files: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize Drive files by type."""
    categories = {
        "excel": [],     # MIS files
        "google_doc": [], # Board notes, meeting notes, portfolio updates
        "pdf": [],        # Board decks, reports
        "other": [],
    }

    for f in files:
        mime = f.get("mimeType", "")
        if mime in [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'application/vnd.google-apps.spreadsheet',
        ]:
            categories["excel"].append(f)
        elif mime == 'application/vnd.google-apps.document':
            categories["google_doc"].append(f)
        elif mime == 'application/pdf':
            categories["pdf"].append(f)
        else:
            categories["other"].append(f)

    return categories
