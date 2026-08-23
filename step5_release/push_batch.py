"""
Retry helper: pushes an already-saved batch file into its pool's
tab. Use this if release_batch succeeded locally but the Sheets
push failed (network, auth) - never re-run release_batch itself for
a retry, since it would try to release a NEW batch, not resend this one.
"""
import argparse
from pathlib import Path

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger
from step4_sheets.client import open_spreadsheet
from step4_sheets.sync import append_batch
from step5_release.models import ReleaseBatch

logger = get_logger("push_batch")


def run(batch_file: str) -> None:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    batch = ReleaseBatch.model_validate_json(Path(batch_file).read_text(encoding="utf-8"))
    spreadsheet = open_spreadsheet(settings)
    append_batch(spreadsheet, batch)
    print(f"\nPushed batch '{batch.batch_id}' ({len(batch.records)} records) to {batch.user_slot}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-file", required=True)
    args = parser.parse_args()
    run(args.batch_file)
