"""
Manual CLI test for row-level read/write - confirms locate_row,
read_row, and update_row work against the real sheet before any
portal is built on top of them.
"""
import argparse

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger
from step3_sampling.models import PoolName
from step4_sheets.client import open_spreadsheet
from step7_updates.row_update import read_row, update_row

logger = get_logger("update_check")


def run(pool_name: str, record_id: str, status: str | None, notes: str | None, fields: list[str] | None) -> None:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    pool = PoolName(pool_name)
    spreadsheet = open_spreadsheet(settings)

    print("--- before ---")
    print(read_row(spreadsheet, pool, record_id))

    field_updates = {}
    for f in fields or []:
        key, _, value = f.partition("=")
        field_updates[key] = value

    if field_updates or status or notes:
        update_row(spreadsheet, pool, record_id, field_updates, status=status, notes=notes)
        print("\n--- after ---")
        print(read_row(spreadsheet, pool, record_id))
    else:
        print("\nNo changes requested - read-only check.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", required=True, choices=[p.value for p in PoolName])
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--status", default=None)
    parser.add_argument("--notes", default=None)
    parser.add_argument("--field", dest="fields", action="append", help="header=value, repeatable, e.g. corr_Year=1960")
    args = parser.parse_args()
    run(args.pool, args.record_id, args.status, args.notes, args.fields)
