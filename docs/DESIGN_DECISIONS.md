# Design decisions

What was decided, why, what was rejected, and what the choice costs. Entries are added when the
decision is taken rather than reconstructed at the end.

Technical terms are explained in plain language the first time they appear.

---

### DD-001. Build a working MVP first, and let the README say what is real

**Decision.** Phase 1 is a small pipeline that does one job end to end: read three feeds, map them
to one schema, and separate what it can map from what it cannot. Everything else is designed in
`PLAN.md` and marked in the README as not built.

**Why.** A narrow thing that runs is worth more than a wide thing that almost runs, and it can be
explained in full. The status markers keep the README accurate while the code is unfinished, which
is exactly when a reader is most likely to be misled.

**Alternative rejected.** Building all the phases at once. Every one of them would be half done at
the deadline, and none of them would be demonstrable.

**Cost.** The README and the plan have to be edited alongside the code in every phase.

### DD-002. One file describes the project: `pyproject.toml`

**Decision.** Project name, version, supported Python versions, dependencies and the settings for
the test runner live in a single `pyproject.toml`.

**Why.** It is the current Python standard, and one file means one place to look. The older layout
spreads the same information across `setup.py`, `requirements.txt`, `pytest.ini` and `.flake8`, and
those drift apart.

**Alternative rejected.** A plain `requirements.txt`. Simpler, but it only lists dependencies. It
cannot describe the project or configure the tools.

**Cost.** The project has to be installed once with `pip install -e .`. The `-e` flag means
editable: Python reads the code from the working directory, so edits take effect immediately and a
notebook can import from `src/` without touching `sys.path`.

### DD-003. No style linter while the work lives in a notebook

**Decision.** The project started with Ruff checking style and formatting across the whole
repository. It was removed. Tests are the only automated check for now.

**Why.** A linter reads code without running it and reports style problems and likely mistakes.
That is worth having over a stable codebase. It is the wrong tool over exploratory notebook cells,
where a comment written while thinking gets blocked for a trailing space and the cost lands on
every commit during the phase where the work changes fastest.

**Alternative rejected.** Keeping Ruff and excluding `notebooks/` from it. That works and is where
this will probably end up, but `src/` is nearly empty right now, so the rule set would be guarding
almost nothing while still needing to be maintained.

**Cost.** Style drifts until the linter comes back. It comes back when `src/` holds the pipeline
and the first tests exist.

### DD-004. Continuous integration runs the tests

**Decision.** GitHub Actions runs the test suite on every push. `make test` runs the same command
locally.

**Why.** Continuous integration here means a clean machine repeating the checks after every push.
It is only useful if the command matches the one used while working, otherwise the failures are
about the environment rather than the code.

**Alternative rejected.** Trusting local runs, which get skipped on the days with the most changes.

**Cost.** A minute of machine time per push, and the workflow file and the `Makefile` have to be
kept in step. Until the first test module exists, the step accepts pytest's "no tests collected"
result instead of failing on it.

### DD-005. The sample data is written by hand, and every defect is documented

**Decision.** The three feeds are 97 records written by hand, not generated. `docs/SAMPLE_DATA.md`
lists every deliberate defect and the record it belongs to.

**Why.** Ninety seven records is enough to show every problem the pipeline has to handle and small enough
that every row can be read and understood. The documented list is what makes detection measurable:
the pipeline can be scored against a known total instead of an estimate, so "10 records rejected"
becomes "10 of the 10 problems that exist".

**Alternative rejected.** A generator producing thousands of rows with random defects. More data,
but nobody can say what is in it without running something, and volume proves nothing here.

**Cost.** Adding a new kind of defect means editing a file by hand and updating the list.

### DD-006. Records that fail are data, not errors

**Decision.** The pipeline produces two tables. Records that map become `VehicleEvent` rows.
Records that do not become `RejectedRecord` rows carrying a reason code, a readable detail and the
original payload.

**Why.** A record that is dropped silently is invisible, and a record that is only logged is
findable but not countable. Keeping failures as rows makes them countable, groupable by cause and
by feed, and fixable: the payload travels with the reason, so the record can be corrected and put
back through instead of being hunted down in the source file.

**Alternative rejected.** Raising an exception and stopping, or writing a warning to a log. The
first makes one bad row block a whole feed, the second buries the problem in text nobody groups.

**Cost.** Every failure path has to choose a reason code, so the list of codes has to stay small
and meaningful.

### DD-007. pandas reshapes the data, Pydantic decides what is valid

**Decision.** pandas reads and reshapes the three feeds into one table. Pydantic validates each
record before it is accepted.

**Why.** They are good at different things. pandas is built for whole-column work, renaming and
converting many values at once, and it is happy to hold a null or a bad string in a column without
complaining. Pydantic is built for one record at a time, and when a record fails it says which
field failed and why, which is exactly what a reason code needs. Using pandas for the reshaping and
Pydantic for the verdict keeps each of them doing what it is good at.

**Alternative rejected.** Validating with pandas alone, using conditions on columns. It works until
a record fails two rules at once and the report has to explain which one mattered.

**Cost.** The records cross a boundary between a table and a list of objects, which is one
conversion step that has to be written and understood.

### DD-008. Exploration in a notebook, code that survives in `src/`

**Decision.** Work starts in a notebook under `notebooks/`. When a piece of it stops changing, it
moves into `src/` as a function with a test, and the notebook imports it from there.

**Why.** Reading an unfamiliar feed is guesswork at first, and a notebook is the right place to
guess: run a cell, look at the output, adjust. But a notebook is a bad place to keep code, because
cells run in whatever order they were last run in and nothing tests them. Moving the settled parts
out keeps the exploration honest and the code reproducible.

**Alternative rejected.** Keeping the whole pipeline in the notebook. Faster today, and impossible
to test or rerun reliably tomorrow.

**Cost.** The same code exists in two places for a short while, and the kernel has to be restarted
after each move.



# Redesign After First Phase

**RD-001:** make `to_km` able to distinguish missing odometer values `NaN`/`null` from unreadable values `twenty thousand` so format failures are visible.

**RD-002:** Make mapping dictionaries the single source of truth for column-to-field mappings, right now they're just useful  for `assert`'s and `E010`

**RD-003:** make `vin_valid` actually work.

**RD-004:** Detect unknown XML elements so schema changes are not silently ignored, right now we manually extract from the XML only what we need: loop through all tags.

**RD-005:** Preserve the original raw record for accepted data to maintain traceability, right now only `RejectedRecord` have them.

**RD-006:** Detect feed-level date-format issues by analyzing failure rates across the full feed 8% failures => bad records | 40% failures => feed format [read feed]

**RD-007:** Keep one primary rejection code per record while allowing additional codes later if needed.

**RD-008:** Use controlled categories **(taxonomy)** instead of free-text descriptions for cross-feed duplicate detection, right now I can detect duplicates by `VIN + date + description` but `differential fluid change` and `diff fluid change f/r` are the same and they wouldn't be marked as duplicated.

**RD-009:** Design algorithm for `IMPLAUSIBLE_KM` using car year and historical general data to flag it, right now it uses 500,000 hardcoded
