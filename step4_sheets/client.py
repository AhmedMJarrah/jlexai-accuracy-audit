"""
Google Sheets client wrapper. Authenticates via a service account -
either a local JSON key file (local dev) or a raw JSON string from
settings (cloud deployment, where secrets are strings, not files).
The JSON-string form takes priority when both are configured. Fails
loudly and clearly if neither is usable, or if the service account
hasn't been granted access to the spreadsheet.
"""
import json

import gspread
from google.oauth2.service_account import Credentials

from step1_scaffold.config import Settings
from step1_scaffold.logging_setup import get_logger

logger = get_logger("sheets_client")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def get_client(settings: Settings) -> gspread.Client:
    if settings.google_service_account_json:
        info = json.loads(settings.google_service_account_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(creds)

    key_path = settings.google_service_account_file
    if not key_path.exists():
        raise FileNotFoundError(
            f"Service account key not found at {key_path} - place the JSON key "
            f"file there (gitignored) for local use, or set "
            f"GOOGLE_SERVICE_ACCOUNT_JSON for cloud deployment."
        )
    creds = Credentials.from_service_account_file(str(key_path), scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(settings: Settings) -> gspread.Spreadsheet:
    if not settings.google_spreadsheet_id:
        raise ValueError("GOOGLE_SPREADSHEET_ID is not set")

    client = get_client(settings)
    try:
        return client.open_by_key(settings.google_spreadsheet_id)
    except gspread.exceptions.APIError as e:
        raise PermissionError(
            "Could not open the spreadsheet - most likely the service account's "
            "client_email has not been shared as Editor on it yet. Original error: "
            f"{e}"
        ) from e
