"""
Typed models mirroring the source JSON. Several source-data quirks
are normalized or accommodated here, not rejected:

1. Missing values sometimes arrive as empty string "" rather than
   JSON null.
2. Mod_Legs.Leg_Number and Mod_Legs.Replaced_For_ID are declared as
   strings in the source schema but arrive as floats (e.g. 10.0).
3. Different export versions of this data have carried different
   field sets - DetailedName and is_amendment on Mod_Legs were added
   here after extra="forbid" correctly caught their absence rather
   than silently dropping them.
"""
import hashlib
import json as _json
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class LegType(str, Enum):
    LAW = "law"
    BYLAW = "bylaw"


def _normalize_raw(data: dict, numeric_id_fields: frozenset[str] = frozenset()) -> dict:
    if not isinstance(data, dict):
        return data
    cleaned = {}
    for k, v in data.items():
        if v == "":
            cleaned[k] = None
        elif k in numeric_id_fields and isinstance(v, (int, float)):
            cleaned[k] = str(int(v)) if float(v).is_integer() else str(v)
        else:
            cleaned[k] = v
    return cleaned


class ArticleSimple(BaseModel):
    text: str
    title: str
    article_number: str


class ModLegArticle(BaseModel):
    article_number: str
    title: str
    enforcement_date: Optional[str] = None
    text: str


class ModLeg(BaseModel):
    model_config = {"extra": "forbid"}

    Leg_Name: str
    Publication: Optional[str] = None
    Leg_Number: Optional[str] = None  # String here, per source schema - see module docstring
    Year: Optional[int] = None
    Article_Count: Optional[str] = None
    Replaced_For: Optional[str] = None
    Canceled_By: Optional[str] = None
    Magazine_Number: Optional[float] = None
    Magazine_Page: Optional[float] = None
    Magazine_Date: Optional[str] = None
    Issue_Date: Optional[str] = None
    Active_Date: Optional[str] = None
    End_Date: Optional[str] = None
    Replaced_By: Optional[str] = None
    URL: Optional[str] = None
    Base_Articles: list[ModLegArticle] = Field(default_factory=list)
    Reflected_Articles: list[ArticleSimple] = Field(default_factory=list)
    Status: Optional[str] = None
    pmk_id: Optional[int] = None
    entity: Optional[str] = None
    parent_ministry: Optional[str] = None
    type: Optional[str] = None
    Replaced_For_ID: Optional[str] = None
    is_amendment: Optional[bool] = None
    DetailedName: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        return _normalize_raw(data, numeric_id_fields=frozenset({"Leg_Number", "Replaced_For_ID"}))


class Legislation(BaseModel):
    model_config = {"extra": "forbid"}

    Leg_Name: str
    Publication: Optional[str] = None
    Leg_Number: Optional[float] = None  # Float here, per source schema
    Year: Optional[int] = None
    Article_Count: Optional[str] = None
    Replaced_For: Optional[str] = None
    Canceled_By: Optional[str] = None
    Magazine_Number: Optional[float] = None
    Magazine_Page: Optional[float] = None
    Magazine_Date: Optional[str] = None
    Issue_Date: Optional[str] = None
    Active_Date: Optional[str] = None
    End_Date: Optional[str] = None
    Replaced_By: Optional[str] = None
    URL: Optional[str] = None
    Base_Articles: list[ArticleSimple] = Field(default_factory=list)
    Mod_Legs: list[ModLeg] = Field(default_factory=list)
    Status: Optional[str] = None
    pmk_id: Optional[int] = None
    entity: Optional[str] = None
    parent_ministry: Optional[str] = None
    type: Optional[str] = None
    Replaced_For_ID: Optional[str] = None
    DetailedName: Optional[str] = None

    # Set post-load, not part of the source JSON.
    leg_type: Optional[LegType] = None
    record_id: Optional[str] = None     # from pmk_id, or a URL-derived ID when pmk_id is absent
    content_hash: Optional[str] = None  # detects drift if source data changes later

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        return _normalize_raw(data, numeric_id_fields=frozenset({"Replaced_For_ID"}))

    @property
    def has_amendments(self) -> bool:
        return len(self.Mod_Legs) > 0


def compute_content_hash(leg: "Legislation") -> str:
    """Deterministic hash of the record's actual content, independent
    of field order. Used to detect if a sampled record's data changed
    since it was drawn, regardless of which identity scheme was used."""
    payload = leg.model_dump(
        mode="json", exclude={"record_id", "content_hash", "leg_type"}
    )
    canonical = _json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
