"""The canonical schema, and the shape of a record the pipeline refuses.

Three feeds disagree about field names, date formats and units. This module is
the single definition of what a well formed service event looks like after
mapping, and Pydantic enforces it in one place instead of every stage checking
for itself.

The second model matters as much as the first. A record that cannot be mapped
is not dropped and it is not logged and forgotten: it becomes a RejectedRecord
with a reason code and the original payload attached, so it can be counted,
grouped by cause, and investigated.

Every field is documented in docs/DATA_DICTIONARY.md.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# I, O and Q are not used in VINs because they are too easy to confuse with
# 1 and 0, so they are left out of the canonical pattern.
VIN_PATTERN = r"^[A-HJ-NPR-Z0-9]{17}$"


class SourceId(str, Enum):
    """The feed a record came from."""

    SHOP_A = "shop_a"
    DEALER_B = "dealer_b"
    FLEET_C = "fleet_c"


class OdometerUnit(str, Enum):
    """The unit the source reported, before conversion to kilometres."""

    KILOMETRES = "km"
    MILES = "mi"


class ReasonCode(str, Enum):
    """Why a record was rejected.

    The first six are found while a record is being read and mapped. The last
    four are found afterwards, by comparing a record against the rest of the
    data, so they can only be raised once every feed has been read.
    """

    INVALID_VIN_LENGTH = "E001"
    INVALID_VIN_CHARS = "E002"
    INVALID_VIN_CHECKDIGIT = "E003"
    MISSING_REQUIRED_FIELD = "E004"
    UNPARSEABLE_DATE = "E005"
    DATE_OUT_OF_RANGE = "E006"
    ODOMETER_ROLLBACK = "E007"
    ODOMETER_IMPLAUSIBLE = "E008"
    DUPLICATE_EVENT = "E009"
    UNMAPPED_SOURCE_FIELD = "E010"


class VehicleEvent(BaseModel):
    """One service or repair event on one vehicle, in canonical form."""

    # Rejecting unknown fields turns a typo in a mapping into a loud error
    # instead of a field that is silently always empty.
    model_config = ConfigDict(extra="forbid")

    source_id: SourceId
    source_record_id: str = Field(min_length=1)

    vin: str = Field(pattern=VIN_PATTERN)
    vin_valid: bool | None = Field(
        default=None,
        description="ISO 3779 check digit result, or None if the check has not been run",
    )

    event_date: date
    odometer_km: int | None = Field(default=None, ge=0)
    odometer_source_unit: OdometerUnit | None = None

    raw_description: str = Field(min_length=1)
    normalized_description: str = Field(min_length=1)

    provider_name: str | None = None
    provider_city: str | None = None
    provider_province: str | None = None

    ingested_at: datetime


class RejectedRecord(BaseModel):
    """A source record the pipeline could not turn into a VehicleEvent."""

    model_config = ConfigDict(extra="forbid")

    source_id: SourceId
    source_record_id: str | None = Field(
        default=None,
        description="Missing when the finding belongs to the feed rather than to one record",
    )
    reason_code: ReasonCode
    detail: str = Field(min_length=1, description="What was wrong, in words, for a human reader")
    raw_record: dict[str, Any] = Field(description="The original values, kept for investigation")
    ingested_at: datetime
