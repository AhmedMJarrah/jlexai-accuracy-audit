"""
Admin-controlled reassignment: moves a batch of NOT-STARTED records
in a pool from one user_slot to another, by updating the sheet's
assigned_user cell directly. Deliberately restricted to not_started
records only - reassigning in-progress or done work risks losing or
duplicating a volunteer's actual review.

Note: this updates the live sheet's assigned_user column, which is
the actual source of truth every portal reads from - it does NOT
touch the original SamplingRound/ReleaseBatch files, which remain an
immutable historical record of how the draw originally happened.
"""
import gspread
from gspread.utils import rowcol_to_a1

from step1_scaffold.logging_setup import get_logger
from step3_sampling.models import PoolName
from step4_sheets.schema import headers_for

logger = get_logger("reassign")


def reassign_not_started(spreadsheet: gspread.Spreadsheet, pool: PoolName,
                          from_slot: str, to_slot: str, count: int) -> list[str]:
    ws = spreadsheet.worksheet(pool.value)
    headers = headers_for(pool)
    col_map = {h: i + 1 for i, h in enumerate(headers)}
    assigned_col = col_map["assigned_user"]
    status_col = col_map["status"]
    record_id_col = col_map["record_id"]

    all_values = ws.get_all_values()
    eligible = []
    for row_num, row in enumerate(all_values[1:], start=2):
        row = row + [""] * (len(headers) - len(row))
        if row[assigned_col - 1] == from_slot and (row[status_col - 1] or "not_started") == "not_started":
            eligible.append((row_num, row[record_id_col - 1]))

    eligible.sort(key=lambda x: x[1])  # deterministic - by record_id
    to_move = eligible[:count]

    if not to_move:
        logger.warning(f"{pool.value}: no not_started records assigned to {from_slot} to reassign")
        return []

    data = [
        {"range": rowcol_to_a1(row_num, assigned_col), "values": [[to_slot]]}
        for row_num, _ in to_move
    ]
    ws.batch_update(data)

    moved_ids = [rid for _, rid in to_move]
    logger.info(f"{pool.value}: reassigned {len(moved_ids)} record(s) from {from_slot} to {to_slot}: {moved_ids}")
    return moved_ids
