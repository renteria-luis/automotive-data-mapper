from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import VehicleEvent, vin_check_digit
from src.pipeline import reason_code

NOW = datetime.now(timezone.utc)
GOOD_VIN = '1HGCV1F30LA100234'


def event(**overrides):
    payload = {
        'source_id': 'test',
        'source_record_id': '1',
        'vin': GOOD_VIN,
        'event_date': '2023-07-26',
        'raw_description': 'oil change',
        'normalized_description': 'oil change',
        'ingested_at': NOW,
    }
    return VehicleEvent(**{**payload, **overrides})


def test_check_digit_is_the_only_check_that_catches_a_transposed_vin():
    """Two swapped characters keep the length and use only legal characters."""
    transposed = GOOD_VIN[:2] + GOOD_VIN[3] + GOOD_VIN[2] + GOOD_VIN[4:]

    assert len(transposed) == 17                      # length check accepts it
    assert not set(transposed) & set('IOQ')           # character check accepts it
    assert transposed[8] != vin_check_digit(transposed)


def test_a_valid_record_is_accepted():
    assert event().vin == GOOD_VIN


@pytest.mark.parametrize(
    'field, value, expected',
    [
        ('vin', '1FTFW1E50KFA1234', 'E001'),
        ('vin', '1G1ZD5ST0LFO04821', 'E002'),
        ('vin', '1HCGV1F30LA100234', 'E003'),
        ('raw_description', '', 'E004'),
        ('event_date', '2026-02-30', 'E005'),
        ('event_date', '2030-01-01', 'E006'),
    ],
)
def test_each_defect_produces_its_reason_code(field, value, expected):
    with pytest.raises(ValidationError) as caught:
        event(**{field: value})
    assert reason_code(caught.value.errors()[0]) == expected


def test_an_unknown_field_is_rejected_rather_than_ignored():
    """extra='forbid' is what stops a field nobody mapped from passing unnoticed."""
    with pytest.raises(ValidationError):
        event(unexpected_field='value')
