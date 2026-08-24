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


def _fit_articles(articles, running_size: int, budget: int) -> tuple[list[dict], int, int]:
    """Adds articles one at a time, checking the actual size against
    the absolute cap before each one - not a relative "amendment
    budget", the real global limit. This is what makes a single
    amendment with many touched articles safe: individual articles
    stop being added once the running total approaches the cap,
    regardless of which amendment they belong to. Returns
    (included_articles, new_running_size, skipped_count)."""
    included = []
    skipped = 0
    for a in articles:
        piece = {"number": a.article_number, "title": a.title, "text": _truncate(a.text, budget)}
        piece_size = len(_json.dumps(piece, ensure_ascii=False)) + 1
        if running_size + piece_size > _MAX_REFLECT_CELL_CHARS:
            skipped += 1
            continue
        included.append(piece)
        running_size += piece_size
    return included, running_size, skipped


def extract_reflect_data(leg: Legislation) -> list[dict]:
    """Frozen snapshot of each amendment's instruction articles
    alongside the SPECIFIC reflected articles it actually touched.

    Reflected_Articles is a snapshot of the law's ENTIRE consolidated
    text at that point in the chain, not just what this amendment
    changed - including it in full would mean re-showing the whole
    law at every amendment. Instead, match on article_number: only
    the reflected articles whose number appears in this amendment's
    own instruction articles are included.

    Two-level hard guarantee, both checked against the real running
    size rather than an estimated budget:
    - article level: within one amendment, articles stop being added
      the moment the running total would exceed the cap - this is
      what keeps a single amendment with dozens of touched articles
      safe on its own, not just amendments relative to each other.
    - amendment level: amendments stop being added once one more
      would exceed the cap, with a note on how many were left out.
    Nothing is ever silently included past the limit - every
    omission (whole amendments or individual articles within one) is
    explicitly noted for the reviewer."""
    mods = leg.Mod_Legs
    if not mods:
        return []

    items: list[dict] = []
    running_size = 200  # rough allowance for the outer JSON array brackets/commas

    for i, mod in enumerate(mods):
        touched_numbers = {a.article_number for a in mod.Base_Articles}
        matching_reflected = [a for a in mod.Reflected_Articles if a.article_number in touched_numbers]

        entry_base_size = running_size + len(_json.dumps(
            {"amendment_name": mod.Leg_Name, "amendment_year": _fmt(mod.Year),
             "instruction_articles": [], "reflected_articles": []}, ensure_ascii=False
        ))

        instr_articles, size_after_instr, instr_skipped = _fit_articles(
            mod.Base_Articles, entry_base_size, _PER_ARTICLE_TEXT_BUDGET
        )
        refl_articles, size_after_refl, refl_skipped = _fit_articles(
            matching_reflected, size_after_instr, _PER_ARTICLE_TEXT_BUDGET
        )

        name = mod.Leg_Name
        total_skipped = instr_skipped + refl_skipped
        if total_skipped:
            name += f" (⚠️ {total_skipped} مادة إضافية ضمن هذا التعديل لم تُعرض بسبب حجم البيانات)"
            logger.warning(f"{leg.record_id}: {total_skipped} article(s) skipped within one amendment")

        entry = {
            "amendment_name": name,
            "amendment_year": _fmt(mod.Year),
            "instruction_articles": instr_articles,
            "reflected_articles": refl_articles,
        }
        entry_size = size_after_refl - running_size

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

    # The omission-marker entry itself isn't size-checked before being
    # appended above, so a small overshoot past the internal target is
    # expected and harmless - only warn if genuinely approaching the
    # real Sheets limit, not the conservative internal target.
    actual_size = len(_json.dumps(items, ensure_ascii=False))
    if actual_size > 48_000:
        logger.warning(f"{leg.record_id}: reflect_data at {actual_size} chars - close to the real 50,000 limit, needs a look")

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
