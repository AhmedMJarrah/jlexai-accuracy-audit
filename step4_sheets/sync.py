"""
Pushes data into the spreadsheet. Two entry points:

- push_round: initial 100-sample - clears and rewrites a tab's full
  body. Idempotent by default (refuses to touch a tab that already
  has data, unless force=True). only_pools optionally scopes a push
  to specific pool(s), so a schema change in one pool doesn't force
  rewriting tabs that didn't change.
- append_batch: full-population release batches - appends rows to
  an EXISTING tab without touching what's already there.

Both tabs get rightToLeft set, since record data (names, notes) is
Arabic even though headers are English identifiers.
"""
import gspread

from step1_scaffold.logging_setup import get_logger
from step3_sampling.models import PoolName, SamplingRound
from step4_sheets.schema import headers_for, row_values
from step5_release.models import ReleaseBatch

logger = get_logger("sheets_sync")


def _ensure_tab(spreadsheet: gspread.Spreadsheet, pool: PoolName, rows_needed: int) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(pool.value)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=pool.value, rows=rows_needed + 10, cols=40)
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


def push_round(spreadsheet: gspread.Spreadsheet, round_: SamplingRound, force: bool = False,
                only_pools: set[str] | None = None) -> None:
    for pool_key, pool_sample in round_.pools.items():
        if only_pools is not None and pool_key not in only_pools:
            continue

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

        record_to_slot = {
            rid: slot for slot, rids in pool_sample.assignments.items() for rid in rids
        }

        rows = [headers]
        for rec in pool_sample.records:
            rows.append(row_values(pool, rec, record_to_slot.get(rec.record_id, ""), round_.round_id))

        ws.clear()
        ws.update(values=rows, range_name="A1")
        ws.freeze(rows=1)
        logger.info(f"{pool.value}: wrote {len(rows) - 1} row(s) for round {round_.round_id}")


def append_batch(spreadsheet: gspread.Spreadsheet, batch: ReleaseBatch) -> None:
    pool = batch.pool

    try:
        ws = spreadsheet.worksheet(pool.value)
    except gspread.exceptions.WorksheetNotFound:
        raise RuntimeError(
            f"Tab '{pool.value}' doesn't exist yet - run the initial "
            f"push_round for this pool before releasing full-population batches."
        )

    rows = [row_values(pool, rec, batch.user_slot, batch.batch_id) for rec in batch.records]
    ws.append_rows(rows, value_input_option="RAW")
    logger.info(f"{pool.value}: appended {len(rows)} row(s) from {batch.batch_id} for {batch.user_slot}")
