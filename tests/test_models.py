"""Tests for the canonical schema.

They cover the rules the schema exists to enforce: a VIN has a fixed shape, an
empty description is not a valid event, and a field name that does not exist
fails instead of disappearing.
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.models import OdometerUnit, ReasonCode, RejectedRecord, SourceId, VehicleEvent

VALID_EVENT = {
    "source_id": SourceId.SHOP_A,
    "source_record_id": "RO-1001",
    "vin": "1FTFW1E50KFA12345",
    "vin_valid": True,
    "event_date": date(2023, 3, 14),
    "odometer_km": 77588,
    "odometer_source_unit": OdometerUnit.MILES,
    "raw_description": "Replaced front brake pads and machined rotors",
    "normalized_description": "replaced front brake pads and machined rotors",
    "provider_name": "Riverside Auto Repair",
    "provider_city": "London",
    "provider_province": "ON",
    "ingested_at": datetime(2026, 8, 5, 9, 0),
}


def test_a_well_formed_event_validates():
    event = VehicleEvent(**VALID_EVENT)

    assert event.source_id is SourceId.SHOP_A
    assert event.odometer_km == 77588


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("vin", "1FTFW1E50KFA1234"),  # 16 characters
        ("vin", "1HGCV1F3OLA100234"),  # letter O is not used in a VIN
        ("vin", "1ftfw1e50kfa12345"),  # lowercase, uppercasing happens before this point
        ("raw_description", ""),  # an empty description is a rejected record, not an event
        ("odometer_km", -1),
        ("source_id", "shop_z"),
        ("odometer_source_unit", "furlongs"),
    ],
)
def test_invalid_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        VehicleEvent(**{**VALID_EVENT, field: value})


def test_an_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        VehicleEvent(**VALID_EVENT, odomter_km=1000)


def test_a_rejected_record_keeps_its_reason_and_its_original_values():
    rejected = RejectedRecord(
        source_id=SourceId.SHOP_A,
        source_record_id="RO-1009",
        reason_code=ReasonCode.INVALID_VIN_LENGTH,
        detail="VIN has 16 characters, expected 17",
        raw_record={"RO_Number": "RO-1009", "VehicleID": "1FTFW1E50KFA1234"},
        ingested_at=datetime(2026, 8, 5, 9, 0),
    )

    assert rejected.reason_code.value == "E001"
    assert rejected.raw_record["VehicleID"] == "1FTFW1E50KFA1234"


def test_a_finding_about_a_whole_feed_needs_no_record_id():
    rejected = RejectedRecord(
        source_id=SourceId.SHOP_A,
        reason_code=ReasonCode.UNMAPPED_SOURCE_FIELD,
        detail="TechnicianID and InvoiceTotal have no target in the canonical schema",
        raw_record={"columns": ["TechnicianID", "InvoiceTotal"]},
        ingested_at=datetime(2026, 8, 5, 9, 0),
    )

    assert rejected.source_record_id is None


def test_a_rejected_record_needs_a_reason():
    with pytest.raises(ValidationError):
        RejectedRecord(
            source_id=SourceId.SHOP_A,
            source_record_id="RO-1009",
            detail="something was wrong",
            raw_record={},
            ingested_at=datetime(2026, 8, 5, 9, 0),
        )
