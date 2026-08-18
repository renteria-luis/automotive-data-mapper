from src.transforms import clean, normalize, standardize_provider, to_km


def test_to_km_strips_the_thousands_separator():
    assert to_km('21,000', 'km') == 21000


def test_to_km_converts_miles():
    assert to_km('30733', 'mi') == 49460


def test_to_km_treats_blank_and_zero_as_unknown():
    """A vehicle in for service does not have zero kilometres, so a zero is a system default."""
    assert to_km(None, 'km') is None
    assert to_km('0', 'km') is None
    assert to_km('', 'km') is None


def test_to_km_returns_none_for_a_value_it_cannot_read():
    """Known limitation: this is indistinguishable from a missing reading. See DESIGN_DECISIONS."""
    assert to_km('twenty thousand', 'km') is None


def test_normalize_collapses_whitespace_and_lowercases():
    assert normalize('  Replace  FRONT brake pads ') == 'replace front brake pads'


def test_standardize_provider_collapses_the_spelling_variants():
    for variant in ('Riverside Auto Service', 'RIVERSIDE AUTO SERVICE', 'Riverside Auto Service Ltd'):
        assert standardize_provider(variant) == 'Riverside Auto Service'


def test_clean_returns_none_for_blank_text():
    assert clean('   ') is None
