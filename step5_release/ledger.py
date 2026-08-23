"""
Reconstructs the full per-pool assignment ledger by folding together
the original SamplingRound(s) and every ReleaseBatch since. This is
a read-only derivation over immutable event files - there is no
separate mutable "current state" file to keep in sync or corrupt.
"""
from pathlib import Path

from step3_sampling.models import PoolName
from step3_sampling.snapshot import load_round
from step5_release.models import ReleaseBatch


def load_all_batches(batches_dir: Path) -> list[ReleaseBatch]:
    batches = []
    for path in sorted(batches_dir.glob("batch_*.json")):
        batches.append(ReleaseBatch.model_validate_json(path.read_text(encoding="utf-8")))
    return batches


def assigned_record_ids(pool: PoolName, snapshots_dir: Path, batches_dir: Path) -> dict[str, str]:
    """record_id -> user_slot for everything already assigned in this
    pool, from the original sample round(s) plus every batch since."""
    assigned: dict[str, str] = {}

    for path in sorted(snapshots_dir.glob("round_*.json")):
        round_ = load_round(path)
        pool_sample = round_.pools.get(pool.value)
        if not pool_sample:
            continue
        for slot, record_ids in pool_sample.assignments.items():
            for rid in record_ids:
                assigned[rid] = slot

    for batch in load_all_batches(batches_dir):
        if batch.pool != pool:
            continue
        for rec in batch.records:
            assigned[rec.record_id] = batch.user_slot

    return assigned
