"""
Row-level read/write for a single volunteer's answer on a single
record. This is the core plumbing every audit portal needs to save
anything - locate the one row for a record_id inside its pool's
tab, and read/write only the columns a volunteer is allowed to
touch (see schema.writable_headers), never system-managed columns
or, for meta pools, the read-only ref_* reference columns.

Note: ws.batch_update() here (Worksheet method, value writes) is a
different call from spreadsheet.batch_update() used elsewhere for
formatting requests (Spreadsheet method, raw Sheets API requests) -
same name, different classes, different payload shape.
"""
from datetime import datetime, timezone

import gspread
from gspread.utils import rowcol_to_a1

from step1_scaffold.logging_setup import get_logger
from step3_sampling.models import PoolName
from step4_sheets.schema import headers_for, writable_headers

logger = get_logger("row_update")


def _header_index_map(pool: PoolName) -> dict[str, int]:
    return {h: i + 1 for i, h in enumerate(headers_for(pool))}


def locate_row(ws: gspread.Worksheet, record_id: str) -> int:
    cell = ws.find(record_id, in_column=1)
    if cell is None:
        raise ValueError(
            f"record_id '{record_id}' not found in tab '{ws.title}' - wrong pool, "
            f"or this record's batch hasn't been synced yet"
        )
    return cell.row


def read_row(spreadsheet: gspread.Spreadsheet, pool: PoolName, record_id: str) -> dict[str, str]:
    ws = spreadsheet.worksheet(pool.value)
    row_num = locate_row(ws, record_id)
    values = ws.row_values(row_num)
    headers = headers_for(pool)
    values += [""] * (len(headers) - len(values))  # pad short rows
    return dict(zip(headers, values))


def update_row(spreadsheet: gspread.Spreadsheet, pool: PoolName, record_id: str,
                field_updates: dict[str, str], status: str | None = None,
                notes: str | None = None) -> None:
    ws = spreadsheet.worksheet(pool.value)
    row_num = locate_row(ws, record_id)
    col_map = _header_index_map(pool)
    allowed = writable_headers(pool)

    updates: dict[str, str] = dict(field_updates)
    if status is not None:
        updates["status"] = status
    if notes is not None:
        updates["reviewer_notes"] = notes

    bad_keys = set(updates) - allowed
    if bad_keys:
        raise ValueError(
            f"Refusing to update non-writable column(s) {sorted(bad_keys)} for pool "
            f"'{pool.value}' - allowed: {sorted(allowed)}"
        )

    updates["last_updated"] = datetime.now(timezone.utc).isoformat()

    data = []
    for header, value in updates.items():
        col = col_map[header]
        a1 = rowcol_to_a1(row_num, col)
        data.append({"range": a1, "values": [[value]]})

    ws.batch_update(data)
    logger.info(f"{pool.value}: updated row {row_num} (record {record_id}) - fields: {sorted(updates)}")
