# src/models.py

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

# https://www.ecfr.gov/current/title-49/subtitle-B/chapter-V/part-565/subpart-B/section-565.15
TRANSLIT = {
    **{c: i + 1 for i, c in enumerate("ABCDEFGH")},
    **{c: i + 1 for i, c in enumerate("JKLMN")},
    "P": 7,
    "R": 9,
    **{c: i + 2 for i, c in enumerate("STUVWXYZ")},
    **{str(d): d for d in range(10)},
}
WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def vin_check_digit(vin: str) -> str:
    """Position 9 of a VIN, computed from the other sixteen characters (ISO 3779)."""
    total = sum(TRANSLIT[c] * w for c, w in zip(vin, WEIGHTS))
    remainder = total % 11
    return "X" if remainder == 10 else str(remainder)


class VehicleEvent(BaseModel):
    """One service event on one vehicle, in the canonical shape."""

    # forbid: reject | ignore: ignores | allow: keeps
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_record_id: str
    vin: str
    # this will remain None within this version, E003 rejects => False not possible
    vin_valid: bool | None = None
    event_date: date
    odometer_km: int | None = None
    odometer_source_unit: str | None = None
    raw_description: str
    normalized_description: str
    provider_name: str | None = None
    provider_city: str | None = None
    provider_province: str | None = None
    ingested_at: datetime  # pydantic not only validates but also converts

    @field_validator("vin", mode="before")
    @classmethod
    def check_vin(cls, v):
        if v is None or str(v).strip() == "":  # not empty
            raise ValueError("E004: vin is empty")
        v = str(v).strip().upper()             # convert to upper+str
        if len(v) != 17:                       # 17 chars
            raise ValueError(f"E001: vin has {len(v)} characters, expected 17")
        illegal = sorted(set(v) & set("IOQ"))
        if illegal:                            # not I, O, Q chars
            raise ValueError(f"E002: vin contains {illegal}, which are not used in VINs")
        expected = vin_check_digit(v)
        if v[8] != expected:                   # check digit
            raise ValueError(f"E003: check digit is {v[8]}, expected {expected}")
        return v

    @field_validator("event_date", mode="before")
    @classmethod
    def check_date(cls, v):
        if v is None or str(v).strip() == "":
            raise ValueError("E004: event_date is empty")
        try:
            parsed = date.fromisoformat(str(v))
        except ValueError:
            raise ValueError(f"E005: {v!r} is not a real calendar date")
        if parsed > date.today():
            raise ValueError(f"E006: {parsed.isoformat()} is in the future")
        return parsed

    @field_validator("source_record_id", "raw_description", mode="before")
    @classmethod
    def check_not_empty(cls, v, info):  # need info to know which field is validating
        if v is None or str(v).strip() == "":
            raise ValueError(f"E004: {info.field_name} is empty")
        return str(v).strip()

    @field_validator("odometer_km")  # mode: after, we need it to be converted to int first
    @classmethod
    def check_odometer(cls, v):
        if v is not None and v < 0:  # E008 is for implausible km such as negative
            raise ValueError(f"E008: odometer is {v}, which cannot be negative")
        return v


class RejectedRecord(BaseModel):
    """One record the pipeline could not turn into a VehicleEvent."""

    source_id: str
    source_record_id: str | None = None  # can be None for E010
    reason_code: str
    detail: str
    raw_record: dict
    ingested_at: datetime