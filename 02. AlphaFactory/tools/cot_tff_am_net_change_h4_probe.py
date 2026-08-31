#!/usr/bin/env python3
"""COT TFF Asset-Manager net-change H4 probe (lagged publication)."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

WORKSPACE = Path(__file__).resolve().parents[2]
RAW = WORKSPACE / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "v8_exogenous" / "raw"
OUT = WORKSPACE / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "v8_probe"
OUT.mkdir(parents=True, exist_ok=True)

MAP = {
    "EURO FX - CHICAGO MERCANTILE EXCHANGE": ("EURUSD", 1),
    "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE": ("GBPUSD", 1),
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE": ("USDJPY", -1),
}
THR = 0.02
HOLD = 18
STRESS_A = 1.5
STRESS_B = 3.0
TRAIN = (date(2018, 1, 1), date(2022, 12, 31))
HOLDWIN = (date(2023, 1, 1), date(2025, 12, 31))
CTRL_LB = 20


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


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def load_cot_events() -> dict[str, list[tuple[date, int]]]:
    """symbol -> list of (available_date, direction)."""
    series: dict[str, list[tuple[date, float, float, int]]] = {
        "EURUSD": [],
        "GBPUSD": [],
        "USDJPY": [],
    }
    for year in range(2018, 2026):
        path = RAW / f"cot_tff_{year}_FinFutYY.txt"
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                name = (row.get("Market_and_Exchange_Names") or "").strip().strip('"')
                if name not in MAP:
                    continue
                sym, sign = MAP[name]
                try:
                    rep = date.fromisoformat(row["Report_Date_as_YYYY-MM-DD"])
                    am_l = float(row["Asset_Mgr_Positions_Long_All"])
                    am_s = float(row["Asset_Mgr_Positions_Short_All"])
                    oi = float(row["Open_Interest_All"])
                except Exception:
                    continue
                net = am_l - am_s
                series[sym].append((rep, net, oi, sign))
    events: dict[str, list[tuple[date, int]]] = {s: [] for s in series}
    for sym, rows in series.items():
        rows = sorted(rows, key=lambda x: x[0])
        prev_net = None
        for rep, net, oi, sign in rows:
            if prev_net is None:
                prev_net = net
                continue
            delta = net - prev_net
            prev_net = net
            if oi <= 0:
                continue
            if abs(delta) / oi < THR:
                continue
            direction = sign * (1 if delta > 0 else -1)
            avail = rep + timedelta(days=3)
            events[sym].append((avail, direction))
    return events


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
    return {
        "trades": n,
        "trades_per_week": n / weeks,
        "pf_stress_a": pf(a),
        "pf_gross": pf(g),
        "expectancy_a": (sum(a) / n) if n else None,
    }


def main() -> int:
    events = load_cot_events()
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    try:
        server = mt5.account_info().server if mt5.account_info() else None
        bars = {}
        for sym in events:
            rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_H4, datetime(2017, 1, 1), datetime(2026, 7, 1))
            rows = []
            for r in rates:
                ts = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
                rows.append({"ts": ts, "date": ts.date(), "close": float(r["close"])})
            bars[sym] = rows

        def sim(use_control: bool, family: str) -> list[Trade]:
            trades = []
            for sym, evs in events.items():
                rows = bars[sym]
                closes = [r["close"] for r in rows]
                next_free = 0
                for avail, direction in evs:
                    entry_i = next((i for i, r in enumerate(rows) if r["date"] > avail), None)
                    if entry_i is None or entry_i < next_free:
                        continue
                    dirn = direction
                    if use_control:
                        if entry_i < CTRL_LB:
                            continue
                        c0, c1 = closes[entry_i - 1 - CTRL_LB], closes[entry_i - 1]
                        if c0 == 0:
                            continue
                        dirn = 1 if (c1 / c0 - 1) > 0 else -1
                    if rows[entry_i]["ts"].weekday() == 4 and rows[entry_i]["ts"].hour >= 16:
                        continue
                    exit_i = min(entry_i + HOLD, len(rows) - 1)
                    for j in range(entry_i + 1, exit_i + 1):
                        if rows[j]["ts"].weekday() == 4 and rows[j]["ts"].hour >= 16:
                            exit_i = j
                            break
                    gross = dirn * (rows[exit_i]["close"] - rows[entry_i]["close"]) / pip_size(sym)
                    trades.append(
                        Trade(
                            symbol=sym,
                            direction=dirn,
                            entry_time=rows[entry_i]["ts"].isoformat(),
                            exit_time=rows[exit_i]["ts"].isoformat(),
                            gross_pips=gross,
                            net_a_pips=gross - STRESS_A,
                            net_b_pips=gross - STRESS_B,
                            family=family,
                        )
                    )
                    next_free = exit_i + 1
            return trades

        cand, ctrl = sim(False, "candidate"), sim(True, "control")
        train_c, train_k = metrics(cand, *TRAIN), metrics(ctrl, *TRAIN)
        reasons = []
        train_pass = True
        tpw = train_c["trades_per_week"] or 0
        if train_c["trades"] < 80:
            train_pass = False
            reasons.append("trades")
        if tpw < 1.2 or tpw > 5.0:
            train_pass = False
            reasons.append("cadence")
        pf_a = train_c["pf_stress_a"]
        if pf_a is None or pf_a < 1.10:
            train_pass = False
            reasons.append("pf")
        if (train_c["expectancy_a"] or 0) <= 0:
            train_pass = False
            reasons.append("expectancy")
        if pf_a is None or train_k["pf_stress_a"] is None or pf_a <= train_k["pf_stress_a"]:
            train_pass = False
            reasons.append("control")

        hold_c = metrics(cand, *HOLDWIN) if train_pass else None
        hold_k = metrics(ctrl, *HOLDWIN) if train_pass else None
        verdict = "KILL_AT_OFFLINE_PROBE"
        if train_pass:
            assert hold_c and hold_k
            if (
                hold_c["trades"] < 40
                or (hold_c["pf_stress_a"] or 0) < 1.0
                or (hold_c["pf_stress_a"] or 0) <= (hold_k["pf_stress_a"] or 0)
            ):
                verdict = "KILL_AT_OFFLINE_PROBE_HOLDOUT"
            else:
                verdict = "PROBE_SURVIVOR_CANDIDATE_FOR_PREREG"

        event_n = {s: len(v) for s, v in events.items()}
        trades_path = OUT / "20260713_COT_TFF_AM_NET_CHANGE_TRADES_V1.csv"
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            fields = list(asdict(cand[0]).keys()) if cand else list(Trade.__dataclass_fields__)
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "cot_tff_am_net_change_h4_probe.v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": verdict,
            "mt5_server": server,
            "event_counts": event_n,
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "kill_reasons": reasons,
            "trades_csv_sha256": hashlib.sha256(trades_path.read_bytes()).hexdigest(),
            "chatgpt_required": False,
        }
        out = OUT / "20260713_COT_TFF_AM_NET_CHANGE_RESULT_V1.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"verdict": verdict, "events": event_n, "train_c": train_c, "train_k": train_k, "reasons": reasons}, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
