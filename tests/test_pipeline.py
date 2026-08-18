import pandas as pd
import pytest

from src.pipeline import run

# the ten unmappable records, copied from docs/SAMPLE_DATA.md, which was written
# before the pipeline existed
EXPECTED = {
    ('shop_a', '184227'): 'E001',
    ('shop_a', '184209'): 'E002',
    ('dealer_b', 'RO-100494-1'): 'E003',
    ('shop_a', '184269'): 'E004',
    ('dealer_b', 'RO-100557-1'): 'E004',
    ('fleet_c', 'WO-2026-4180'): 'E004',
    ('shop_a', '184278'): 'E005',
    ('fleet_c', 'WO-2026-4145'): 'E005',
    ('dealer_b', 'RO-100536-1'): 'E006',
    ('shop_a', '184302'): 'E009',
}


@pytest.fixture(scope='module')
def result():
    return run()


def test_every_record_read_ends_up_in_one_of_the_two_tables(result):
    events, rejected = result
    assert len(events) + len(rejected) == 97


def test_the_documented_counts_hold(result):
    events, rejected = result
    assert len(events) == 87
    assert len(rejected) == 10


def test_it_finds_all_ten_documented_defects_and_nothing_else(result):
    """The list was written before the code, so this is a measurement and not a claim."""
    _, rejected = result
    found = {(r.source_id, r.source_record_id): r.reason_code for r in rejected}
    assert found == EXPECTED


def test_every_rejection_carries_its_original_record(result):
    """Without the payload, fixing a rejected record means hunting for it in the source file."""
    _, rejected = result
    for r in rejected:
        assert r.raw_record


def test_messy_but_valid_records_are_normalized_rather_than_rejected(result):
    events, _ = result
    df = pd.DataFrame([e.model_dump() for e in events])

    assert (df['provider_name'] == 'Riverside Auto Service').any()   # three spellings collapsed
    assert df['vin'].str.isupper().all()                             # one feed sends lowercase
    assert df['odometer_km'].isna().sum() == 4                       # blank odometers kept
