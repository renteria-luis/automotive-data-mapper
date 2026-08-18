# src/pipeline.py

import re

from pydantic import ValidationError

from src.mappers import INGESTED_AT, map_dealer_b, map_fleet_c, map_shop_a
from src.models import RejectedRecord, VehicleEvent
from src.readers import read_dealer_b, read_fleet_c, read_shop_a


def reason_code(error: dict) -> str:
    """The code the validator declared, or E004 for Pydantic's own missing-field errors."""
    found = re.search(r"E0\d{2}", error.get("msg", ""))
    if found:
        return found.group(0)
    return {"missing": "E004"}.get(error["type"], "E004")


def run() -> tuple[list[VehicleEvent], list[RejectedRecord]]:
    """Run the three feeds end to end. Returns accepted events and rejected records."""
    feeds = [
        ('shop_a', read_shop_a(), map_shop_a),
        ('dealer_b', read_dealer_b(), map_dealer_b),
        ('fleet_c', read_fleet_c(), map_fleet_c),
    ]
    total = sum(len(df) for _, df, _ in feeds)

    events: list[VehicleEvent] = []
    rejected: list[RejectedRecord] = []

    # this loop process one record at a time
    for source_id, df, mapper in feeds:  # feed by feed
        seen: set = set()  # only compares within the feed

        for _, row in df.iterrows():  # record by record
            payload = mapper(row)
            raw = row.to_dict()

            # before validating, check whether seen an identical row from that feed already
            fingerprint = tuple(sorted((k, str(v)) for k, v in raw.items()))
            if fingerprint in seen:
                rejected.append(
                    RejectedRecord(
                        source_id=source_id,
                        source_record_id=payload['source_record_id'],
                        reason_code='E009',
                        detail='identical row already read from this feed',
                        raw_record=raw,
                        ingested_at=INGESTED_AT,
                    )
                )
                continue
            seen.add(fingerprint)

            try:
                events.append(VehicleEvent(**payload))
            except ValidationError as error:
                first = error.errors()[0]
                rejected.append(
                    RejectedRecord(
                        source_id=source_id,
                        source_record_id=payload['source_record_id'],
                        reason_code=reason_code(first),
                        detail=first['msg'].replace('Value error, ', ''),
                        raw_record=raw,
                        ingested_at=INGESTED_AT,
                    )
                )

    # accepted plus rejected has to equal what we read
    # if not, a record disappeared without anyone reporting it
    assert len(events) + len(rejected) == total, 'a record was lost along the way'

    return events, rejected