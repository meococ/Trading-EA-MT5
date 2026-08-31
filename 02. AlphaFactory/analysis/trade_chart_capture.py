#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-trade chart snapshots after a headless MT5 backtest.

Reconstructs OHLC windows from tester-history (MetaTrader5) or a bars file,
then draws two PNGs per trade:

- entry (asof): bars closed at/before fill; SL/TP known at entry; no exit fill
- exit (anatomy): through SL/TP fill; outcome view only

Sonic overlay (causal from bars already fetched):
- round-number S/R (SNR_SRLevels)
- PVSRA candle colors (prior-bar volume average)
- London/NY session shading
- Dragon EMA34 high/mid/low + EMA89

Fail-open: missing MT5, matplotlib, or rates writes trades_index.json and
returns 0. Never used as a PF/cadence gate.

Usage:
  python trade_chart_capture.py --run-dir ".../runs/EA/RUN_ID"
  python trade_chart_capture.py --logs-dir ".../analysis/logs" --report ".../report.html" --out ".../analysis/trade_charts"
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

_ANALYSIS_DIR = Path(__file__).resolve().parent
if str(_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_DIR))

try:
    import MetaTrader5 as mt5

    HAS_MT5 = True
except ImportError:
    mt5 = None
    HAS_MT5 = False

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    HAS_MPL = True
except Exception:
    plt = None
    Rectangle = None
    HAS_MPL = False

try:
    from quant_analyzer import Deal, infer_exit_tag, parse_deals
    from quant_analyzer import Trade as QaTrade

    HAS_REPORT_PARSER = True
except Exception:
    Deal = None  # type: ignore
    QaTrade = None  # type: ignore
    infer_exit_tag = None  # type: ignore
    parse_deals = None  # type: ignore
    HAS_REPORT_PARSER = False

SCHEMA = "trade_chart_capture.v2"

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1 if HAS_MT5 else 1,
    "M5": mt5.TIMEFRAME_M5 if HAS_MT5 else 5,
    "M15": mt5.TIMEFRAME_M15 if HAS_MT5 else 15,
    "M30": mt5.TIMEFRAME_M30 if HAS_MT5 else 30,
    "H1": mt5.TIMEFRAME_H1 if HAS_MT5 else 60,
    "H4": mt5.TIMEFRAME_H4 if HAS_MT5 else 240,
    "D1": mt5.TIMEFRAME_D1 if HAS_MT5 else 1440,
}

TF_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

SNR_SR_NONE = 0
SNR_SR_WHOLE = 1
SNR_SR_HALF = 2
SNR_SR_QUARTER = 4

PVSRA_UNKNOWN = 0
PVSRA_LOW = 1
PVSRA_NORMAL = 2
PVSRA_RISING = 3
PVSRA_CLIMAX = 4

PVSRA_COLORS = {
    PVSRA_UNKNOWN: ("#9e9e9e", "#9e9e9e"),
    PVSRA_LOW: ("#90a4ae", "#78909c"),
    PVSRA_NORMAL: ("#2e7d32", "#c62828"),
    PVSRA_RISING: ("#1e90ff", "#ff6347"),
    PVSRA_CLIMAX: ("#ffd700", "#da70d6"),
}

SR_STYLE = {
    SNR_SR_WHOLE: ("#e65100", "-", 1.6, "SR-W"),
    SNR_SR_HALF: ("#1565c0", "--", 1.1, "SR-H"),
    SNR_SR_QUARTER: ("#78909c", ":", 0.8, "SR-Q"),
}


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
    session: str = ""


def _parse_dt(s: str) -> Optional[datetime]:
    ss = (s or "").strip()
    if not ss:
        return None
    for fmt in (
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(ss[:19] if "T" in ss and len(ss) >= 19 else ss, fmt)
        except ValueError:
            continue
    return None


def _safe_float(s: Any) -> Optional[float]:
    if s is None:
        return None
    ss = str(s).strip().replace(" ", "")
    if not ss:
        return None
    try:
        value = float(ss)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value


def _row_get(row: dict, *names: str) -> str:
    lower = {(k or "").strip().lower(): v for k, v in row.items()}
    for name in names:
        value = lower.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def bar_duration(timeframe: str) -> timedelta:
    return timedelta(minutes=TF_MINUTES.get((timeframe or "M15").upper(), 15))


def default_round_whole(symbol: str) -> float:
    token = (symbol or "").upper()
    if "XAU" in token or "GOLD" in token:
        return 10.0
    if "JPY" in token:
        return 1.0
    return 0.01


def parse_override_float(overrides: str, key: str, default: float) -> float:
    for part in (overrides or "").split(";"):
        if "=" not in part:
            continue
        name, raw = part.split("=", 1)
        if name.strip() != key:
            continue
        value = _safe_float(raw)
        return default if value is None else value
    return default


def classify_close_reason(explicit: str, comment: str, entry_time: datetime, exit_time: Optional[datetime]) -> str:
    text = (explicit or "").strip().strip('"')
    if text:
        upper = text.upper()
        if upper in {"SL", "TP"}:
            return upper
        if "TP" in upper and "SL" not in upper:
            return "TP"
        if re.search(r"\bSL\b", upper):
            return "SL"
        return text
    if HAS_REPORT_PARSER and infer_exit_tag is not None and QaTrade is not None and exit_time is not None:
        tag = infer_exit_tag(
            QaTrade(
                entry_time=entry_time,
                exit_time=exit_time,
                side="",
                profit=0.0,
                n_out_deals=1,
                exit_comment=comment or "",
                entry_comment="",
            )
        )
        if tag == "sl":
            return "SL"
        if tag == "tp":
            return "TP"
        if tag and tag not in {"other_comment"}:
            return str(tag)
    comment_l = (comment or "").strip().lower()
    if re.search(r"\btp\b|take profit", comment_l):
        return "TP"
    if re.search(r"\bsl\b|stop loss|\bso\b", comment_l):
        return "SL"
    return (comment or "").strip()


def read_trades(logs_dir: Path) -> List[TradeRow]:
    if logs_dir is None or not logs_dir.is_dir():
        return []
    files = sorted(logs_dir.glob("*_Trades_*.csv"))
    if not files:
        return []
    rows: List[TradeRow] = []
    for path in files:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                ot = _parse_dt(_row_get(row, "OpenTime", "open_time", "event_time"))
                op = _safe_float(_row_get(row, "OpenPrice", "open_price", "entry_price", "price"))
                if ot is None or not op or op <= 0:
                    continue
                ct = _parse_dt(_row_get(row, "CloseTime", "close_time"))
                rows.append(
                    TradeRow(
                        ticket=_row_get(row, "PositionID", "position_id", "ticket", "deal") or "NA",
                        open_time=ot,
                        close_time=ct,
                        direction=_row_get(row, "Direction", "direction", "side") or "",
                        open_price=op,
                        close_price=_safe_float(_row_get(row, "ClosePrice", "close_price")),
                        sl=_safe_float(_row_get(row, "StopLoss", "stoploss", "sl", "initial_sl")),
                        tp=_safe_float(_row_get(row, "TakeProfit", "takeprofit", "tp", "initial_tp")),
                        close_reason=classify_close_reason(
                            _row_get(row, "CloseReason", "close_reason", "exit_reason", "close_source"),
                            _row_get(row, "Comment", "comment"),
                            ot,
                            ct,
                        ),
                        zone_top=_safe_float(_row_get(row, "EntryZoneTop", "zone_top")),
                        zone_bottom=_safe_float(_row_get(row, "EntryZoneBottom", "zone_bottom")),
                        session=_row_get(row, "Session", "session"),
                    )
                )
    return rows


def trades_from_deals(deals: Sequence[Any]) -> List[TradeRow]:
    """FIFO pair using parse_deals output; keeps fill prices (quant_analyzer.Trade does not)."""
    trades: List[TradeRow] = []
    open_positions: List[dict] = []
    eps = 1e-9

    def _emit(pos: dict) -> None:
        entry = pos["entry"]
        outs = pos["outs"]
        close_time = outs[-1].time if outs else entry.time
        close_price = outs[-1].price if outs else None
        comment = outs[-1].comment if outs else ""
        trades.append(
            TradeRow(
                ticket=str(entry.deal_id),
                open_time=entry.time,
                close_time=close_time,
                direction=entry.side or "",
                open_price=float(entry.price),
                close_price=close_price,
                sl=None,
                tp=None,
                close_reason=classify_close_reason("", comment, entry.time, close_time),
                zone_top=None,
                zone_bottom=None,
            )
        )

    for deal in deals:
        side = (deal.side or "").strip().lower()
        direction = (deal.direction or "").strip().lower()
        if side == "balance":
            continue
        if direction == "in":
            open_positions.append({"entry": deal, "remaining": abs(deal.volume), "outs": []})
            continue
        if direction != "out":
            continue
        remaining_out = abs(deal.volume)
        target = "buy" if side == "sell" else "sell" if side == "buy" else None
        while remaining_out > eps and open_positions:
            pos_index = None
            for i, pos in enumerate(open_positions):
                if pos["entry"].symbol != deal.symbol:
                    continue
                if target is not None and (pos["entry"].side or "").strip().lower() != target:
                    continue
                pos_index = i
                break
            if pos_index is None:
                for i, pos in enumerate(open_positions):
                    if pos["entry"].symbol == deal.symbol:
                        pos_index = i
                        break
            if pos_index is None:
                break
            pos = open_positions[pos_index]
            alloc = min(pos["remaining"], remaining_out)
            pos["outs"].append(deal)
            pos["remaining"] -= alloc
            remaining_out -= alloc
            if pos["remaining"] <= eps:
                _emit(pos)
                open_positions.pop(pos_index)
    for pos in open_positions:
        _emit(pos)
    return [t for t in trades if t.open_price > 0]


def read_trades_from_report(report_path: Path) -> List[TradeRow]:
    if not HAS_REPORT_PARSER or parse_deals is None or not report_path or not report_path.exists():
        return []
    return trades_from_deals(parse_deals(report_path))


def snr_round_kind(price: float, whole: float) -> int:
    if whole <= 0 or not math.isfinite(price):
        return SNR_SR_NONE
    quarter = whole * 0.25
    units = price / quarter
    if abs(units - round(units)) > 1e-8:
        return SNR_SR_NONE
    step = int(round(abs(units)))
    if step % 4 == 0:
        return SNR_SR_WHOLE
    if step % 2 == 0:
        return SNR_SR_HALF
    return SNR_SR_QUARTER


def collect_sr_levels(anchor: float, whole: float, each_side: int = 6, include_quarter: bool = True) -> List[Tuple[float, int]]:
    """Causal SNR_SRLevels: visible round numbers around last closed close."""
    if whole <= 0 or not math.isfinite(anchor) or each_side < 1:
        return []
    step = whole * 0.25 if include_quarter else whole * 0.5
    center = round(anchor / step) * step
    out: List[Tuple[float, int]] = []
    for i in range(-each_side, each_side + 1):
        price = center + i * step
        kind = snr_round_kind(price, whole)
        if kind == SNR_SR_NONE:
            continue
        if not include_quarter and kind == SNR_SR_QUARTER:
            continue
        out.append((price, kind))
    return out


def session_name(hour: int, london=(8, 16), ny=(12, 17)) -> str:
    in_lon = london[0] <= hour < london[1]
    in_ny = ny[0] <= hour < ny[1]
    if in_lon and in_ny:
        return "London+NY"
    if in_lon:
        return "London"
    if in_ny:
        return "NY"
    return "Off"


def classify_pvsra_series(
    high: Sequence[float],
    low: Sequence[float],
    volume: Sequence[float],
    avg_bars: int = 10,
    rising_mult: float = 1.5,
    climax_mult: float = 2.0,
) -> List[int]:
    """Causal PVSRA: average and max spread-volume use strictly prior bars."""
    n = len(high)
    out = [PVSRA_UNKNOWN] * n
    if avg_bars < 1 or n <= avg_bars:
        return out
    for i in range(avg_bars, n):
        prior_vol = [float(volume[j]) for j in range(i - avg_bars, i)]
        if any(v < 0 or not math.isfinite(v) for v in prior_vol):
            continue
        average = sum(prior_vol) / float(avg_bars)
        if average <= 0:
            continue
        max_sv = 0.0
        for j in range(i - avg_bars, i):
            sv = (float(high[j]) - float(low[j])) * float(volume[j])
            if sv > max_sv:
                max_sv = sv
        vol0 = float(volume[i])
        cls = PVSRA_NORMAL
        if vol0 >= average * climax_mult:
            cls = PVSRA_CLIMAX
        elif vol0 >= average * rising_mult:
            cls = PVSRA_RISING
        elif vol0 < average:
            cls = PVSRA_LOW
        sv0 = (float(high[i]) - float(low[i])) * vol0
        if max_sv > 0 and sv0 >= max_sv and cls != PVSRA_CLIMAX:
            cls = PVSRA_CLIMAX
        out[i] = cls
    return out


def _ema(values: Sequence[float], span: int) -> List[float]:
    if span < 1 or not values:
        return [float("nan")] * len(values)
    alpha = 2.0 / (span + 1.0)
    out: List[float] = []
    prev = float(values[0])
    for value in values:
        prev = alpha * float(value) + (1.0 - alpha) * prev
        out.append(prev)
    return out


def attach_overlays(df, round_whole: float, has_volume: bool) -> Any:
    if df is None or df.empty:
        return df
    close = df["close"].astype(float).tolist()
    high = df["high"].astype(float).tolist()
    low = df["low"].astype(float).tolist()
    df = df.copy()
    df["ema89"] = _ema(close, 89)
    df["dragon_high"] = _ema(high, 34)
    df["dragon_mid"] = _ema(close, 34)
    df["dragon_low"] = _ema(low, 34)
    if has_volume and "tick_volume" in df.columns:
        vol = df["tick_volume"].astype(float).tolist()
        df["pvsra"] = classify_pvsra_series(high, low, vol)
    else:
        df["pvsra"] = PVSRA_UNKNOWN
    df["session"] = [session_name(ts.hour) for ts in df.index.to_pydatetime()]
    df.attrs["round_whole"] = round_whole
    return df


def load_bars_file(path: Path):
    if not HAS_PANDAS:
        return None
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    time_col = next((c for c in ("time", "time_utc", "datetime") if c in df.columns), None)
    if time_col is None:
        raise ValueError(f"bars file missing time column: {path}")
    df = df.sort_values(time_col).reset_index(drop=True)
    df.index = pd.to_datetime(df[time_col])
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"bars file missing {col}")
    if "tick_volume" not in df.columns:
        df["tick_volume"] = 0.0
    return df[["open", "high", "low", "close", "tick_volume"]]


def connect_mt5(terminal_path: str = "") -> bool:
    if not HAS_MT5:
        return False
    kwargs = {}
    if terminal_path:
        kwargs["path"] = terminal_path
    return bool(mt5.initialize(**kwargs))


def disconnect_mt5() -> None:
    if HAS_MT5:
        mt5.shutdown()


def copy_rates_range(symbol: str, timeframe: str, dt_from: datetime, dt_to: datetime):
    if not HAS_PANDAS or not HAS_MT5:
        return None
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        return None
    rates = mt5.copy_rates_range(symbol, tf, dt_from, dt_to)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    if "tick_volume" not in df.columns:
        df["tick_volume"] = 0.0
    return df[["open", "high", "low", "close", "tick_volume"]]


def overlapping_bars(df, start: datetime, end: datetime):
    if df is None or df.empty or not HAS_PANDAS:
        return None
    lo = pd.Timestamp(start)
    hi = pd.Timestamp(end)
    if hi < lo:
        lo, hi = hi, lo
    sliced = df[(df.index >= lo) & (df.index <= hi)]
    return sliced if sliced is not None and not sliced.empty else None


def slice_asof(df, entry_time: datetime, timeframe: str, pre_bars: int):
    if df is None or df.empty:
        return df
    entry = pd.Timestamp(entry_time)
    dur = bar_duration(timeframe)
    closes_at = df.index + dur
    closed = df[closes_at <= entry]
    if closed.empty:
        closed = df[df.index < entry]
    if closed.empty:
        closed = df[df.index <= entry]
    if closed.empty:
        return closed
    return closed.iloc[-max(1, pre_bars) :]


def slice_anatomy(df, entry_time: datetime, exit_time: Optional[datetime], timeframe: str, pre_bars: int, post_bars: int):
    if df is None or df.empty:
        return df
    asof = slice_asof(df, entry_time, timeframe, pre_bars)
    end = pd.Timestamp(exit_time or entry_time)
    start = asof.index[0] if asof is not None and not asof.empty else df.index[0]
    through = df[(df.index >= start) & (df.index <= end)]
    after = df[df.index > end].iloc[: max(0, post_bars)]
    parts = [p for p in (through, after) if p is not None and not p.empty]
    if not parts:
        return asof
    return pd.concat(parts)


def _candle_color(row) -> str:
    cls = int(row.get("pvsra", PVSRA_UNKNOWN) or PVSRA_UNKNOWN)
    bull = float(row["close"]) >= float(row["open"])
    pair = PVSRA_COLORS.get(cls, PVSRA_COLORS[PVSRA_NORMAL])
    if cls in (PVSRA_UNKNOWN, PVSRA_NORMAL):
        return "#2e7d32" if bull else "#c62828"
    return pair[0] if bull else pair[1]


def plot_trade_frame(
    df,
    trade: TradeRow,
    out_png: Path,
    title: str,
    mode: str,
    round_whole: float,
    overlays_used: List[str],
) -> bool:
    if df is None or df.empty or not HAS_MPL:
        return False
    frame = df.reset_index()
    time_col = frame.columns[0]
    n = len(frame)
    fig, ax = plt.subplots(figsize=(12.2, 6.2), dpi=110)

    last_session = None
    span_start = 0
    session_colors = {"London": "#bbdefb", "NY": "#ffe0b2", "London+NY": "#c8e6c9", "Off": None}
    sessions = frame["session"].tolist() if "session" in frame.columns else ["Off"] * n
    for i, sess in enumerate(sessions + [None]):
        if sess != last_session:
            if last_session and session_colors.get(last_session):
                ax.axvspan(span_start - 0.5, i - 0.5, color=session_colors[last_session], alpha=0.18, zorder=0)
            last_session = sess
            span_start = i

    for i, row in frame.iterrows():
        color = _candle_color(row)
        ax.vlines(i, row["low"], row["high"], color=color, linewidth=0.8, zorder=2)
        body_lo, body_hi = sorted((float(row["open"]), float(row["close"])))
        ax.add_patch(
            Rectangle(
                (i - 0.35, body_lo),
                0.7,
                max(body_hi - body_lo, 1e-12),
                facecolor=color,
                edgecolor=color,
                linewidth=0.4,
                zorder=3,
            )
        )

    if "dragon_high" in frame.columns:
        x = list(range(n))
        ax.plot(x, frame["dragon_high"], color="#6a1b9a", linewidth=0.9, alpha=0.85, label="Dragon H")
        ax.plot(x, frame["dragon_mid"], color="#8e24aa", linewidth=1.1, alpha=0.9, label="Dragon M")
        ax.plot(x, frame["dragon_low"], color="#6a1b9a", linewidth=0.9, alpha=0.85, label="Dragon L")
        ax.plot(x, frame["ema89"], color="#ef6c00", linewidth=1.15, alpha=0.95, label="EMA89")

    y_lo = float(frame["low"].min())
    y_hi = float(frame["high"].max())
    pad = max((y_hi - y_lo) * 0.08, 1e-8)
    anchor = float(frame["close"].iloc[-1 if mode != "asof" else -1])
    sr_levels = collect_sr_levels(anchor, round_whole)
    labeled = set()
    for price, kind in sr_levels:
        if price < y_lo - pad or price > y_hi + pad:
            continue
        color, ls, lw, lab = SR_STYLE[kind]
        ax.axhline(price, color=color, linestyle=ls, linewidth=lw, alpha=0.7, zorder=1)
        if lab not in labeled:
            ax.text(n - 0.6, price, lab, color=color, fontsize=7, va="bottom", ha="right")
            labeled.add(lab)

    ax.axhline(trade.open_price, color="#1565c0", linewidth=1.15, linestyle="--", zorder=4)
    if trade.sl:
        ax.axhline(trade.sl, color="#c62828", linewidth=1.05, linestyle=":", zorder=4)
    elif mode == "anatomy" and (trade.close_reason or "").upper() == "SL" and trade.close_price:
        ax.axhline(trade.close_price, color="#c62828", linewidth=1.05, linestyle=":", zorder=4)
    if trade.tp:
        ax.axhline(trade.tp, color="#2e7d32", linewidth=1.05, linestyle=":", zorder=4)
    elif mode == "anatomy" and (trade.close_reason or "").upper() == "TP" and trade.close_price:
        ax.axhline(trade.close_price, color="#2e7d32", linewidth=1.05, linestyle=":", zorder=4)
    if trade.zone_top and trade.zone_bottom and trade.zone_top > trade.zone_bottom:
        ax.axhspan(trade.zone_bottom, trade.zone_top, color="#f9a825", alpha=0.12, zorder=0)

    side = (trade.direction or "").lower()
    marker = "^" if side in ("buy", "long", "1") else "v"
    if mode == "asof":
        entry_x = n - 0.15
    else:
        stamps = pd.to_datetime(frame[time_col])
        entry_x = int(stamps.searchsorted(pd.Timestamp(trade.open_time), side="left"))
        entry_x = min(max(entry_x, 0), n - 1)
    ax.scatter([entry_x], [trade.open_price], marker=marker, s=90, color="#1565c0", zorder=6, edgecolor="#0d1b2a", linewidth=0.6)
    ax.annotate(
        f"ENTRY {trade.open_time:%m-%d %H:%M}\n{trade.open_price:.5g}",
        xy=(entry_x, trade.open_price),
        xytext=(8, 14),
        textcoords="offset points",
        fontsize=7.5,
        color="#1565c0",
        fontweight="bold",
    )
    if mode == "anatomy" and trade.close_time and trade.close_price:
        exit_x = int(stamps.searchsorted(pd.Timestamp(trade.close_time), side="right")) - 1
        exit_x = min(max(exit_x, 0), n - 1)
        ax.scatter([exit_x], [trade.close_price], marker="X", s=95, color="#6a1b9a", zorder=6, edgecolor="#0d1b2a", linewidth=0.6)
        ax.annotate(
            f"EXIT {trade.close_reason or ''} {trade.close_time:%m-%d %H:%M}\n{trade.close_price:.5g}",
            xy=(exit_x, trade.close_price),
            xytext=(8, -28),
            textcoords="offset points",
            fontsize=7.5,
            color="#6a1b9a",
            fontweight="bold",
        )

    ticks = list(range(0, n, max(1, n // 8)))
    ax.set_xlim(-1, n)
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [pd.Timestamp(frame[time_col].iloc[i]).strftime("%m-%d %H:%M") for i in ticks],
        rotation=30,
        ha="right",
        fontsize=7,
    )
    note = (
        "asof: closed bars only; SL/TP planned at entry; no exit fill"
        if mode == "asof"
        else "anatomy: through SL/TP fill; not entry-quality evidence"
    )
    sl_txt = f"{trade.sl:.5g}" if trade.sl else (
        "fill" if mode == "anatomy" and (trade.close_reason or "").upper() == "SL" else "-"
    )
    tp_txt = f"{trade.tp:.5g}" if trade.tp else (
        "fill" if mode == "anatomy" and (trade.close_reason or "").upper() == "TP" else "-"
    )
    ax.text(
        0.01,
        0.99,
        f"{note}\nSL {sl_txt} | TP {tp_txt}\nPVSRA gold/orchid=climax  blue/tomato=rising\nSR-W whole  SR-H half  SR-Q quarter",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=7.2,
        family="monospace",
        bbox={"boxstyle": "round,pad=0.3", "fc": "#f8fafc", "ec": "#90a4ae", "alpha": 0.92},
    )
    ax.set_title(title, loc="left", fontsize=10)
    ax.grid(alpha=0.22)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="upper right", fontsize=7, framealpha=0.85)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)
    overlays_used.append(mode)
    return True


def resolve_context(args: argparse.Namespace) -> dict:
    run_dir = Path(args.run_dir) if args.run_dir else None
    report = Path(args.report) if args.report else None
    logs_dir = Path(args.logs_dir) if args.logs_dir else None
    out_dir = Path(args.out) if args.out else None
    symbol = args.symbol
    timeframe = args.timeframe
    overrides = ""
    if run_dir:
        if report is None:
            candidate = run_dir / "report.html"
            if candidate.exists():
                report = candidate
        if logs_dir is None:
            for cand in (run_dir / "analysis" / "logs", run_dir / "logs"):
                if cand.is_dir():
                    logs_dir = cand
                    break
        if out_dir is None:
            out_dir = run_dir / "analysis" / "trade_charts"
        manifest_path = run_dir / "run_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                symbol = symbol or str(manifest.get("symbol") or "")
                timeframe = timeframe or str(manifest.get("period") or "")
                overrides = str(manifest.get("overrides") or "")
            except (OSError, json.JSONDecodeError, TypeError):
                pass
    if report is None:
        report = Path()
    if logs_dir is None:
        logs_dir = Path()
    if out_dir is None:
        out_dir = Path("trade_charts")
    if not symbol:
        symbol = "XAUUSD"
    if not timeframe:
        timeframe = "M15"
    round_whole = args.round_whole
    if round_whole <= 0:
        round_whole = parse_override_float(overrides, "InpRoundWhole", default_round_whole(symbol))
    return {
        "run_dir": run_dir,
        "report": report,
        "logs_dir": logs_dir,
        "out_dir": out_dir,
        "symbol": symbol,
        "timeframe": timeframe,
        "round_whole": round_whole,
        "overrides": overrides,
    }


def empty_index(ctx: dict, source: str, extra_notes: Optional[List[str]] = None) -> dict:
    notes = [
        "Fail-open: chart errors do not fail backtest or PF/cadence verdict.",
        "Tester Visual Mode is not used.",
        "SL/TP prices come from trade CSV when present; report deals often only have fill + comment.",
        "Dragon is reconstructed EMA34 H/M/L + EMA89 on the tester timeframe (not a bitmap of the MT5 indicator).",
        "PVSRA colors use prior-bar tick_volume average; skipped when volume is missing.",
        "SR levels are causal round-numbers around the last closed close in the window (SNR_SRLevels).",
    ]
    if extra_notes:
        notes.extend(extra_notes)
    return {
        "schema_version": SCHEMA,
        "symbol": ctx.get("symbol"),
        "timeframe": ctx.get("timeframe"),
        "round_whole": ctx.get("round_whole"),
        "source": source,
        "ohlc_source": "none",
        "frames": ["entry", "exit"],
        "overlays": ["ohlc", "entry_sl_tp", "sr_levels", "pvsra", "session", "dragon_ema"],
        "n_trades_found": 0,
        "rendered": [],
        "skipped": [],
        "notes": notes,
        "limitations": notes,
    }


def write_index(out_dir: Path, index: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "trades_index.json"
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def reconstruct_bars_around_trades(
    trades: Sequence[TradeRow],
    timeframe: str,
    bars_left: int,
    bars_right: int,
):
    """Opt-in smoke path when the connected terminal has no overlapping history."""
    if not HAS_PANDAS or not trades:
        return None
    tf = bar_duration(timeframe)
    rows: dict = {}
    for trade in trades:
        start = trade.open_time - tf * max(1, bars_left)
        end = (trade.close_time or trade.open_time) + tf * max(0, bars_right)
        n = max(int(round((end - start) / tf)), bars_left + 8)
        entry_i = min(max(1, bars_left), n - 2)
        hold = max(1, int(round(((trade.close_time or trade.open_time) - trade.open_time) / tf)))
        exit_i = min(n - 1, entry_i + hold)
        px0 = float(trade.open_price)
        px1 = float(trade.close_price) if trade.close_price else px0
        wig = 0.12 if abs(px0) < 50 else max(abs(px0) * 0.00018, 0.06)
        for i in range(n):
            t = start + tf * i
            if i <= entry_i:
                mid = px0
            else:
                frac = (i - entry_i) / max(exit_i - entry_i, 1)
                mid = px0 + (px1 - px0) * min(max(frac, 0.0), 1.0)
            o = mid - wig * 0.25
            c = mid + wig * 0.25
            rows[t] = (o, max(o, c) + wig, min(o, c) - wig, c, 90.0 + (160.0 if i in (entry_i, exit_i) else 0.0))
    times = sorted(rows)
    return pd.DataFrame(
        {
            "open": [rows[t][0] for t in times],
            "high": [rows[t][1] for t in times],
            "low": [rows[t][2] for t in times],
            "close": [rows[t][3] for t in times],
            "tick_volume": [rows[t][4] for t in times],
        },
        index=pd.DatetimeIndex(times, name="time"),
    )


def capture_trades(
    *,
    logs_dir: Path,
    report: Path,
    out_dir: Path,
    symbol: str,
    timeframe: str,
    round_whole: float,
    bars_df=None,
    bars_left: int = 120,
    bars_right: int = 40,
    max_trades: int = 2000,
    frames: str = "both",
    mt5_path: str = "",
    force_report: bool = False,
    allow_reconstructed: bool = False,
) -> dict:
    ctx = {
        "symbol": symbol,
        "timeframe": timeframe,
        "round_whole": round_whole,
    }
    source = "logs"
    trades: List[TradeRow] = []
    if not force_report:
        trades = read_trades(logs_dir)
    if not trades and report and report.exists():
        trades = read_trades_from_report(report)
        source = "report"
    index = empty_index(ctx, source)
    index["n_trades_found"] = len(trades)
    trades = trades[: max(0, max_trades)]
    if not trades:
        index["skipped"].append({"reason": "no_trades"})
        write_index(out_dir, index)
        return index

    connected = False
    ohlc_source = "bars_file" if bars_df is not None else "none"
    try:
        if bars_df is None:
            if not HAS_MT5:
                index["skipped"].append({"reason": "missing_MetaTrader5_package"})
                index["notes"].append("OHLC fetch requires a running MT5 terminal + MetaTrader5 package, or --bars-file.")
                write_index(out_dir, index)
                return index
            if not HAS_PANDAS:
                index["skipped"].append({"reason": "missing_pandas"})
                write_index(out_dir, index)
                return index
            if not connect_mt5(mt5_path):
                index["skipped"].append({"reason": "mt5_initialize_failed"})
                write_index(out_dir, index)
                return index
            connected = True
            selected = symbol
            if not mt5.symbol_select(selected, True):
                alt = re.sub(r"[+._-]+$", "", selected)
                if alt != selected and mt5.symbol_select(alt, True):
                    selected = alt
                else:
                    index["skipped"].append({"reason": f"symbol_unavailable:{symbol}"})
                    write_index(out_dir, index)
                    return index
            tf_min = TF_MINUTES.get(timeframe.upper(), 15)
            dt_from = min(t.open_time for t in trades) - timedelta(minutes=tf_min * bars_left)
            last_close = max((t.close_time or t.open_time) for t in trades)
            dt_to = last_close + timedelta(minutes=tf_min * bars_right)
            fetched = copy_rates_range(selected, timeframe, dt_from, dt_to)
            bars_df = overlapping_bars(fetched, dt_from, dt_to)
            ohlc_source = "mt5"
            if bars_df is None:
                index["notes"].append(
                    "MT5 copy_rates_range returned no bars overlapping the trade window "
                    "(connected terminal history is shorter than the backtest)."
                )
        elif bars_df is not None and not bars_df.empty:
            tf_min = TF_MINUTES.get(timeframe.upper(), 15)
            dt_from = min(t.open_time for t in trades) - timedelta(minutes=tf_min * bars_left)
            last_close = max((t.close_time or t.open_time) for t in trades)
            dt_to = last_close + timedelta(minutes=tf_min * bars_right)
            overlapped = overlapping_bars(bars_df, dt_from, dt_to)
            if overlapped is None:
                index["notes"].append("Provided bars do not overlap the trade window.")
                bars_df = None
            else:
                bars_df = overlapped
        if (bars_df is None or getattr(bars_df, "empty", True)) and allow_reconstructed:
            bars_df = reconstruct_bars_around_trades(trades, timeframe, bars_left, bars_right)
            ohlc_source = "reconstructed_from_deals"
            index["notes"].append(
                "OHLC is a path around deal fills, not tester/broker history. "
                "Opt-in --allow-reconstructed-ohlc only; alpha.ps1 backtest does not set this."
            )
        index["ohlc_source"] = ohlc_source
        if bars_df is None or bars_df.empty:
            index["skipped"].append({"reason": "no_rates"})
            write_index(out_dir, index)
            return index

        has_volume = "tick_volume" in bars_df.columns and float(bars_df["tick_volume"].fillna(0).abs().sum()) > 0
        bars_df = attach_overlays(bars_df, round_whole, has_volume)
        if not has_volume:
            index["notes"].append("tick_volume missing or zero; PVSRA overlay skipped, candles are up/down only.")
        if source == "report":
            index["notes"].append(
                "Trade CSV absent (typical when telemetry_profile=none); SL/TP lines use logged prices only if present, else exit fill when reason is SL/TP."
            )

        want_entry = frames in ("both", "entry")
        want_exit = frames in ("both", "exit")
        overlays_ok = ["ohlc", "entry_sl_tp", "sr_levels", "session", "dragon_ema"]
        if has_volume:
            overlays_ok.append("pvsra")
        index["overlays"] = overlays_ok

        for trade in trades:
            safe_ticket = re.sub(r"[^A-Za-z0-9_-]+", "", trade.ticket or "NA") or "NA"
            ts = trade.open_time.strftime("%Y%m%d_%H%M")
            record = {
                "ticket": safe_ticket,
                "open_time": trade.open_time.isoformat(sep=" "),
                "close_time": trade.close_time.isoformat(sep=" ") if trade.close_time else None,
                "reason": trade.close_reason or "",
                "direction": trade.direction,
                "open_price": trade.open_price,
                "close_price": trade.close_price,
                "sl": trade.sl,
                "tp": trade.tp,
                "entry_png": None,
                "exit_png": None,
            }
            used: List[str] = []
            if want_entry:
                asof = slice_asof(bars_df, trade.open_time, timeframe, bars_left)
                entry_png = out_dir / f"trade_{safe_ticket}_{ts}_entry.png"
                title = f"{symbol} {timeframe} | ENTRY asof | {trade.direction} | ticket={safe_ticket}"
                if plot_trade_frame(asof, trade, entry_png, title, "asof", round_whole, used):
                    record["entry_png"] = entry_png.name
                else:
                    index["skipped"].append({"ticket": safe_ticket, "frame": "entry", "reason": "plot_failed_or_empty_window"})
            if want_exit:
                anatomy = slice_anatomy(bars_df, trade.open_time, trade.close_time, timeframe, bars_left, bars_right)
                exit_png = out_dir / f"trade_{safe_ticket}_{ts}_exit.png"
                title = f"{symbol} {timeframe} | EXIT {trade.close_reason or ''} | {trade.direction} | ticket={safe_ticket}"
                if plot_trade_frame(anatomy, trade, exit_png, title, "anatomy", round_whole, used):
                    record["exit_png"] = exit_png.name
                else:
                    index["skipped"].append({"ticket": safe_ticket, "frame": "exit", "reason": "plot_failed_or_empty_window"})
            if record["entry_png"] or record["exit_png"]:
                index["rendered"].append(record)
            elif not any(s.get("ticket") == safe_ticket for s in index["skipped"]):
                index["skipped"].append({"ticket": safe_ticket, "reason": "not_rendered"})
    finally:
        if connected:
            disconnect_mt5()

    write_index(out_dir, index)
    return index


def _main_impl(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", default="", help="AlphaFactory run folder (preferred)")
    ap.add_argument("--logs-dir", default="", help="Directory containing *_Trades_*.csv")
    ap.add_argument("--out", default="", help="Output directory (default: <run>/analysis/trade_charts)")
    ap.add_argument("--symbol", default="", help="Symbol for OHLC fetch")
    ap.add_argument("--timeframe", default="", help="Timeframe for OHLC fetch")
    ap.add_argument("--bars-left", type=int, default=120)
    ap.add_argument("--bars-right", type=int, default=40)
    ap.add_argument("--max-trades", type=int, default=2000)
    ap.add_argument("--report", default="", help="report.html fallback when logs missing")
    ap.add_argument("--bars-file", default="", help="Optional OHLC CSV/parquet; skips MT5")
    ap.add_argument("--mt5-path", default="", help="terminal64.exe for MetaTrader5.initialize")
    ap.add_argument("--round-whole", type=float, default=0.0, help="SNR whole step; 0 = from manifest/symbol")
    ap.add_argument("--frames", choices=("both", "entry", "exit"), default="both")
    ap.add_argument("--force-report", action="store_true")
    ap.add_argument(
        "--allow-reconstructed-ohlc",
        action="store_true",
        help="Smoke-only: synthesize OHLC around fills when terminal history does not overlap",
    )
    args = ap.parse_args(argv)

    ctx = resolve_context(args)
    out_dir: Path = ctx["out_dir"]
    bars_df = None
    if args.bars_file:
        bars_path = Path(args.bars_file)
        if not bars_path.exists():
            index = empty_index(ctx, "none", [f"bars file missing: {bars_path}"])
            index["skipped"].append({"reason": "bars_file_missing"})
            write_index(out_dir, index)
            print(f"[trade_chart_capture] fail-open: bars file missing {bars_path}")
            return 0
        bars_df = load_bars_file(bars_path)

    index = capture_trades(
        logs_dir=ctx["logs_dir"],
        report=ctx["report"],
        out_dir=out_dir,
        symbol=ctx["symbol"],
        timeframe=ctx["timeframe"],
        round_whole=ctx["round_whole"],
        bars_df=bars_df,
        bars_left=args.bars_left,
        bars_right=args.bars_right,
        max_trades=args.max_trades,
        frames=args.frames,
        mt5_path=args.mt5_path,
        force_report=args.force_report,
        allow_reconstructed=args.allow_reconstructed_ohlc,
    )
    print(
        f"[trade_chart_capture] out={out_dir} source={index.get('source')} "
        f"ohlc={index.get('ohlc_source')} rendered={len(index.get('rendered', []))} "
        f"skipped={len(index.get('skipped', []))}"
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        return _main_impl(argv)
    except Exception as exc:
        print(f"[trade_chart_capture] fail-open: {exc}")
        traceback.print_exc()
        try:
            args = argv if argv is not None else sys.argv[1:]
            # Best-effort index so callers always find trades_index.json.
            out = None
            run_dir = None
            for i, tok in enumerate(args):
                if tok == "--out" and i + 1 < len(args):
                    out = Path(args[i + 1])
                if tok == "--run-dir" and i + 1 < len(args):
                    run_dir = Path(args[i + 1])
            if out is None and run_dir is not None:
                out = run_dir / "analysis" / "trade_charts"
            if out is not None:
                write_index(out, empty_index({"symbol": "", "timeframe": "", "round_whole": 0}, "none", [str(exc)]))
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
