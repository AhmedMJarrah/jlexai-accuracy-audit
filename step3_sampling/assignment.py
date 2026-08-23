"""
Splits a pool's sample across N user slots with zero overlap. Real
usernames map onto these slots in Step 5 (auth) - sampling stays
ignorant of actual usernames so redoing auth later never requires
re-sampling.
"""
import random

from step3_sampling.models import PoolName, SampledRecord


def assign_round_robin(sample: list[SampledRecord], num_users: int, pool: PoolName, base_seed: int) -> dict[str, list[str]]:
    rng = random.Random(base_seed + hash(pool.value) % 100_000)
    record_ids = [s.record_id for s in sample]
    rng.shuffle(record_ids)

    slots: dict[str, list[str]] = {f"user_slot_{i+1}": [] for i in range(num_users)}
    for idx, rid in enumerate(record_ids):
        slot = f"user_slot_{(idx % num_users) + 1}"
        slots[slot].append(rid)
    return slots