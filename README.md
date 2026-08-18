# automotive-data-mapper

Vehicle service records come from three systems in three formats. This maps them into one schema and separates records that can be mapped from those that cannot, with a reason for each rejection.

## The problem

The same event, "replaced front brake pads", arrives as a CSV row from an independent shop, as a job
inside a namespaced XML repair order from a dealership, and as a record in a JSON export from a
fleet provider. Field names differ. The odometer is sometimes miles, sometimes kilometres, sometimes
written `21,000`, sometimes empty.

A wrong mapping is worse than a missing record because it looks valid downstream. The pipeline rejects records that do not fit, assigns a reason, counts them, and groups them by cause.

## Results

97 records read, 87 mapped, 10 rejected.

`docs/SAMPLE_DATA.md` lists all 10 unmappable records and their expected reason codes, and it was
written before the code. So this is a measurement, not a claim.

| | |
|---|---|
| Documented defects detected | 10 of 10 |
| False positives | 0 |
| Mapping rate | 90% |
| Mapped but incomplete, no odometer | 4 |

Rejections by code: 1 × E001, 1 × E002, 1 × E003, 3 × E004, 2 × E005, 1 × E006, 1 × E009.

Some values are messy but valid: an odometer with a thousands separator, a reading in miles, or a shop name written three ways. These are normalized rather than rejected.

`docs/SAMPLE_DATA.md` lists the 10 expected unmappable records and their reason codes. It was written before the code, so the results can be checked against it.

## Input formats

| Feed | What breaks a naive reader |
|---|---|
| `shop_a` CSV | `21,000` contains the delimiter, so it is quoted. Splitting on commas shifts every column after it |
| `dealer_b` XML | Every element sits in a default namespace. `findall("RepairOrder")` returns an empty list, so the feed looks empty rather than broken |
| `fleet_c` JSON | `odometer.value` arrives as a number, a string with a comma, and null, across records |

None of these cases raises an exception, and each can produce output that looks correct.

One more: a repair order can hold several jobs, and each job is its own event. A reader producing
one row per order loses 5 of 27 and reports nothing.

## Findings

**Check order matters.** One vehicle reports 994,120 km. This makes the next genuine reading look like a rollback. Running the rollback check first produces 2 problems instead of 1. Removing the implausible reading first avoids the false rollback. `tests/test_checks.py` covers this.

**The duplicate key needs the description.** Matching on vehicle and date flags 12 records, but 10 are valid multi-job repair orders. Adding the normalized description leaves 1 real cross-feed duplicate. This currently works because both sources use the same description, so a service taxonomy is the next step.

## Status

| | |
|---|---|
| Readers for CSV, namespaced XML, nested JSON | ✅ |
| Source to target mapping, audited against the files | ✅ |
| Canonical schema and validation in Pydantic | ✅ |
| Rejected records table with reason codes | ✅ |
| Whole dataset checks: implausible, rollback, cross-feed duplicate | ✅ |
| Coverage and rejection report | ✅ |
| Service taxonomy and rule-based classification | 📋 |
| VIN decoding against a public API | 📋 |
| Human review of low-confidence records | 📋 |

📋 means designed in `PLAN.md`, not built. Known gaps and pending decisions are in
`docs/DESIGN_DECISIONS.md`.

## Layout

```
src/
  readers.py      one reader per feed, each hiding its own trap
  mappings.py     source to target, declared as data
  mapping.py      row in, canonical payload out
  transforms.py   units, dates, text, provider names
  models.py       the schema and the reason codes, in Pydantic
  pipeline.py     read, map, validate, split
  checks.py       the checks that need every feed
notebooks/
  01_sources.ipynb    what each feed is, and where each field goes
  02_pipeline.ipynb   the pipeline, with the decisions written down
```

Exploration happens in the notebooks. Stable code moves to `src/` with tests, notebooks keep them for now.

## Running it

```bash
pip install -e .
pytest
```

## Documentation

| | |
|---|---|
| [Architecture](https://luisrenteria.me/architecture/automotive-data-mapper) | Project architecture with progress tracking |
| [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | Every canonical field, its source in each feed, and the reason codes |
| [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md) | Every deliberate defect, by record, with the format sources cited |
| [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) | Each decision, why, what was rejected, and what it costs |
| [PLAN.md](PLAN.md) | The phases that are not built |

## Scope

The records are synthetic. No real customer or vehicle data. The 24 VINs carry correct ISO 3779
check digits and real manufacturer prefixes; the broken ones are broken on purpose.

Small pipeline for reading and auditing the data. No orchestration engine or warehouse.

## License

MIT, see [LICENSE](LICENSE).