"""
Admin CLI: releases the next N unassigned records in a pool to a
specific user, saves the batch immutably, and pushes it into the
spreadsheet in one step. Pulls deterministically (sorted by
record_id) from whatever the ledger says is still unassigned - not
randomized, since this is population coverage, not sampling.

If the spreadsheet push fails (network, auth), the batch file is
already saved and the ledger already treats those records as
assigned - re-running release will NOT re-release them. Retry the
push alone with step5_release.push_batch --batch-file <path>.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger
from step2_ingestion.adapters import get_adapter
from step2_ingestion.models import LegType, Legislation
from step3_sampling.models import LegKind, PoolName
from step3_sampling.sampler import build_population, to_sampled_record
from step4_sheets.client import open_spreadsheet
from step4_sheets.sync import append_batch
from step5_release.ledger import assigned_record_ids
from step5_release.models import ReleaseBatch

logger = get_logger("release_batch")


def next_batch_records(pool: PoolName, count: int, records: list[Legislation],
                        snapshots_dir: Path, batches_dir: Path) -> list[Legislation]:
    population = build_population(records, pool)
    already = assigned_record_ids(pool, snapshots_dir, batches_dir)
    remaining = sorted(
        (r for r in population if r.record_id not in already),
        key=lambda r: r.record_id,
    )
    return remaining[:count]


def run(pool_name: str, user_slot: str, count: int, law_filename: str, note: str) -> None:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    pool = PoolName(pool_name)
    if pool.leg_kind == LegKind.BYLAW:
        raise NotImplementedError(
            "Bylaw full-population release not available yet - bylaws adapter not implemented."
        )

    records = get_adapter(LegType.LAW).load(settings.data_dir / law_filename)

    snapshots_dir = settings.data_dir / "snapshots"
    batches_dir = settings.data_dir / "batches"

    to_release = next_batch_records(pool, count, records, snapshots_dir, batches_dir)
    if not to_release:
        print(f"{pool.value}: nothing left to release - full population already assigned.")
        return
    if len(to_release) < count:
        logger.warning(f"{pool.value}: only {len(to_release)} unassigned record(s) remain, releasing all of them")

    batch_id = datetime.now(timezone.utc).strftime(f"batch_{pool.value}_%Y%m%d_%H%M%S")
    sampled = [to_sampled_record(r, pool) for r in to_release]
    batch = ReleaseBatch(batch_id=batch_id, pool=pool, user_slot=user_slot, records=sampled, note=note)

    path = batches_dir / f"{batch_id}.json"
    path.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"Saved batch {batch_id} ({len(sampled)} records) to {path}")

    try:
        spreadsheet = open_spreadsheet(settings)
        append_batch(spreadsheet, batch)
        print(f"\nReleased and synced {len(sampled)} record(s) from '{pool.value}' to {user_slot}.")
    except Exception as e:
        print(f"\nBatch saved locally ({path}) but the Sheets push failed: {e}")
        print(f"Retry with: python -m step5_release.push_batch --batch-file {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", required=True, choices=[p.value for p in PoolName])
    parser.add_argument("--user", required=True, help="e.g. user_slot_2")
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--law-filename", required=True)
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    run(args.pool, args.user, args.count, args.law_filename, args.note)
