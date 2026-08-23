"""
Persists a SamplingRound to disk as JSON under data/snapshots/
(gitignored - working data, not source code). A round is immutable:
re-running sampling creates a NEW round file, never overwrites an
existing one - so in-progress volunteer work is never invalidated
by a later re-run.
"""
from pathlib import Path

from step3_sampling.models import SamplingRound


def save_round(round_: SamplingRound, snapshots_dir: Path) -> Path:
    path = snapshots_dir / f"{round_.round_id}.json"
    if path.exists():
        raise FileExistsError(f"Round {round_.round_id} already exists at {path} - rounds are immutable, use a new round_id")
    path.write_text(round_.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_round(path: Path) -> SamplingRound:
    return SamplingRound.model_validate_json(path.read_text(encoding="utf-8"))