# Data dictionary

Every field of the canonical record, what it means, and where it comes from in each feed.

The schema is defined in `src/models.py` and enforced by Pydantic. This document and that file have
to agree. If they disagree, the file is right and this document is a bug.

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

### `shop_a`, independent repair shop

CSV, `data/raw/shop_a/service_records.csv`, one row per event.

| Canonical field | Source column | Transformation |
|---|---|---|
| `source_record_id` | `RO_Number` | strip |
| `vin` | `VehicleID` | strip, uppercase |
| `event_date` | `SvcDate` | parse with `%m/%d/%Y`, then `%d-%b-%y` |
| `odometer_km` | `Miles` | to integer, multiply by 1.609344, round |
| `odometer_source_unit` | constant | `mi` |
| `raw_description` | `WorkPerformed` | strip |
| `normalized_description` | `WorkPerformed` | strip, lowercase, collapse whitespace |
| `provider_name` | `ShopName` | strip, standardize the spelling variants |
| `provider_city` | `City` | strip |
| `provider_province` | `Prov` | strip, uppercase |

Not mapped: `TechnicianID`, `InvoiceTotal`.

### `dealer_b`, dealership management system

JSON, `data/raw/dealer_b/repair_orders.json`. Line items are nested inside repair orders, so one
order with two line items becomes two events that share a VIN, a date and an odometer reading.

| Canonical field | Source path | Transformation |
|---|---|---|
| `source_record_id` | `repair_orders[].ro_id` and `lines[].line_no` | join with a dash, for example `DMS-4402-2` |
| `vin` | `repair_orders[].vin` | strip, uppercase |
| `event_date` | `repair_orders[].opened_at` | parse the ISO timestamp, keep the date |
| `odometer_km` | `repair_orders[].odometer.value` | to integer, already kilometres |
| `odometer_source_unit` | `repair_orders[].odometer.uom` | lowercase |
| `raw_description` | `lines[].description` | strip |
| `normalized_description` | `lines[].description` | strip, lowercase, collapse whitespace |
| `provider_name` | `repair_orders[].dealer.name` | strip, standardize the spelling variants |
| `provider_city` | `repair_orders[].dealer.city` | strip |
| `provider_province` | `repair_orders[].dealer.province` | strip, uppercase |

Not mapped: `export_version`, `source_system`, `pay_type`, `lines[].op_code`, `lines[].labour_hours`.

### `fleet_c`, fleet provider

XML, `data/raw/fleet_c/maintenance_events.xml`. Most values are attributes rather than element
text, which is the reason this feed is here.

| Canonical field | Source location | Transformation |
|---|---|---|
| `source_record_id` | `Event/@id` | strip |
| `vin` | `Event/@vin` | strip, uppercase |
| `event_date` | `Event/@date` | parse with `%d/%m/%Y`, day first |
| `odometer_km` | `Event/@odometer` with `Event/@units` | to integer, convert when the unit is `MI` |
| `odometer_source_unit` | `Event/@units` | lowercase |
| `raw_description` | `Event/Description` text | strip |
| `normalized_description` | `Event/Description` text | strip, lowercase, collapse whitespace |
| `provider_name` | `Event/Vendor/@name` | strip |
| `provider_city` | `Event/Vendor/@city` | strip |
| `provider_province` | `Event/Vendor/@region` | strip, uppercase |

Not mapped: `MaintenanceExport/@provider`, `MaintenanceExport/@version`, `Event/@cost`.

Note the trap in this feed: `07/06/2024` is 7 June 2024. Reading it with a month-first parser
produces 6 July, a date that is real, so nothing fails and the record is quietly wrong. That is why
the date format belongs to the mapping specification of each feed rather than to a shared guess.
