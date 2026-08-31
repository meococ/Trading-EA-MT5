"""Contract tests for analysis/trade_chart_capture.py (asof + anatomy PNGs)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
CAPTURE = ALPHA_ROOT / "analysis" / "trade_chart_capture.py"
sys.path.insert(0, str(ALPHA_ROOT / "analysis"))

import trade_chart_capture as tcc  # noqa: E402


def _bars(tmp: Path, n: int = 240) -> Path:
    t = pd.date_range("2021-06-01 00:00", periods=n, freq="15min")
    base = 1800.0 + pd.Series(range(n)) * 0.12
    vol = [50.0] * n
    for i in range(40, n, 17):
        vol[i] = 140.0
    df = pd.DataFrame(
        {
            "time": t,
            "open": base,
            "high": base + 0.8,
            "low": base - 0.8,
            "close": base + 0.15,
            "tick_volume": vol,
        }
    )
    out = tmp / "bars.csv"
    df.to_csv(out, index=False)
    return out


def _trades_csv(tmp: Path) -> Path:
    logs = tmp / "logs"
    logs.mkdir()
    path = logs / "EA_SonicR_PVSRA_Trades_tester.csv"
    path.write_text(
        "PositionID,OpenTime,CloseTime,Direction,OpenPrice,ClosePrice,StopLoss,TakeProfit,CloseReason,EntryZoneTop,EntryZoneBottom\n"
        "101,2021.06.02 12:00,2021.06.02 15:00,buy,1808.50,1812.00,1804.00,1816.00,TP,1809.20,1807.80\n"
        "102,2021.06.03 09:00,2021.06.03 11:30,sell,1820.00,1815.50,1824.00,1814.00,SL,1821.00,1819.00\n",
        encoding="utf-8",
    )
    return logs


def _run_cli(tmp: Path, extra: list[str] | None = None) -> dict:
    out_dir = tmp / "trade_charts"
    cmd = [
        sys.executable,
        str(CAPTURE),
        "--logs-dir",
        str(_trades_csv(tmp)),
        "--bars-file",
        str(_bars(tmp)),
        "--out",
        str(out_dir),
        "--symbol",
        "XAUUSD",
        "--timeframe",
        "M15",
        "--round-whole",
        "10",
        "--frames",
        "both",
        "--max-trades",
        "8",
    ]
    if extra:
        cmd.extend(extra)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    index_path = out_dir / "trades_index.json"
    assert index_path.is_file()
    return json.loads(index_path.read_text(encoding="utf-8"))


def test_sr_levels_include_whole_and_half() -> None:
    levels = tcc.collect_sr_levels(1803.4, 10.0, each_side=4, include_quarter=True)
    prices = [p for p, _ in levels]
    assert 1800.0 in prices
    assert 1805.0 in prices
    kinds = {p: k for p, k in levels}
    assert kinds[1800.0] == tcc.SNR_SR_WHOLE
    assert kinds[1805.0] == tcc.SNR_SR_HALF
    assert kinds[1802.5] == tcc.SNR_SR_QUARTER


def test_pvsra_uses_prior_bars_only() -> None:
    high = [1.0] * 16
    low = [0.0] * 16
    vol = [10.0] * 15 + [100.0]
    classes = tcc.classify_pvsra_series(high, low, vol, avg_bars=10, rising_mult=1.5, climax_mult=2.0)
    assert classes[9] == tcc.PVSRA_UNKNOWN
    assert classes[-1] == tcc.PVSRA_CLIMAX
    # A high-volume bar must not leak into the prior average of the next bar.
    vol2 = [10.0] * 10 + [100.0] + [10.0] * 5
    classes2 = tcc.classify_pvsra_series(high, low, vol2, avg_bars=10)
    assert classes2[10] == tcc.PVSRA_CLIMAX
    assert classes2[11] in (tcc.PVSRA_LOW, tcc.PVSRA_NORMAL)


def test_cli_renders_entry_and_exit_pngs(tmp_path: Path) -> None:
    manifest = _run_cli(tmp_path)
    assert manifest["schema_version"] == "trade_chart_capture.v2"
    assert manifest["ohlc_source"] == "bars_file"
    assert len(manifest["rendered"]) == 2
    out_dir = tmp_path / "trade_charts"
    for row in manifest["rendered"]:
        assert row["ticket"] in {"101", "102"}
        assert row["open_time"]
        assert row["close_time"]
        assert row["reason"] in {"TP", "SL"}
        assert row["entry_png"]
        assert row["exit_png"]
        entry = out_dir / row["entry_png"]
        exit_png = out_dir / row["exit_png"]
        assert entry.is_file() and entry.stat().st_size > 4000
        assert exit_png.is_file() and exit_png.stat().st_size > 4000
    reasons = {row["ticket"]: row["reason"] for row in manifest["rendered"]}
    assert reasons["101"] == "TP"
    assert reasons["102"] == "SL"


def test_asof_window_stops_at_closed_bars(tmp_path: Path) -> None:
    bars = tcc.load_bars_file(_bars(tmp_path))
    entry = datetime(2021, 6, 2, 12, 0, 0)
    window = tcc.slice_asof(bars, entry, "M15", 80)
    assert not window.empty
    last_close = window.index[-1] + pd.Timedelta(minutes=15)
    assert last_close <= pd.Timestamp(entry)
    anatomy = tcc.slice_anatomy(bars, entry, datetime(2021, 6, 2, 15, 0, 0), "M15", 80, 8)
    assert anatomy.index[-1] >= pd.Timestamp("2021-06-02 15:00")


def test_fail_open_without_rates_writes_index(tmp_path: Path) -> None:
    logs = _trades_csv(tmp_path)
    out_dir = tmp_path / "empty_charts"
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "tick_volume"])
    empty.index = pd.DatetimeIndex([], name="time")
    index = tcc.capture_trades(
        logs_dir=logs,
        report=Path("missing.html"),
        out_dir=out_dir,
        symbol="XAUUSD",
        timeframe="M15",
        round_whole=10.0,
        bars_df=empty,
    )
    assert (out_dir / "trades_index.json").is_file()
    assert index["n_trades_found"] == 2
    assert index["rendered"] == []
    assert any(item.get("reason") == "no_rates" for item in index["skipped"])


def test_rejects_bars_outside_trade_window(tmp_path: Path) -> None:
    logs = _trades_csv(tmp_path)
    t = pd.date_range("2026-05-05 15:00", periods=40, freq="15min")
    df = pd.DataFrame(
        {
            "open": 4500.0,
            "high": 4501.0,
            "low": 4499.0,
            "close": 4500.5,
            "tick_volume": 100.0,
        },
        index=t,
    )
    index = tcc.capture_trades(
        logs_dir=logs,
        report=Path("missing.html"),
        out_dir=tmp_path / "mismatch",
        symbol="XAUUSD",
        timeframe="M15",
        round_whole=10.0,
        bars_df=df,
    )
    assert index["rendered"] == []
    assert any(item.get("reason") == "no_rates" for item in index["skipped"])


def test_alpha_ps1_wires_fail_open_trade_charts() -> None:
    text = (ALPHA_ROOT / "alpha.ps1").read_text(encoding="utf-8-sig")
    assert "[switch]$TradeCharts" in text
    assert "function Invoke-TradeChartCaptureSafe" in text
    assert "trade_chart_capture.py" in text
    assert "analysis\\trade_charts" in text or "analysis/trade_charts" in text
    assert "$Charts -or $TradeCharts" in text
    assert "-TradeCharts" in text
