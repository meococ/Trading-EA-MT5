#!/usr/bin/env python3
"""Offline probe: lagged CFTC TFF leveraged-money FX positioning regime (H4).

Frozen a priori (self-research, no GPT). Independent of killed carry books and
EqCloseFlow S682-S685. MetaQuotes-Demo falsification only.

Mechanism:
  Net Lev_Money (long-short) on CME EURO FX / BRITISH POUND / JAPANESE YEN
  futures, lagged past CFTC Friday release, gates Mon-Thu H4 directional
  exposure on EURUSD / GBPUSD / USDJPY. Friday flat. Matched momentum control
  ignores COT.

Release lag (conservative):
  Report_Date (as-of Tuesday) + 4 calendar days => available_at 00:00 UTC
  (covers Friday 15:30 ET publish + buffer; no same-week peek).
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

WORKSPACE = Path(__file__).resolve().parents[2]
RESEARCH = WORKSPACE / "03. EA Developer" / "EA_SonicR" / "research"
COT_DIR = RESEARCH / "preflight" / "v8_exogenous" / "raw" / "cot_tff_extracted"
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")
MARKET_MAP = {
    "EURUSD": ("EURO FX", 1),   # +net lev money => long EURUSD
    "GBPUSD": ("BRITISH POUND", 1),
    "USDJPY": ("JAPANESE YEN", -1),  # +net yen futures => long JPY => short USDJPY
}
TRAIN_START, TRAIN_END = date(2021, 1, 1), date(2023, 12, 31)
HOLD_START, HOLD_END = date(2024, 1, 1), date(2025, 12, 31)
STRESS_A, STRESS_B = 1.5, 2.5
ATR_PERIOD, SL_ATR, TIME_STOP = 14, 1.5, 6
MOM_LB = 20
COT_LAG_DAYS = 4
NET_DEADBAND = 5000  # contracts; a priori, not tuned
PROBE_ID = "V8_COT_TFF_LEVMONEY_H4_V1"
RESULT = "20260713_V8_COT_TFF_LEVMONEY_H4_PROBE_RESULT_V1.json"
TRADES = "20260713_V8_COT_TFF_LEVMONEY_H4_PROBE_TRADES_V1.csv"


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
    exit_reason: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date:
    return date.fromisoformat(s.strip()[:10].replace("/", "-").replace(".", "-"))


def load_cot_net() -> dict[str, dict[date, float]]:
    """available_at -> net lev money for each FX symbol orientation."""
    raw: dict[str, dict[date, float]] = {s: {} for s in SYMBOLS}
    files = sorted(COT_DIR.glob("FinFutYY_*.txt"))
    if not files:
        raise SystemExit(f"no_cot_files:{COT_DIR}")
    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                name = (row.get("Market_and_Exchange_Names") or "").upper()
                try:
                    asof = parse_ymd(row["Report_Date_as_YYYY-MM-DD"])
                    lev_l = float(row["Lev_Money_Positions_Long_All"])
                    lev_s = float(row["Lev_Money_Positions_Short_All"])
                except Exception:
                    continue
                net = lev_l - lev_s
                avail = asof + timedelta(days=COT_LAG_DAYS)
                for sym, (needle, sign) in MARKET_MAP.items():
                    if needle in name:
                        raw[sym][avail] = sign * net
    return raw


def asof(series: dict[date, float], d: date) -> float | None:
    best_d = None
    best = None
    for ad, v in series.items():
        if ad <= d and (best_d is None or ad > best_d):
            best_d = ad
            best = v
    return best


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def fetch_h4(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, datetime(2019, 1, 1), datetime(2026, 7, 1))
    if rates is None:
        raise RuntimeError(f"no_h4:{symbol}:{mt5.last_error()}")
    out = []
    for r in rates:
        t = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
        out.append(
            {
                "time": t,
                "date": t.date(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            }
        )
    return out


def wilder_atr(rows: list[dict], period: int = ATR_PERIOD) -> list[float | None]:
    atr: list[float | None] = [None] * len(rows)
    if len(rows) < period + 1:
        return atr
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i]["high"], rows[i]["low"], rows[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    prev = sum(trs[:period]) / period
    atr[period] = prev
    for i in range(period + 1, len(rows)):
        prev = (prev * (period - 1) + trs[i - 1]) / period
        atr[i] = prev
    return atr


def metrics(trades: list[Trade], start: date, end: date) -> dict:
    subset = [t for t in trades if start <= parse_ymd(t.entry_time[:10]) <= end]
    n = len(subset)
    weeks = max((end - start).days / 7.0, 1e-9)

    def pf(vals: list[float]) -> float | None:
        gp = sum(v for v in vals if v > 0)
        gl = -sum(v for v in vals if v < 0)
        if gl <= 0:
            return None if gp <= 0 else float("inf")
        return gp / gl

    g = [t.gross_pips for t in subset]
    a = [t.net_a_pips for t in subset]
    b = [t.net_b_pips for t in subset]
    return {
        "trades": n,
        "trades_per_week": n / weeks,
        "expectancy_a_pips": (sum(a) / n) if n else None,
        "pf_gross": pf(g),
        "pf_stress_a": pf(a),
        "pf_stress_b": pf(b),
        "sum_net_a_pips": sum(a),
    }


def simulate(h4, atrs, dir_fn, family: str) -> list[Trade]:
    by_time: dict[datetime, dict[str, int]] = {}
    for sym, rows in h4.items():
        for i, row in enumerate(rows):
            by_time.setdefault(row["time"], {})[sym] = i
    times = sorted(t for t, m in by_time.items() if all(s in m for s in SYMBOLS))
    trades: list[Trade] = []
    pos_sym = None
    pos_dir = 0
    entry_px = 0.0
    entry_time = None
    stop_px = 0.0
    bars_held = 0

    def close(sym, t, px, reason):
        nonlocal pos_sym, pos_dir, entry_px, entry_time, stop_px, bars_held
        if pos_sym is None or entry_time is None:
            return
        gross = pos_dir * (px - entry_px) / pip_size(sym)
        trades.append(
            Trade(
                symbol=sym,
                direction=pos_dir,
                entry_time=entry_time.isoformat(),
                exit_time=t.isoformat(),
                gross_pips=gross,
                net_a_pips=gross - STRESS_A,
                net_b_pips=gross - STRESS_B,
                family=family,
                exit_reason=reason,
            )
        )
        pos_sym = None
        pos_dir = 0
        entry_px = 0.0
        entry_time = None
        stop_px = 0.0
        bars_held = 0

    for t in times:
        idxs = by_time[t]
        if pos_sym is not None:
            i = idxs[pos_sym]
            row = h4[pos_sym][i]
            bars_held += 1
            hit = False
            if pos_dir > 0 and row["low"] <= stop_px:
                close(pos_sym, t, stop_px, "stop")
                hit = True
            elif pos_dir < 0 and row["high"] >= stop_px:
                close(pos_sym, t, stop_px, "stop")
                hit = True
            if not hit and bars_held >= TIME_STOP:
                close(pos_sym, t, row["close"], "time_stop")

        if t.weekday() == 4:
            if pos_sym is not None:
                close(pos_sym, t, h4[pos_sym][idxs[pos_sym]]["close"], "friday_flat")
            continue
        if t.weekday() > 4:
            continue

        dirs = {s: dir_fn(s, t.date(), idxs[s], h4) for s in SYMBOLS}
        if any(v is None for v in dirs.values()):
            continue
        cands = [(s, v) for s, v in dirs.items() if v not in (0, None)]
        if not cands:
            if pos_sym is not None:
                close(pos_sym, t, h4[pos_sym][idxs[pos_sym]]["close"], "flat_signal")
            continue
        best_sym, strength = max(cands, key=lambda x: (abs(x[1]), -SYMBOLS.index(x[0])))
        target_dir = 1 if strength > 0 else -1
        if pos_sym == best_sym and pos_dir == target_dir:
            continue
        if pos_sym is not None:
            close(pos_sym, t, h4[pos_sym][idxs[pos_sym]]["close"], "rebalance")
        i = idxs[best_sym]
        atr = atrs[best_sym][i]
        if atr is None or atr <= 0:
            continue
        entry_px = h4[best_sym][i]["close"]
        pos_sym = best_sym
        pos_dir = target_dir
        entry_time = t
        bars_held = 0
        stop_px = entry_px - SL_ATR * atr if target_dir > 0 else entry_px + SL_ATR * atr

    if pos_sym is not None and times:
        t = times[-1]
        close(pos_sym, t, h4[pos_sym][by_time[t][pos_sym]]["close"], "end")
    return trades


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"mt5_init_failed:{mt5.last_error()}")
    try:
        info = mt5.account_info()
        server = getattr(info, "server", None) if info else None
        cot = load_cot_net()
        for s in SYMBOLS:
            if len(cot[s]) < 50:
                raise SystemExit(f"cot_sparse:{s}:{len(cot[s])}")

        h4 = {s: fetch_h4(s) for s in SYMBOLS}
        atrs = {s: wilder_atr(h4[s]) for s in SYMBOLS}

        def cot_dir(sym, d, idx, bars):
            v = asof(cot[sym], d)
            if v is None:
                return None
            if v > NET_DEADBAND:
                return float(v)
            if v < -NET_DEADBAND:
                return float(v)
            return 0.0

        def mom_dir(sym, d, idx, bars):
            rows = bars[sym]
            if idx < MOM_LB:
                return None
            c0, c1 = rows[idx - MOM_LB]["close"], rows[idx]["close"]
            if c0 <= 0:
                return None
            r = c1 / c0 - 1.0
            if r > 0:
                return 1.0
            if r < 0:
                return -1.0
            return 0.0

        cand = simulate(h4, atrs, cot_dir, "candidate")
        ctrl = simulate(h4, atrs, mom_dir, "control")
        train_c, train_k = metrics(cand, TRAIN_START, TRAIN_END), metrics(ctrl, TRAIN_START, TRAIN_END)

        reasons = []
        train_pass = True
        if (train_c["trades"] or 0) < 80:
            train_pass = False
            reasons.append("train_trades<80")
        if (train_c["trades_per_week"] or 0) < 0.5:
            train_pass = False
            reasons.append("train_cadence_below_structural_floor")
        pf_a = train_c["pf_stress_a"]
        if pf_a is None or pf_a < 1.10:
            train_pass = False
            reasons.append("train_pf_stress_a<1.10")
        kpf = train_k["pf_stress_a"]
        if pf_a is not None and kpf is not None and pf_a <= kpf:
            train_pass = False
            reasons.append("train_did_not_beat_control_pf")

        hold_c = hold_k = None
        hold_reasons = []
        hold_pass = None
        if train_pass:
            hold_c, hold_k = metrics(cand, HOLD_START, HOLD_END), metrics(ctrl, HOLD_START, HOLD_END)
            hold_pass = True
            if (hold_c["pf_stress_b"] or 0) < 1.0:
                hold_pass = False
                hold_reasons.append("holdout_pf_stress_b<1.00")
            if (hold_c["expectancy_a_pips"] or 0) <= 0:
                hold_pass = False
                hold_reasons.append("holdout_exp<=0")
            tpw = hold_c["trades_per_week"] or 0
            if tpw < 0.5 or tpw > 8:
                hold_pass = False
                hold_reasons.append("holdout_tpw_outside_[0.5,8]")
            if (hold_c["pf_stress_a"] or 0) <= (hold_k["pf_stress_a"] or 0):
                hold_pass = False
                hold_reasons.append("holdout_did_not_beat_control_pf")

        status = "PROBE_SURVIVOR" if (train_pass and hold_pass) else "KILL_AT_OFFLINE_PROBE"
        trades_path = OUT_DIR / TRADES
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            fields = list(asdict(cand[0]).keys()) if cand else [
                "symbol", "direction", "entry_time", "exit_time", "gross_pips",
                "net_a_pips", "net_b_pips", "family", "exit_reason",
            ]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "v8_cot_tff_levmoney_h4_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "mt5_server": server,
            "note": "Demo falsification only. Not Model 0. COT lag +4d from Report_Date.",
            "design_frozen": {
                "symbols": list(SYMBOLS),
                "cot_fields": "Lev_Money_Long - Lev_Money_Short",
                "cot_lag_days_from_report_date": COT_LAG_DAYS,
                "net_deadband_contracts": NET_DEADBAND,
                "timeframe": "H4",
                "friday_flat": True,
                "stop": f"{SL_ATR}*ATR{ATR_PERIOD}",
                "time_stop": TIME_STOP,
                "stress_a": STRESS_A,
                "stress_b": STRESS_B,
                "control": "sign_prior_20_H4_returns",
                "train": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
                "holdout": [HOLD_START.isoformat(), HOLD_END.isoformat()],
            },
            "cot_coverage": {s: len(cot[s]) for s in SYMBOLS},
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "train_pass": train_pass,
            "holdout_pass": hold_pass,
            "kill_reasons": reasons + hold_reasons,
            "trades_csv": str(trades_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "trades_csv_sha256": sha256_file(trades_path),
            "authority_flags": {
                "registry_append_authorized": status == "PROBE_SURVIVOR",
                "prereg_freeze_authorized": status == "PROBE_SURVIVOR",
                "ea_build_authorized": False,
                "model_0_authorized": False,
            },
        }
        out = OUT_DIR / RESULT
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": status, "train": train_c, "control": train_k, "kill_reasons": result["kill_reasons"], "out": str(out)}, indent=2))
        return 0 if status == "PROBE_SURVIVOR" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
