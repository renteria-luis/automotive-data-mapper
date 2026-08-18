# src/checks.py
"""Checks that need every feed mapped first.

None of these can run on a single record: they compare records against each other. And the order
matters, because E008 removes a reading that would otherwise produce a false E007.
"""

import pandas as pd

IMPLAUSIBLE_KM = 500_000

DUPLICATE_KEYS = ['vin', 'event_date', 'normalized_description']


def find_implausible(events_df: pd.DataFrame) -> pd.DataFrame:
    """E008. A reading no vehicle of that age reaches."""
    return events_df[
        events_df['odometer_km'].notna() & (events_df['odometer_km'] > IMPLAUSIBLE_KM)
    ]


def count_rollbacks(frame: pd.DataFrame) -> list[dict]:
    """E007. A later event on the same vehicle with a lower reading than the one before it."""
    findings = []
    # take out empty odometer readings, and sort by date oldest --> newest
    known = frame[frame['odometer_km'].notna()].sort_values('event_date')

    # separate the records in groups, 1 per vehicle
    for vin, group in known.groupby('vin'):
        previous = None

        for _, row in group.iterrows():
            # previous is not None means "it's not the first"
            if previous is not None and row['odometer_km'] < previous['odometer_km']:
                findings.append(
                    {
                        'vin': vin,
                        'previous_record': previous['source_record_id'],
                        'previous_date': previous['event_date'],
                        'previous_km': int(previous['odometer_km']),
                        'record': row['source_record_id'],
                        'date': row['event_date'],
                        'km': int(row['odometer_km']),
                        'drop_km': int(previous['odometer_km'] - row['odometer_km']),
                    }
                )
            # always executed, current row becomes the previous for the next loop
            previous = row

    return findings


def find_cross_feed_duplicates(events_df: pd.DataFrame) -> pd.DataFrame:
    """E009. The same event reported by two feeds, worded the same way.

    Matching on vehicle and date alone flags legitimate multi-job repair orders, so the description
    is part of the key.
    """
    return events_df[
        events_df.duplicated(subset=DUPLICATE_KEYS, keep=False)
    ].sort_values(DUPLICATE_KEYS)