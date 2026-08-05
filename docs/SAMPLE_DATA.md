# Sample data

The three feeds in `data/raw/` hold 50 service events across 12 vehicles. They are synthetic and
written by hand, which means every value in them was chosen. This file is the list of what was
chosen to be wrong.

It exists so that detection can be measured. Knowing that 11 records are unmappable, and which
ones, turns "the pipeline rejected 11 records" into "the pipeline found 11 of the 11 problems that
are there", which is a different claim.

## The vehicles

Twelve VINs, each with a correct ISO 3779 check digit. The first three characters are a real
manufacturer prefix and position 10 is the model year code, so a decoding service resolves the
manufacturer and the year. The middle section is invented, so the model it reports may not match
anything real.

| VIN | Manufacturer prefix | Model year |
|---|---|---|
| `1FTFW1E50KFA12345` | 1FT, Ford, trucks, United States | 2019 |
| `2T1BURHE4JC021345` | 2T1, Toyota, Canada | 2018 |
| `1HGCV1F30LA100234` | 1HG, Honda, United States | 2020 |
| `3VWC57BU8KM052318` | 3VW, Volkswagen, Mexico | 2019 |
| `1G1ZD5ST0LF004821` | 1G1, Chevrolet, United States | 2020 |
| `1C4RJFAG8MC612907` | 1C4, Chrysler group, United States | 2021 |
| `KNDEPCAA2M7533104` | KND, Kia, South Korea | 2021 |
| `2HKRW2H86NH512044` | 2HK, Honda, Canada | 2022 |
| `1N4BL4BV4NC108455` | 1N4, Nissan, United States | 2022 |
| `WBA5R1C54KA018732` | WBA, BMW, Germany | 2019 |
| `1FMCU9J94MUA03917` | 1FM, Ford, multipurpose, United States | 2021 |
| `5YJ3E1EA9KF312876` | 5YJ, Tesla, United States | 2019 |

## Records that cannot be mapped

Eleven records, found while reading. Each one should end up in the rejected-records table with the
code below.

| Record | Feed | What is wrong | Expected code |
|---|---|---|---|
| `RO-1009` | shop_a | VIN has 16 characters, the last one was dropped | `E001` |
| `RO-1010` | shop_a | VIN carries a letter `O` where the check digit `0` belongs | `E002` |
| `FC-7005` | fleet_c | VIN starts with the letter `I` instead of the digit `1` | `E002` |
| `RO-1011` | shop_a | Last two characters transposed, `...345` became `...354` | `E003` |
| `DMS-4410` | dealer_b | Last two characters transposed, `...876` became `...867` | `E003` |
| `RO-1007` | shop_a | Empty work description | `E004` |
| `DMS-4406` | dealer_b | Line item with an empty description | `E004` |
| `RO-1006` | shop_a | Service date reads `n/a` | `E005` |
| `DMS-4408` | dealer_b | Opened date reads `pending` | `E005` |
| `FC-7006` | fleet_c | Date reads `31/31/2024`, a day and month that do not exist | `E005` |
| `RO-1025` | shop_a | Service date is in 2027 | `E006` |

The two transpositions are the reason the check digit is worth implementing. Both VINs are 17
characters long and use only legal characters, so length and character checks accept them. Only the
checksum catches them.

## Problems found after every feed is read

These records map cleanly. They only look wrong next to the rest of the data, so they cannot be
caught while reading a single row.

| Record | Feed | What is wrong | Expected code |
|---|---|---|---|
| `RO-1013` | shop_a | 39,000 miles in March 2024, after 52,880 miles in July 2023 on the same vehicle | `E007` |
| `RO-1015` | shop_a | 998,000 miles, roughly 1.6 million kilometres | `E008` |
| `RO-1024` and `DMS-4407` | shop_a, dealer_b | Same vehicle, same day, same brake job, worded differently, 31,060 km in both | `E009` |
| `RO-1026` and `FC-7012` | shop_a, fleet_c | Same vehicle, same day, same bumper replacement, 122,632 km against 122,600 km | `E009` |

The rollback only shows up after the miles are converted to kilometres, and the two duplicate pairs
only show up after both feeds are read and the units are the same. Neither is visible in one file.

## Source fields with no canonical target

Not broken records, but data that goes nowhere. Reporting them as `E010` is what makes the gap
visible instead of silent.

| Feed | Fields |
|---|---|
| shop_a | `TechnicianID`, `InvoiceTotal` |
| dealer_b | `export_version`, `source_system`, `pay_type`, `op_code`, `labour_hours` |
| fleet_c | `MaintenanceExport/@provider`, `MaintenanceExport/@version`, `Event/@cost` |

## Values that are messy but valid

These must be normalized, not rejected. A pipeline that rejects them is as wrong as one that
accepts a broken VIN.

| Case | Where | What has to happen |
|---|---|---|
| Second date format `22-Aug-23` | `RO-1004` | Parse it as well as `MM/DD/YYYY` |
| Day-first dates | every fleet_c record | `07/06/2024` is 7 June, not 6 July |
| Lowercase VIN | `DMS-4405` | Uppercase it before validating |
| Leading and trailing spaces in the description | `RO-1026` | Strip them |
| Odometer in miles | all of shop_a, plus `FC-7003` and `FC-7008` | Convert to kilometres and keep the original unit |
| Odometer missing | `RO-1005`, `DMS-4404`, `FC-7007` | Keep the record, leave the field empty. The odometer is optional, so a missing reading is an incomplete record and not a rejected one |
| Shop name typed four ways | shop_a | `Riverside Auto Repair`, `RIVERSIDE AUTO REPAIR`, `Riverside Auto Repair Inc.` and `riverside auto repair` are one business |
| Dealer name typed three ways | dealer_b | `Forest City Motors`, `FOREST CITY MOTORS` and `Forest City Motors Ltd` are one business |
| One repair order, several line items | `DMS-4402`, `DMS-4409` | Each line item is its own event |
| Description in capitals | `RO-1008` | Lowercase it in the normalized field, keep the original |

## Totals

| | Count |
|---|---|
| Records across the three feeds | 50 |
| shop_a rows | 26 |
| dealer_b line items | 12, inside 10 repair orders |
| fleet_c events | 12 |
| Vehicles | 12 |
| Rejected while reading | 11 |
| Records that map to the canonical schema | 39 |
| Of those, flagged by the checks that need the whole dataset | 4, being 2 duplicate pairs, 1 rollback and 1 implausible reading |
