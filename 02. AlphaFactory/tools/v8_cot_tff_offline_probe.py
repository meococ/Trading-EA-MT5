#!/usr/bin/env python3
"""V8 COT TFF speculative net-change offline probe (frozen contract).

Authority: Owner skip-GPT self-research + 1A fail-closed (2026-07-13).
Contract: research/preflight/v8_exogenous/20260713_V8_COT_TFF_PROBE_CONTRACT_V1.md
Discovery-only. Not Strategy Tester. Not promotion. Demo MT5 OK for falsification.
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

PROBE_ID = "V8_COT_TFF_SPEC_NET_CHG_V1"
RESULT_NAME = "20260713_V8_COT_TFF_PROBE_RESULT_V1.json"
TRADES_NAME = "20260713_V8_COT_TFF_PROBE_TRADES_V1.csv"

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")
TRAIN_START = date(2022, 1, 1)
TRAIN_END = date(2023, 12, 31)  # contract [2022-01-01, 2024-01-01)
HOLD_START = date(2024, 1, 1)
HOLD_END = date(2025, 12, 31)
STRESS_A = 1.5
STRESS_B = 3.0
OI_THRESH = 0.015
ATR_MULT = 1.5
ATR_PERIOD = 14
RELEASE_LAG_DAYS = 3

# Market name prefixes → (symbol, direction_sign for +d_spec)
# JPY futures: +spec on JPY → short USDJPY
MARKET_MAP = {
    "EURO FX - CHICAGO MERCANTILE EXCHANGE": ("EURUSD", 1),
    "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE": ("GBPUSD", 1),
    "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE": ("GBPUSD", 1),
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE": ("USDJPY", -1),
}

TRAIN_MIN_TRADES = 80
TRAIN_MIN_TPW = 0.5
TRAIN_MIN_PF_A = 1.05


@dataclass
class Trade:
    symbol: str
    direction: int
    entry_date: str
    exit_date: str
    gross_pips: float
    net_a_pips: float
    net_b_pips: float
    family: str
    d_spec_oi: float


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date:
    return date.fromisoformat(s.strip()[:10])


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def fnum(x: str | None) -> float:
    if x is None:
        return 0.0
    s = str(x).strip().replace(",", "")
    if s in ("", ".", "NA"):
        return 0.0
    return float(s)


def load_cot_series() -> dict[str, list[dict]]:
    """symbol -> list of {report_date, available_at, spec_net, oi} sorted."""
    by_sym: dict[str, dict[date, dict]] = {s: {} for s in SYMBOLS}
    for year in (2022, 2023, 2024, 2025):
        path = COT_DIR / f"FinFutYY_{year}.txt"
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open(encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                mkt = (row.get("Market_and_Exchange_Names") or "").strip().strip('"')
                mapped = MARKET_MAP.get(mkt)
                if mapped is None:
                    continue
                symbol, _dir_sign = mapped
                try:
                    report = parse_ymd(row["Report_Date_as_YYYY-MM-DD"])
                except Exception:
                    continue
                oi = fnum(row.get("Open_Interest_All"))
                am_l = fnum(row.get("Asset_Mgr_Positions_Long_All"))
                am_s = fnum(row.get("Asset_Mgr_Positions_Short_All"))
                lm_l = fnum(row.get("Lev_Money_Positions_Long_All"))
                lm_s = fnum(row.get("Lev_Money_Positions_Short_All"))
                spec_net = (am_l - am_s) + (lm_l - lm_s)
                by_sym[symbol][report] = {
                    "report_date": report,
                    "available_at": report + timedelta(days=RELEASE_LAG_DAYS),
                    "spec_net": spec_net,
                    "oi": oi,
                    "dir_sign": MARKET_MAP[mkt][1],
                }
    out: dict[str, list[dict]] = {}
    for sym, dmap in by_sym.items():
        rows = sorted(dmap.values(), key=lambda x: x["report_date"])
        if len(rows) < 2:
            raise RuntimeError(f"insufficient COT rows for {sym}: {len(rows)}")
        out[sym] = rows
    return out


def fetch_d1(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_D1,
        datetime(2021, 1, 1),
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


def atr14(bars: list[dict], idx: int) -> float | None:
    if idx < ATR_PERIOD:
        return None
    trs = []
    for i in range(idx - ATR_PERIOD + 1, idx + 1):
        h, l, prev_c = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    return sum(trs) / ATR_PERIOD


def find_entry_idx(bars: list[dict], available_at: date) -> int | None:
    for i, b in enumerate(bars):
        if b["date"] >= available_at:
            return i
    return None


def simulate_symbol(
    symbol: str,
    cot_rows: list[dict],
    bars: list[dict],
    family: str,
) -> list[Trade]:
    date_to_idx = {b["date"]: i for i, b in enumerate(bars)}
    dir_sign = cot_rows[0]["dir_sign"]
    trades: list[Trade] = []
    ps = pip_size(symbol)

    for t in range(1, len(cot_rows)):
        prev, cur = cot_rows[t - 1], cot_rows[t]
        d_spec = cur["spec_net"] - prev["spec_net"]
        oi = max(cur["oi"], 1.0)
        d_spec_oi = abs(d_spec) / oi
        if d_spec_oi < OI_THRESH:
            continue
        available_at = cur["available_at"]
        entry_i = find_entry_idx(bars, available_at)
        if entry_i is None or entry_i < ATR_PERIOD:
            continue
        # Skip weekend entry: move to next weekday bar if needed
        while entry_i < len(bars) and bars[entry_i]["date"].weekday() >= 5:
            entry_i += 1
        if entry_i >= len(bars):
            continue

        if family == "candidate":
            direction = dir_sign if d_spec > 0 else -dir_sign
        else:
            # control: sign of prior 5 completed D1 log returns ending at bar before entry
            if entry_i < 6:
                continue
            r = 0.0
            ok = True
            for k in range(entry_i - 5, entry_i):
                c0, c1 = bars[k - 1]["close"], bars[k]["close"]
                if c0 <= 0:
                    ok = False
                    break
                r += math.log(c1 / c0)
            if not ok or r == 0:
                continue
            direction = 1 if r > 0 else -1

        entry = bars[entry_i]
        atr = atr14(bars, entry_i)
        if atr is None or atr <= 0:
            continue
        stop_dist = ATR_MULT * atr
        entry_px = entry["close"]
        stop_px = entry_px - direction * stop_dist

        # Exit: next COT available_at entry bar, or Friday flatten before weekend
        next_avail = None
        if t + 1 < len(cot_rows):
            next_avail = cot_rows[t + 1]["available_at"]

        exit_i = None
        exit_px = None
        for j in range(entry_i + 1, len(bars)):
            b = bars[j]
            # intraday stop using high/low of bar
            if direction > 0:
                if b["low"] <= stop_px:
                    exit_i, exit_px = j, stop_px
                    break
            else:
                if b["high"] >= stop_px:
                    exit_i, exit_px = j, stop_px
                    break
            # Friday flatten at close (no weekend hold)
            if b["date"].weekday() == 4:
                exit_i, exit_px = j, b["close"]
                break
            # Next COT decision day reached
            if next_avail is not None and b["date"] >= next_avail:
                exit_i, exit_px = j, b["close"]
                break
        if exit_i is None:
            # last bar
            exit_i = len(bars) - 1
            exit_px = bars[exit_i]["close"]
            if exit_i <= entry_i:
                continue

        gross = direction * (exit_px - entry_px) / ps
        trades.append(
            Trade(
                symbol=symbol,
                direction=direction,
                entry_date=str(entry["date"]),
                exit_date=str(bars[exit_i]["date"]),
                gross_pips=gross,
                net_a_pips=gross - STRESS_A,
                net_b_pips=gross - STRESS_B,
                family=family,
                d_spec_oi=d_spec_oi if family == "candidate" else 0.0,
            )
        )
    return trades


def summarize(trades: list[Trade]) -> dict:
    if not trades:
        return {
            "trades": 0,
            "trades_per_week": 0.0,
            "expectancy_gross_pips": 0.0,
            "expectancy_a_pips": 0.0,
            "pf_gross": 0.0,
            "pf_stress_a": 0.0,
            "pf_stress_b": 0.0,
            "sum_net_a_pips": 0.0,
            "sum_net_b_pips": 0.0,
        }
    gp = [t.gross_pips for t in trades]
    na = [t.net_a_pips for t in trades]
    nb = [t.net_b_pips for t in trades]

    def pf(xs: list[float]) -> float:
        wins = sum(x for x in xs if x > 0)
        losses = -sum(x for x in xs if x < 0)
        if losses <= 0:
            return 999.0 if wins > 0 else 0.0
        return wins / losses

    d0 = date.fromisoformat(min(t.entry_date for t in trades))
    d1 = date.fromisoformat(max(t.exit_date for t in trades))
    weeks = max((d1 - d0).days / 7.0, 1e-9)
    return {
        "trades": len(trades),
        "trades_per_week": len(trades) / weeks,
        "expectancy_gross_pips": sum(gp) / len(gp),
        "expectancy_a_pips": sum(na) / len(na),
        "pf_gross": pf(gp),
        "pf_stress_a": pf(na),
        "pf_stress_b": pf(nb),
        "sum_net_a_pips": sum(na),
        "sum_net_b_pips": sum(nb),
    }


def in_split(t: Trade, start: date, end: date) -> bool:
    ed = date.fromisoformat(t.entry_date)
    return start <= ed <= end


def elapsed_weeks(start: date, end: date) -> float:
    return max((end - start).days / 7.0, 1e-9)


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(f"mt5 init failed: {mt5.last_error()}")
    try:
        info = mt5.account_info()
        server = info.server if info else "UNKNOWN"
        cot = load_cot_series()
        bars = {s: fetch_d1(s) for s in SYMBOLS}

        cand: list[Trade] = []
        ctrl: list[Trade] = []
        for s in SYMBOLS:
            cand.extend(simulate_symbol(s, cot[s], bars[s], "candidate"))
            ctrl.extend(simulate_symbol(s, cot[s], bars[s], "control"))

        train_c = [t for t in cand if in_split(t, TRAIN_START, TRAIN_END)]
        train_k = [t for t in ctrl if in_split(t, TRAIN_START, TRAIN_END)]
        sc = summarize(train_c)
        sk = summarize(train_k)
        # Use elapsed calendar weeks of train window for cadence (GOAL rule)
        train_weeks = elapsed_weeks(TRAIN_START, TRAIN_END)
        sc["trades_per_week"] = sc["trades"] / train_weeks
        sk["trades_per_week"] = sk["trades"] / train_weeks

        kills: list[str] = []
        if sc["trades"] < TRAIN_MIN_TRADES:
            kills.append("train_trades<80")
        if sc["trades_per_week"] < TRAIN_MIN_TPW:
            kills.append("train_cadence_below_structural_floor")
        if sc["pf_stress_a"] < TRAIN_MIN_PF_A:
            kills.append("train_pf_stress_a<1.05")
        beat_pf = sc["pf_stress_a"] > sk["pf_stress_a"]
        beat_exp = sc["expectancy_a_pips"] > sk["expectancy_a_pips"]
        if not (beat_pf and beat_exp):
            kills.append("fail_beat_control_pf_and_expectancy")

        train_pass = len(kills) == 0
        hold_c = hold_k = None
        if train_pass:
            hc = [t for t in cand if in_split(t, HOLD_START, HOLD_END)]
            hk = [t for t in ctrl if in_split(t, HOLD_START, HOLD_END)]
            hold_weeks = elapsed_weeks(HOLD_START, HOLD_END)
            hold_c = summarize(hc)
            hold_k = summarize(hk)
            hold_c["trades_per_week"] = hold_c["trades"] / hold_weeks
            hold_k["trades_per_week"] = hold_k["trades"] / hold_weeks

        trades_path = OUT_DIR / TRADES_NAME
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=list(asdict(cand[0]).keys()) if cand else [
                    "symbol",
                    "direction",
                    "entry_date",
                    "exit_date",
                    "gross_pips",
                    "net_a_pips",
                    "net_b_pips",
                    "family",
                    "d_spec_oi",
                ],
            )
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "v8_cot_tff_spec_net_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PROBE_SURVIVOR" if train_pass else "KILL_AT_OFFLINE_PROBE",
            "mt5_server": server,
            "note": (
                "MetaQuotes-Demo falsification only; not FivePercentOnline-Real "
                "cost provenance. Not Strategy Tester. Frozen contract "
                "20260713_V8_COT_TFF_PROBE_CONTRACT_V1.md. Independent of killed "
                "carry weekly/daily/rate-event books."
            ),
            "design_frozen": {
                "symbols": list(SYMBOLS),
                "timeframe": "D1",
                "oi_thresh": OI_THRESH,
                "release_lag_days": RELEASE_LAG_DAYS,
                "stress_a_pips": STRESS_A,
                "stress_b_pips": STRESS_B,
                "atr_stop_mult": ATR_MULT,
                "train": [str(TRAIN_START), str(TRAIN_END)],
                "holdout": [str(HOLD_START), str(HOLD_END)],
                "control": "sign_prior_5d_log_return_same_calendar",
                "spec_net": "AssetMgr_net + LevMoney_net",
            },
            "train_candidate": sc,
            "train_control": sk,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "train_pass": train_pass,
            "kill_reasons": kills,
            "trades_csv": str(trades_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "trades_csv_sha256": sha256_file(trades_path),
            "authority_flags": {
                "registry_append_authorized": bool(train_pass),
                "prereg_freeze_authorized": bool(train_pass),
                "ea_build_authorized": bool(train_pass),
                "compile_authorized": bool(train_pass),
                "backtest_authorized": bool(train_pass),
                "model_0_authorized": False,  # still needs frozen prereg + cost gate
            },
        }
        out_path = OUT_DIR / RESULT_NAME
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"status": result["status"], "kills": kills, "train": sc}, indent=2))
        return 0 if train_pass else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
