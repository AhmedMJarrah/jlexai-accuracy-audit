"""
Draws reproducible random samples per pool. Each pool gets its own
derived seed (base seed + pool name) so pools aren't accidental
copies of each other, while the whole round stays reproducible from
one configured random_seed.
"""
import hashlib
import json as _json
import random

from step1_scaffold.logging_setup import get_logger
from step2_ingestion.models import Legislation
from step3_sampling.models import META_FIELDS, AuditKind, PoolName, SampledRecord

logger = get_logger("sampler")

# Google Sheets hard-caps a single cell at 50,000 characters. Stay
# safely under that with margin for JSON structural overhead.
_MAX_REFLECT_CELL_CHARS = 42_000


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


def _truncate(text: str, max_len: int) -> str:
    """The marker itself takes up space - the returned string
    (content + marker together) must never exceed max_len, or the
    budget calculation upstream silently loses its guarantee."""
    if len(text) <= max_len:
        return text
    original_len = len(text)
    marker = f" …[تم اقتصاص النص، الطول الأصلي {original_len} حرف]"
    content_budget = max(0, max_len - len(marker))
    return text[:content_budget] + marker


_PER_ARTICLE_TEXT_BUDGET = 1500  # generous - several real paragraphs per article


def _build_reflect_entry(mod, matching_reflected) -> dict:
    return {
        "amendment_name": mod.Leg_Name,
        "amendment_year": _fmt(mod.Year),
        "instruction_articles": [
            {
                "number": a.article_number,
                "title": a.title,
                "text": _truncate(a.text, _PER_ARTICLE_TEXT_BUDGET),
            }
            for a in mod.Base_Articles
        ],
        "reflected_articles": [
            {
                "number": a.article_number,
                "title": a.title,
                "text": _truncate(a.text, _PER_ARTICLE_TEXT_BUDGET),
            }
            for a in matching_reflected
        ],
    }


def extract_reflect_data(leg: Legislation) -> list[dict]:
    """Frozen snapshot of each amendment's instruction articles
    alongside the SPECIFIC reflected articles it actually touched.

    Reflected_Articles is a snapshot of the law's ENTIRE consolidated
    text at that point in the chain, not just what this amendment
    changed - including it in full would mean re-showing the whole
    law at every amendment. Instead, match on article_number: only
    the reflected articles whose number appears in this amendment's
    own instruction articles are included - the actual before/after
    pair a reviewer needs.

    Every included article gets a fixed, comfortable text budget
    (not squeezed thinner as amendment count grows). Amendments are
    added one at a time, checking the real running size before each
    addition - the moment one more would exceed the Sheets cell
    limit, building stops and a note records how many were left out.
    This is a hard guarantee, not an estimate: the result can never
    exceed the cap, and nothing is ever silently mangled into an
    unreadable fragment to make room for more."""
    mods = leg.Mod_Legs
    if not mods:
        return []

    items: list[dict] = []
    running_size = 200  # rough allowance for the outer JSON array brackets/commas

    for i, mod in enumerate(mods):
        touched_numbers = {a.article_number for a in mod.Base_Articles}
        matching_reflected = [a for a in mod.Reflected_Articles if a.article_number in touched_numbers]

        entry = _build_reflect_entry(mod, matching_reflected)
        entry_size = len(_json.dumps(entry, ensure_ascii=False)) + 1  # +1 for the joining comma

        if items and running_size + entry_size > _MAX_REFLECT_CELL_CHARS:
            omitted = len(mods) - i
            items.append({
                "amendment_name": f"⚠️ تم حذف {omitted} تعديل إضافي من هذا العرض بسبب حجم البيانات",
                "amendment_year": "",
                "instruction_articles": [],
                "reflected_articles": [],
            })
            logger.warning(f"{leg.record_id}: omitted {omitted} amendment(s) from reflect_data due to cell size")
            break

        items.append(entry)
        running_size += entry_size

    actual_size = len(_json.dumps(items, ensure_ascii=False))
    if actual_size > _MAX_REFLECT_CELL_CHARS:
        logger.warning(
            f"{leg.record_id}: reflect_data still {actual_size} chars even with the omission "
            f"guard - a single amendment's touched articles alone exceed the cell limit"
        )

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
