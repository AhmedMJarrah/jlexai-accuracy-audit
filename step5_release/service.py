"""
Core release-batch logic, shared between the CLI
(step5_release.release_batch) and the admin portal UI - both need
identical semantics: pull the next N unassigned records
deterministically, save an immutable batch file, and hand back the
batch for the caller to push to the sheet however fits that
caller's interface (CLI prints a retry command on failure; the UI
shows a Streamlit error).
"""
from datetime import datetime, timezone
from pathlib import Path

from step1_scaffold.config import Settings
from step1_scaffold.logging_setup import get_logger
from step2_ingestion.models import Legislation
from step3_sampling.models import LegKind, PoolName
from step3_sampling.sampler import build_population, to_sampled_record
from step5_release.ledger import assigned_record_ids
from step5_release.models import ReleaseBatch

logger = get_logger("release_service")


def next_batch_records(pool: PoolName, count: int, records: list[Legislation],
                        snapshots_dir: Path, batches_dir: Path) -> list[Legislation]:
    population = build_population(records, pool)
    already = assigned_record_ids(pool, snapshots_dir, batches_dir)
    remaining = sorted(
        (r for r in population if r.record_id not in already),
        key=lambda r: r.record_id,
    )
    return remaining[:count]


def create_batch(pool: PoolName, user_slot: str, count: int, records: list[Legislation],
                  settings: Settings, note: str = "") -> ReleaseBatch | None:
    """Returns None if nothing remains to release - callers should
    treat that as a normal, non-error outcome."""
    if pool.leg_kind == LegKind.BYLAW:
        raise NotImplementedError(
            "Bylaw full-population release not available yet - bylaws adapter not implemented."
        )

    snapshots_dir = settings.data_dir / "snapshots"
    batches_dir = settings.data_dir / "batches"

    to_release = next_batch_records(pool, count, records, snapshots_dir, batches_dir)
    if not to_release:
        return None

    batch_id = datetime.now(timezone.utc).strftime(f"batch_{pool.value}_%Y%m%d_%H%M%S")
    sampled = [to_sampled_record(r, pool) for r in to_release]
    batch = ReleaseBatch(batch_id=batch_id, pool=pool, user_slot=user_slot, records=sampled, note=note)

    path = batches_dir / f"{batch_id}.json"
    path.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"Saved batch {batch_id} ({len(sampled)} records) to {path}")
    return batch
