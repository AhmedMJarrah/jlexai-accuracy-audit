"""
Column layout per pool tab. Core columns apply to every pool.

META pools get a frozen reference + editable correction column pair
per Phase 1 metadata field.

CHAIN pools get a frozen chain_data_json snapshot (system) plus a
single chain_correct verdict column (writable).

REFLECT pools get a frozen mod_legs_json snapshot (system - each
amendment's instruction text, the article text as it stood right
before that amendment, and the resulting consolidated text) plus a
single reflection_correct verdict column (writable). Judgment is
per-law (covering the whole amendment sequence), not per individual
amendment, to keep review workload manageable - notes cover where
any problem was found.

Notes reuse the shared reviewer_notes core column everywhere.

release_id holds either a SamplingRound.round_id or a
ReleaseBatch.batch_id - either way, an immutable identifier for
where that row's assignment came from.

writable_headers() is driven by an explicit per-audit-kind writable
set, never "everything in TYPE_SPECIFIC_HEADERS" - both chain and
reflect mix one system column with one writable column.
"""
import json

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
REFLECT_HEADERS = ["mod_legs_json", "reflection_correct"]

TYPE_SPECIFIC_HEADERS: dict[AuditKind, list[str]] = {
    AuditKind.META: _meta_headers(),
    AuditKind.CHAIN: CHAIN_HEADERS,
    AuditKind.REFLECT: REFLECT_HEADERS,
}

TYPE_SPECIFIC_WRITABLE: dict[AuditKind, set[str]] = {
    AuditKind.META: {h for h in _meta_headers() if h.startswith("corr_")},
    AuditKind.CHAIN: {"chain_correct"},
    AuditKind.REFLECT: {"reflection_correct"},
}


def headers_for(pool: PoolName) -> list[str]:
    return CORE_HEADERS + TYPE_SPECIFIC_HEADERS[pool.audit_kind]


def writable_headers(pool: PoolName) -> set[str]:
    """Columns a volunteer (or the row-update layer) may write to.
    Excludes system-managed columns (record_id, pmk_id, leg_name,
    assigned_user, release_id, content_hash) and, per pool, whatever
    is frozen/system rather than volunteer-facing (ref_* for meta,
    chain_data_json for chain, mod_legs_json for reflect)."""
    return {"status", "reviewer_notes"} | TYPE_SPECIFIC_WRITABLE[pool.audit_kind]


def _meta_value_cells(rec: SampledRecord) -> list[str]:
    cells = []
    for field in META_FIELDS:
        cells.append(rec.meta_fields.get(field, ""))
        cells.append("")  # correction - blank until a volunteer flags an issue
    return cells


def _chain_value_cells(rec: SampledRecord) -> list[str]:
    return [json.dumps(rec.chain_data, ensure_ascii=False), ""]


def _reflect_value_cells(rec: SampledRecord) -> list[str]:
    return [json.dumps(rec.reflect_data, ensure_ascii=False), ""]


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
    elif pool.audit_kind == AuditKind.REFLECT:
        row += _reflect_value_cells(rec)
    return row
