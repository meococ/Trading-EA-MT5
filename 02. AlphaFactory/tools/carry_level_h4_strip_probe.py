#!/usr/bin/env python3
"""Carry LEVEL sign daily H4 strip probe — independent of weekly rank and Δ-event."""
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
HOLD_BARS = 2
STRESS_A = 1.5
STRESS_B = 3.0
TRAIN = (date(2018, 1, 1), date(2022, 12, 31))
HOLD = (date(2023, 1, 1), date(2025, 12, 31))


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
    carry: float


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
                out[parse_ymd(row[cols[0]])] = float(row[cols[1]])
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


def load_boe() -> dict[date, float]:
    out: dict[date, float] = {}
    with (RAW / "boe_bank_rate.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[parse_ymd(row["DATE"])] = float(row["IUDBEDR"])
            except Exception:
                continue
    return out


def load_jpy() -> dict[date, float]:
    out: dict[date, float] = {}
    with (RAW / "jpy_boj_uncollateralized_overnight_call_daily.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
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


def asof_value(items: list[tuple[date, float]], d: date) -> float | None:
    lo, hi, best = 0, len(items) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid][0] <= d:
            best = items[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def pair_carry(symbol: str, usd: float, eur: float, gbp: float, jpy: float) -> float:
    if symbol == "EURUSD":
        return eur - usd
    if symbol == "GBPUSD":
        return gbp - usd
    return usd - jpy


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def fetch_h4(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol, mt5.TIMEFRAME_H4, datetime(2017, 1, 1), datetime(2026, 7, 1)
    )
    if rates is None:
        raise RuntimeError(f"{symbol}: {mt5.last_error()}")
    rows = []
    for r in rates:
        ts = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
        rows.append({"ts": ts, "date": ts.date(), "close": float(r["close"])})
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
    g = [t.gross_pips for t in sub]
    b = [t.net_b_pips for t in sub]
    return {
        "trades": n,
        "trades_per_week": n / weeks,
        "pf_gross": pf(g),
        "pf_stress_a": pf(a),
        "pf_stress_b": pf(b),
        "expectancy_a": (sum(a) / n) if n else None,
        "sum_net_a": sum(a),
    }


def simulate(
    bars: dict[str, list[dict]],
    usd_i,
    eur_i,
    gbp_i,
    jpy_i,
    family: str,
    use_control: bool,
) -> list[Trade]:
    trades: list[Trade] = []
    for sym in SYMBOLS:
        rows = bars[sym]
        # first bar index per UTC date
        first_i: dict[date, int] = {}
        for i, row in enumerate(rows):
            first_i.setdefault(row["date"], i)
        # prior day close map
        day_close: dict[date, float] = {}
        for row in rows:
            day_close[row["date"]] = row["close"]
        dates = sorted(first_i)
        next_free = 0
        for d in dates:
            i = first_i[d]
            if i < next_free:
                continue
            u = asof_value(usd_i, d)
            e = asof_value(eur_i, d)
            g = asof_value(gbp_i, d)
            j = asof_value(jpy_i, d)
            if None in (u, e, g, j):
                continue
            carry = pair_carry(sym, u, e, g, j)  # type: ignore[arg-type]
            if use_control:
                prev_days = [x for x in dates if x < d]
                if len(prev_days) < 2:
                    continue
                d1, d0 = prev_days[-1], prev_days[-2]
                if day_close[d0] == 0:
                    continue
                direction = 1 if (day_close[d1] / day_close[d0] - 1.0) > 0 else -1
            else:
                direction = 1 if carry > 0 else (-1 if carry < 0 else 0)
            if direction == 0:
                continue
            ts = rows[i]["ts"]
            if ts.weekday() == 4 and ts.hour >= 16:
                continue
            exit_i = min(i + HOLD_BARS, len(rows) - 1)
            for j in range(i + 1, exit_i + 1):
                if rows[j]["ts"].weekday() == 4 and rows[j]["ts"].hour >= 16:
                    exit_i = j
                    break
            gross = direction * (rows[exit_i]["close"] - rows[i]["close"]) / pip_size(sym)
            trades.append(
                Trade(
                    symbol=sym,
                    direction=direction,
                    entry_time=rows[i]["ts"].isoformat(),
                    exit_time=rows[exit_i]["ts"].isoformat(),
                    gross_pips=gross,
                    net_a_pips=gross - STRESS_A,
                    net_b_pips=gross - STRESS_B,
                    family=family,
                    carry=carry,
                )
            )
            next_free = exit_i + 1
    return trades


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    try:
        server = mt5.account_info().server if mt5.account_info() else None
        usd = load_fred(EXO / "us_fed_funds_DFF.csv")
        usd.update(load_fred(EXO / "us_sofr_SOFR.csv"))
        eur, gbp, jpy = load_ecb(), load_boe(), load_jpy()
        usd_l, eur_l, gbp_l, jpy_l = (
            lag_map(usd, 1),
            lag_map(eur, 1),
            lag_map(gbp, 1),
            lag_map(jpy, 2),
        )
        usd_i, eur_i, gbp_i, jpy_i = (
            sorted(usd_l.items()),
            sorted(eur_l.items()),
            sorted(gbp_l.items()),
            sorted(jpy_l.items()),
        )
        bars = {s: fetch_h4(s) for s in SYMBOLS}
        cand = simulate(bars, usd_i, eur_i, gbp_i, jpy_i, "candidate", False)
        ctrl = simulate(bars, usd_i, eur_i, gbp_i, jpy_i, "control", True)
        train_c, train_k = metrics(cand, *TRAIN), metrics(ctrl, *TRAIN)
        reasons = []
        train_pass = True
        tpw = train_c["trades_per_week"] or 0
        if train_c["trades"] < 150:
            train_pass = False
            reasons.append("train_trades<150")
        if tpw < 2.0 or tpw > 6.0:
            train_pass = False
            reasons.append("train_cadence_out_of_2_6")
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
            assert hold_c and hold_k
            htpw = hold_c["trades_per_week"] or 0
            if (
                hold_c["trades"] < 60
                or htpw < 1.5
                or htpw > 7.0
                or (hold_c["pf_stress_a"] or 0) < 1.0
                or (hold_c["pf_stress_a"] or 0) <= (hold_k["pf_stress_a"] or 0)
            ):
                verdict = "KILL_AT_OFFLINE_PROBE_HOLDOUT"
            else:
                verdict = "PROBE_SURVIVOR_CANDIDATE_FOR_PREREG"

        trades_path = OUT / "20260713_CARRY_LEVEL_H4_STRIP_TRADES_V1.csv"
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
                "carry",
            ]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "carry_level_h4_strip_probe.v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": verdict,
            "mt5_server": server,
            "design_freeze": "03. EA Developer/EA_SonicR/research/preregs/20260713_H_CARRY_LEVEL_H4_STRIP_V1_PROBE_FREEZE.md",
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "train_pass": train_pass,
            "kill_reasons": reasons,
            "trades_csv_sha256": sha256_file(trades_path),
            "authority_flags": {
                "registry_append_authorized": verdict == "PROBE_SURVIVOR_CANDIDATE_FOR_PREREG",
                "chatgpt_required": False,
            },
        }
        out = OUT / "20260713_CARRY_LEVEL_H4_STRIP_RESULT_V1.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"verdict": verdict, "train_c": train_c, "train_k": train_k, "reasons": reasons}, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
