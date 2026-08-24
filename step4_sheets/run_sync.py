"""
CLI entry point: loads a saved sampling round snapshot and pushes it
into the Google Sheet(s) - main and reflect, resolved automatically
per pool. Defaults to the most recently created snapshot if
--round-file is omitted. --pool (repeatable) scopes the push to
specific pool(s) - default is every pool in the round.
"""
import argparse
from pathlib import Path

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger
from step3_sampling.snapshot import load_round
from step4_sheets.client import open_spreadsheets_for_settings
from step4_sheets.sync import push_round

logger = get_logger("run_sync")


def _latest_snapshot(snapshots_dir: Path) -> Path:
    files = sorted(snapshots_dir.glob("round_*.json"))
    if not files:
        raise FileNotFoundError(f"No snapshot files found in {snapshots_dir}")
    return files[-1]


def run(round_file: str | None, force: bool, pools: list[str] | None) -> None:
    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    path = Path(round_file) if round_file else _latest_snapshot(settings.data_dir / "snapshots")
    logger.info(f"Loading round from {path}")
    round_ = load_round(path)

    spreadsheets = open_spreadsheets_for_settings(settings)
    only_pools = set(pools) if pools else None
    push_round(spreadsheets, round_, force=force, only_pools=only_pools)
    print(f"\nSynced round '{round_.round_id}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-file", default=None, help="Path to a snapshot json; defaults to the latest")
    parser.add_argument("--force", action="store_true", help="Clear and rewrite tabs that already have data")
    parser.add_argument("--pool", dest="pools", action="append",
                         help="Limit to specific pool(s), repeatable. Default: all pools in the round.")
    args = parser.parse_args()
    run(args.round_file, args.force, args.pools)
