# src/transforms.py

import re

import pandas as pd


def clean(value) -> str | None:
    """Stripped text, or None when the value is missing or blank after stripping."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value).strip() or None


def to_km(value, unit: str | None) -> int | None:
    """Odometer to whole kilometres. Blank, zero and unparseable all mean unknown."""
    text = clean(value)
    if text is None:
        return None
    text = text.replace(',', '')
    try:
        number = int(float(text))  # int('1200.0') would not pass
    except ValueError:
        return None  # cannot convert? => None
    if number == 0:
        return None
    return round(number * 1.609344) if unit == 'mi' else number


def normalize(text) -> str | None:
    """Lowercased, whitespace collapsed. Input to the phase two taxonomy."""
    text = clean(text)
    if text is None:
        return None
    return re.sub(r'\s+', ' ', text).lower() or None


# hardcode mapping of provider names to a single canonical spelling, for the phase two taxonomy
PROVIDER_NAMES = {
    'riverside auto service': 'Riverside Auto Service',
    'riverside auto service ltd': 'Riverside Auto Service',
    'forest city motors': 'Forest City Motors',
    'forest city motors ltd': 'Forest City Motors',
}


def standardize_provider(name) -> str | None:
    """One business, one spelling. Three variants of each name arrive in the feeds."""
    text = clean(name)
    if text is None:
        return None
    return PROVIDER_NAMES.get(normalize(text), text)