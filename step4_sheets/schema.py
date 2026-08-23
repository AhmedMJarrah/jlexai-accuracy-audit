"""
Column layout per pool tab. Core columns apply to every pool.

META pools get a frozen reference + editable correction column pair
per Phase 1 metadata field.

CHAIN pools get a frozen chain_data_json snapshot (system - never
volunteer-writable) plus a single chain_correct verdict column
(writable). Notes reuse the shared reviewer_notes core column.

REFLECT stays a single-column placeholder until its rubric is
defined.

release_id holds either a SamplingRound.round_id (initial 100-sample
rows) or a ReleaseBatch.batch_id (full-population rows added later).

writable_headers() is driven by an explicit per-audit-kind writable
set, not "everything in TYPE_SPECIFIC_HEADERS" - chain's mix of one
system column and one writable column is exactly why that assumption
would have been wrong.
"""
from step3_sampling.models import META_FIELDS, AuditKind, PoolName, SampledRecord

CORE_HEADERS = [
    "record_id",
    "pmk_id",
    "leg_name",
    "assigned_user",
    "status",
    "reviewer_notes",
    "last_updated",
    "release_id",
    "content_hash",
]

DEFAULT_STATUS = "not_started"


def _meta_headers() -> list[str]:
    headers = []
    for field in META_FIELDS:
        headers.append(f"ref_{field}")
        headers.append(f"corr_{field}")
    return headers


CHAIN_HEADERS = ["chain_data_json", "chain_correct"]

TYPE_SPECIFIC_HEADERS: dict[AuditKind, list[str]] = {
    AuditKind.META: _meta_headers(),
    AuditKind.CHAIN: CHAIN_HEADERS,
    AuditKind.REFLECT: ["reflection_correct"],  # placeholder - finalize next
}

TYPE_SPECIFIC_WRITABLE: dict[AuditKind, set[str]] = {
    AuditKind.META: {h for h in _meta_headers() if h.startswith("corr_")},
    AuditKind.CHAIN: {"chain_correct"},
    AuditKind.REFLECT: {"reflection_correct"},  # placeholder - finalize next
}


def headers_for(pool: PoolName) -> list[str]:
    return CORE_HEADERS + TYPE_SPECIFIC_HEADERS[pool.audit_kind]


def writable_headers(pool: PoolName) -> set[str]:
    """Columns a volunteer (or the row-update layer) may write to.
    Excludes system-managed columns (record_id, pmk_id, leg_name,
    assigned_user, release_id, content_hash) and, per pool, whatever
    is frozen/system rather than volunteer-facing (ref_* for meta,
    chain_data_json for chain)."""
    return {"status", "reviewer_notes"} | TYPE_SPECIFIC_WRITABLE[pool.audit_kind]


def _meta_value_cells(rec: SampledRecord) -> list[str]:
    cells = []
    for field in META_FIELDS:
        cells.append(rec.meta_fields.get(field, ""))
        cells.append("")  # correction - blank until a volunteer flags an issue
    return cells


def _chain_value_cells(rec: SampledRecord) -> list[str]:
    import json
    return [json.dumps(rec.chain_data, ensure_ascii=False), ""]  # chain_data_json, chain_correct (blank)


def row_values(pool: PoolName, rec: SampledRecord, assigned_user: str, release_id: str,
                status: str = DEFAULT_STATUS) -> list[str]:
    row = [
        rec.record_id,
        rec.pmk_id or "",
        rec.leg_name,
        assigned_user,
        status,
        "",  # reviewer_notes
        "",  # last_updated
        release_id,
        rec.content_hash,
    ]
    if pool.audit_kind == AuditKind.META:
        row += _meta_value_cells(rec)
    elif pool.audit_kind == AuditKind.CHAIN:
        row += _chain_value_cells(rec)
    else:
        row += [""] * len(TYPE_SPECIFIC_HEADERS[pool.audit_kind])
    return row
