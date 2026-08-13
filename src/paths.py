# src/paths.py
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

SHOP_A = RAW / "shop_a" / "service_records_20260731.csv"
DEALER_B = RAW / "dealer_b" / "ProcessRepairOrder_20260731.xml"
FLEET_C = RAW / "fleet_c" / "maintenance_events_2026-07.json"