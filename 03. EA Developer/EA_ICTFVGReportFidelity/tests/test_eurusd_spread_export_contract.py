from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "research" / "export_fivepercent_eurusd_spread_evidence.py"


def test_exporter_is_read_only_and_bound_to_frozen_scope():
    text = EXPORTER.read_text(encoding="utf-8")
    assert 'EXPECTED_SERVER = "FivePercentOnline-Real"' in text
    assert 'EXPECTED_COMPANY = "Five Percent Online Ltd"' in text
    assert 'SYMBOL = "EURUSD"' in text
    assert 'DEFAULT_FROM = "2019.01.01"' in text
    assert 'DEFAULT_TO = "2022.12.31"' in text
    assert "mt5.copy_rates_range" in text
    assert "order_send" not in text
    assert "terminal.trade_allowed" in text
    assert "ACCOUNT_TRADE_MODE_DEMO" in text


def test_exporter_fails_cost_gate_on_material_zero_spread_rows():
    text = EXPORTER.read_text(encoding="utf-8")
    assert "MAX_ZERO_SPREAD_RATIO = 0.001" in text
    assert '"spread_column_usable_as_cost": spread_usable' in text
    assert '"promotion_eligible": False' in text
    assert '"orders_sent": 0' in text
    assert '"positions_opened": 0' in text
