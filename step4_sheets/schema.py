"""
Column layout per pool tab. Core columns apply to every pool.
META pools get a frozen reference + editable correction column pair
per Phase 1 metadata field (entity/parent_ministry/Publication/etc.
deferred to a later phase). CHAIN/REFLECT stay single-column
placeholders until their rubrics are defined.

release_id holds either a SamplingRound.round_id (initial 100-sample
rows) or a ReleaseBatch.batch_id (full-population rows added later) -
either way, an immutable identifier for where that row's assignment
came from.
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


TYPE_SPECIFIC_HEADERS: dict[AuditKind, list[str]] = {
    AuditKind.META: _meta_headers(),
    AuditKind.CHAIN: ["chain_complete"],        # placeholder - finalize next
    AuditKind.REFLECT: ["reflection_correct"],  # placeholder - finalize next
}


def headers_for(pool: PoolName) -> list[str]:
    return CORE_HEADERS + TYPE_SPECIFIC_HEADERS[pool.audit_kind]


def writable_headers(pool: PoolName) -> set[str]:
    """Columns a volunteer (or the row-update layer) may write to.
    Excludes system-managed columns (record_id, pmk_id, leg_name,
    assigned_user, release_id, content_hash) and, for meta pools, the
    read-only ref_* reference columns."""
    base = {"status", "reviewer_notes"}
    if pool.audit_kind == AuditKind.META:
        base |= {h for h in TYPE_SPECIFIC_HEADERS[AuditKind.META] if h.startswith("corr_")}
    else:
        base |= set(TYPE_SPECIFIC_HEADERS[pool.audit_kind])
    return base


def _meta_value_cells(rec: SampledRecord) -> list[str]:
    cells = []
    for field in META_FIELDS:
        cells.append(rec.meta_fields.get(field, ""))
        cells.append("")  # correction - blank until a volunteer flags an issue
    return cells


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
    else:
        row += [""] * len(TYPE_SPECIFIC_HEADERS[pool.audit_kind])
    return row
