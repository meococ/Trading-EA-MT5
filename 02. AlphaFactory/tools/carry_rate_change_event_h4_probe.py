#!/usr/bin/env python3
"""Independent offline probe: carry RATE-CHANGE events on H4 (not weekly rank).

Frozen design:
  research/preregs/20260713_H_CARRY_RATE_CHANGE_EVENT_H4_V1_PROBE_FREEZE.md

Not a rescue of the killed Friday D1 cross-sectional weekly carry book.
"""
from __future__ import annotations

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
OUT = RESEARCH / "preflight" / "v8_probe"
OUT.mkdir(parents=True, exist_ok=True)

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")
MIN_DELTA = 0.05  # 5 bps in rate percentage points
HOLD_BARS = 12
STRESS_A = 1.5
STRESS_B = 3.0
TRAIN = (date(2018, 1, 1), date(2022, 12, 31))
HOLD = (date(2023, 1, 1), date(2025, 12, 31))
CTRL_LOOKBACK = 20


@dataclass
class Trade:
    symbol: str
    direction: int
    entry_time: str
    exit_time: str
    gross_pips: float
    net_a_pips: float
    net_b_pips: float
    family: str
    delta_carry: float


def parse_ymd(s: str) -> date:
    s = s.strip().replace("/", "-")
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    for fmt in ("%d %b %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(s)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fred(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        cols = list(r.fieldnames or [])
        for row in r:
            try:
                d = parse_ymd(row[cols[0]])
                v = float(row[cols[1]])
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def load_ecb() -> dict[date, float]:
    out: dict[date, float] = {}
    with (RAW / "ecb_dfr_daily.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[parse_ymd(row["TIME_PERIOD"])] = float(row["OBS_VALUE"])
            except Exception:
                continue
    return out


def load_boe() -> dict[date, float]:
    out: dict[date, float] = {}
    path = RAW / "boe_bank_rate.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[parse_ymd(row["DATE"])] = float(row["IUDBEDR"])
            except Exception:
                continue
    return out


def load_jpy() -> dict[date, float]:
    out: dict[date, float] = {}
    path = RAW / "jpy_boj_uncollateralized_overnight_call_daily.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            raw = row.get("BOJ_CALL_ON")
            if raw in (None, "", "NA"):
                continue
            try:
                out[parse_ymd(row["observation_date"])] = float(raw)
            except Exception:
                continue
    return out


def lag_map(series: dict[date, float], days: int) -> dict[date, float]:
    return {d + timedelta(days=days): v for d, v in series.items()}


def asof_value(sorted_items: list[tuple[date, float]], d: date) -> float | None:
    # last available_at <= d
    lo, hi = 0, len(sorted_items) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_items[mid][0] <= d:
            best = sorted_items[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def asof_date(sorted_items: list[tuple[date, float]], d: date) -> date | None:
    lo, hi = 0, len(sorted_items) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_items[mid][0] <= d:
            best = sorted_items[mid][0]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def pair_carry(symbol: str, usd: float, eur: float, gbp: float, jpy: float) -> float:
    if symbol == "EURUSD":
        return eur - usd
    if symbol == "GBPUSD":
        return gbp - usd
    if symbol == "USDJPY":
        return usd - jpy
    raise KeyError(symbol)


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def fetch_h4(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_H4,
        datetime(2017, 1, 1),
        datetime(2026, 7, 1),
    )
    if rates is None:
        raise RuntimeError(f"{symbol}: {mt5.last_error()}")
    rows = []
    for r in rates:
        ts = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
        rows.append(
            {
                "ts": ts,
                "date": ts.date(),
                "open": float(r["open"]),
                "close": float(r["close"]),
            }
        )
    return rows


def metrics(trades: list[Trade], start: date, end: date) -> dict:
    sub = [
        t
        for t in trades
        if start <= datetime.fromisoformat(t.entry_time).date() <= end
    ]
    n = len(sub)
    weeks = max((end - start).days / 7.0, 1e-9)

    def pf(vals: list[float]) -> float | None:
        gp = sum(v for v in vals if v > 0)
        gl = -sum(v for v in vals if v < 0)
        if gl <= 0:
            return None if gp <= 0 else float("inf")
        return gp / gl

    a = [t.net_a_pips for t in sub]
    b = [t.net_b_pips for t in sub]
    g = [t.gross_pips for t in sub]
    return {
        "trades": n,
        "trades_per_week": n / weeks,
        "pf_gross": pf(g),
        "pf_stress_a": pf(a),
        "pf_stress_b": pf(b),
        "expectancy_a": (sum(a) / n) if n else None,
        "sum_net_a": sum(a),
    }


def simulate(bars: dict[str, list[dict]], events: dict[str, list[tuple[date, float, float]]], family: str, use_control: bool) -> list[Trade]:
    """events[sym] = list of (available_date, new_carry, delta). One position per symbol."""
    trades: list[Trade] = []
    for sym in SYMBOLS:
        rows = bars[sym]
        closes = [row["close"] for row in rows]
        next_free_i = 0
        for avail_d, new_carry, delta in events[sym]:
            entry_i = None
            for i, row in enumerate(rows):
                if row["date"] > avail_d:
                    entry_i = i
                    break
            if entry_i is None or entry_i < next_free_i:
                continue
            if use_control:
                if entry_i < CTRL_LOOKBACK:
                    continue
                c1 = closes[entry_i - 1]
                c0 = closes[entry_i - 1 - CTRL_LOOKBACK]
                if c0 == 0:
                    continue
                direction = 1 if (c1 / c0 - 1.0) > 0 else -1
            else:
                direction = 1 if new_carry > 0 else (-1 if new_carry < 0 else 0)
            if direction == 0:
                continue
            ets = rows[entry_i]["ts"]
            if ets.weekday() == 4 and ets.hour >= 16:
                continue
            exit_i = min(entry_i + HOLD_BARS, len(rows) - 1)
            for j in range(entry_i + 1, exit_i + 1):
                ts = rows[j]["ts"]
                if ts.weekday() == 4 and ts.hour >= 16:
                    exit_i = j
                    break
            ep = rows[entry_i]["close"]
            xp = rows[exit_i]["close"]
            ps = pip_size(sym)
            gross = direction * (xp - ep) / ps
            trades.append(
                Trade(
                    symbol=sym,
                    direction=direction,
                    entry_time=rows[entry_i]["ts"].isoformat(),
                    exit_time=rows[exit_i]["ts"].isoformat(),
                    gross_pips=gross,
                    net_a_pips=gross - STRESS_A,
                    net_b_pips=gross - STRESS_B,
                    family=family,
                    delta_carry=delta,
                )
            )
            next_free_i = exit_i + 1
    return trades


def build_events(
    usd_s, eur_s, gbp_s, jpy_s
) -> dict[str, list[tuple[date, float, float]]]:
    # Build calendar of available dates = union of lagged series dates
    usd_items = sorted(usd_s.items())
    eur_items = sorted(eur_s.items())
    gbp_items = sorted(gbp_s.items())
    jpy_items = sorted(jpy_s.items())
    all_days = sorted({d for d, _ in usd_items + eur_items + gbp_items + jpy_items})

    prev: dict[str, float | None] = {s: None for s in SYMBOLS}
    events: dict[str, list[tuple[date, float, float]]] = {s: [] for s in SYMBOLS}
    for d in all_days:
        u = asof_value(usd_items, d)
        e = asof_value(eur_items, d)
        g = asof_value(gbp_items, d)
        j = asof_value(jpy_items, d)
        if None in (u, e, g, j):
            continue
        for sym in SYMBOLS:
            c = pair_carry(sym, u, e, g, j)  # type: ignore[arg-type]
            if prev[sym] is None:
                prev[sym] = c
                continue
            delta = c - prev[sym]
            if abs(delta) >= MIN_DELTA:
                events[sym].append((d, c, delta))
            prev[sym] = c
    return events


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        acct = mt5.account_info()
        server = acct.server if acct else None

        usd = load_fred(EXO / "us_fed_funds_DFF.csv")
        usd.update(load_fred(EXO / "us_sofr_SOFR.csv"))
        eur = load_ecb()
        gbp = load_boe()
        jpy = load_jpy()
        usd_l, eur_l, gbp_l, jpy_l = lag_map(usd, 1), lag_map(eur, 1), lag_map(gbp, 1), lag_map(jpy, 2)

        events = build_events(usd_l, eur_l, gbp_l, jpy_l)
        bars = {s: fetch_h4(s) for s in SYMBOLS}

        cand = simulate(bars, events, "candidate", use_control=False)
        ctrl = simulate(bars, events, "control", use_control=True)

        train_c = metrics(cand, *TRAIN)
        train_k = metrics(ctrl, *TRAIN)

        reasons = []
        train_pass = True
        if train_c["trades"] < 100:
            train_pass = False
            reasons.append("train_trades<100")
        if (train_c["trades_per_week"] or 0) < 1.5:
            train_pass = False
            reasons.append("train_cadence<1.5")
        pf_a = train_c["pf_stress_a"]
        if pf_a is None or pf_a < 1.10:
            train_pass = False
            reasons.append("train_pf_a<1.10")
        if (train_c["expectancy_a"] or 0) <= 0:
            train_pass = False
            reasons.append("train_expectancy_a<=0")
        ctrl_pf = train_k["pf_stress_a"]
        if pf_a is None or ctrl_pf is None or pf_a <= ctrl_pf:
            train_pass = False
            reasons.append("train_not_beat_control")

        hold_c = metrics(cand, *HOLD) if train_pass else None
        hold_k = metrics(ctrl, *HOLD) if train_pass else None
        verdict = "KILL_AT_OFFLINE_PROBE"
        if train_pass:
            verdict = "PASS_TRAIN"
            assert hold_c is not None and hold_k is not None
            if (
                hold_c["trades"] < 40
                or (hold_c["trades_per_week"] or 0) < 1.0
                or (hold_c["pf_stress_a"] or 0) < 1.0
                or (hold_c["pf_stress_a"] or 0) <= (hold_k["pf_stress_a"] or 0)
            ):
                verdict = "KILL_AT_OFFLINE_PROBE_HOLDOUT"
            else:
                verdict = "PROBE_SURVIVOR_CANDIDATE_FOR_PREREG"

        trades_path = OUT / "20260713_CARRY_RATE_CHANGE_EVENT_H4_TRADES_V1.csv"
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            fields = list(asdict(cand[0]).keys()) if cand else [
                "symbol",
                "direction",
                "entry_time",
                "exit_time",
                "gross_pips",
                "net_a_pips",
                "net_b_pips",
                "family",
                "delta_carry",
            ]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        event_counts = {s: len(events[s]) for s in SYMBOLS}
        result = {
            "schema": "carry_rate_change_event_h4_probe.v1b",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": verdict,
            "mt5_server": server,
            "design_freeze": "03. EA Developer/EA_SonicR/research/preregs/20260713_H_CARRY_RATE_CHANGE_EVENT_H4_V1_PROBE_FREEZE.md",
            "independence": "NOT weekly D1 cross-sectional rank; event Δcarry on H4",
            "integrity_note": "v1b enforces one position per symbol (next_free_i); v1a overlap bug discarded",
            "min_delta_pp": MIN_DELTA,
            "hold_h4_bars": HOLD_BARS,
            "event_counts": event_counts,
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "train_pass": train_pass,
            "kill_reasons": reasons,
            "trades_csv_sha256": sha256_file(trades_path),
            "authority_flags": {
                "registry_append_authorized": verdict == "PROBE_SURVIVOR_CANDIDATE_FOR_PREREG",
                "prereg_freeze_authorized": verdict == "PROBE_SURVIVOR_CANDIDATE_FOR_PREREG",
                "ea_build_authorized": False,
                "compile_authorized": False,
                "backtest_authorized": False,
                "chatgpt_required": False,
            },
        }
        out = OUT / "20260713_CARRY_RATE_CHANGE_EVENT_H4_RESULT_V1.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"verdict": verdict, "train_c": train_c, "train_k": train_k, "reasons": reasons, "events": event_counts}, indent=2))
        print(f"wrote {out}")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
