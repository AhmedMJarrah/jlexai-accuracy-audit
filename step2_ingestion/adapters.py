"""
Adapter layer: normalizes whatever shape a source file is in into
the common Legislation model. Laws are ready now. Bylaws stay a
stub until that file's shape is confirmed.

Identity: pmk_id is preferred when present (the stable identifier
used by the original export). Some export variants of this data
omit pmk_id (and entity/parent_ministry/type/Replaced_For_ID)
entirely while still carrying a unique per-law URL - for those, a
stable numeric ID is extracted from the URL's path instead, so
record identity stays consistent even as the source export's shape
changes across versions.

load() reads from a local path; load_from_text() does the same
validation from an already-loaded JSON string - used by the admin
portal's file-uploader, which has no local path to read from.
"""
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import ValidationError

from step1_scaffold.logging_setup import get_logger
from step2_ingestion.models import Legislation, LegType, compute_content_hash

logger = get_logger("adapters")

_URL_ID_PATTERN = re.compile(r"/info/(\d+)/")


def _url_based_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _URL_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _extract_identity(leg: Legislation) -> tuple[str | None, str]:
    """Returns (identity_value, source) - source is "pmk_id" or "url",
    kept for a clear log line about which scheme was actually used."""
    if leg.pmk_id is not None:
        return str(leg.pmk_id), "pmk_id"
    url_id = _url_based_id(leg.URL)
    if url_id is not None:
        return url_id, "url"
    return None, "none"


class LegislationAdapter(ABC):
    leg_type: LegType

    @abstractmethod
    def load(self, path: Path) -> list[Legislation]:
        raise NotImplementedError


class LawsJSONAdapter(LegislationAdapter):
    leg_type = LegType.LAW

    def load(self, path: Path) -> list[Legislation]:
        return self.load_from_text(path.read_text(encoding="utf-8"))

    def load_from_text(self, raw_text: str) -> list[Legislation]:
        if raw_text.startswith("\ufeff"):
            raw_text = raw_text[1:]

        raw = json.loads(raw_text)
        if not isinstance(raw, list):
            raise ValueError(f"Expected a JSON array, got {type(raw)}")

        records: list[Legislation] = []
        seen_ids: dict[str, int] = {}
        errors = 0
        id_sources = {"pmk_id": 0, "url": 0}

        for i, item in enumerate(raw):
            try:
                leg = Legislation(**item)
                leg.leg_type = self.leg_type

                identity, source = _extract_identity(leg)
                if identity is None:
                    errors += 1
                    logger.warning(
                        f"Skipping record at index {i}: no pmk_id and no usable URL for identity"
                    )
                    continue

                rid = identity
                if rid in seen_ids:
                    first_index = seen_ids[rid]
                    logger.warning(
                        f"Duplicate {source} identity '{rid}' at index {i} "
                        f"(first seen at index {first_index}) - disambiguating record_id"
                    )
                    rid = f"{rid}#{i}"
                else:
                    seen_ids[rid] = i

                leg.record_id = rid
                leg.content_hash = compute_content_hash(leg)
                records.append(leg)
                id_sources[source] += 1
            except ValidationError as e:
                errors += 1
                logger.warning(
                    f"Skipping invalid law record at index {i}: {e.error_count()} field error(s)"
                )

        logger.info(
            f"Loaded {len(records)} law records, {errors} skipped "
            f"(identity source: pmk_id={id_sources['pmk_id']}, url={id_sources['url']})"
        )
        return records


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
