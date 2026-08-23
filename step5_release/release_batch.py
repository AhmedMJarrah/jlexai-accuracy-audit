"""
Admin CLI: releases the next N unassigned records in a pool to a
specific user, saves the batch immutably, and pushes it into the
spreadsheet in one step. Thin wrapper around
step5_release.service.create_batch - the admin portal UI uses the
same shared function, so CLI and UI can never drift apart on the
actual release semantics.
"""
import argparse

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger
from step2_ingestion.adapters import get_adapter
from step2_ingestion.models import LegType
from step3_sampling.models import PoolName
from step4_sheets.client import open_spreadsheet
from step4_sheets.sync import append_batch
from step5_release.service import create_batch

logger = get_logger("release_batch")


def run(pool_name: str, user_slot: str, count: int, law_filename: str, note: str) -> None:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    filename = law_filename or settings.active_law_filename
    if not filename:
        raise SystemExit("No --law-filename given and ACTIVE_LAW_FILENAME is not set in .env")

    pool = PoolName(pool_name)
    records = get_adapter(LegType.LAW).load(settings.data_dir / filename)

    batch = create_batch(pool, user_slot, count, records, settings, note)
    if batch is None:
        print(f"{pool.value}: nothing left to release - full population already assigned.")
        return

    try:
        spreadsheet = open_spreadsheet(settings)
        append_batch(spreadsheet, batch)
        print(f"\nReleased and synced {len(batch.records)} record(s) from '{pool.value}' to {user_slot}.")
    except Exception as e:
        path = settings.data_dir / "batches" / f"{batch.batch_id}.json"
        print(f"\nBatch saved locally ({path}) but the Sheets push failed: {e}")
        print(f"Retry with: python -m step5_release.push_batch --batch-file {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", required=True, choices=[p.value for p in PoolName])
    parser.add_argument("--user", required=True, help="e.g. user_slot_2")
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--law-filename", default=None,
                         help="Filename inside data/; defaults to ACTIVE_LAW_FILENAME in .env")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    run(args.pool, args.user, args.count, args.law_filename, args.note)
