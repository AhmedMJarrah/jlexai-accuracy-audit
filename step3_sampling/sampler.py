"""
Draws reproducible random samples per pool. Each pool gets its own
derived seed (base seed + pool name) so pools aren't accidental
copies of each other, while the whole round stays reproducible from
one configured random_seed.
"""
import hashlib
import random

from step1_scaffold.logging_setup import get_logger
from step2_ingestion.models import Legislation
from step3_sampling.models import AuditKind, PoolName, SampledRecord

logger = get_logger("sampler")


def _pool_seed(base_seed: int, pool: PoolName) -> int:
    return base_seed + int(hashlib.sha256(pool.value.encode()).hexdigest(), 16) % 100_000


def build_population(records: list[Legislation], pool: PoolName) -> list[Legislation]:
    """meta/chain: every record of that leg_kind is eligible, including
    unamended ones - confirming an empty chain is correctly empty is
    itself a valid finding. reflect: only records that actually have
    amendments, since there is nothing to reflect-check otherwise."""
    same_kind = [r for r in records if r.leg_type is not None and r.leg_type.value == pool.leg_kind.value]
    if pool.audit_kind == AuditKind.REFLECT:
        return [r for r in same_kind if r.has_amendments]
    return same_kind


def draw_sample(population: list[Legislation], sample_size: int, pool: PoolName, base_seed: int) -> list[SampledRecord]:
    if not population:
        logger.warning(f"{pool.value}: empty population, nothing to sample")
        return []

    rng = random.Random(_pool_seed(base_seed, pool))
    n = min(sample_size, len(population))
    if n < sample_size:
        logger.warning(f"{pool.value}: population only {len(population)}, sampling all of it (< requested {sample_size})")

    chosen = rng.sample(population, n)
    return [
        SampledRecord(record_id=r.record_id, pmk_id=r.pmk_id, leg_name=r.Leg_Name, content_hash=r.content_hash)
        for r in chosen
    ]