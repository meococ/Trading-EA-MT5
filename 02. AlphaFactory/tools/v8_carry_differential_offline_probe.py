#!/usr/bin/env python3
"""V8 local offline probe: point-in-time G3 carry differential vs return-rank control.

Authority: Owner unlimited-GOAL + 1A evidence quality (2026-07-13).
Discovery-only. Not Strategy Tester. Not promotion. Demo MT5 history OK for
falsification only. Missing broker cost ≠ zero — use explicit pip stress.

Frozen modes (no post-hoc edit after reading results in the same run):
- weekly: Friday D1 close; long single highest positive-carry pair (legacy V1).
- daily: every D1 close; long max / short min when (max-min) >= deadband 0.25;
  hold until flip or flat (spread < deadband).
- rate_event: same portfolio as daily, but rebalance only on days when any G3
  lagged rate moves >= 5 bp vs its prior available observation day.

Shared constants:
- Symbols: EURUSD, GBPUSD, USDJPY
- Decision bar: closed D1
- Control: identical portfolio machinery with 20-day lagged spot-return scores
  (percent) replacing rate differentials.
- Train 2018-01-01..2022-12-31; holdout 2023-01-01..2025-12-31 gated.
- Cost stresses: 1.5 pip and 3.0 pip round-turn haircuts (kill-only).

CLI:
  python v8_carry_differential_offline_probe.py --rebalance weekly
  python v8_carry_differential_offline_probe.py --rebalance daily
  python v8_carry_differential_offline_probe.py --rebalance rate_event
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

WORKSPACE = Path(r"d:\Trading EA MT5")
RESEARCH = WORKSPACE / "03. EA Developer" / "EA_SonicR" / "research"
RAW = RESEARCH / "preflight" / "v8_exogenous" / "raw"
EXO = RESEARCH / "data" / "exogenous"
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")
TRAIN_START = date(2018, 1, 1)
TRAIN_END = date(2022, 12, 31)
HOLD_START = date(2023, 1, 1)
HOLD_END = date(2025, 12, 31)
STRESS_A = 1.5  # pips RT
STRESS_B = 3.0
LOOKBACK_RET = 20
DEADBAND = 0.25  # rate pp (candidate) / return percent (control)
RATE_EVENT_BP = 5.0  # a priori; 5 bp = 0.05 percentage points

# Pre-declared train gates (fail-closed). Holdout evaluated only if train passes.
TRAIN_MIN_TRADES = 80
TRAIN_MIN_TRADES_PER_WEEK = 0.5  # structural; North-Star 2-5 is later stage
TRAIN_MIN_PF_A = 1.05
TRAIN_BEAT_CONTROL_PF = True

MODE_META = {
    "weekly": {
        "schema": "v8_carry_differential_offline_probe.v1",
        "result_name": "20260713_V8_CARRY_DIFF_PROBE_RESULT_V1.json",
        "trades_name": "20260713_V8_CARRY_DIFF_PROBE_TRADES_V1.csv",
        "probe_id": "V8_CARRY_DIFF_WEEKLY_V1",
    },
    "daily": {
        "schema": "v8_carry_daily_rank_offline_probe.v1",
        "result_name": "20260713_V8_CARRY_DAILY_PROBE_RESULT_V1.json",
        "trades_name": "20260713_V8_CARRY_DAILY_PROBE_TRADES_V1.csv",
        "probe_id": "V8_CARRY_DAILY_RANK_V1",
    },
    "rate_event": {
        "schema": "v8_carry_rate_event_offline_probe.v1",
        "result_name": "20260713_V8_CARRY_RATE_EVENT_PROBE_RESULT_V1.json",
        "trades_name": "20260713_V8_CARRY_RATE_EVENT_PROBE_TRADES_V1.csv",
        "probe_id": "V8_CARRY_RATE_EVENT_5BP_V1",
    },
}


@dataclass
class Trade:
    symbol: str
    direction: int  # +1 long, -1 short
    entry_date: str
    exit_date: str
    gross_pips: float
    net_a_pips: float
    net_b_pips: float
    family: str  # candidate|control


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date:
    s = s.strip().replace("/", "-")
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    for fmt in ("%d %b %Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unparsed_date:{s!r}")


def load_fred_series(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        cols = r.fieldnames or []
        date_col = cols[0]
        val_col = cols[1]
        for row in r:
            try:
                d = parse_ymd(row[date_col])
                v = float(row[val_col])
            except (KeyError, ValueError, TypeError):
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def load_treasury_4w() -> dict[date, float]:
    """USD T-bill 4-week coupon equivalent when present, else first numeric col."""
    out: dict[date, float] = {}
    for year in range(2018, 2027):
        path = RAW / f"us_treasury_bill_rates_{year}.csv"
        if not path.is_file():
            continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    d = parse_ymd(row["Date"])
                except Exception:
                    continue
                val = None
                for key in (
                    "4 WEEKS COUPON EQUIVALENT",
                    "4 WEEKS BANK DISCOUNT",
                    "8 WEEKS COUPON EQUIVALENT",
                ):
                    if key in row and row[key] not in (None, ""):
                        try:
                            val = float(row[key])
                            break
                        except ValueError:
                            pass
                if val is None:
                    for k, raw in row.items():
                        if k == "Date":
                            continue
                        try:
                            val = float(raw)
                            break
                        except (TypeError, ValueError):
                            continue
                if val is not None and math.isfinite(val):
                    out[d] = val
    return out


def load_ecb_dfr() -> dict[date, float]:
    path = RAW / "ecb_dfr_daily.csv"
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                d = parse_ymd(row["TIME_PERIOD"])
                v = float(row["OBS_VALUE"])
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def load_boe() -> dict[date, float]:
    path = RAW / "boe_bank_rate.csv"
    if not path.is_file():
        return load_fred_series(EXO / "gbp_sonia_IUDSOIA.csv")
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            vals = list(row.values())
            keys = list(row.keys())
            try:
                d = parse_ymd(row.get("DATE") or row.get("Date") or vals[0])
            except Exception:
                continue
            v = None
            for k in keys[1:]:
                try:
                    v = float(row[k])
                    break
                except (TypeError, ValueError):
                    continue
            if v is not None and math.isfinite(v):
                out[d] = v
    return out


def load_jpy_call() -> dict[date, float]:
    path = RAW / "jpy_boj_uncollateralized_overnight_call_daily.csv"
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            raw = (
                row.get("BOJ_CALL_ON")
                or row.get("value")
                or row.get("OBS_VALUE")
                or row.get("rate")
            )
            draw = (
                row.get("observation_date")
                or row.get("date")
                or row.get("DATE")
                or row.get("TIME_PERIOD")
            )
            if raw in (None, "", "NA", "n.a.", "ND"):
                continue
            try:
                d = parse_ymd(draw)
                v = float(raw)
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def lag_series(series: dict[date, float], lag_days: int) -> dict[date, float]:
    """available_at = observation + lag_days (calendar); conservative."""
    out: dict[date, float] = {}
    for d, v in series.items():
        out[d + timedelta(days=lag_days)] = v
    return out


def asof(series: dict[date, float], d: date) -> float | None:
    """Last available observation with available_at <= d."""
    best = None
    best_d = None
    for ad, v in series.items():
        if ad <= d and (best_d is None or ad > best_d):
            best_d = ad
            best = v
    return best


def asof_with_date(series: dict[date, float], d: date) -> tuple[date | None, float | None]:
    best = None
    best_d = None
    for ad, v in series.items():
        if ad <= d and (best_d is None or ad > best_d):
            best_d = ad
            best = v
    return best_d, best


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def pair_carry(symbol: str, usd: float, eur: float, gbp: float, jpy: float) -> float:
    """Carry of long base / short quote in percent points (annualized levels)."""
    if symbol == "EURUSD":
        return eur - usd
    if symbol == "GBPUSD":
        return gbp - usd
    if symbol == "USDJPY":
        return usd - jpy
    raise KeyError(symbol)


def fetch_d1(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_D1,
        datetime(2017, 1, 1),
        datetime(2026, 7, 1),
    )
    if rates is None:
        raise RuntimeError(f"no rates for {symbol}: {mt5.last_error()}")
    rows = []
    for r in rates:
        d = datetime.utcfromtimestamp(int(r["time"])).date()
        rows.append(
            {
                "date": d,
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            }
        )
    return rows


def friday_rebalance_dates(dates: list[date]) -> set[date]:
    return {d for d in dates if d.weekday() == 4}


def rate_event_rebalance_dates(
    dates: list[date],
    lagged_series: list[dict[date, float]],
    threshold_pp: float,
) -> set[date]:
    """Days where any lagged G3 rate moves >= threshold_pp vs prior available value."""
    out: set[date] = set()
    # Track last observed level per series (by available_at walk).
    last_level: list[float | None] = [None] * len(lagged_series)
    last_avail: list[date | None] = [None] * len(lagged_series)
    for d in dates:
        moved = False
        for i, series in enumerate(lagged_series):
            ad, v = asof_with_date(series, d)
            if v is None or ad is None:
                continue
            if last_avail[i] is None:
                last_avail[i] = ad
                last_level[i] = v
                continue
            if ad != last_avail[i]:
                # New available observation became visible.
                if last_level[i] is not None and abs(v - last_level[i]) >= threshold_pp:
                    moved = True
                last_avail[i] = ad
                last_level[i] = v
            elif last_level[i] is not None and abs(v - last_level[i]) >= threshold_pp:
                # Same available_at key overwritten (rare); still count.
                moved = True
                last_level[i] = v
        if moved:
            out.add(d)
    return out


def simulate_weekly_long_only(
    bars: dict[str, list[dict]],
    signal_fn,
    family: str,
) -> list[Trade]:
    """Weekly Friday rebalance: hold the single highest-signal symbol long;
    if signal <= 0 for that symbol, stay flat. One position max (book sleeve).
    """
    by_date: dict[date, dict[str, dict]] = {}
    for sym, rows in bars.items():
        for row in rows:
            by_date.setdefault(row["date"], {})[sym] = row
    dates = sorted(by_date)
    reb = friday_rebalance_dates(dates)

    trades: list[Trade] = []
    pos_sym: str | None = None
    pos_dir = 0
    entry_px = 0.0
    entry_d: date | None = None

    def close_pos(d: date, px: float) -> None:
        nonlocal pos_sym, pos_dir, entry_px, entry_d
        if pos_sym is None or pos_dir == 0 or entry_d is None:
            return
        ps = pip_size(pos_sym)
        gross = pos_dir * (px - entry_px) / ps
        trades.append(
            Trade(
                symbol=pos_sym,
                direction=pos_dir,
                entry_date=entry_d.isoformat(),
                exit_date=d.isoformat(),
                gross_pips=gross,
                net_a_pips=gross - STRESS_A,
                net_b_pips=gross - STRESS_B,
                family=family,
            )
        )
        pos_sym = None
        pos_dir = 0
        entry_px = 0.0
        entry_d = None

    for d in dates:
        if d not in reb:
            continue
        day = by_date[d]
        if any(s not in day for s in SYMBOLS):
            continue
        scores = {s: signal_fn(s, d, bars) for s in SYMBOLS}
        if any(v is None for v in scores.values()):
            continue
        best_sym = max(SYMBOLS, key=lambda s: scores[s])  # type: ignore[arg-type]
        best_score = scores[best_sym]
        target_sym = best_sym if best_score is not None and best_score > 0 else None
        target_dir = 1 if target_sym else 0

        if pos_sym == target_sym and pos_dir == target_dir:
            continue
        if pos_sym is not None:
            close_pos(d, day[pos_sym]["close"])
        if target_sym is not None and target_dir != 0:
            pos_sym = target_sym
            pos_dir = target_dir
            entry_px = day[target_sym]["close"]
            entry_d = d

    if pos_sym is not None and dates:
        d = dates[-1]
        if pos_sym in by_date.get(d, {}):
            close_pos(d, by_date[d][pos_sym]["close"])
    return trades


def simulate_long_short_deadband(
    bars: dict[str, list[dict]],
    signal_fn,
    family: str,
    rebalance_dates: set[date] | None,
    deadband: float,
) -> list[Trade]:
    """Long max / short min when spread >= deadband; hold until flip or flat.

    rebalance_dates=None means every calendar D1 with full universe.
    """
    by_date: dict[date, dict[str, dict]] = {}
    for sym, rows in bars.items():
        for row in rows:
            by_date.setdefault(row["date"], {})[sym] = row
    dates = sorted(by_date)

    trades: list[Trade] = []
    # Up to two legs: symbol -> (dir, entry_px, entry_d)
    positions: dict[str, tuple[int, float, date]] = {}

    def close_leg(sym: str, d: date, px: float) -> None:
        if sym not in positions:
            return
        direction, entry_px, entry_d = positions.pop(sym)
        ps = pip_size(sym)
        gross = direction * (px - entry_px) / ps
        trades.append(
            Trade(
                symbol=sym,
                direction=direction,
                entry_date=entry_d.isoformat(),
                exit_date=d.isoformat(),
                gross_pips=gross,
                net_a_pips=gross - STRESS_A,
                net_b_pips=gross - STRESS_B,
                family=family,
            )
        )

    def close_all(d: date, day: dict[str, dict]) -> None:
        for sym in list(positions):
            if sym in day:
                close_leg(sym, d, day[sym]["close"])

    for d in dates:
        if rebalance_dates is not None and d not in rebalance_dates:
            continue
        day = by_date[d]
        if any(s not in day for s in SYMBOLS):
            continue
        scores = {s: signal_fn(s, d, bars) for s in SYMBOLS}
        if any(v is None for v in scores.values()):
            continue

        max_sym = max(SYMBOLS, key=lambda s: scores[s])  # type: ignore[arg-type]
        min_sym = min(SYMBOLS, key=lambda s: scores[s])  # type: ignore[arg-type]
        spread = scores[max_sym] - scores[min_sym]  # type: ignore[operator]

        if spread is None or spread < deadband or max_sym == min_sym:
            target: dict[str, int] = {}
        else:
            target = {max_sym: 1, min_sym: -1}

        # Close legs that are wrong or unwanted.
        for sym in list(positions):
            want = target.get(sym)
            have_dir = positions[sym][0]
            if want is None or want != have_dir:
                close_leg(sym, d, day[sym]["close"])

        # Open missing target legs (hold if already correct — no churn).
        for sym, direction in target.items():
            if sym in positions and positions[sym][0] == direction:
                continue
            if sym in positions:
                close_leg(sym, d, day[sym]["close"])
            positions[sym] = (direction, day[sym]["close"], d)

    if positions and dates:
        d = dates[-1]
        day = by_date.get(d, {})
        close_all(d, day)
    return trades


def metrics(trades: list[Trade], start: date, end: date) -> dict:
    subset = [t for t in trades if start <= parse_ymd(t.entry_date) <= end]
    n = len(subset)
    weeks = max((end - start).days / 7.0, 1e-9)

    def pf(vals: list[float]) -> float | None:
        gp = sum(v for v in vals if v > 0)
        gl = -sum(v for v in vals if v < 0)
        if gl <= 0:
            return None if gp <= 0 else float("inf")
        return gp / gl

    gross = [t.gross_pips for t in subset]
    a = [t.net_a_pips for t in subset]
    b = [t.net_b_pips for t in subset]
    return {
        "trades": n,
        "trades_per_week": n / weeks,
        "expectancy_gross_pips": (sum(gross) / n) if n else None,
        "expectancy_a_pips": (sum(a) / n) if n else None,
        "pf_gross": pf(gross),
        "pf_stress_a": pf(a),
        "pf_stress_b": pf(b),
        "sum_net_a_pips": sum(a),
        "sum_net_b_pips": sum(b),
    }


def evaluate_gates(train_c: dict, train_k: dict) -> tuple[bool, list[str]]:
    train_pass = True
    reasons: list[str] = []
    if train_c["trades"] < TRAIN_MIN_TRADES:
        train_pass = False
        reasons.append(f"train_trades<{TRAIN_MIN_TRADES}")
    if (train_c["trades_per_week"] or 0) < TRAIN_MIN_TRADES_PER_WEEK:
        train_pass = False
        reasons.append("train_cadence_below_structural_floor")
    pf_a = train_c["pf_stress_a"]
    if pf_a is None or (isinstance(pf_a, float) and pf_a < TRAIN_MIN_PF_A):
        train_pass = False
        reasons.append("train_pf_stress_a_fail")
    ctrl_pf = train_k["pf_stress_a"]
    if TRAIN_BEAT_CONTROL_PF:
        if pf_a is None or ctrl_pf is None or pf_a <= ctrl_pf:
            train_pass = False
            reasons.append("train_not_beat_control")
    return train_pass, reasons


def run_probe(rebalance: str) -> int:
    meta = MODE_META[rebalance]
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        acct = mt5.account_info()
        server = acct.server if acct else None

        usd_raw = load_fred_series(EXO / "us_fed_funds_DFF.csv")
        sofr = load_fred_series(EXO / "us_sofr_SOFR.csv")
        usd_mm = dict(usd_raw)
        usd_mm.update(sofr)
        eur = load_ecb_dfr()
        gbp = load_boe()
        jpy = load_jpy_call()
        if not jpy:
            jpy = load_fred_series(EXO / "jpy_call_money_monthly_IRSTCI01JPM156N.csv")

        usd_l = lag_series(usd_mm, 1)
        eur_l = lag_series(eur, 1)
        gbp_l = lag_series(gbp, 1)
        jpy_l = lag_series(jpy, 2)

        bars = {s: fetch_d1(s) for s in SYMBOLS}
        closes: dict[str, dict[date, float]] = {
            s: {r["date"]: r["close"] for r in rows} for s, rows in bars.items()
        }

        def carry_signal(sym: str, d: date, _bars) -> float | None:
            u, e, g, j = asof(usd_l, d), asof(eur_l, d), asof(gbp_l, d), asof(jpy_l, d)
            if None in (u, e, g, j):
                return None
            return pair_carry(sym, u, e, g, j)  # type: ignore[arg-type]

        def control_signal(sym: str, d: date, _bars) -> float | None:
            # 20-day lagged return ending yesterday (no same-bar lookahead).
            # Expressed in percent so deadband 0.25 is same frozen constant.
            hist_dates = sorted(c for c in closes[sym] if c < d)
            if len(hist_dates) < LOOKBACK_RET + 1:
                return None
            d1 = hist_dates[-1]
            d0 = hist_dates[-(LOOKBACK_RET + 1)]
            c1 = closes[sym][d1]
            c0 = closes[sym][d0]
            if c0 == 0:
                return None
            ret = (c1 / c0) - 1.0
            if rebalance == "weekly":
                return ret
            return ret * 100.0  # percent for deadband-matched daily/event

        by_date: dict[date, dict[str, dict]] = {}
        for sym, rows in bars.items():
            for row in rows:
                by_date.setdefault(row["date"], {})[sym] = row
        all_dates = sorted(by_date)

        if rebalance == "weekly":
            cand_trades = simulate_weekly_long_only(bars, carry_signal, "candidate")
            ctrl_trades = simulate_weekly_long_only(bars, control_signal, "control")
            design_rebalance = "Friday_close"
            design_extra = {"portfolio": "long_max_if_positive"}
        elif rebalance == "daily":
            cand_trades = simulate_long_short_deadband(
                bars, carry_signal, "candidate", None, DEADBAND
            )
            ctrl_trades = simulate_long_short_deadband(
                bars, control_signal, "control", None, DEADBAND
            )
            design_rebalance = "daily_D1_close"
            design_extra = {
                "portfolio": "long_max_short_min",
                "deadband": DEADBAND,
                "hold_policy": "until_flip_or_flat",
            }
        else:  # rate_event
            threshold_pp = RATE_EVENT_BP / 100.0
            event_days = rate_event_rebalance_dates(
                all_dates, [usd_l, eur_l, gbp_l, jpy_l], threshold_pp
            )
            cand_trades = simulate_long_short_deadband(
                bars, carry_signal, "candidate", event_days, DEADBAND
            )
            ctrl_trades = simulate_long_short_deadband(
                bars, control_signal, "control", event_days, DEADBAND
            )
            design_rebalance = "rate_event_G3_ge_5bp"
            design_extra = {
                "portfolio": "long_max_short_min",
                "deadband": DEADBAND,
                "hold_policy": "until_flip_or_flat",
                "rate_change_threshold_bp": RATE_EVENT_BP,
                "event_rebalance_days_total": len(event_days),
            }

        train_c = metrics(cand_trades, TRAIN_START, TRAIN_END)
        train_k = metrics(ctrl_trades, TRAIN_START, TRAIN_END)
        train_pass, reasons = evaluate_gates(train_c, train_k)

        hold_c = metrics(cand_trades, HOLD_START, HOLD_END) if train_pass else None
        hold_k = metrics(ctrl_trades, HOLD_START, HOLD_END) if train_pass else None

        verdict = "PASS_TRAIN_CONTINUE_HOLDOUT" if train_pass else "KILL_AT_OFFLINE_PROBE"
        if train_pass and hold_c is not None:
            if (
                hold_c["trades"] < 40
                or (hold_c["pf_stress_a"] or 0) < 1.0
                or (hold_c["pf_stress_a"] or 0) <= (hold_k["pf_stress_a"] or 0)
            ):
                verdict = "KILL_AT_OFFLINE_PROBE_HOLDOUT"
            else:
                verdict = "PROBE_SURVIVOR_NO_EA_YET"

        trades_path = OUT_DIR / meta["trades_name"]
        fieldnames = [
            "symbol",
            "direction",
            "entry_date",
            "exit_date",
            "gross_pips",
            "net_a_pips",
            "net_b_pips",
            "family",
        ]
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for t in cand_trades + ctrl_trades:
                w.writerow(asdict(t))

        result = {
            "schema": meta["schema"],
            "probe_id": meta["probe_id"],
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": verdict,
            "mt5_server": server,
            "note": (
                "MetaQuotes-Demo falsification only; not FivePercentOnline-Real "
                "cost provenance. Not Strategy Tester. Not EA authority unless "
                "PROBE_SURVIVOR and separate prereg/cost gates. Daily/event modes "
                "are independent frozen probes — not post-hoc rescues of weekly kill."
            ),
            "design_frozen": {
                "symbols": list(SYMBOLS),
                "timeframe": "D1",
                "rebalance": design_rebalance,
                "stress_a_pips": STRESS_A,
                "stress_b_pips": STRESS_B,
                "train": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
                "holdout": [HOLD_START.isoformat(), HOLD_END.isoformat()],
                "control": "20d_lagged_spot_return_rank_portfolio",
                **design_extra,
            },
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "train_pass": train_pass,
            "kill_reasons": reasons,
            "trades_csv": str(trades_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "trades_csv_sha256": sha256_file(trades_path),
            "authority_flags": {
                "registry_append_authorized": verdict.startswith("PROBE_SURVIVOR"),
                "prereg_freeze_authorized": False,
                "ea_build_authorized": False,
                "compile_authorized": False,
                "backtest_authorized": False,
                "model_0_authorized": False,
            },
        }
        out = OUT_DIR / meta["result_name"]
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "probe_id": meta["probe_id"],
                    "verdict": verdict,
                    "train": train_c,
                    "control": train_k,
                    "reasons": reasons,
                },
                indent=2,
            )
        )
        print(f"wrote {out}")
        return 0
    finally:
        mt5.shutdown()


def main() -> int:
    p = argparse.ArgumentParser(description="V8 carry offline probe")
    p.add_argument(
        "--rebalance",
        choices=("weekly", "daily", "rate_event"),
        default="weekly",
        help="Frozen rebalance mode (default: weekly legacy)",
    )
    args = p.parse_args()
    return run_probe(args.rebalance)


if __name__ == "__main__":
    raise SystemExit(main())
