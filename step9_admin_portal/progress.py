"""
Aggregates progress across every pool tab currently synced in the
spreadsheet - per-pool status counts and a per-user breakdown within
each pool. Read-only. Pools that don't have a tab yet (not synced,
or bylaws not ready) report total=0 rather than erroring.
"""
import gspread

from step3_sampling.models import PoolName
from step4_sheets.schema import headers_for


def _read_pool_rows(spreadsheet: gspread.Spreadsheet, pool: PoolName) -> list[dict]:
    try:
        ws = spreadsheet.worksheet(pool.value)
    except gspread.exceptions.WorksheetNotFound:
        return []
    headers = headers_for(pool)
    all_values = ws.get_all_values()
    rows = []
    for row in all_values[1:]:
        row = row + [""] * (len(headers) - len(row))
        rows.append(dict(zip(headers, row)))
    return rows


def pool_progress(spreadsheet: gspread.Spreadsheet, pool: PoolName) -> dict:
    rows = _read_pool_rows(spreadsheet, pool)
    status_counts = {"not_started": 0, "in_progress": 0, "done": 0, "flagged": 0}
    per_user: dict[str, dict[str, int]] = {}

    for r in rows:
        status = r.get("status") or "not_started"
        status_counts[status] = status_counts.get(status, 0) + 1

        user = r.get("assigned_user") or "(غير مُسند)"
        per_user.setdefault(user, {"not_started": 0, "in_progress": 0, "done": 0, "flagged": 0, "total": 0})
        per_user[user][status] = per_user[user].get(status, 0) + 1
        per_user[user]["total"] += 1

    return {
        "pool": pool.value,
        "total": len(rows),
        "status_counts": status_counts,
        "per_user": per_user,
    }


def all_pools_progress(spreadsheet: gspread.Spreadsheet) -> list[dict]:
    return [pool_progress(spreadsheet, pool) for pool in PoolName]
