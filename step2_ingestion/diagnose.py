"""
One-off diagnostic - not part of the pipeline. Shows exactly which
fields fail validation on specific records, and compares two records
with colliding pmk_id side by side to determine if they're true
duplicates or distinct records with an ID collision.
"""
import argparse
import json

from pydantic import ValidationError

from step1_scaffold.config import get_settings
from step2_ingestion.models import Legislation

IDENTITY_FIELDS = [
    "Leg_Name", "Leg_Number", "Year", "pmk_id", "entity",
    "parent_ministry", "type", "Status", "Publication",
]


def show_validation_errors(raw: list, indices: list[int]) -> None:
    for i in indices:
        item = raw[i]
        print(f"\n=== index {i} - raw identity fields ===")
        for f in IDENTITY_FIELDS:
            print(f"  {f}: {item.get(f)!r}")
        try:
            Legislation(**item)
            print("  -> VALID (no errors)")
        except ValidationError as e:
            print(f"  -> {e.error_count()} error(s):")
            for err in e.errors():
                loc = ".".join(str(p) for p in err["loc"])
                print(f"     field={loc}  type={err['type']}  input={err.get('input')!r}  msg={err['msg']}")


def compare_records(raw: list, i: int, j: int) -> None:
    print(f"\n=== comparing index {i} vs index {j} (same pmk_id) ===")
    for f in IDENTITY_FIELDS:
        vi, vj = raw[i].get(f), raw[j].get(f)
        flag = "  <-- DIFFERS" if vi != vj else ""
        print(f"  {f}: {vi!r}  |  {vj!r}{flag}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", required=True)
    parser.add_argument("--error-indices", type=int, nargs="*", default=[0, 25, 67])
    parser.add_argument("--compare", type=int, nargs=2, default=[1184, 1186])
    args = parser.parse_args()

    settings = get_settings()
    path = settings.data_dir / args.filename
    raw = json.loads(path.read_text(encoding="utf-8"))

    show_validation_errors(raw, args.error_indices)
    compare_records(raw, *args.compare)