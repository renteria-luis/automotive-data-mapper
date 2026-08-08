# Sample data

Three feeds, 97 records, 24 vehicles. They are fixtures written for this project, but the formats
are not invented: each one follows a specification that a real automotive data feed uses, and the
sources are listed below so any claim about them can be checked.

Every defect in the files was placed on purpose. This document is the list. It exists so detection
can be measured: knowing that 10 records are unmappable, and which ones, turns "the pipeline
rejected 10 records" into "the pipeline found 10 of the 10 problems that are there".

## Where the formats come from

| Feed | Format | Modelled on | Where to look |
|---|---|---|---|
| `shop_a` | CSV | The column names and their meaning come from the CARFAX Service Data Transfer file that a shop management system uploads | [amattu2/CARFAX-Wrapper](https://github.com/amattu2/CARFAX-Wrapper), `src/FTP.php`, the `HEADER_FIELDS` constant around line 54 for the 24 column names |
| `dealer_b` | XML | The STAR RepairOrder schema used for dealer management system exchange | [STAR 5.3.4 schema documentation](https://schemas.liquid-technologies.com/STAR/5.3.4/repairorder_xsd.html) for the element names, and [ProcessRepairOrder.xsd](https://schemas.liquid-technologies.com/STAR/5.3.4/processrepairorder_xsd.html) for the document wrapper |
| `fleet_c` | JSON | A REST export from a fleet maintenance aggregator: envelope with paging metadata, nested vendor, ISO 8601 timestamps | No public specification. This one is a reasonable modern API shape, not a standard |

Two honest notes about `dealer_b`. The element names taken from the published schema documentation
are `DealerParty`, `ServiceAdvisorParty`, `LocationID`, `Vehicle`, `LicenseNumberString`,
`InDistanceMeasure`, `OutDistanceMeasure`, `RepairOrderOpenedDate`, `RepairOrderCompletedDate`,
`Job`, `LaborActualHoursNumeric`, `RepairOrderStatus`, `DepartmentType` and
`SecondaryReferenceNumberString`. The names inside `Job`, such as `CustomerConcernDescription` and
`CorrectionDescription`, are chosen here and not verified against the schema. And the file is
modelled on STAR, it is not a schema valid STAR document.

## The three feeds

### `shop_a`, independent repair shop

`data/raw/shop_a/service_records_20260731.csv`, 42 data rows.

The 24 columns are the ones a shop management system sends to CARFAX. The real transfer file is
pipe delimited; this fixture is comma delimited CSV, which is one of the three formats the project
handles and which brings its own problem: `21,000` and `Lube oil and filter, 5W30 synthetic` both
contain commas, so they are quoted, and a reader that splits on commas instead of parsing CSV
shifts every column after them.

Dates are `MM/DD/YYYY`. `ODOMETER_MEASURE` says whether `MILEAGE` is in `MI` or `KM`, which is the
reason a service feed cannot assume a unit. The shop runs Protractor and reports mostly in
kilometres, but a handful of rows come through in miles.

### `dealer_b`, dealership management system

`data/raw/dealer_b/ProcessRepairOrder_20260731.xml`, 22 repair orders holding 27 jobs.

The document has a default XML namespace, so `findall("RepairOrder")` finds nothing until the
namespace is handled. Odometer readings are `InDistanceMeasure` and `OutDistanceMeasure` with a
`unitCode` attribute: `KMT` for kilometres, `SMI` for statute miles. Each `Job` inside a repair
order is one service event, so one order can produce three.

Each job carries two free text fields: what the customer said and what the technician did.
`CustomerConcernDescription` reads "Grinding noise when braking", `CorrectionDescription` reads
"R&R rear brake pads, resurface rotors". Deciding which one describes the service is a mapping
decision, and it has to be written down.

### `fleet_c`, fleet maintenance aggregator

`data/raw/fleet_c/maintenance_events_2026-07.json`, 28 records.

An envelope with a `meta` block and a `records` array. Timestamps are ISO 8601 in UTC, the odometer
is an object with `value` and `unit`, and `value` arrives sometimes as a number, sometimes as a
string with a thousands separator, and sometimes as `null`.

## Records that cannot be mapped

Ten records, all detectable while reading. This is about 10 percent of the file, which is what a
feed of this kind actually looks like.

| Record | Feed | What is wrong | Expected code |
|---|---|---|---|
| `184227` | shop_a | VIN truncated to 16 characters | `E001` |
| `184209` | shop_a | VIN carries the letter `O` where the check digit belongs | `E002` |
| `RO-100494` job 1 | dealer_b | Two adjacent VIN characters transposed | `E003` |
| `184269` | shop_a | `SERVICE_DESCRIPTION` empty | `E004` |
| `RO-100557` job 1 | dealer_b | Job carries neither a customer concern nor a correction | `E004` |
| `WO-2026-4180` | fleet_c | `description` is `null` | `E004` |
| `184278` | shop_a | `RO_OPEN_DATE` is `00/00/0000` | `E005` |
| `WO-2026-4145` | fleet_c | `service_date` is 30 February | `E005` |
| `RO-100536` job 1 | dealer_b | Repair order opened in 2027 | `E006` |
| `184302` | shop_a | The same row submitted twice, an integration retry | `E009` |

The transposed VIN is the one that matters. It is 17 characters long and uses only legal
characters, so a length check and a character check both accept it. Only the ISO 3779 check digit
catches it.

## Problems that only appear once every feed is read

| Records | What is wrong | Expected code |
|---|---|---|
| `WO-2026-4240` against `184215` | The fleet provider reports 46,740 km in February 2025 on a vehicle that showed 71,240 km at the shop a year earlier | `E007` |
| `WO-2026-4205` | 994,120 km on a 2021 Golf | `E008` |
| `WO-2026-4235` and `184233` | Same vehicle, same day, same repair, worded differently by the shop and by the fleet provider | `E009` |

There is a fourth case worth noticing, and it is the most instructive one. Because
`WO-2026-4205` reports 994,120 km, the next genuine reading on that vehicle looks like a rollback.
A pipeline that flags symptoms will report two problems where there is one. Fixing the implausible
reading makes the false rollback disappear, and that ordering is the point.

## Values that are messy but valid

These have to be normalized, not rejected. A pipeline that rejects them is as wrong as one that
accepts a broken VIN.

| Case | Where | What has to happen |
|---|---|---|
| Odometer in miles | Lines with `ODOMETER_MEASURE` of `MI`, and `unitCode="SMI"` in the XML, and `"unit": "mi"` in the JSON | Convert to kilometres and keep the unit the source reported |
| Odometer with a thousands separator | shop_a `MILEAGE` such as `21,000`, quoted because of the comma, and fleet_c `"value": "44,032"` | Strip the separator before converting to a number |
| Odometer blank or zero | `184242` blank, `184251` zero, `WO-2026-4130` and `WO-2026-4165` null | Keep the record with an empty odometer. A missing reading makes a record incomplete, not invalid |
| Lowercase VIN | One fleet_c record | Uppercase before validating |
| Trailing spaces in the description | Several shop_a rows | Strip |
| Shop name typed three ways | `Riverside Auto Service`, `RIVERSIDE AUTO SERVICE`, `Riverside Auto Service Ltd` | One business, one standardized name |
| Dealer name typed three ways | `Forest City Motors`, `FOREST CITY MOTORS`, `Forest City Motors Ltd` | Same |
| Plate and province blank | Several shop_a rows | Optional fields, leave empty |
| `MODEL_YEAR` blank | `184290`, `184308` | Optional, and the model year is also recoverable from position 10 of the VIN |
| Repair order still open | `184260` has no `RO_CLOSE_DATE` | Use the open date, and record that the close date was missing |
| XML namespace | Every element in dealer_b | Handle the namespace or find nothing at all |
| One order, several jobs | Several dealer_b orders | Each job is its own event |

## Totals

| | Count |
|---|---|
| Records across the three feeds | 97 |
| shop_a rows | 42 |
| dealer_b jobs, inside 22 repair orders | 27 |
| fleet_c records | 28 |
| Vehicles | 24, all with a correct ISO 3779 check digit |
| Rejected while reading | 10 |
| Mapped to the canonical schema | 87 |
| Of those, flagged by the checks that need every feed | 3, being 1 rollback, 1 implausible reading and 1 cross feed duplicate |
| Mapped but incomplete, with no odometer | 4 |
