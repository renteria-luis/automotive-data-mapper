# Data dictionary

Every field of the canonical record, what it means, and where it comes from in each feed.

This document is the specification. `src/models.py` implements it with Pydantic, and once it does,
the file is the authority: if the two disagree, the file is right and this document is a bug.

## Canonical record: `VehicleEvent`

One record is one service or repair event on one vehicle.

| Field | Type | Required | Validation | Meaning |
|---|---|---|---|---|
| `source_id` | `shop_a`, `dealer_b` or `fleet_c` | yes | one of the three feeds | Which feed the record came from |
| `source_record_id` | string | yes | not empty | The identifier the originating system uses, so a record can be traced back to its row |
| `vin` | string | yes | exactly 17 characters, `A-H J-N P R-Z 0-9`, no I, O or Q | Vehicle identification number, uppercased and stripped |
| `vin_valid` | boolean or null | no | none | Whether the ISO 3779 check digit is correct. Null means the check has not been run |
| `event_date` | date | yes | must be a real calendar date | Date the work was done, normalized to ISO 8601 |
| `odometer_km` | integer or null | no | zero or greater | Odometer reading converted to kilometres. Null when the source left it empty |
| `odometer_source_unit` | `km` or `mi` | no | one of the two | The unit the source reported, kept so the conversion can be checked |
| `raw_description` | string | yes | not empty | The original free text, never edited |
| `normalized_description` | string | yes | not empty | Lowercased, whitespace collapsed |
| `provider_name` | string or null | no | none | Shop, dealer or vendor name, after standardizing the spelling variants |
| `provider_city` | string or null | no | none | City |
| `provider_province` | string or null | no | none | Province code |
| `ingested_at` | datetime | yes | none | When the record was read from its file |

The natural key is `source_id` plus `source_record_id`. The same real event arriving from two feeds
produces two records with two keys, which is deliberate: the duplicate stays visible until the
duplicate check decides they are the same event and records why.

## Rejected record: `RejectedRecord`

One record the pipeline could not turn into a `VehicleEvent`.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `source_id` | `shop_a`, `dealer_b` or `fleet_c` | yes | Which feed it came from |
| `source_record_id` | string or null | no | Null when the finding belongs to the feed rather than to one record, which is the case for an unmapped column |
| `reason_code` | `E001` to `E010` | yes | Why it was rejected |
| `detail` | string | yes | What was wrong, in words, for whoever investigates it |
| `raw_record` | object | yes | The original values, so the record can be fixed and reprocessed rather than hunted for in the source file |
| `ingested_at` | datetime | yes | When the record was read |

## Reason codes

| Code | Name | Meaning |
|---|---|---|
| `E001` | `INVALID_VIN_LENGTH` | Not 17 characters |
| `E002` | `INVALID_VIN_CHARS` | Contains I, O or Q, which are not used in VINs |
| `E003` | `INVALID_VIN_CHECKDIGIT` | Position 9 does not match the ISO 3779 checksum |
| `E004` | `MISSING_REQUIRED_FIELD` | A field the schema requires is empty |
| `E005` | `UNPARSEABLE_DATE` | The date does not parse in any known format |
| `E006` | `DATE_OUT_OF_RANGE` | A service date in the future |
| `E007` | `ODOMETER_ROLLBACK` | A later event with a lower reading on the same vehicle |
| `E008` | `ODOMETER_IMPLAUSIBLE` | A reading no vehicle of that age reaches |
| `E009` | `DUPLICATE_EVENT` | The same event already arrived from another feed |
| `E010` | `UNMAPPED_SOURCE_FIELD` | A source field with no canonical target |

## Source to target mapping

The exact column names, paths and element names below are read from the files in `data/raw/`.
Where each format comes from is documented in [SAMPLE_DATA.md](SAMPLE_DATA.md).

### `shop_a`, independent repair shop

`data/raw/shop_a/service_records_20260731.csv`. Comma delimited, header row included, values
containing a comma are quoted. One row is one service line, so several rows can share an invoice
number.

| Canonical field | Source column | Transformation |
|---|---|---|
| `source_record_id` | `RO_INVOICE_NUMBER` | strip |
| `vin` | `VIN` | strip, uppercase |
| `event_date` | `RO_OPEN_DATE` | parse `%m/%d/%Y` |
| `odometer_km` | `MILEAGE` with `ODOMETER_MEASURE` | remove thousands separators, to integer, convert when the measure is `MI`, treat blank and `0` as unknown |
| `odometer_source_unit` | `ODOMETER_MEASURE` | lowercase |
| `raw_description` | `SERVICE_DESCRIPTION` | strip |
| `normalized_description` | `SERVICE_DESCRIPTION` | strip, lowercase, collapse whitespace |
| `provider_name` | `LOCATION_NAME` | strip, standardize the spelling variants |
| `provider_city` | `CITY` | strip |
| `provider_province` | `STATE` | strip, uppercase |

Read and not mapped: `RO_CLOSE_DATE`, `LABOR_DESCRIPTION`, `PART_NAME_DESCRIPTION`,
`PART_QUANTITY`, `MAKE`, `MODEL`, `MODEL_YEAR`, `PLATE`, `PLATE_STATE`, `MANAGEMENT_SYSTEM`,
`LOCATION_ID`, `ADDRESS`, `POSTAL_CODE`, `PHONE`, `URL`.

Most of those are not junk, they are data this schema has no home for yet: the plate and the
make, model and year would matter for record linkage and for checking a VIN decode. Reporting them
as `E010` is how that gap becomes a decision instead of an oversight.

### `dealer_b`, dealership management system

`data/raw/dealer_b/ProcessRepairOrder_20260731.xml`. Every element sits in the default namespace
`http://www.starstandard.org/STAR/5`, so a path without the namespace matches nothing. Each `Job`
inside a `RepairOrderLineItem` is one event.

| Canonical field | Source location | Transformation |
|---|---|---|
| `source_record_id` | `RepairOrderHeader/DocumentID` and `Job/JobID` | join with a dash, for example `RO-100480-J1` |
| `vin` | `RepairOrderLineItem/Vehicle/VehicleID` | strip, uppercase |
| `event_date` | `RepairOrderHeader/RepairOrderOpenedDate` | parse the ISO timestamp with its offset, keep the date |
| `odometer_km` | `InDistanceMeasure` text with its `unitCode` attribute | to integer, convert when `unitCode` is `SMI`, keep as is when `KMT` |
| `odometer_source_unit` | `InDistanceMeasure/@unitCode` | `SMI` becomes `mi`, `KMT` becomes `km` |
| `raw_description` | `Job/CorrectionDescription`, falling back to `Job/CustomerConcernDescription` | strip |
| `normalized_description` | same | strip, lowercase, collapse whitespace |
| `provider_name` | `DealerParty/OrganizationName` | strip, standardize the spelling variants |
| `provider_city` | `DealerParty/CityName` | strip |
| `provider_province` | `DealerParty/StateOrProvinceCountrySubDivisionID` | strip, uppercase |

Read and not mapped: `SecondaryReferenceNumberString`, `ServiceAdvisorParty`, `LocationID`,
`DepartmentType`, `RepairOrderStatus`, `RepairOrderCompletedDate`, `LicenseNumberString`,
`OutDistanceMeasure`, `ServiceLaborOperationCode`, `LaborActualHoursNumeric`, and the whole
`ApplicationArea`.

**The decision that has to be written down:** each job carries two free text fields.
`CustomerConcernDescription` is what the customer said, `CorrectionDescription` is what the
technician did. The vehicle history needs the work performed, so the correction wins and the
concern is only a fallback when the correction is empty. A pipeline that silently picked the first
non-empty of the two would produce a history of complaints instead of repairs.

### `fleet_c`, fleet maintenance aggregator

`data/raw/fleet_c/maintenance_events_2026-07.json`. An envelope with `meta` and `records`.

| Canonical field | Source path | Transformation |
|---|---|---|
| `source_record_id` | `records[].work_order_id` | strip |
| `vin` | `records[].vin` | strip, uppercase |
| `event_date` | `records[].service_date` | parse the ISO 8601 timestamp, keep the date |
| `odometer_km` | `records[].odometer.value` with `.unit` | remove thousands separators, to integer, convert when the unit is `mi`, `null` stays unknown |
| `odometer_source_unit` | `records[].odometer.unit` | lowercase |
| `raw_description` | `records[].description` | strip |
| `normalized_description` | `records[].description` | strip, lowercase, collapse whitespace |
| `provider_name` | `records[].vendor.name` | strip |
| `provider_city` | `records[].vendor.city` | strip |
| `provider_province` | `records[].vendor.region` | strip, uppercase |

Read and not mapped: the whole `meta` block, `records[].plate`, `records[].vendor.id`,
`records[].invoice_total_cad`, `records[].cost_centre`.

## The trap in each feed

| Feed | What breaks a naive reader |
|---|---|
| `shop_a` | `MILEAGE` arrives as `21,000`, quoted because it contains the delimiter, so a plain `int()` raises and `pd.to_numeric` quietly returns nothing. The unit lives in a different column |
| `dealer_b` | The XML namespace. `root.findall("RepairOrder")` returns an empty list and the feed looks empty rather than broken |
| `fleet_c` | `odometer.value` changes type between records: number, string with a comma, and `null` |
