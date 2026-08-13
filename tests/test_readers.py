# tests/test_readers.py
from src.readers import read_dealer_b, read_fleet_c, read_shop_a


def test_shop_a_row_count():
    assert len(read_shop_a()) == 42


def test_dealer_b_keeps_every_job():
    assert len(read_dealer_b()) == 27


def test_fleet_c_matches_its_declared_total():
    assert len(read_fleet_c()) == 28