# src/mappers.py

"""One mapper per feed. Row in, canonical payload out.

Structure and cleaning only. Nothing is rejected here on purpose: if mapping could also reject,
reason codes would come from two places and neither would hold the full list.
"""

from datetime import datetime, timezone

from src.transforms import clean, normalize, standardize_provider, to_km

# computed once, and the same timestamp is used for all of the mapped records
INGESTED_AT = datetime.now(timezone.utc)

UNIT_BY_CODE = {'KMT': 'km', 'SMI': 'mi'}


def map_shop_a(row) -> dict:
    source_record_id = clean(row['RO_INVOICE_NUMBER'])
    vin = clean(row['VIN'])
    unit = normalize(row['ODOMETER_MEASURE'])
    odometer_km = to_km(row['MILEAGE'], unit)
    raw_description = clean(row['SERVICE_DESCRIPTION'])
    normalized_description = normalize(raw_description)
    provider_name = standardize_provider(row['LOCATION_NAME'])
    provider_city = clean(row['CITY'])
    provider_province = (clean(row['STATE']) or '').upper() or None

    try:
        event_date = datetime.strptime(str(row['RO_OPEN_DATE']).strip(), '%m/%d/%Y').date().isoformat()
    except ValueError:
        event_date = clean(row['RO_OPEN_DATE'])

    return {
        'source_id': 'shop_a',
        'source_record_id': source_record_id,
        'vin': vin,
        'event_date': event_date,
        'odometer_km': odometer_km,
        'odometer_source_unit': unit,
        'raw_description': raw_description,
        'normalized_description': normalized_description,
        'provider_name': provider_name,
        'provider_city': provider_city,
        'provider_province': provider_province,
        'ingested_at': INGESTED_AT,
    }


def map_dealer_b(row) -> dict:
    """
    considerations:
    - event id not exist in the file, it is built from the order and the job id.
    - the correction wins over the customer concern.
    """
    source_record_id = f"{clean(row['DocumentID'])}-{clean(row['JobID'])}"
    vin = clean(row['VehicleID'])
    unit = UNIT_BY_CODE.get(row['unitCode'])
    odometer_km = to_km(row['InDistanceMeasure'], unit)
    raw_description = clean(row['CorrectionDescription']) or clean(row['CustomerConcernDescription'])
    normalized_description = normalize(raw_description)
    provider_name = standardize_provider(row['OrganizationName'])
    provider_city = clean(row['CityName'])
    provider_province = (clean(row['StateOrProvinceCountrySubDivisionID']) or '').upper() or None

    try:
        event_date = datetime.fromisoformat(str(row['RepairOrderOpenedDate'])).date().isoformat()
    except (ValueError, TypeError):
        event_date = clean(row['RepairOrderOpenedDate'])

    return {
        'source_id': 'dealer_b',
        'source_record_id': source_record_id,
        'vin': vin,
        'event_date': event_date,
        'odometer_km': odometer_km,
        'odometer_source_unit': unit,
        'raw_description': raw_description,
        'normalized_description': normalized_description,
        'provider_name': provider_name,
        'provider_city': provider_city,
        'provider_province': provider_province,
        'ingested_at': INGESTED_AT,
    }


def map_fleet_c(row) -> dict:
    source_record_id = clean(row['work_order_id'])
    vin = clean(row['vin'])
    unit = normalize(row['odometer.unit'])
    odometer_km = to_km(row['odometer.value'], unit)
    raw_description = clean(row['description'])
    normalized_description = normalize(raw_description)
    provider_name = standardize_provider(row['vendor.name'])
    provider_city = clean(row['vendor.city'])
    provider_province = (clean(row['vendor.region']) or '').upper() or None

    try:
        stamp = str(row['service_date']).replace('Z', '+00:00')
        event_date = datetime.fromisoformat(stamp).date().isoformat()
    except ValueError:
        event_date = str(row['service_date'])[:10]

    return {
        'source_id': 'fleet_c',
        'source_record_id': source_record_id,
        'vin': vin,
        'event_date': event_date,
        'odometer_km': odometer_km,
        'odometer_source_unit': unit,
        'raw_description': raw_description,
        'normalized_description': normalized_description,
        'provider_name': provider_name,
        'provider_city': provider_city,
        'provider_province': provider_province,
        'ingested_at': INGESTED_AT,
    }


MAPPERS = {
    'shop_a': map_shop_a,
    'dealer_b': map_dealer_b,
    'fleet_c': map_fleet_c,
}