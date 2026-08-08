# automotive-data-mapper

Vehicle service records arrive from three different systems in three different formats. This
project maps them into one canonical schema, and separates the records it can map from the records
it cannot, with a reason for every rejection.

> **Status: the MVP is being built.**
> The sample feeds, the canonical schema and the tooling are in place. The ingestion pipeline is
> the work in progress. Everything beyond the MVP is described in [PLAN.md](PLAN.md) as design, not
> as code, and is marked as such below.
>
> Every claim in this README corresponds to code in this repository. Nothing is marked ✅ before it
> runs, and no metric is written by hand.

| Marker | Meaning |
|---|---|
| ✅ | Implemented and covered by tests or a real run |
| 🚧 | In progress |
| 📋 | Designed, not built |

---

## The problem

The same event, "replaced front brake pads", arrives from an independent shop as a CSV row, from a
dealership management system as a job inside a namespaced XML repair order, and from a fleet
provider as a record in a JSON export. Field names differ. Dates come in three
formats, one of which does not parse. The odometer is sometimes miles and sometimes kilometres,
sometimes written with a comma, sometimes empty, and occasionally lower than the reading from the
year before.

A record that is mapped wrong is worse than a record that is missing, because nothing downstream
knows it is wrong. So the interesting part is not the happy path. It is what happens to the
records that do not fit: they have to be caught, given a reason, counted, and grouped by cause so
the cause can be fixed.

## Scope

**The MVP, which is what is being built now:**

1. Read the three feeds: a CSV file, a namespaced XML document with `xml.etree.ElementTree`, and a
   nested JSON export.
2. Map every source field to the canonical schema with pandas, converting units and date formats.
3. Validate each mapped record with Pydantic.
4. Route what fails to a rejected-records table with a reason code and the original payload
   attached, instead of dropping it.
5. Print a report: records read per feed, records mapped, records rejected grouped by reason code
   and by feed.

**Deliberately out of the MVP:** the service taxonomy, the classifier, the review tool, VIN
decoding against an external API, and packaging. They are designed in [PLAN.md](PLAN.md) and marked
📋 in this README. They are the next phases, not hidden work.

## Status

| Component | Status | Where |
|---|---|---|
| Sample feeds in three real formats, with documented defects | ✅ | `data/raw/`, [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md) |
| Canonical schema and rejected-record model | 🚧 | `src/models.py` |
| Data dictionary and source to target mapping | ✅ | [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) |
| Tooling: packaging, linting, tests, CI | ✅ | `pyproject.toml`, `Makefile`, `.github/workflows/ci.yml` |
| Readers for the three formats | 🚧 | phase 1 |
| Field mapping and normalization | 🚧 | phase 1 |
| Validation and the rejected-records table | 🚧 | phase 1 |
| Quality checks: duplicates, odometer rollback | 🚧 | phase 1 |
| Report of coverage and rejections by reason code | 🚧 | phase 1 |
| Service taxonomy and rule-based classification | 📋 | phase 2 |
| VIN decoding against a public API, decode rate | 📋 | phase 3 |
| Human review of low-confidence records | 📋 | phase 4 |
| Docker packaging | 📋 | phase 5 |

## The data

The three feeds live in `data/raw/` and hold 97 records across 24 vehicles. They are fixtures
written for this project, but the formats are not invented. `shop_a` is a CSV whose columns are the ones a shop
management system sends to CARFAX in its service data transfer file. `dealer_b` follows the element names of the STAR RepairOrder schema used between dealer
management systems, namespace included. `fleet_c` is a REST style JSON export.

Every defect in them is deliberate: 10 records cannot be mapped at all, and the rest carry the
ordinary mess of a real feed, such as an odometer written as `21,000`, a unit that changes between
records, and a shop name typed three different ways.

[docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md) lists every defect and the record it belongs to. That
list is what makes a detection rate a measurement rather than an estimate: the pipeline can be
scored against a known total instead of against a guess.

## How the work is organised

Exploration happens in a notebook, in `notebooks/`. When a piece of it works and stops changing,
it moves into `src/` as a function with a test, and the notebook imports it from there instead of
keeping its own copy. The notebook keeps the exploration and the numbers, `src/` keeps the code
that runs.

## Running it

```bash
make install              # creates .venv and installs the project and its dependencies
source .venv/bin/activate
make check                # ruff (lint and formatting) and pytest, the same commands CI runs
make kernel               # registers this environment as a Jupyter kernel
```

The pipeline entry point is part of the work in progress and is not in the repository yet.

## Repository layout

```
automotive-data-mapper/
├── README.md                        ✅ this file
├── PLAN.md                          ✅ the design, including the phases that are not built
├── pyproject.toml                   ✅ metadata, dependencies, lint and test configuration
├── Makefile                         ✅ install · lint · format · test · check · kernel
├── .github/workflows/ci.yml         ✅ lint and tests on every push
│
├── data/raw/
│   ├── shop_a/service_records_20260731.csv     ✅ CSV, CARFAX service transfer column names
│   ├── dealer_b/ProcessRepairOrder_20260731.xml ✅ STAR style repair order XML, with a namespace
│   └── fleet_c/maintenance_events_2026-07.json  ✅ REST export, nested, mixed value types
│
├── src/
│   ├── models.py                    🚧 canonical schema, rejected record, reason codes
│   └── (readers, mapping, checks)   🚧 added as each piece works in the notebook
│
├── notebooks/                       ✅ exploratory work
├── docs/
│   ├── SAMPLE_DATA.md               ✅ every deliberate defect and the record it is in
│   ├── DATA_DICTIONARY.md           ✅ every canonical field and its source in each feed
│   └── DESIGN_DECISIONS.md          ✅ what was decided, why, and what it costs
└── tests/                           🚧 one test module per module in src
```

## Reason codes

Nothing is dropped in silence. Every record the pipeline cannot map lands in the rejected-records
table with one of these codes.

| Code | Meaning | Found |
|---|---|---|
| `E001` | `INVALID_VIN_LENGTH`, not 17 characters | while reading |
| `E002` | `INVALID_VIN_CHARS`, contains I, O or Q | while reading |
| `E003` | `INVALID_VIN_CHECKDIGIT`, fails the ISO 3779 check | while reading |
| `E004` | `MISSING_REQUIRED_FIELD` | while reading |
| `E005` | `UNPARSEABLE_DATE` | while reading |
| `E006` | `DATE_OUT_OF_RANGE`, a service date in the future | while reading |
| `E007` | `ODOMETER_ROLLBACK`, a later event with a lower reading | after all feeds are read |
| `E008` | `ODOMETER_IMPLAUSIBLE`, a jump no vehicle makes | after all feeds are read |
| `E009` | `DUPLICATE_EVENT`, the same event reported by two feeds | after all feeds are read |
| `E010` | `UNMAPPED_SOURCE_FIELD`, a source field with no canonical target | while reading |

## Metrics

🚧 Not available yet.

Coverage, rejection rate by reason code, and detection against the known defect list will be
printed by the pipeline and copied here from that output. This section stays empty until the code
that computes those numbers exists.

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1. MVP | Three readers, mapping to the canonical schema, validation, rejected-records table, report | 🚧 |
| 2. Taxonomy | A service taxonomy and keyword-based classification of the free-text descriptions | 📋 |
| 3. VIN decoding | Decode valid VINs against a public API, cache the responses, report a decode rate | 📋 |
| 4. Review | A small tool for a person to review and correct the records the rules are unsure about | 📋 |
| 5. Packaging | Docker, so the pipeline runs the same way on another machine | 📋 |

The phases after the MVP are described in [PLAN.md](PLAN.md). They are a design, and the README
will only mark them ✅ when there is code behind them.

## Documentation

| Document | Contents |
|---|---|
| [PLAN.md](PLAN.md) | The problem, the architecture, and the phases that are not built yet |
| [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md) | Every deliberate defect in the sample feeds, by record |
| [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | Every canonical field: type, source in each feed, transformation, validation rule |
| [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) | Each decision, its reason, the alternative rejected, and the cost |

## Scope and disclaimers

- **The service records are synthetic.** They are fixtures written for this repository, with
  defects placed on purpose. The file formats follow real specifications, which are cited in
  [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md). No real customer or vehicle data is used.
- **The VINs are structurally valid.** The 24 vehicle identification numbers carry correct ISO 3779
  check digits and real manufacturer prefixes. The broken ones are broken deliberately.
- **This is not a production data platform.** No orchestration engine, no distributed compute, no
  warehouse. It is a small pipeline meant to be read and audited.

## License

MIT, see [LICENSE](LICENSE).
