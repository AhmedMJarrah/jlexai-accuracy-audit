"""
One-off completeness check - not part of the pipeline. Compares
every key actually present in the raw file (top-level and nested
Mod_Legs) against what the models declare. Anything in data but
not in the model is being silently dropped - this is how
DetailedName was missed. Run against any new data version before
trusting ingestion again.
"""
import argparse
import json

from step1_scaffold.config import get_settings
from step2_ingestion.models import Legislation, ModLeg


def census(raw: list) -> None:
    top_keys, mod_keys = set(), set()
    for item in raw:
        top_keys.update(item.keys())
        for m in item.get("Mod_Legs", []) or []:
            if isinstance(m, dict):
                mod_keys.update(m.keys())

    model_top = set(Legislation.model_fields) - {"leg_type", "record_id", "content_hash"}
    model_mod = set(ModLeg.model_fields)

    print("=== Top-level Legislation ===")
    print(f"In data, NOT in model: {sorted(top_keys - model_top) or 'none'}")
    print(f"In model, never in data: {sorted(model_top - top_keys) or 'none'}")

    print("\n=== Nested Mod_Legs ===")
    print(f"In data, NOT in model: {sorted(mod_keys - model_mod) or 'none'}")
    print(f"In model, never in data: {sorted(model_mod - mod_keys) or 'none'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", required=True)
    args = parser.parse_args()
    settings = get_settings()
    raw = json.loads((settings.data_dir / args.filename).read_text(encoding="utf-8"))
    census(raw)