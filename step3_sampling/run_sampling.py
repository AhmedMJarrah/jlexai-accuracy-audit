"""
Orchestrates a full sampling round: loads laws (bylaws once
available), builds all 6 pool populations, draws samples, assigns
users, saves an immutable snapshot, prints a summary.
"""
import argparse
import hashlib
from datetime import datetime, timezone

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger
from step2_ingestion.adapters import get_adapter
from step2_ingestion.models import LegType
from step3_sampling.assignment import assign_round_robin
from step3_sampling.models import PoolName, PoolSample, SamplingRound
from step3_sampling.sampler import build_population, draw_sample
from step3_sampling.snapshot import save_round

logger = get_logger("run_sampling")


def _fingerprint(records: list) -> str:
    joined = "|".join(sorted(f"{r.record_id}:{r.content_hash}" for r in records))
    return hashlib.sha256(joined.encode()).hexdigest()


def run(law_filename: str, round_id: str | None = None) -> None:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    law_path = settings.data_dir / law_filename
    if not law_path.exists():
        raise FileNotFoundError(f"Expected {law_path}")

    law_records = get_adapter(LegType.LAW).load(law_path)
    fingerprint = _fingerprint(law_records)

    round_id = round_id or datetime.now(timezone.utc).strftime("round_%Y%m%d_%H%M%S")
    pools: dict[str, PoolSample] = {}
    skipped: list[str] = []

    for pool in PoolName:
        if pool.leg_kind.value == "bylaw":
            skipped.append(pool.value)
            logger.warning(f"{pool.value}: skipped - bylaws data not available yet")
            continue

        population = build_population(law_records, pool)
        sample = draw_sample(population, settings.sample_size, pool, settings.random_seed)
        assignments = assign_round_robin(sample, settings.num_users, pool, settings.random_seed)

        pools[pool.value] = PoolSample(
            pool=pool,
            population_size=len(population),
            sample_size=len(sample),
            records=sample,
            assignments=assignments,
        )

    round_ = SamplingRound(
        round_id=round_id,
        source_filename=law_filename,
        source_fingerprint=fingerprint,
        num_users=settings.num_users,
        pools=pools,
        skipped_pools=skipped,
    )

    path = save_round(round_, settings.data_dir / "snapshots")

    print(f"\n--- Sampling round '{round_id}' ---")
    print(f"Saved to: {path}")
    for name, p in pools.items():
        counts = {slot: len(ids) for slot, ids in p.assignments.items()}
        print(f"  {name}: population={p.population_size}  sampled={p.sample_size}  per-user={counts}")
    if skipped:
        print(f"  Skipped (no data yet): {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--law-filename", required=True)
    parser.add_argument("--round-id", default=None)
    args = parser.parse_args()
    run(args.law_filename, args.round_id)