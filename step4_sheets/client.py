"""
Google Sheets client wrapper. Authenticates via a service account
JSON key and opens the target spreadsheet by ID. Fails loudly and
clearly if the key file is missing or the service account hasn't
been granted access - both are common first-run mistakes.
"""
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
    key_path = settings.google_service_account_file
    if not key_path.exists():
        raise FileNotFoundError(
            f"Service account key not found at {key_path} - place the JSON key "
            f"file there (gitignored) before running Sheets sync."
        )
    creds = Credentials.from_service_account_file(str(key_path), scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(settings: Settings) -> gspread.Spreadsheet:
    if not settings.google_spreadsheet_id:
        raise ValueError("GOOGLE_SPREADSHEET_ID is not set in .env")

    client = get_client(settings)
    try:
        return client.open_by_key(settings.google_spreadsheet_id)
    except gspread.exceptions.APIError as e:
        raise PermissionError(
            "Could not open the spreadsheet - most likely the service account's "
            "client_email has not been shared as Editor on it yet. Original error: "
            f"{e}"
        ) from e
