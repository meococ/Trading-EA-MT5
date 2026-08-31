from pathlib import Path
import importlib.util
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "execution_data_qfsi_nolive_capture.py"
SPEC = importlib.util.spec_from_file_location("qfsi_capture", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_quote_only_mode_skips_account_history_call_site():
    source = SOURCE.read_text(encoding="utf-8")
    assert '"--skip-account-history"' in source
    assert "if args.skip_account_history" in source
    assert re.search(
        r"commission_paths\s*=\s*\(\s*\{\}\s*if args\.skip_account_history\s*else export_commission_lifecycles",
        source,
        re.S,
    )


def test_capture_surface_remains_read_only():
    source = SOURCE.read_text(encoding="utf-8")
    forbidden = (
        "mt5.order_send",
        "OrderSend(",
        "mt5.positions_get",
        "TRADE_ACTION",
    )
    for token in forbidden:
        assert token not in source
    assert "symbol_info_tick" in source
    assert "copy_ticks_range" in source
    assert '"orders_sent": 0' in source
    assert '"live_trading_authorized": False' in source


def test_broker_tick_clock_is_normalized_to_utc():
    raw = 1_784_784_337_089
    receipt = 1_784_773_536_339
    offset = MODULE.infer_tick_clock_offset_ms(raw, receipt)
    assert offset == 10_800_000
    assert MODULE.normalize_tick_utc_msc(raw, offset) == 1_784_773_537_089


def test_clock_inference_rejects_non_timezone_residual():
    raw = 1_784_784_337_089
    receipt = raw - 10_800_000 - 31_000
    try:
        MODULE.infer_tick_clock_offset_ms(raw, receipt)
    except RuntimeError as exc:
        assert "residual" in str(exc)
    else:
        raise AssertionError("clock residual must fail closed")


def test_normalize_before_compare_suppresses_repeated_raw_quote():
    raw = 1_800_010_800_000
    offset = 10_800_000
    first = MODULE.fresh_normalized_tick_msc(raw, offset, 0)
    assert first == 1_800_000_000_000
    assert MODULE.fresh_normalized_tick_msc(raw, offset, first) is None
