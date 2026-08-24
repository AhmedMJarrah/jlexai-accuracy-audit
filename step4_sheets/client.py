"""
Google Sheets client wrapper. Authenticates via a service account -
either a local JSON key file (local dev) or a raw JSON string from
settings (cloud deployment, where secrets are strings, not files).

open_spreadsheet() can open ANY spreadsheet by ID, not just the main
one - open_spreadsheets_for_settings() opens both the main and
reflect spreadsheets together, and spreadsheet_for_pool() routes a
given pool to the right one. This is the single place that decides
"which spreadsheet does this pool live in" - nothing else in the
codebase should hardcode that routing.
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


def open_spreadsheet(settings: Settings, spreadsheet_id: str | None = None) -> gspread.Spreadsheet:
    sid = spreadsheet_id or settings.google_spreadsheet_id
    if not sid:
        raise ValueError("No spreadsheet ID available - set GOOGLE_SPREADSHEET_ID, or pass one explicitly")

    client = get_client(settings)
    try:
        return client.open_by_key(sid)
    except gspread.exceptions.APIError as e:
        raise PermissionError(
            "Could not open the spreadsheet - most likely the service account's "
            "client_email has not been shared as Editor on it yet. Original error: "
            f"{e}"
        ) from e


def open_spreadsheets_for_settings(settings: Settings) -> dict:
    """Opens both spreadsheets this project uses. "reflect" is only
    included if GOOGLE_REFLECT_SPREADSHEET_ID is actually set -
    callers that need it should go through spreadsheet_for_pool(),
    which raises a clear error if it's missing rather than a
    confusing KeyError."""
    result = {"main": open_spreadsheet(settings)}
    if settings.google_reflect_spreadsheet_id:
        result["reflect"] = open_spreadsheet(settings, settings.google_reflect_spreadsheet_id)
    return result


def spreadsheet_for_pool(pool, spreadsheets: dict) -> gspread.Spreadsheet:
    """Routes a pool to the correct already-opened spreadsheet.
    Import is local to avoid a circular import between client.py and
    the sampling models."""
    from step3_sampling.models import AuditKind

    if pool.audit_kind == AuditKind.REFLECT:
        if "reflect" not in spreadsheets:
            raise ValueError(
                "Reflect spreadsheet not configured - set GOOGLE_REFLECT_SPREADSHEET_ID"
            )
        return spreadsheets["reflect"]
    return spreadsheets["main"]
