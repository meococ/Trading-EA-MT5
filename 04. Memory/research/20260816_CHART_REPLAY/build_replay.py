#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chart replay from MQ Demo tester reports + portable OHLC.

Read-only vs Owner GUI / FivePercent Real. Connects only to
02. AlphaFactory/runtime/mt5-portable-mqdemo. Does not kill terminals.
Train window 2018-01-01 .. 2023-12-31 only. No holdout.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[3]
ANALYSIS = ROOT / "02. AlphaFactory" / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

from quant_analyzer import Deal, parse_deals  # noqa: E402

OUT = ROOT / "04. Memory" / "research" / "20260816_CHART_REPLAY"
PORTABLE = ROOT / "02. AlphaFactory" / "runtime" / "mt5-portable-mqdemo"
TERMINAL = PORTABLE / "terminal64.exe"
TRAIN_FROM = datetime(2018, 1, 1)
TRAIN_TO = datetime(2023, 12, 31, 23, 59, 59)
FORBIDDEN_LOGIN = {26451822}
FORBIDDEN_NAME = ("fivepercent", "5percent")

TF_MINUTES = {"M15": 15, "H1": 60, "H4": 240}
TF_MT5 = {}


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    side: str
    volume: float
    entry_price: float
    exit_price: float
    profit: float
    commission: float
    swap: float
    entry_comment: str
    exit_comment: str
    entry_deal_id: int
    exit_deal_id: int
    balance_after: float
    hold_minutes: float = 0.0
    sl: float | None = None
    tp: float | None = None
    atr: float | None = None
    exit_class: str = "UNKNOWN"
    thesis_ok: bool | None = None
    thesis_note: str = ""
    levels: dict[str, float] = field(default_factory=dict)
    stratum: str = ""

    @property
    def direction(self) -> int:
        return 1 if self.side.lower() == "buy" else -1

    @property
    def r_multiple(self) -> float | None:
        if self.sl is None or self.entry_price <= 0:
            return None
        risk = abs(self.entry_price - self.sl)
        if risk <= 1e-9:
            return None
        signed = (self.exit_price - self.entry_price) * self.direction
        return signed / risk


RUNS = [
    {
        "key": "SWEEPFADE",
        "hyp": "HYP-SWEEPFADE-XAUUSD-H1-001",
        "run_id": "20260816_130548",
        "ea": "EA_H1SweepFade",
        "symbol": "XAUUSD",
        "tf": "H1",
        "thesis": "PDH/PDL sweep-reclaim fade",
        "time_stop": 24,
        "max_sl_atr": 2.5,
        "min_sl_atr": 0.80,
        "family": "sweepfade",
    },
    {
        "key": "GBB_S2",
        "hyp": "HYP-GBB-S2-XAUUSD-H1-002",
        "run_id": "20260816_124307",
        "ea": "EA_GBB_TrendPullback",
        "symbol": "XAUUSD",
        "tf": "H1",
        "thesis": "GBB S2 trend-pullback (code ±2)",
        "time_stop": 24,
        "max_sl_atr": 2.5,
        "min_sl_atr": 0.80,
        "family": "gbb",
    },
    {
        "key": "ASIA_LONDON",
        "hyp": "HYP-ASIA-LONDON-BRK-XAUUSD-M15-001",
        "run_id": "20260816_134530",
        "ea": "EA_M15AsiaLondonBreak",
        "symbol": "XAUUSD",
        "tf": "M15",
        "thesis": "Asia H/L close-break after London open",
        "time_stop": 32,
        "max_sl_atr": 8.0,
        "min_sl_atr": 0.80,
        "family": "asia",
    },
    {
        "key": "H4_DONCHIAN",
        "hyp": "HYP-H4-DONCHIAN-XAUUSD-H4-001",
        "run_id": "20260816_141128",
        "ea": "EA_H4DonchianBreak",
        "symbol": "XAUUSD",
        "tf": "H4",
        "thesis": "Donchian N=20 close-break",
        "time_stop": 20,
        "max_sl_atr": 8.0,
        "min_sl_atr": 0.80,
        "family": "donchian",
    },
    {
        "key": "PDBREAK",
        "hyp": "HYP-PDBREAK-EURUSD-H1-001",
        "run_id": "20260816_140021",
        "ea": "EA_H1PrevDayBreak",
        "symbol": "EURUSD",
        "tf": "H1",
        "thesis": "PDH/PDL break continuation",
        "time_stop": 24,
        "max_sl_atr": 15.0,
        "min_sl_atr": 0.80,
        "family": "pdbreak",
        "optional": True,
    },
    {
        "key": "M15_TRENDPB",
        "hyp": "HYP-M15-TRENDPB-XAUUSD-M15-001",
        "run_id": "20260816_132913",
        "ea": "EA_M15TrendPullback",
        "symbol": "XAUUSD",
        "tf": "M15",
        "thesis": "H1 EMA/structure + M15 EMA21 pullback",
        "time_stop": 32,
        "max_sl_atr": 2.5,
        "min_sl_atr": 0.80,
        "family": "trendpb",
        "optional": True,
    },
]


def report_path(spec: dict[str, Any]) -> Path:
    return ROOT / "02. AlphaFactory" / "runs" / spec["ea"] / spec["run_id"] / "report.html"


def pair_trades(deals: list[Deal]) -> list[Trade]:
    trades: list[Trade] = []
    open_pos: list[dict[str, Any]] = []
    eps = 1e-9

    def emit(pos: dict[str, Any]) -> None:
        entry: Deal = pos["entry"]
        outs: list[Deal] = pos["outs"]
        if not outs:
            return
        closed = float(pos["closed_volume"])
        if closed <= eps:
            return
        exit_px = sum(o.price * abs(o.volume) for o in outs) / max(closed, eps)
        profit = sum(o.profit + o.swap + o.commission for o in outs) + entry.commission
        last = outs[-1]
        trades.append(
            Trade(
                entry_time=entry.time,
                exit_time=last.time,
                side=entry.side.lower(),
                volume=closed,
                entry_price=entry.price,
                exit_price=exit_px,
                profit=profit,
                commission=entry.commission + sum(o.commission for o in outs),
                swap=sum(o.swap for o in outs),
                entry_comment=entry.comment or "",
                exit_comment=last.comment or "",
                entry_deal_id=entry.deal_id,
                exit_deal_id=last.deal_id,
                balance_after=last.balance,
                hold_minutes=(last.time - entry.time).total_seconds() / 60.0,
            )
        )

    for d in deals:
        side = (d.side or "").strip().lower()
        direction = (d.direction or "").strip().lower()
        if side == "balance":
            continue
        if direction == "in":
            open_pos.append(
                {"entry": d, "remaining": abs(d.volume), "closed_volume": 0.0, "outs": []}
            )
            continue
        if direction != "out":
            continue
        want = "buy" if side == "sell" else "sell" if side == "buy" else None
        need = abs(d.volume)
        for pos in open_pos:
            if need <= eps:
                break
            entry_side = (pos["entry"].side or "").strip().lower()
            if want and entry_side != want:
                continue
            take = min(pos["remaining"], need)
            if take <= eps:
                continue
            pos["remaining"] -= take
            pos["closed_volume"] += take
            pos["outs"].append(d)
            need -= take
            if pos["remaining"] <= eps:
                emit(pos)
        open_pos = [p for p in open_pos if p["remaining"] > eps]
    return trades


def ema_series(close: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(close), np.nan)
    if len(close) < period:
        return out
    k = 2.0 / (period + 1.0)
    out[period - 1] = close[:period].mean()
    for i in range(period, len(close)):
        out[i] = close[i] * k + out[i - 1] * (1.0 - k)
    return out


def atr_wilder(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.full(n, np.nan)
    if n < period:
        return atr
    atr[period - 1] = tr[:period].mean()
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def connect_portable():
    import MetaTrader5 as mt5

    if not TERMINAL.exists():
        raise SystemExit(f"portable terminal missing: {TERMINAL}")
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000, portable=True):
        raise SystemExit(f"portable initialize failed: {mt5.last_error()}")
    info = mt5.terminal_info()
    acct = mt5.account_info()
    if info is None:
        mt5.shutdown()
        raise SystemExit(f"terminal_info empty: {mt5.last_error()}")
    data_path = str(getattr(info, "data_path", "") or "")
    company = str(getattr(acct, "company", "") if acct else "").lower()
    server = str(getattr(acct, "server", "") if acct else "").lower()
    login = int(getattr(acct, "login", 0) or 0)
    if "mt5-portable-mqdemo" not in data_path.replace("/", "\\").lower():
        mt5.shutdown()
        raise SystemExit(f"refusing non-portable data_path={data_path}")
    if any(x in company or x in server or x in data_path.lower() for x in FORBIDDEN_NAME):
        mt5.shutdown()
        raise SystemExit("refusing FivePercent / forbidden broker identity")
    if login in FORBIDDEN_LOGIN:
        mt5.shutdown()
        raise SystemExit(f"refusing forbidden login {login}")
    TF_MT5["M15"] = mt5.TIMEFRAME_M15
    TF_MT5["H1"] = mt5.TIMEFRAME_H1
    TF_MT5["H4"] = mt5.TIMEFRAME_H4
    return mt5, {
        "data_path": data_path,
        "company": getattr(acct, "company", None) if acct else None,
        "server": getattr(acct, "server", None) if acct else None,
        "login": login,
        "connected": bool(getattr(info, "connected", False)),
    }


def fetch_rates(mt5, symbol: str, tf: str) -> pd.DataFrame:
    if not mt5.symbol_select(symbol, True):
        raise SystemExit(f"symbol_select {symbol} failed: {mt5.last_error()}")
    frames = []
    pulled = mt5.copy_rates_from(symbol, TF_MT5[tf], TRAIN_TO, 250000)
    if pulled is not None and len(pulled) > 0:
        frames.append(pd.DataFrame(pulled))
    for year in range(2018, 2024):
        for month in range(1, 13):
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year, 12, 31, 23, 59, 59)
            else:
                end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            rates = mt5.copy_rates_range(symbol, TF_MT5[tf], start, end)
            if rates is None or len(rates) == 0:
                continue
            frames.append(pd.DataFrame(rates))
    if not frames:
        raise SystemExit(f"no OHLC for {symbol} {tf} on portable")
    out = pd.concat(frames, ignore_index=True)
    out["time"] = pd.to_datetime(out["time"], unit="s")
    out = out.drop_duplicates("time").sort_values("time")
    out = out[(out["time"] >= TRAIN_FROM) & (out["time"] <= TRAIN_TO)].reset_index(drop=True)
    close = out["close"].to_numpy()
    out["atr"] = atr_wilder(out["high"].to_numpy(), out["low"].to_numpy(), close)
    out["ema21"] = ema_series(close, 21)
    out["ema50"] = ema_series(close, 50)
    print(f"  OHLC {symbol} {tf}: {len(out)} bars {out['time'].iloc[0]} -> {out['time'].iloc[-1]}")
    return out


def bar_index(df: pd.DataFrame, ts: datetime) -> int | None:
    if df.empty:
        return None
    times = df["time"].to_numpy()
    target = np.datetime64(pd.Timestamp(ts).to_datetime64())
    i = int(np.searchsorted(times, target, side="right") - 1)
    if i < 0 or i >= len(df):
        return None
    return i


def day_key(ts: pd.Timestamp) -> int:
    t = pd.Timestamp(ts)
    return t.year * 10000 + t.month * 100 + t.day


def prior_complete_day(df: pd.DataFrame, signal_i: int, lookback: int = 96, min_bars: int = 12):
    start = max(0, signal_i - lookback + 1)
    sig_day = day_key(df.loc[signal_i, "time"])
    i = signal_i
    while i >= start:
        dk = day_key(df.loc[i, "time"])
        if dk == sig_day:
            i -= 1
            continue
        day = dk
        hi = -math.inf
        lo = math.inf
        count = 0
        j = i
        while j >= start and day_key(df.loc[j, "time"]) == day:
            hi = max(hi, float(df.loc[j, "high"]))
            lo = min(lo, float(df.loc[j, "low"]))
            count += 1
            j -= 1
        if count >= min_bars and hi > lo:
            return day, hi, lo
        i = j
    return None, None, None


# MetaQuotes-Demo tester bars are server time. EA converts with TimeCurrent-TimeGMT.
# MQ Demo is treated as GMT+2 for replay (same assumption as many MQ history dumps).
SERVER_GMT_OFFSET_H = 2


def last_sunday(year: int, month: int) -> int:
    if month == 12:
        d = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = datetime(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d.day


def uk_dst(ts: datetime) -> bool:
    # UK DST: last Sunday March 01:00 GMT → last Sunday October 01:00 GMT
    start = datetime(ts.year, 3, last_sunday(ts.year, 3), 1, 0, 0)
    end = datetime(ts.year, 10, last_sunday(ts.year, 10), 1, 0, 0)
    return start <= ts < end


def to_gmt(ts: pd.Timestamp) -> datetime:
    t = pd.Timestamp(ts).to_pydatetime()
    return t - timedelta(hours=SERVER_GMT_OFFSET_H)


def london_hour(gmt: datetime) -> int:
    hour = gmt.hour + (1 if uk_dst(gmt) else 0)
    return hour - 24 if hour >= 24 else hour


def asia_range(df: pd.DataFrame, signal_i: int) -> tuple[float | None, float | None, int]:
    sig_gmt = to_gmt(df.loc[signal_i, "time"])
    sig_day = sig_gmt.date()
    bars = 0
    hi = -math.inf
    lo = math.inf
    for j in range(signal_i, -1, -1):
        gmt = to_gmt(df.loc[j, "time"])
        if gmt.date() != sig_day:
            break
        if 0 <= gmt.hour < 7:
            hi = max(hi, float(df.loc[j, "high"]))
            lo = min(lo, float(df.loc[j, "low"]))
            bars += 1
    if bars < 12 or hi <= lo:
        return None, None, bars
    return hi, lo, bars


def donchian_prior(df: pd.DataFrame, signal_i: int, period: int = 20) -> tuple[float | None, float | None]:
    # rates[0]=signal, rates[1..period] prior (as-series). Need period bars immediately before signal.
    if signal_i < period:
        return None, None
    window = df.iloc[signal_i - period : signal_i]
    return float(window["high"].max()), float(window["low"].min())


def clamp_risk(raw: float, atr: float, min_mult: float, max_mult: float) -> float:
    return max(min_mult * atr, min(raw, max_mult * atr))


def classify_exit(trade: Trade, spec: dict[str, Any], hold_bars: int | None) -> str:
    t = trade.exit_time
    minute = t.hour * 60 + t.minute
    if t.weekday() == 4 and minute >= 20 * 60:
        return "FRIDAY_FLAT"
    if minute >= 21 * 60 + 50:
        return "DAILY_FLAT"
    if hold_bars is not None and hold_bars >= int(spec["time_stop"]):
        return "TIME_STOP"
    tol = 0.20 * trade.atr if trade.atr else None
    if trade.sl is not None and tol:
        if abs(trade.exit_price - trade.sl) <= tol:
            return "SL"
    if trade.tp is not None and tol:
        if abs(trade.exit_price - trade.tp) <= tol:
            return "TP"
    if trade.atr and abs(trade.exit_price - trade.entry_price) <= 0.20 * trade.atr:
        return "SCRATCH_NEAR_ENTRY"
    return "OTHER"


def annotate(trade: Trade, df: pd.DataFrame, spec: dict[str, Any]) -> None:
    entry_i = bar_index(df, trade.entry_time)
    exit_i = bar_index(df, trade.exit_time)
    if entry_i is None:
        trade.thesis_note = "no entry bar"
        return
    signal_i = entry_i - 1 if entry_i > 0 else None
    hold_bars = None
    if exit_i is not None and entry_i is not None:
        hold_bars = max(0, exit_i - entry_i)
    atr = float(df.loc[signal_i, "atr"]) if signal_i is not None and pd.notna(df.loc[signal_i, "atr"]) else None
    trade.atr = atr
    family = spec["family"]
    direction = trade.direction

    if signal_i is None or atr is None or atr <= 0:
        trade.exit_class = classify_exit(trade, spec, hold_bars)
        return

    sig = df.loc[signal_i]
    sh, sl_, sc = float(sig["high"]), float(sig["low"]), float(sig["close"])

    if family == "sweepfade":
        _day, pdh, pdl = prior_complete_day(df, signal_i)
        if pdh is not None and pdl is not None:
            trade.levels = {"pdh": pdh, "pdl": pdl, "signal_high": sh, "signal_low": sl_, "signal_close": sc}
            long_ok = sl_ < pdl and sc > pdl
            short_ok = sh > pdh and sc < pdh
            expected = 1 if long_ok and not short_ok else -1 if short_ok and not long_ok else 0
            trade.thesis_ok = expected == direction
            if expected == 0:
                trade.thesis_note = "signal bar không sweep-reclaim một phía (cả hai hoặc không)"
            elif trade.thesis_ok:
                trade.thesis_note = "đúng fade: wick xuyên PDH/PDL rồi close reclaim"
            else:
                trade.thesis_note = f"hướng lệch thesis (chart {expected:+d} vs deal {direction:+d})"
        raw_stop = (sl_ - 0.20 * atr) if direction > 0 else (sh + 0.20 * atr)
        risk = clamp_risk(abs(trade.entry_price - raw_stop), atr, spec["min_sl_atr"], spec["max_sl_atr"])
        trade.sl = trade.entry_price - direction * risk
        trade.tp = trade.entry_price + direction * 1.5 * risk

    elif family == "gbb":
        raw_stop = (sl_ - 0.20 * atr) if direction > 0 else (sh + 0.20 * atr)
        risk = clamp_risk(abs(trade.entry_price - raw_stop), atr, spec["min_sl_atr"], spec["max_sl_atr"])
        trade.sl = trade.entry_price - direction * risk
        trade.tp = trade.entry_price + direction * 1.5 * risk
        sma = float(df.loc[max(0, signal_i - 19) : signal_i, "close"].mean())
        trade.levels = {"sma20": sma, "signal_high": sh, "signal_low": sl_, "signal_close": sc}
        trade.thesis_ok = None
        trade.thesis_note = (
            "GBB S2: iCustom code ±2 không đọc được trên replay. "
            "SL/TP ảo từ signal extreme (thiếu band KAMA). SMA20 chỉ để nhìn cấu trúc."
        )

    elif family == "asia":
        a_hi, a_lo, n_asia = asia_range(df, signal_i)
        if a_hi is not None and a_lo is not None:
            trade.levels = {"asia_high": a_hi, "asia_low": a_lo, "signal_close": sc, "asia_bars": float(n_asia)}
            long_ok = sc > a_hi
            short_ok = sc < a_lo
            expected = 1 if long_ok and not short_ok else -1 if short_ok and not long_ok else 0
            london_ok = london_hour(to_gmt(sig["time"])) >= 8
            trade.thesis_ok = expected == direction and london_ok
            if expected == 0:
                trade.thesis_note = "close nến tín hiệu không phá Asia H/L"
            elif not london_ok:
                trade.thesis_note = "phá range nhưng London local < 08:00"
            elif trade.thesis_ok:
                trade.thesis_note = "đúng close-break Asia sau London"
            else:
                trade.thesis_note = "hướng lệch so với phá Asia"
            raw_stop = (a_lo - 0.20 * atr) if direction > 0 else (a_hi + 0.20 * atr)
        else:
            trade.thesis_ok = False
            trade.thesis_note = f"không dựng được Asia range (bars={n_asia})"
            raw_stop = (sl_ - 0.20 * atr) if direction > 0 else (sh + 0.20 * atr)
        risk = abs(trade.entry_price - raw_stop)
        if atr * spec["min_sl_atr"] <= risk <= atr * spec["max_sl_atr"]:
            trade.sl = trade.entry_price - direction * risk
            trade.tp = trade.entry_price + direction * 1.5 * risk
        else:
            trade.sl = raw_stop
            trade.tp = trade.entry_price + direction * 1.5 * abs(trade.entry_price - raw_stop)

    elif family == "donchian":
        d_hi, d_lo = donchian_prior(df, signal_i, 20)
        if d_hi is not None and d_lo is not None:
            trade.levels = {"donchian_high": d_hi, "donchian_low": d_lo, "signal_high": sh, "signal_low": sl_, "signal_close": sc}
            long_ok = sc > d_hi
            short_ok = sc < d_lo
            expected = 1 if long_ok and not short_ok else -1 if short_ok and not long_ok else 0
            trade.thesis_ok = expected == direction
            if expected == 0:
                trade.thesis_note = "close nến tín hiệu không phá Donchian 20 (trước nến tín hiệu)"
            elif trade.thesis_ok:
                trade.thesis_note = "đúng close-break Donchian N=20"
            else:
                trade.thesis_note = "hướng lệch so với phá channel"
            swing = sl_ if direction > 0 else sh
            edge = d_hi if direction > 0 else d_lo
            raw_stop = (min(swing, edge) - 0.20 * atr) if direction > 0 else (max(swing, edge) + 0.20 * atr)
        else:
            trade.thesis_ok = False
            trade.thesis_note = "không đủ bar Donchian"
            raw_stop = (sl_ - 0.20 * atr) if direction > 0 else (sh + 0.20 * atr)
        risk = abs(trade.entry_price - raw_stop)
        if risk >= spec["min_sl_atr"] * atr:
            trade.sl = trade.entry_price - direction * risk
            trade.tp = trade.entry_price + direction * 1.5 * risk

    elif family == "pdbreak":
        _day, pdh, pdl = prior_complete_day(df, signal_i)
        if pdh is not None and pdl is not None:
            trade.levels = {"pdh": pdh, "pdl": pdl, "signal_close": sc}
            long_ok = sc > pdh
            short_ok = sc < pdl
            expected = 1 if long_ok and not short_ok else -1 if short_ok and not long_ok else 0
            trade.thesis_ok = expected == direction
            if expected == 0:
                trade.thesis_note = "close nến tín hiệu không phá PDH/PDL (continuation)"
            elif trade.thesis_ok:
                trade.thesis_note = "đúng close-break PDH/PDL continuation"
            else:
                trade.thesis_note = "hướng lệch so với phá prior-day"
            raw_stop = (pdl - 0.20 * atr) if direction > 0 else (pdh + 0.20 * atr)
        else:
            trade.thesis_ok = False
            trade.thesis_note = "không dựng được prior day"
            raw_stop = (sl_ - 0.20 * atr) if direction > 0 else (sh + 0.20 * atr)
        risk = abs(trade.entry_price - raw_stop)
        if atr * spec["min_sl_atr"] <= risk <= atr * spec["max_sl_atr"]:
            trade.sl = trade.entry_price - direction * risk
            trade.tp = trade.entry_price + direction * 1.5 * risk

    elif family == "trendpb":
        ema = float(sig["ema21"]) if pd.notna(sig.get("ema21", np.nan)) else None
        so = float(sig["open"])
        trade.levels = {"ema21": ema} if ema else {}
        if ema is not None:
            long_pb = sl_ <= ema and sc > ema and sc > so
            short_pb = sh >= ema and sc < ema and sc < so
            expected = 1 if long_pb and not short_pb else -1 if short_pb and not long_pb else 0
            trade.thesis_ok = expected == direction
            if expected == 0:
                trade.thesis_note = "M15 không thấy wick-touch + reclaim EMA21 (H1 bias chưa overlay đủ)"
            elif trade.thesis_ok:
                trade.thesis_note = "M15 pullback EMA21 đúng hướng; H1 EMA50 chỉ trên overview H1"
            else:
                trade.thesis_note = "hướng lệch so với reclaim EMA21"
        swing_lo = float(df.loc[max(0, signal_i - 2) : signal_i, "low"].min())
        swing_hi = float(df.loc[max(0, signal_i - 2) : signal_i, "high"].max())
        raw_stop = (swing_lo - 0.20 * atr) if direction > 0 else (swing_hi + 0.20 * atr)
        risk = clamp_risk(abs(trade.entry_price - raw_stop), atr, spec["min_sl_atr"], spec["max_sl_atr"])
        trade.sl = trade.entry_price - direction * risk
        trade.tp = trade.entry_price + direction * 1.5 * risk

    else:
        raw_stop = (sl_ - 0.20 * atr) if direction > 0 else (sh + 0.20 * atr)
        risk = clamp_risk(abs(trade.entry_price - raw_stop), atr, spec["min_sl_atr"], spec["max_sl_atr"])
        trade.sl = trade.entry_price - direction * risk
        trade.tp = trade.entry_price + direction * 1.5 * risk
        trade.thesis_note = "optional run — SL/TP ước từ signal extreme"

    trade.exit_class = classify_exit(trade, spec, hold_bars)


def select_cases(trades: list[Trade], df: pd.DataFrame | None = None, n_target: int = 12) -> list[Trade]:
    if not trades:
        return []
    pool = trades
    if df is not None and not df.empty:
        covered = [t for t in trades if bar_index(df, t.entry_time) is not None]
        if len(covered) >= 8:
            pool = covered
    winners = sorted([t for t in pool if t.profit > 0], key=lambda t: t.profit, reverse=True)
    losers = sorted([t for t in pool if t.profit <= 0], key=lambda t: t.profit)
    picked: list[Trade] = []

    def add(items: list[Trade], k: int, label: str) -> None:
        for t in items[:k]:
            if t not in picked:
                t.stratum = label
                picked.append(t)

    add(winners, 3, "largest_win")
    add(losers, 3, "largest_loss")
    if winners:
        mid = len(winners) // 2
        add(winners[max(0, mid - 1) : mid + 1], 2, "median_win")
    if losers:
        mid = len(losers) // 2
        add(losers[max(0, mid - 1) : mid + 1], 2, "median_loss")

    eq = 0.0
    peak = 0.0
    worst_dd = 0.0
    trough_i = 0
    for i, t in enumerate(pool):
        eq += t.profit
        peak = max(peak, eq)
        dd = peak - eq
        if dd > worst_dd:
            worst_dd = dd
            trough_i = i
    start = max(0, trough_i - 8)
    cluster = pool[start : trough_i + 1]
    cluster_loss = sorted(cluster, key=lambda t: t.profit)[:3]
    add(cluster_loss, 3, "dd_cluster")

    # keep chronological uniqueness, cap
    uniq = []
    seen = set()
    for t in picked:
        key = (t.entry_deal_id, t.exit_deal_id)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(t)
    return uniq[:n_target]


def equity_series(trades: list[Trade], deposit: float = 10000.0) -> pd.DataFrame:
    rows = []
    eq = deposit
    peak = deposit
    for t in trades:
        eq += t.profit
        peak = max(peak, eq)
        rows.append(
            {
                "time": t.exit_time,
                "equity": eq,
                "dd": peak - eq,
                "profit": t.profit,
                "side": t.side,
                "entry_time": t.entry_time,
            }
        )
    return pd.DataFrame(rows)


def window_df(df: pd.DataFrame, trade: Trade, tf: str) -> pd.DataFrame:
    pre = {"M15": 24, "H1": 18, "H4": 10}[tf]
    post = {"M15": 8, "H1": 6, "H4": 4}[tf]
    a = bar_index(df, trade.entry_time)
    b = bar_index(df, trade.exit_time)
    if a is None:
        return df.iloc[0:0]
    left = max(0, a - pre)
    right = min(len(df), (b if b is not None else a) + post + 1)
    # cap very long holds so subplot stays readable
    max_bars = {"M15": 64, "H1": 48, "H4": 36}[tf]
    if right - left > max_bars:
        right = min(len(df), left + max_bars)
    return df.iloc[left:right].copy()


def add_candle(fig, row, col, wdf: pd.DataFrame, name: str) -> None:
    fig.add_trace(
        go.Candlestick(
            x=wdf["time"],
            open=wdf["open"],
            high=wdf["high"],
            low=wdf["low"],
            close=wdf["close"],
            name=name,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            showlegend=False,
        ),
        row=row,
        col=col,
    )


def overlay_trade(fig, row, col, trade: Trade, wdf: pd.DataFrame) -> None:
    color = "#26a69a" if trade.profit > 0 else "#ef5350"
    fig.add_trace(
        go.Scatter(
            x=[trade.entry_time],
            y=[trade.entry_price],
            mode="markers",
            marker=dict(symbol="triangle-up" if trade.side == "buy" else "triangle-down", size=12, color="#42a5f5"),
            name="entry",
            showlegend=False,
            hovertext=f"IN {trade.side} {trade.entry_price:.2f}",
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=[trade.exit_time],
            y=[trade.exit_price],
            mode="markers",
            marker=dict(symbol="x", size=11, color=color),
            name="exit",
            showlegend=False,
            hovertext=f"OUT {trade.exit_price:.2f} pnl={trade.profit:.2f} {trade.exit_class}",
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=[trade.entry_time, trade.exit_time],
            y=[trade.entry_price, trade.exit_price],
            mode="lines",
            line=dict(color=color, width=1.5),
            showlegend=False,
        ),
        row=row,
        col=col,
    )
    if trade.sl is not None:
        fig.add_hline(y=trade.sl, line=dict(color="#ef9a9a", width=1, dash="dot"), row=row, col=col)
    if trade.tp is not None:
        fig.add_hline(y=trade.tp, line=dict(color="#a5d6a7", width=1, dash="dot"), row=row, col=col)
    for key in ("pdh", "pdl", "asia_high", "asia_low", "donchian_high", "donchian_low", "sma20", "ema21"):
        if key in trade.levels:
            fig.add_hline(
                y=trade.levels[key],
                line=dict(color="#90caf9", width=1, dash="dash"),
                row=row,
                col=col,
            )


def render_run(spec: dict[str, Any], trades: list[Trade], cases: list[Trade], df: pd.DataFrame, out_html: Path) -> dict[str, Any]:
    eq = equity_series(trades)
    wins = [t for t in trades if t.profit > 0]
    losses = [t for t in trades if t.profit <= 0]
    gp = sum(t.profit for t in wins)
    gl = abs(sum(t.profit for t in losses))
    pf = (gp / gl) if gl > 1e-9 else None
    exit_counts: dict[str, int] = {}
    thesis_yes = thesis_no = thesis_na = 0
    for t in trades:
        exit_counts[t.exit_class] = exit_counts.get(t.exit_class, 0) + 1
        if t.thesis_ok is True:
            thesis_yes += 1
        elif t.thesis_ok is False:
            thesis_no += 1
        else:
            thesis_na += 1

    fig = make_subplots(
        rows=3,
        cols=1,
        row_heights=[0.34, 0.22, 0.44],
        vertical_spacing=0.06,
        subplot_titles=(
            f"{spec['hyp']}  {spec['run_id']}  — equity (deposit 10k, observed, not edge)",
            "Trade PnL scatter (màu = thắng/thua)",
            "Underwater / DD từ đỉnh chạy",
        ),
    )
    fig.add_trace(
        go.Scatter(x=eq["time"], y=eq["equity"], name="equity", line=dict(color="#90caf9", width=1.6)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=eq["time"],
            y=eq["profit"],
            mode="markers",
            marker=dict(
                size=np.clip(np.abs(eq["profit"].to_numpy()) / 2.0, 4, 16),
                color=["#26a69a" if p > 0 else "#ef5350" for p in eq["profit"]],
                opacity=0.7,
            ),
            name="trade pnl",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=eq["time"], y=-eq["dd"], fill="tozeroy", name="dd", line=dict(color="#ef9a9a", width=1)),
        row=3,
        col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        height=980,
        title=dict(
            text=(
                f"{spec['thesis']} | N={len(trades)} observed PF="
                f"{pf:.2f} net={sum(t.profit for t in trades):.1f} | "
                f"thesis_ok={thesis_yes}/{len(trades)} false={thesis_no} | SL đỏ chấm, TP xanh chấm"
            ),
            font=dict(size=14),
        ),
        margin=dict(t=80, l=50, r=20, b=40),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(rangeslider_visible=False)
    overview_html = out_html.with_name(out_html.stem + "_overview.html")
    fig.write_html(overview_html, include_plotlyjs="cdn", full_html=True)

    n = len(cases)
    cols = 3
    rows = max(1, math.ceil(n / cols))
    titles = []
    for t in cases:
        mark = "OK" if t.thesis_ok else ("NO" if t.thesis_ok is False else "?")
        titles.append(
            f"{t.stratum} {t.side.upper()} {t.entry_time:%Y-%m-%d %H:%M} "
            f"pnl={t.profit:+.1f} {t.exit_class} thesis={mark}"
        )
    while len(titles) < rows * cols:
        titles.append("")
    case_fig = make_subplots(rows=rows, cols=cols, subplot_titles=titles, vertical_spacing=0.06, horizontal_spacing=0.04)
    for i, t in enumerate(cases):
        r, c = divmod(i, cols)
        wdf = window_df(df, t, spec["tf"])
        if wdf.empty:
            continue
        add_candle(case_fig, r + 1, c + 1, wdf, f"t{i}")
        overlay_trade(case_fig, r + 1, c + 1, t, wdf)
    case_fig.update_layout(
        template="plotly_dark",
        height=420 * rows,
        title=dict(
            text=(
                f"Cases {spec['hyp']} — nến {spec['tf']} + entry/exit + SL/TP ảo. "
                "Mẫu đóng băng: 3 win lớn, 3 loss lớn, 2 median win, 2 median loss, cụm DD. "
                "Không phải evidence population."
            ),
            font=dict(size=13),
        ),
        margin=dict(t=90, l=40, r=20, b=30),
    )
    case_fig.update_xaxes(rangeslider_visible=False)
    cases_html = out_html.with_name(out_html.stem + "_cases.html")
    case_fig.write_html(cases_html, include_plotlyjs="cdn", full_html=True)

    # combined landing per run
    case_rows = []
    for t in cases:
        case_rows.append(
            {
                "stratum": t.stratum,
                "side": t.side,
                "entry": t.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit": t.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "in": round(t.entry_price, 2),
                "out": round(t.exit_price, 2),
                "sl": None if t.sl is None else round(t.sl, 2),
                "tp": None if t.tp is None else round(t.tp, 2),
                "pnl": round(t.profit, 2),
                "R": None if t.r_multiple is None else round(t.r_multiple, 2),
                "hold_min": round(t.hold_minutes, 1),
                "exit_class": t.exit_class,
                "thesis_ok": t.thesis_ok,
                "note": t.thesis_note,
                "comment": t.entry_comment,
            }
        )
    landing = f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>{spec['hyp']}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#111;color:#eee;margin:24px}}
a{{color:#90caf9}} td,th{{padding:4px 8px;border-bottom:1px solid #333;font-size:13px}}
.ok{{color:#80cbc4}} .no{{color:#ef9a9a}}
</style></head><body>
<h1>{spec['hyp']}</h1>
<p>Run <b>{spec['run_id']}</b> · {spec['ea']} · {spec['symbol']} {spec['tf']} · train 2018-01-01..2023-12-31 · MQ Demo portable.</p>
<p>Observed N={len(trades)} PF={('n/a' if pf is None else f'{pf:.3f}')} net={sum(t.profit for t in trades):.2f}
 WR={100*len(wins)/max(len(trades),1):.1f}% · thesis_ok={thesis_yes} / false={thesis_no} / na={thesis_na}.</p>
<p>Exit class: {json.dumps(exit_counts, ensure_ascii=False)}</p>
<p><a href="{overview_html.name}">Overview equity/scatter</a> · <a href="{cases_html.name}">OHLC + lệnh tiêu biểu</a></p>
<p>SL/TP là ảo dựng lại từ contract (không có trên broker deal). GBB S2 không xác minh iCustom trong replay này.</p>
<table><tr>
<th>stratum</th><th>side</th><th>entry</th><th>exit</th><th>in</th><th>out</th>
<th>SL</th><th>TP</th><th>pnl</th><th>R</th><th>exit</th><th>thesis</th><th>note</th>
</tr>
"""
    for r in case_rows:
        klass = "ok" if r["thesis_ok"] else "no"
        landing += (
            f"<tr><td>{r['stratum']}</td><td>{r['side']}</td><td>{r['entry']}</td><td>{r['exit']}</td>"
            f"<td>{r['in']}</td><td>{r['out']}</td><td>{r['sl']}</td><td>{r['tp']}</td>"
            f"<td>{r['pnl']}</td><td>{r['R']}</td><td>{r['exit_class']}</td>"
            f"<td class='{klass}'>{r['thesis_ok']}</td><td>{r['note']}</td></tr>"
        )
    landing += "</table></body></html>"
    out_html.write_text(landing, encoding="utf-8")
    return {
        "hyp": spec["hyp"],
        "run_id": spec["run_id"],
        "n": len(trades),
        "pf": pf,
        "net": sum(t.profit for t in trades),
        "win_rate": len(wins) / max(len(trades), 1),
        "exit_class": exit_counts,
        "thesis_yes": thesis_yes,
        "thesis_no": thesis_no,
        "thesis_na": thesis_na,
        "landing": str(out_html),
        "overview": str(overview_html),
        "cases": str(cases_html),
        "selected": case_rows,
        "max_dd": float(eq["dd"].max()) if not eq.empty else 0.0,
    }


def render_overview(summaries: list[dict[str, Any]], series: dict[str, pd.DataFrame], path: Path) -> None:
    fig = make_subplots(rows=2, cols=1, subplot_titles=("Equity 4 run ưu tiên (observed)", "Trade scatter theo thời gian"))
    colors = ["#90caf9", "#ce93d8", "#ffe082", "#80cbc4"]
    for i, s in enumerate(summaries):
        eq = series[s["run_id"]]
        fig.add_trace(
            go.Scatter(x=eq["time"], y=eq["equity"], name=s["hyp"].split("-")[1] if "-" in s["hyp"] else s["hyp"],
                       line=dict(color=colors[i % len(colors)], width=1.5)),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=eq["time"],
                y=eq["profit"],
                mode="markers",
                marker=dict(size=5, color=colors[i % len(colors)], opacity=0.45),
                name=s["run_id"],
                showlegend=False,
            ),
            row=2, col=1,
        )
    fig.update_layout(template="plotly_dark", height=860, title="20260816 chart replay — overview, không phải edge")
    fig.write_html(path, include_plotlyjs="cdn", full_html=True)


def trade_to_json(t: Trade) -> dict[str, Any]:
    d = asdict(t)
    d["entry_time"] = t.entry_time.isoformat(sep=" ")
    d["exit_time"] = t.exit_time.isoformat(sep=" ")
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    mt5, ident = connect_portable()
    print("PORTABLE", json.dumps(ident, ensure_ascii=False))
    try:
        rates: dict[str, pd.DataFrame] = {}
        summaries = []
        series = {}
        all_selected = {}
        missing_optional = []
        for spec in RUNS:
            rp = report_path(spec)
            if not rp.exists():
                if spec.get("optional"):
                    missing_optional.append(f"{spec['ea']}/{spec['run_id']}")
                    print("SKIP optional missing", rp)
                    continue
                raise SystemExit(f"report missing: {rp}")
            print("PARSE", spec["hyp"], rp)
            deals = parse_deals(rp)
            trades = pair_trades(deals)
            symbol = spec["symbol"]
            tf = spec["tf"]
            cache_key = f"{symbol}_{tf}"
            if cache_key not in rates:
                print("OHLC", symbol, tf)
                rates[cache_key] = fetch_rates(mt5, symbol, tf)
            bars = rates[cache_key]
            for t in trades:
                annotate(t, bars, spec)
            covered_n = sum(1 for t in trades if bar_index(bars, t.entry_time) is not None)
            chart_spec = spec
            chart_bars = bars
            ohlc_note = f"{symbol} {tf} {covered_n}/{len(trades)} lệnh có nến portable"
            if covered_n == 0 and tf != "H1":
                h1_key = f"{symbol}_H1"
                if h1_key not in rates:
                    print("OHLC fallback H1", symbol)
                    rates[h1_key] = fetch_rates(mt5, symbol, "H1")
                chart_bars = rates[h1_key]
                chart_spec = dict(spec)
                chart_spec["tf"] = "H1"
                ohlc_note += f" — case vẽ H1 context vì {tf} portable không phủ cửa sổ lệnh"
            cases = select_cases(trades, chart_bars)
            landing = OUT / f"{spec['key']}_{spec['run_id']}.html"
            summary = render_run(chart_spec, trades, cases, chart_bars, landing)
            summary["ohlc_note"] = ohlc_note
            summary["optional"] = bool(spec.get("optional"))
            summaries.append(summary)
            series[spec["run_id"]] = equity_series(trades)
            all_selected[spec["run_id"]] = summary
            print(
                f"  N={summary['n']} PF={summary['pf']:.3f} thesis_ok={summary['thesis_yes']} "
                f"false={summary['thesis_no']} exits={summary['exit_class']}"
            )
        core = [s for s in summaries if not s.get("optional")]
        if core:
            render_overview(core, series, OUT / "00_OVERVIEW.html")
        payload = {
            "generated_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
            "portable": ident,
            "window": "2018.01.01-2023.12.31",
            "missing_optional": missing_optional,
            "runs": all_selected,
        }
        (OUT / "selected_cases.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        write_notes(summaries, missing_optional)
        write_index(summaries, missing_optional)
        print("DONE", OUT)
        return 0
    finally:
        mt5.shutdown()


def write_index(summaries: list[dict[str, Any]], missing_optional: list[str]) -> None:
    rows = ""
    for s in summaries:
        pf = f"{s['pf']:.2f}" if s["pf"] is not None else "n/a"
        rows += (
            f"<tr><td><a href='{Path(s['landing']).name}'>{s['hyp']}</a></td>"
            f"<td>{s['run_id']}</td><td>{s['n']}</td><td>{pf}</td>"
            f"<td>{s['net']:.1f}</td><td>{s['thesis_yes']}/{s['n']}</td>"
            f"<td><a href='{Path(s['overview']).name}'>equity</a> · "
            f"<a href='{Path(s['cases']).name}'>ohlc</a></td></tr>"
        )
    html = f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>20260816_CHART_REPLAY</title>
<style>body{{font-family:Segoe UI,Arial;background:#111;color:#eee;margin:24px}}
a{{color:#90caf9}} td,th{{padding:6px 10px;border-bottom:1px solid #333}}</style></head>
<body>
<h1>20260816 chart replay</h1>
<p>Giá + lệnh từ deal tester + OHLC portable <code>mt5-portable-mqdemo</code>. Không Visual Tester. Không holdout. Không edge.</p>
<p><a href="00_OVERVIEW.html">Overview 4 run</a> · <a href="NOTES.md">NOTES trader</a></p>
<table><tr><th>hypothesis</th><th>run</th><th>N</th><th>PF obs</th><th>net</th><th>thesis_ok</th><th>charts</th></tr>
{rows}
</table>
<p>Optional missing: {', '.join(missing_optional) if missing_optional else 'none'}</p>
</body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


def write_notes(summaries: list[dict[str, Any]], missing_optional: list[str]) -> None:
    lines = [
        "# 20260816 chart replay — ghi chú trader",
        "",
        "Nguồn: `report.html` deals + OHLC portable `mt5-portable-mqdemo` XAUUSD. Không Visual Tester (tránh cướp GUI Owner).",
        "Cửa sổ: train 2018.01.01–2023.12.31. Không đọc holdout. PF là observed, không phải edge.",
        "SL/TP trên chart là ảo dựng lại từ contract (broker SL/TP = 0). GBB S2: proxy SMA, không iCustom.",
        "Mẫu case đóng băng trước khi diễn giải: 3 win lớn / 3 loss lớn / median win-loss / cụm DD.",
        "",
    ]
    for s in summaries:
        lines.append(f"## {s['hyp']} `{s['run_id']}`")
        lines.append(f"- Chart: `{Path(s['landing']).name}` · `{Path(s['overview']).name}` · `{Path(s['cases']).name}`")
        pf = f"{s['pf']:.2f}" if s["pf"] is not None else "n/a"
        lines.append(
            f"- Observed N={s['n']} PF={pf} net={s['net']:.1f} WR={100*s['win_rate']:.1f}% "
            f"maxDD≈{s['max_dd']:.0f} thesis_ok={s['thesis_yes']} false={s['thesis_no']}"
        )
        lines.append(f"- Exit class: `{json.dumps(s['exit_class'], ensure_ascii=False)}`")
        lines.append("")
    if missing_optional:
        lines.append("## Optional không có artifact")
        for m in missing_optional:
            lines.append(f"- `{m}`")
        lines.append("")
    (OUT / "NOTES_AUTO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
