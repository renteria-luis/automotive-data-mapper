import pandas as pd
import pytest

from src.checks import count_rollbacks, find_cross_feed_duplicates, find_implausible
from src.pipeline import run


@pytest.fixture(scope='module')
def events_df():
    events, _ = run()
    return pd.DataFrame([e.model_dump() for e in events])


def test_finds_the_implausible_reading(events_df):
    implausible = find_implausible(events_df)
    assert len(implausible) == 1
    assert implausible.iloc[0]['source_record_id'] == 'WO-2026-4205'


def test_removing_the_implausible_reading_removes_a_false_rollback(events_df):
    """The ordering decision, as a test.

    The 994,120 km reading makes the next genuine reading look like it went backwards. Run the
    rollback check first and it reports two problems where there is one.
    """
    implausible = find_implausible(events_df)

    assert len(count_rollbacks(events_df)) == 2
    assert len(count_rollbacks(events_df.drop(implausible.index))) == 1


def test_the_remaining_rollback_is_the_real_one(events_df):
    implausible = find_implausible(events_df)
    rollbacks = count_rollbacks(events_df.drop(implausible.index))

    assert rollbacks[0]['record'] == 'WO-2026-4240'
    assert rollbacks[0]['previous_record'] == '184215'


def test_the_duplicate_key_needs_the_description(events_df):
    """Vehicle and date alone flags legitimate multi-job repair orders."""
    naive = events_df.duplicated(subset=['vin', 'event_date'], keep=False).sum()
    with_description = len(find_cross_feed_duplicates(events_df))

    assert naive == 12
    assert with_description == 2


def test_the_cross_feed_duplicate_is_the_documented_pair(events_df):
    duplicates = find_cross_feed_duplicates(events_df)
    assert set(duplicates['source_record_id']) == {'184233', 'WO-2026-4235'}
