"""
Pushes a SamplingRound into the spreadsheet: one tab per pool, header
row + one row per sampled record with its assignment. Idempotent by
default - refuses to push into a tab that already has data rows,
unless force clears it first. Also sets each tab to right-to-left,
since the record data (names, notes) is Arabic even though headers
are English identifiers.
"""
import gspread

from step1_scaffold.logging_setup import get_logger
from step3_sampling.models import PoolName, SamplingRound
from step4_sheets.schema import DEFAULT_STATUS, headers_for

logger = get_logger("sheets_sync")


def _ensure_tab(spreadsheet: gspread.Spreadsheet, pool: PoolName, rows_needed: int) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(pool.value)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=pool.value, rows=rows_needed + 10, cols=20)
        logger.info(f"Created tab: {pool.value}")

    spreadsheet.batch_update({
        "requests": [{
            "updateSheetProperties": {
                "properties": {"sheetId": ws.id, "rightToLeft": True},
                "fields": "rightToLeft",
            }
        }]
    })
    return ws


def _existing_data_row_count(ws: gspread.Worksheet) -> int:
    values = ws.get_all_values()
    return max(0, len(values) - 1)  # minus header row, if any


def push_round(spreadsheet: gspread.Spreadsheet, round_: SamplingRound, force: bool = False) -> None:
    for pool_key, pool_sample in round_.pools.items():
        pool = PoolName(pool_key)
        headers = headers_for(pool)
        ws = _ensure_tab(spreadsheet, pool, len(pool_sample.records))

        existing = _existing_data_row_count(ws)
        if existing > 0 and not force:
            logger.warning(
                f"{pool.value}: already has {existing} data row(s) - skipping "
                f"(pass force=True to clear and rewrite)"
            )
            continue

        # invert assignments: record_id -> user_slot
        record_to_slot = {
            rid: slot for slot, rids in pool_sample.assignments.items() for rid in rids
        }

        rows = [headers]
        for rec in pool_sample.records:
            row = [
                rec.record_id,
                rec.pmk_id or "",
                rec.leg_name,
                record_to_slot.get(rec.record_id, ""),
                DEFAULT_STATUS,
                "",  # reviewer_notes
                "",  # last_updated
                round_.round_id,
                rec.content_hash,
            ]
            row += [""] * (len(headers) - len(row))
            rows.append(row)

        ws.clear()
        ws.update(values=rows, range_name="A1")
        ws.freeze(rows=1)
        logger.info(f"{pool.value}: wrote {len(rows) - 1} row(s) for round {round_.round_id}")
