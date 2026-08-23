"""
Column layout per pool tab. Core columns apply to every pool;
type-specific columns are provisional placeholders until the exact
audit rubric for meta/chain/reflect is finalized - changing these
later means re-running Step 4 sync, not a schema migration, since
sync always rewrites the full sheet body.
"""
from step3_sampling.models import AuditKind, PoolName

CORE_HEADERS = [
    "record_id",
    "pmk_id",
    "leg_name",
    "assigned_user",
    "status",
    "reviewer_notes",
    "last_updated",
    "round_id",
    "content_hash",
]

TYPE_SPECIFIC_HEADERS: dict[AuditKind, list[str]] = {
    AuditKind.META: ["field_discrepancies"],       # placeholder - finalize rubric
    AuditKind.CHAIN: ["chain_complete"],            # placeholder - finalize rubric
    AuditKind.REFLECT: ["reflection_correct"],      # placeholder - finalize rubric
}

DEFAULT_STATUS = "not_started"


def headers_for(pool: PoolName) -> list[str]:
    return CORE_HEADERS + TYPE_SPECIFIC_HEADERS[pool.audit_kind]
