"""
Assignment queries for a logged-in volunteer: everything currently
assigned to their user_slot in a given pool, with status, so a
portal can show a worklist and a simple progress count. Reads raw
values and zips against headers_for(pool) manually - deliberately
not gspread's get_all_records(), which chokes on the sheet's extra
blank trailing columns and auto-coerces numeric-looking strings.

Pool-agnostic - shared across all portals, not specific to any one
audit type.
"""
import gspread

from step3_sampling.models import PoolName
from step4_sheets.schema import headers_for


def list_assigned(spreadsheet: gspread.Spreadsheet, pool: PoolName, user_slot: str) -> list[dict]:
    ws = spreadsheet.worksheet(pool.value)
    headers = headers_for(pool)
    all_values = ws.get_all_values()

    records = []
    for row in all_values[1:]:  # skip header row
        row = row + [""] * (len(headers) - len(row))
        rec = dict(zip(headers, row))
        if rec.get("assigned_user") == user_slot:
            records.append(rec)
    return records


def progress_summary(assigned: list[dict]) -> dict[str, int]:
    summary = {"total": len(assigned), "not_started": 0, "in_progress": 0, "done": 0, "flagged": 0}
    for r in assigned:
        status = r.get("status") or "not_started"
        summary[status] = summary.get(status, 0) + 1
    return summary
