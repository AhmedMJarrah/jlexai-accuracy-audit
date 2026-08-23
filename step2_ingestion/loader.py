"""
Orchestrates: pick the right adapter, load, validate, report stats.
Run directly to sanity-check a file before it ever touches sampling.
"""
import argparse
import sys
from pathlib import Path

from step1_scaffold.config import get_settings
from step1_scaffold.logging_setup import setup_logging, get_logger
from step2_ingestion.adapters import get_adapter
from step2_ingestion.models import LegType

logger = get_logger("loader")


def load_legislation(leg_type: LegType, filename: str) -> list:
    settings = get_settings()
    path = settings.data_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Expected data file at {path} - place it there first")

    adapter = get_adapter(leg_type)
    records = adapter.load(path)
    _report(records, leg_type)
    return records


def _report(records: list, leg_type: LegType) -> None:
    total = len(records)
    amended = sum(1 for r in records if r.has_amendments)
    missing_status = sum(1 for r in records if not r.Status)
    missing_pmk_id = sum(1 for r in records if r.pmk_id is None)

    print(f"\n--- {leg_type.value} ingestion report ---")
    print(f"Total records:        {total}")
    if total:
        print(f"With amendments:      {amended} ({amended/total:.1%})")
    else:
        print("With amendments:      0")
    print(f"Without amendments:   {total - amended}")
    print(f"Missing Status:       {missing_status}")
    print(f"Missing pmk_id:       {missing_pmk_id}")

    logger.info(
        "Ingestion report",
        extra={"leg_type": leg_type.value, "total": total, "amended": amended},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["law", "bylaw"], required=True)
    parser.add_argument("--filename", required=True, help="filename inside data/")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_dir, settings.log_level)

    load_legislation(LegType(args.type), args.filename)