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
from step3_sampling.models import META_FIELDS, AuditKind, PoolName, SampledRecord

logger = get_logger("sampler")


def _pool_seed(base_seed: int, pool: PoolName) -> int:
    return base_seed + int(hashlib.sha256(pool.value.encode()).hexdigest(), 16) % 100_000


def _fmt(v) -> str:
    """Shared value formatter: None -> "", integer-valued floats
    (e.g. 1449.0) -> "1449" instead of an ugly trailing .0."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def extract_meta_fields(leg: Legislation) -> dict[str, str]:
    """Frozen snapshot of the Phase 1 metadata field values, as they
    stood when sampled - never re-read live later."""
    return {field: _fmt(getattr(leg, field, None)) for field in META_FIELDS}


def extract_chain_data(leg: Legislation) -> list[dict[str, str]]:
    """Frozen snapshot of the amendment chain: base law first, then
    each Mod_Leg in order (already oldest-to-newest per the source
    data)."""
    chain = [{
        "kind": "base",
        "leg_name": leg.Leg_Name,
        "leg_number": _fmt(leg.Leg_Number),
        "year": _fmt(leg.Year),
        "status": leg.Status or "",
    }]
    for mod in leg.Mod_Legs:
        chain.append({
            "kind": "amendment",
            "leg_name": mod.Leg_Name,
            "leg_number": mod.Leg_Number or "",
            "year": _fmt(mod.Year),
            "status": mod.Status or "",
        })
    return chain


def _flatten_articles(articles) -> str:
    if not articles:
        return ""
    return " | ".join(f"{a.title}: {a.text}" for a in articles)


def extract_reflect_data(leg: Legislation) -> list[dict[str, str]]:
    """Frozen snapshot of each amendment's instruction text alongside
    the resulting consolidated article text - one entry per Mod_Leg.
    Phase 1 judgment is per-amendment, not per-article, to keep the
    review workload manageable."""
    items = []
    for mod in leg.Mod_Legs:
        items.append({
            "amendment_name": mod.Leg_Name,
            "amendment_year": _fmt(mod.Year),
            "instruction_text": _flatten_articles(mod.Base_Articles),
            "reflected_text": _flatten_articles(mod.Reflected_Articles),
        })
    return items


def build_population(records: list[Legislation], pool: PoolName) -> list[Legislation]:
    """meta: every record of that leg_kind is eligible, including
    unamended ones - confirming an empty metadata set is itself
    checkable. chain/reflect: only records that actually have
    amendments, since there is nothing to check otherwise - an
    unamended law wastes a chain-review slot on a trivial confirm."""
    same_kind = [r for r in records if r.leg_type is not None and r.leg_type.value == pool.leg_kind.value]
    if pool.audit_kind in (AuditKind.CHAIN, AuditKind.REFLECT):
        return [r for r in same_kind if r.has_amendments]
    return same_kind


def to_sampled_record(leg: Legislation, pool: PoolName) -> SampledRecord:
    return SampledRecord(
        record_id=leg.record_id,
        pmk_id=leg.pmk_id,
        leg_name=leg.Leg_Name,
        content_hash=leg.content_hash,
        meta_fields=extract_meta_fields(leg) if pool.audit_kind == AuditKind.META else {},
        chain_data=extract_chain_data(leg) if pool.audit_kind == AuditKind.CHAIN else [],
        reflect_data=extract_reflect_data(leg) if pool.audit_kind == AuditKind.REFLECT else [],
    )


def draw_sample(population: list[Legislation], sample_size: int, pool: PoolName, base_seed: int) -> list[SampledRecord]:
    if not population:
        logger.warning(f"{pool.value}: empty population, nothing to sample")
        return []

    rng = random.Random(_pool_seed(base_seed, pool))
    n = min(sample_size, len(population))
    if n < sample_size:
        logger.warning(f"{pool.value}: population only {len(population)}, sampling all of it (< requested {sample_size})")

    chosen = rng.sample(population, n)
    return [to_sampled_record(r, pool) for r in chosen]
