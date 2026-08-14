# automotive-data-mapper

Vehicle service records arrive from three systems in three different formats. This project maps
them into one canonical schema and separates the records it can map from the ones it cannot, with a
reason for every rejection.

> **Status: the pipeline is being written.** The three readers and the mapping rules are in
> `src/` with tests. The canonical schema and the validation step are being written now. The
> whole dataset checks and the report are specified and not built.
>
> Every claim in this README corresponds to something in this repository. Nothing is marked done
> before it runs, and no metric is written by hand.

| Marker | Meaning |
|---|---|
| ✅ | Implemented, and covered by a test or a real run |
| 🚧 | In progress |
| 📋 | Designed, not built |

## The problem

The same event, "replaced front brake pads", arrives from an independent shop as a CSV row, from a
dealership as a job inside a namespaced XML repair order, and from a fleet provider as a record in
a JSON export. Field names differ. Dates come in three formats and one of them does not parse. The
odometer is sometimes miles and sometimes kilometres, sometimes written with a thousands separator,
sometimes empty, and occasionally lower than the reading from the year before.

A record that is mapped wrong is worse than a record that is missing, because nothing downstream
knows it is wrong. So the work is in what happens to the records that do not fit: they have to be
caught, given a reason, counted, and grouped by cause so the cause can be fixed.

## The data

`data/raw/` holds 97 records across 24 vehicles in three formats. They are fixtures written for
this project, and each format follows a real specification, cited in
[docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md).

Every defect in them is deliberate. Ten records cannot be mapped at all, and the rest carry the
ordinary mess of a real feed: an odometer written as `21,000`, a unit that changes between records,
a shop name typed three ways. SAMPLE_DATA.md lists every defect and the record it belongs to, which
is what makes a detection rate a measurement rather than an estimate.

## Status

| Component | Status |
|---|---|
| Sample feeds in three formats, with every defect documented | ✅ |
| Canonical schema, source to target mapping and reason codes, specified | ✅ |
| Tooling: packaging, tests, CI | ✅ |
| Readers for CSV, namespaced XML and nested JSON | ✅ |
| Source to target mapping dictionaries, audited against the files | ✅ |
| Canonical schema implemented in Pydantic | 🚧 |
| Unit, date and text normalization | 🚧 |
| Validation and the rejected records table | 🚧 |
| Whole dataset checks: duplicates, odometer rollback, implausible readings | 📋 |
| Report of coverage and rejections by reason code | 📋 |
| Service taxonomy and rule based classification | 📋 |
| VIN decoding against a public API | 📋 |
| Human review of low confidence records | 📋 |

The reason codes and the canonical fields are specified in
[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) and are not repeated here, so there is one place
to change when they change.

## Metrics

🚧 Not available yet. This section is filled from the pipeline's own output once the pipeline runs.

## How the work is organised

Exploration happens in `notebooks/`. When a piece of it works and stops changing, it moves into
`src/` as a function with a test, and the notebook imports it from there instead of keeping its own
copy.

That has happened three times so far: `readers.py` reads the three feeds, `mappings.py` holds the
source to target mapping for each one, and `profiling.py` counts nulls, distinct values and stray
whitespace. The mapping tests are the audit: they fail if a dictionary and its file stop agreeing
on which fields exist.

## Running it

```bash
make install              # creates .venv and installs the project in editable mode
source .venv/bin/activate
make test                 # pytest, the same command CI runs
make kernel               # registers this environment as a Jupyter kernel
```

There is no pipeline entry point yet.

## Documentation

| Document | Contents |
|---|---|
| [PLAN.md](PLAN.md) | The architecture, and the phases that are not built |
| [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | Every canonical field, its source in each feed, and the reason codes |
| [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md) | Every deliberate defect, by record |
| [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) | Each decision, its reason, the alternative rejected, and its cost |

## Scope

- The service records are synthetic. No real customer or vehicle data is used.
- The 24 VINs carry correct ISO 3779 check digits and real manufacturer prefixes. The broken ones
  are broken on purpose.
- This is a small pipeline meant to be read and audited. No orchestration engine, no distributed
  compute, no warehouse.

## License

MIT, see [LICENSE](LICENSE).