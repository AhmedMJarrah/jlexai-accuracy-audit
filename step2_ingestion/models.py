"""
Typed models mirroring the source JSON. Two confirmed source-data
quirks are normalized here, not rejected:

1. Missing values sometimes arrive as empty string "" rather than
   JSON null.
2. Mod_Legs.Leg_Number and Mod_Legs.Replaced_For_ID are declared as
   strings in the source schema but arrive as floats (e.g. 10.0) -
   confirmed via diagnose.py against the real ReflectedLaws_V10.json.

Neither is a claim about the legislation's own data - they're export
formatting inconsistencies, so they're normalized silently here
rather than surfaced to volunteers as findings.
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
    Leg_Number: Optional[str] = None
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

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        return _normalize_raw(data, numeric_id_fields=frozenset({"Leg_Number", "Replaced_For_ID"}))


class Legislation(BaseModel):
    model_config = {"extra": "forbid"}
    Leg_Name: str
    Publication: Optional[str] = None
    Leg_Number: Optional[float] = None
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
    DetailedName: Optional[str] = None
    Base_Articles: list[ArticleSimple] = Field(default_factory=list)
    Mod_Legs: list[ModLeg] = Field(default_factory=list)
    Status: Optional[str] = None
    pmk_id: Optional[int] = None
    entity: Optional[str] = None
    parent_ministry: Optional[str] = None
    type: Optional[str] = None
    Replaced_For_ID: Optional[str] = None

    # Set post-load, not part of the source JSON.
    leg_type: Optional[LegType] = None
    record_id: Optional[str] = None     # from pmk_id; disambiguated with #index on collision
    content_hash: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        return _normalize_raw(data, numeric_id_fields=frozenset({"Replaced_For_ID"}))

    @property
    def has_amendments(self) -> bool:
        return len(self.Mod_Legs) > 0


def compute_content_hash(leg: "Legislation") -> str:
    payload = leg.model_dump(
        mode="json", exclude={"record_id", "content_hash", "leg_type"}
    )
    canonical = _json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()