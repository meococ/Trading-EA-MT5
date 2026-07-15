#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trade_chart_capture.py
=====================
Tạo ảnh "chart snapshot" cho từng trade trong backtest, từ datalog CSV:
- Nguồn: *_Trades_*.csv (OpenTime/CloseTime/OpenPrice/SL/TP/ZoneTop/ZoneBottom...)
- Dữ liệu giá: lấy trực tiếp từ MT5 qua official MetaTrader5 Python package

Điểm mạnh:
- Không phụ thuộc Visual mode của MT5 tester
- Reproducible, chạy batch sau backtest

Output:
- out/trades_index.json
- out/trade_<ticket>_<open_time>.png (nếu matplotlib có sẵn)

Usage:
  python trade_chart_capture.py --logs-dir ".../analysis/logs" --out ".../analysis/trade_charts" --symbol XAUUSD --timeframe M15
"""

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    from quant_analyzer import parse_deals
    HAS_REPORT_PARSER = True
except Exception:
    HAS_REPORT_PARSER = False


TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1 if HAS_MT5 else 1,
    "M5": mt5.TIMEFRAME_M5 if HAS_MT5 else 5,
    "M15": mt5.TIMEFRAME_M15 if HAS_MT5 else 15,
    "M30": mt5.TIMEFRAME_M30 if HAS_MT5 else 30,
    "H1": mt5.TIMEFRAME_H1 if HAS_MT5 else 60,
    "H4": mt5.TIMEFRAME_H4 if HAS_MT5 else 240,
    "D1": mt5.TIMEFRAME_D1 if HAS_MT5 else 1440,
}


def _parse_dt(s: str) -> Optional[datetime]:
    ss = (s or "").strip()
    if not ss:
        return None
    for fmt in ("%Y.%m.%d %H:%M", "%Y.%m.%d %H:%M:%S"):
        try:
            return datetime.strptime(ss, fmt)
        except ValueError:
            pass
    return None


def _safe_float(s: str) -> Optional[float]:
    ss = (s or "").strip().replace(" ", "")
    if not ss:
        return None
    try:
        return float(ss)
    except ValueError:
        return None


def connect_mt5() -> None:
    if not HAS_MT5:
        raise SystemExit("MetaTrader5 package not installed. Run: pip install MetaTrader5")
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}. Ensure MT5 terminal is running.")


def disconnect_mt5() -> None:
    if HAS_MT5:
        mt5.shutdown()


def copy_rates_range(symbol: str, timeframe: str, dt_from: datetime, dt_to: datetime):
    if not HAS_PANDAS:
        raise SystemExit("pandas is required. Run: pip install pandas")
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        raise SystemExit(f"Invalid timeframe: {timeframe}. Valid: {list(TIMEFRAMES.keys())}")

    rates = mt5.copy_rates_range(symbol, tf, dt_from, dt_to)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    return df


@dataclass
class TradeRow:
    ticket: str
    open_time: datetime
    close_time: Optional[datetime]
    direction: str
    open_price: float
    close_price: Optional[float]
    sl: Optional[float]
    tp: Optional[float]
    close_reason: str
    zone_top: Optional[float]
    zone_bottom: Optional[float]


def read_trades(logs_dir: Path) -> List[TradeRow]:
    files = sorted(logs_dir.glob("*_Trades_*.csv"))
    if not files:
        return []

    rows: List[TradeRow] = []
    for p in files:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            r = csv.DictReader(f)
            for row in r:
                ot = _parse_dt(row.get("OpenTime", ""))
                if ot is None:
                    continue
                ct = _parse_dt(row.get("CloseTime", ""))
                op = _safe_float(row.get("OpenPrice", "")) or 0.0
                if op <= 0:
                    continue
                rows.append(
                    TradeRow(
                        ticket=(row.get("PositionID") or "").strip(),
                        open_time=ot,
                        close_time=ct,
                        direction=(row.get("Direction") or "").strip(),
                        open_price=op,
                        close_price=_safe_float(row.get("ClosePrice", "")),
                        sl=_safe_float(row.get("StopLoss", "")),
                        tp=_safe_float(row.get("TakeProfit", "")),
                        close_reason=(row.get("CloseReason") or "").strip().strip('"'),
                        zone_top=_safe_float(row.get("EntryZoneTop", "")),
                        zone_bottom=_safe_float(row.get("EntryZoneBottom", "")),
                    )
                )
    return rows


def read_trades_from_report(report_path: Path) -> List[TradeRow]:
    if not HAS_REPORT_PARSER:
        return []

    if not report_path.exists():
        return []

    deals = parse_deals(report_path)
    trades: List[TradeRow] = []

    entry = None
    out_deals = []
    for d in deals:
        if (d.side or "").strip().lower() == "balance":  # v11.2: case-insensitive
            continue
        if d.direction == "in":
            # Flush previous
            if entry is not None:
                close_time = out_deals[-1].time if out_deals else entry.time
                close_price = out_deals[-1].price if out_deals else None
                trades.append(
                    TradeRow(
                        ticket=str(entry.deal_id),
                        open_time=entry.time,
                        close_time=close_time,
                        direction=entry.side,
                        open_price=entry.price,
                        close_price=close_price,
                        sl=None,
                        tp=None,
                        close_reason="",
                        zone_top=None,
                        zone_bottom=None,
                    )
                )
            entry = d
            out_deals = []
            continue

        if d.direction == "out" and entry is not None:
            out_deals.append(d)

    if entry is not None:
        close_time = out_deals[-1].time if out_deals else entry.time
        close_price = out_deals[-1].price if out_deals else None
        trades.append(
            TradeRow(
                ticket=str(entry.deal_id),
                open_time=entry.time,
                close_time=close_time,
                direction=entry.side,
                open_price=entry.price,
                close_price=close_price,
                sl=None,
                tp=None,
                close_reason="",
                zone_top=None,
                zone_bottom=None,
            )
        )

    return trades


def plot_trade(df, t: TradeRow, out_png: Path, title: str) -> bool:
    if df is None or df.empty or not HAS_MPL:
        return False

    # Simple candlestick-like plot using vertical lines + body
    times = df.index.to_pydatetime()
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title(title)

    # Wicks
    ax.vlines(times, l, h, color="black", linewidth=0.6, alpha=0.7)
    # Bodies
    for tt, oo, cc in zip(times, o, c):
        color = "green" if cc >= oo else "red"
        ax.vlines(tt, oo, cc, color=color, linewidth=2.5, alpha=0.8)

    # Entry/SL/TP
    ax.axhline(t.open_price, color="blue", linestyle="-", linewidth=1.2, alpha=0.9, label="Entry")
    if t.sl:
        ax.axhline(t.sl, color="red", linestyle="--", linewidth=1.0, alpha=0.9, label="SL")
    if t.tp:
        ax.axhline(t.tp, color="green", linestyle="--", linewidth=1.0, alpha=0.9, label="TP")

    # Zone band
    if t.zone_top and t.zone_bottom and t.zone_top > t.zone_bottom:
        ax.axhspan(t.zone_bottom, t.zone_top, color="gold", alpha=0.15, label="EntryZone")

    # Mark open time
    ax.axvline(t.open_time, color="blue", linestyle=":", linewidth=1.0, alpha=0.9)
    if t.close_time:
        ax.axvline(t.close_time, color="gray", linestyle=":", linewidth=1.0, alpha=0.7)

    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left")

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs-dir", required=True, help="Directory containing *_Trades_*.csv")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--symbol", default="XAUUSD", help="Symbol for OHLC fetch")
    ap.add_argument("--timeframe", default="M15", help="Timeframe for OHLC fetch")
    ap.add_argument("--bars-left", type=int, default=240, help="Bars before entry to include")
    ap.add_argument("--bars-right", type=int, default=120, help="Bars after entry to include")
    ap.add_argument("--max-trades", type=int, default=500, help="Safety cap")
    ap.add_argument("--report", default="", help="Fallback report.html when logs missing")
    ap.add_argument("--force-report", action="store_true", help="Force using report.html even if logs exist")
    args = ap.parse_args()

    logs_dir = Path(args.logs_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = Path(args.report) if args.report else None
    trades = []
    source = "logs"
    if not args.force_report:
        trades = read_trades(logs_dir)

    if not trades and report_path:
        trades = read_trades_from_report(report_path)
        source = "report"

    trades = trades[: max(0, args.max_trades)]

    index = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "n_trades_found": len(trades),
        "source": source,
        "rendered": [],
        "skipped": [],
        "notes": [
            "Requires MT5 terminal running + MetaTrader5 package for OHLC fetch.",
            "If matplotlib missing, images will not be created (index still generated).",
        ],
    }

    if not trades:
        (out_dir / "trades_index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[trade_chart_capture] no trades in {logs_dir}")
        return 0

    if not HAS_MT5:
        index["skipped"].append({"reason": "missing_MetaTrader5_package"})
        (out_dir / "trades_index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        print("[trade_chart_capture] MetaTrader5 package missing -> skipped rendering.")
        return 0

    connect_mt5()
    if not mt5.symbol_select(args.symbol, True):
        raise SystemExit(f"Symbol {args.symbol} not available in MT5")
    try:
        for t in trades:
            # build time window by bars (approx) -> convert bars to minutes using timeframe
            tf_min = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}.get(args.timeframe.upper(), 15)
            dt_from = t.open_time - timedelta(minutes=tf_min * args.bars_left)
            dt_to = t.open_time + timedelta(minutes=tf_min * args.bars_right)

            df = copy_rates_range(args.symbol, args.timeframe, dt_from, dt_to)
            if df.empty:
                index["skipped"].append({"ticket": t.ticket, "open_time": t.open_time.isoformat(), "reason": "no_rates"})
                continue

            safe_ticket = t.ticket or "NA"
            ts = t.open_time.strftime("%Y%m%d_%H%M")
            out_png = out_dir / f"trade_{safe_ticket}_{ts}.png"
            title = f"{args.symbol} {args.timeframe} | ticket={safe_ticket} | {t.direction} | {t.close_reason}"
            ok = plot_trade(df, t, out_png, title)
            if ok:
                index["rendered"].append({"ticket": safe_ticket, "png": str(out_png), "open_time": t.open_time.isoformat()})
            else:
                index["skipped"].append({"ticket": t.ticket, "open_time": t.open_time.isoformat(), "reason": "plot_failed_or_no_mpl"})
    finally:
        disconnect_mt5()

    (out_dir / "trades_index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[trade_chart_capture] out={out_dir} rendered={len(index['rendered'])} skipped={len(index['skipped'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

