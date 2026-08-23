"""
Sampling domain models - pools, samples, and per-round snapshots.
Six pools total: {law, bylaw} x {meta, chain, reflect}. Bylaw pools
stay unavailable until the bylaws adapter (step2) is implemented.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LegKind(str, Enum):
    LAW = "law"
    BYLAW = "bylaw"


class AuditKind(str, Enum):
    META = "meta"
    CHAIN = "chain"
    REFLECT = "reflect"


class PoolName(str, Enum):
    LAW_META = "law_meta"
    LAW_CHAIN = "law_chain"
    LAW_REFLECT = "law_reflect"
    BYLAW_META = "bylaw_meta"
    BYLAW_CHAIN = "bylaw_chain"
    BYLAW_REFLECT = "bylaw_reflect"

    @property
    def leg_kind(self) -> LegKind:
        return LegKind.LAW if self.value.startswith("law_") else LegKind.BYLAW

    @property
    def audit_kind(self) -> AuditKind:
        return AuditKind(self.value.split("_", 1)[1])


# Phase 1 metadata fields confirmed for the meta audit. entity,
# parent_ministry, Publication, URL, DetailedName, Leg_Name,
# Article_Count, type deliberately deferred to a later phase.
META_FIELDS: list[str] = [
    "Leg_Number",
    "Year",
    "Status",
    "Magazine_Number",
    "Magazine_Page",
    "Magazine_Date",
    "Issue_Date",
    "Active_Date",
    "End_Date",
    "Replaced_By",
    "Replaced_For",
    "Canceled_By",
]


class SampledRecord(BaseModel):
    """Minimal frozen reference - enough to detect later drift via
    content_hash, without duplicating the full legislation payload
    into the snapshot.

    meta_fields: frozen Phase 1 metadata values, populated only for
    META pools - the value shown to volunteers is always "as
    sampled", even if the source file changes later.

    chain_data: frozen amendment sequence, populated only for CHAIN
    pools - a list of {kind, leg_name, leg_number, year, status}
    dicts, element 0 always the base law itself (kind="base"),
    followed by each Mod_Leg in order (kind="amendment")."""
    record_id: str
    pmk_id: Optional[int] = None
    leg_name: str
    content_hash: str
    meta_fields: dict[str, str] = Field(default_factory=dict)
    chain_data: list[dict[str, str]] = Field(default_factory=list)


class PoolSample(BaseModel):
    pool: PoolName
    population_size: int
    sample_size: int
    records: list[SampledRecord]
    assignments: dict[str, list[str]]  # user_slot -> [record_id, ...]


class SamplingRound(BaseModel):
    round_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_filename: str
    source_fingerprint: str  # detects if the source file changes after this round is drawn
    num_users: int
    pools: dict[str, PoolSample]
    skipped_pools: list[str] = Field(default_factory=list)
