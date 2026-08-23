"""
Full-population release batches - admin-controlled expansion beyond
the initial 100-sample. Each batch is an immutable event, same
philosophy as SamplingRound: never overwritten, always a new file,
so replaying the full batch history reliably reconstructs the
current assignment state.
"""
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from step3_sampling.models import PoolName, SampledRecord


class ReleaseBatch(BaseModel):
    batch_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pool: PoolName
    user_slot: str
    records: list[SampledRecord]
    note: str = ""
