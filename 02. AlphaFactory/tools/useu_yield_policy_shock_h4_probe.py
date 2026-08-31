#!/usr/bin/env python3
"""US DGS2 vs ECB DFR differential shock probe on EURUSD H4."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

WORKSPACE = Path(__file__).resolve().parents[2]
RESEARCH = WORKSPACE / "03. EA Developer" / "EA_SonicR" / "research"
RAW = RESEARCH / "preflight" / "v8_exogenous" / "raw"
EXO = RESEARCH / "data" / "exogenous"
OUT = RESEARCH / "preflight" / "v8_probe"
OUT.mkdir(parents=True, exist_ok=True)

MIN_DELTA = 0.05
HOLD_BARS = 12
STRESS_A = 1.5
STRESS_B = 3.0
TRAIN = (date(2018, 1, 1), date(2022, 12, 31))
HOLD = (date(2023, 1, 1), date(2025, 12, 31))
CTRL_LB = 20
SYMBOL = "EURUSD"


@dataclass
class Trade:
    direction: int
    entry_time: str
    exit_time: str
    gross_pips: float
    net_a_pips: float
    net_b_pips: float
    family: str
    delta: float


def parse_ymd(s: str) -> date:
    s = s.strip().replace("/", "-")
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        for fmt in ("%d %b %Y",):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        raise


def load_fred(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        cols = list(r.fieldnames or [])
        for row in r:
            try:
                v = float(row[cols[1]])
                if math.isfinite(v):
                    out[parse_ymd(row[cols[0]])] = v
            except Exception:
                continue
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


def lag_map(s: dict[date, float], n: int) -> dict[date, float]:
    return {d + timedelta(days=n): v for d, v in s.items()}


def asof(items: list[tuple[date, float]], d: date) -> float | None:
    lo, hi, best = 0, len(items) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid][0] <= d:
            best = items[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()


def metrics(trades: list[Trade], start: date, end: date) -> dict:
    sub = [t for t in trades if start <= datetime.fromisoformat(t.entry_time).date() <= end]
    n = len(sub)
    weeks = max((end - start).days / 7.0, 1e-9)

    def pf(vals):
        gp = sum(v for v in vals if v > 0)
        gl = -sum(v for v in vals if v < 0)
        if gl <= 0:
            return None if gp <= 0 else float("inf")
        return gp / gl

    a = [t.net_a_pips for t in sub]
    g = [t.gross_pips for t in sub]
    b = [t.net_b_pips for t in sub]
    return {
        "trades": n,
        "trades_per_week": n / weeks,
        "pf_gross": pf(g),
        "pf_stress_a": pf(a),
        "pf_stress_b": pf(b),
        "expectancy_a": (sum(a) / n) if n else None,
    }


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    try:
        server = mt5.account_info().server if mt5.account_info() else None
        dgs2 = lag_map(load_fred(EXO / "us_dgs2_DGS2.csv"), 1)
        ecb = lag_map(load_ecb(), 1)
        dgs_i, ecb_i = sorted(dgs2.items()), sorted(ecb.items())
        days = sorted(set(dgs2) | set(ecb))
        events: list[tuple[date, float, float]] = []
        prev = None
        for d in days:
            a = asof(dgs_i, d)
            e = asof(ecb_i, d)
            if a is None or e is None:
                continue
            state = a - e
            if prev is None:
                prev = state
                continue
            delta = state - prev
            if abs(delta) >= MIN_DELTA:
                events.append((d, state, delta))
            prev = state

        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_H4, datetime(2017, 1, 1), datetime(2026, 7, 1))
        rows = []
        for r in rates:
            ts = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
            rows.append({"ts": ts, "date": ts.date(), "close": float(r["close"])})
        closes = [r["close"] for r in rows]

        def sim(use_control: bool, family: str) -> list[Trade]:
            trades = []
            next_free = 0
            for avail_d, state, delta in events:
                entry_i = next((i for i, r in enumerate(rows) if r["date"] > avail_d), None)
                if entry_i is None or entry_i < next_free:
                    continue
                if use_control:
                    if entry_i < CTRL_LB:
                        continue
                    c0, c1 = closes[entry_i - 1 - CTRL_LB], closes[entry_i - 1]
                    if c0 == 0:
                        continue
                    direction = 1 if (c1 / c0 - 1) > 0 else -1
                else:
                    direction = 1 if state > 0 else (-1 if state < 0 else 0)
                if direction == 0:
                    continue
                if rows[entry_i]["ts"].weekday() == 4 and rows[entry_i]["ts"].hour >= 16:
                    continue
                exit_i = min(entry_i + HOLD_BARS, len(rows) - 1)
                for j in range(entry_i + 1, exit_i + 1):
                    if rows[j]["ts"].weekday() == 4 and rows[j]["ts"].hour >= 16:
                        exit_i = j
                        break
                gross = direction * (rows[exit_i]["close"] - rows[entry_i]["close"]) / 0.0001
                trades.append(
                    Trade(
                        direction=direction,
                        entry_time=rows[entry_i]["ts"].isoformat(),
                        exit_time=rows[exit_i]["ts"].isoformat(),
                        gross_pips=gross,
                        net_a_pips=gross - STRESS_A,
                        net_b_pips=gross - STRESS_B,
                        family=family,
                        delta=delta,
                    )
                )
                next_free = exit_i + 1
            return trades

        cand, ctrl = sim(False, "candidate"), sim(True, "control")
        train_c, train_k = metrics(cand, *TRAIN), metrics(ctrl, *TRAIN)
        reasons = []
        train_pass = True
        tpw = train_c["trades_per_week"] or 0
        if train_c["trades"] < 100:
            train_pass = False
            reasons.append("trades<100")
        if tpw < 1.5 or tpw > 5.0:
            train_pass = False
            reasons.append("cadence_out_of_band")
        pf_a = train_c["pf_stress_a"]
        if pf_a is None or pf_a < 1.10:
            train_pass = False
            reasons.append("pf_a")
        if (train_c["expectancy_a"] or 0) <= 0:
            train_pass = False
            reasons.append("expectancy")
        if pf_a is None or train_k["pf_stress_a"] is None or pf_a <= train_k["pf_stress_a"]:
            train_pass = False
            reasons.append("control")

        hold_c = metrics(cand, *HOLD) if train_pass else None
        hold_k = metrics(ctrl, *HOLD) if train_pass else None
        verdict = "KILL_AT_OFFLINE_PROBE"
        if train_pass:
            assert hold_c and hold_k
            if (
                hold_c["trades"] < 40
                or (hold_c["trades_per_week"] or 0) < 1.0
                or (hold_c["pf_stress_a"] or 0) < 1.0
                or (hold_c["pf_stress_a"] or 0) <= (hold_k["pf_stress_a"] or 0)
            ):
                verdict = "KILL_AT_OFFLINE_PROBE_HOLDOUT"
            else:
                verdict = "PROBE_SURVIVOR_CANDIDATE_FOR_PREREG"

        trades_path = OUT / "20260713_USEU_YIELD_POLICY_SHOCK_TRADES_V1.csv"
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            fields = list(asdict(cand[0]).keys()) if cand else list(Trade.__dataclass_fields__)
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "useu_yield_policy_shock_h4_probe.v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": verdict,
            "mt5_server": server,
            "n_events": len(events),
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "kill_reasons": reasons,
            "trades_csv_sha256": sha256_file(trades_path),
            "chatgpt_required": False,
        }
        out = OUT / "20260713_USEU_YIELD_POLICY_SHOCK_RESULT_V1.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"verdict": verdict, "events": len(events), "train_c": train_c, "train_k": train_k, "reasons": reasons}, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
