"""
Adapter layer: normalizes whatever shape a source file is in into
the common Legislation model. Laws are ready now. Bylaws stay a
stub until that file's shape is confirmed.
"""
import json
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import ValidationError

from step1_scaffold.logging_setup import get_logger
from step2_ingestion.models import Legislation, LegType, compute_content_hash

logger = get_logger("adapters")


class LegislationAdapter(ABC):
    leg_type: LegType

    @abstractmethod
    def load(self, path: Path) -> list[Legislation]:
        raise NotImplementedError


class LawsJSONAdapter(LegislationAdapter):
    leg_type = LegType.LAW

    def load(self, path: Path) -> list[Legislation]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"Expected a JSON array at {path}, got {type(raw)}")

        records: list[Legislation] = []
        seen_ids: dict[str, int] = {}
        duplicates: list[dict] = []
        errors = 0

        for i, item in enumerate(raw):
            try:
                leg = Legislation(**item)
                leg.leg_type = self.leg_type

                if leg.pmk_id is None:
                    errors += 1
                    logger.warning(f"Skipping record at index {i}: missing pmk_id")
                    continue

                rid = str(leg.pmk_id)
                if rid in seen_ids:
                    first_index = seen_ids[rid]
                    duplicates.append(
                        {"pmk_id": rid, "first_index": first_index, "duplicate_index": i}
                    )
                    logger.warning(
                        f"Duplicate pmk_id={rid} at index {i} "
                        f"(first seen at index {first_index}) - disambiguating record_id"
                    )
                    rid = f"{rid}#{i}"  # disambiguated - not the raw pmk_id
                else:
                    seen_ids[rid] = i

                leg.record_id = rid
                leg.content_hash = compute_content_hash(leg)
                records.append(leg)
            except ValidationError as e:
                errors += 1
                logger.warning(
                    f"Skipping invalid law record at index {i}: {e.error_count()} field error(s)"
                )

        logger.info(
            f"Loaded {len(records)} law records, {errors} skipped, "
            f"{len(duplicates)} duplicate pmk_id collision(s)"
        )
        self._report_duplicates(raw, duplicates)
        return records

    @staticmethod
    def _report_duplicates(raw: list, duplicates: list[dict]) -> None:
        if not duplicates:
            return
        print(f"\n--- {len(duplicates)} duplicate pmk_id pair(s) - review before sampling ---")
        for dup in duplicates:
            a, b = raw[dup["first_index"]], raw[dup["duplicate_index"]]
            diffs = [k for k in a.keys() if a.get(k) != b.get(k)]
            print(
                f"  pmk_id={dup['pmk_id']}: index {dup['first_index']} vs {dup['duplicate_index']} "
                f"- differing field(s): {diffs if diffs else '(none - exact duplicate)'}"
            )


class BylawsJSONAdapter(LegislationAdapter):
    leg_type = LegType.BYLAW

    def load(self, path: Path) -> list[Legislation]:
        raise NotImplementedError(
            "Bylaws adapter not implemented yet - confirm the source file shape first."
        )


def get_adapter(leg_type: LegType) -> LegislationAdapter:
    return {
        LegType.LAW: LawsJSONAdapter(),
        LegType.BYLAW: BylawsJSONAdapter(),
    }[leg_type]