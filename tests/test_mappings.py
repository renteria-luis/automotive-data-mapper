from src.mappings import DEALER_B_MAP, FLEET_C_MAP, SHOP_A_MAP
from src.readers import read_dealer_b, read_fleet_c, read_shop_a


def test_shop_a_map_matches_the_file():
    assert set(SHOP_A_MAP) == set(read_shop_a().columns)


def test_dealer_b_map_matches_the_reader():
    assert set(DEALER_B_MAP) == set(read_dealer_b().columns)


def test_fleet_c_map_matches_the_reader():
    assert set(FLEET_C_MAP) == set(read_fleet_c().columns)