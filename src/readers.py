# src/readers.py

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from src import paths


def read_shop_a(path: Path = paths.SHOP_A) -> pd.DataFrame:
    return pd.read_csv(path)


def read_dealer_b(path: Path = paths.DEALER_B) -> pd.DataFrame:
    root = ET.parse(path).getroot()
    ns = {'star': root.tag.split('}')[0].strip('{')}

    rows = []

    for order in root.findall('.//star:RepairOrder', ns):
        distance = order.find('.//star:InDistanceMeasure', ns)

        header = {
            'DocumentID': order.findtext('.//star:DocumentID', default=None, namespaces=ns),
            'VehicleID': order.findtext('.//star:VehicleID', default=None, namespaces=ns),
            'RepairOrderOpenedDate': order.findtext(
                './/star:RepairOrderOpenedDate', default=None, namespaces=ns
            ),
            'InDistanceMeasure': distance.text.strip() if distance is not None else None,
            'unitCode': distance.get('unitCode') if distance is not None else None,
            'OrganizationName': order.findtext(
                './/star:OrganizationName', default=None, namespaces=ns
            ),
            'CityName': order.findtext('.//star:CityName', default=None, namespaces=ns),
            'StateOrProvinceCountrySubDivisionID': order.findtext(
                './/star:StateOrProvinceCountrySubDivisionID',
                default=None,
                namespaces=ns
            ),
        }

        for job in order.findall('.//star:Job', ns):
            rows.append({
                **header,
                'JobID': job.findtext('star:JobID', default=None, namespaces=ns),
                'CustomerConcernDescription': job.findtext(
                    'star:CustomerConcernDescription',
                    default=None,
                    namespaces=ns
                ),
                'CorrectionDescription': job.findtext(
                    'star:CorrectionDescription',
                    default=None,
                    namespaces=ns
                ),
            })

    return pd.DataFrame(rows)


def read_fleet_c(path: Path = paths.FLEET_C) -> pd.DataFrame:
    with open(path, encoding='utf-8') as f:
        doc = json.load(f)

    df = pd.json_normalize(doc['records'], sep='.')

    if len(df) != doc['meta']['total_records']:
        raise ValueError('Record count does not match metadata')

    return df


READERS = {
    'shop_a': read_shop_a,
    'dealer_b': read_dealer_b,
    'fleet_c': read_fleet_c,
}
