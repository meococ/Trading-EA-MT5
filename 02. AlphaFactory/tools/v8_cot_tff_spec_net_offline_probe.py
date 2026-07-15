#!/usr/bin/env python3
"""V8 COT TFF Spec-Net Change offline probe (frozen contract).

Authority: Owner GOAL + skip-GPT self-research (2026-07-13).
Contract: research/preflight/v8_exogenous/20260713_V8_COT_TFF_PROBE_CONTRACT_V1.md
Discovery-only. MetaQuotes-Demo falsification. Not Strategy Tester / Model 0.
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
COT_DIR = RESEARCH / "preflight" / "v8_exogenous" / "raw" / "cot_tff_extracted"
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROBE_ID = "V8_COT_TFF_SPEC_NET_CHG_V1"
RESULT_NAME = "20260713_V8_COT_TFF_SPEC_NET_PROBE_RESULT_V1.json"
TRADES_NAME = "20260713_V8_COT_TFF_SPEC_NET_PROBE_TRADES_V1.csv"

YEARS = (2022, 2023, 2024, 2025)
TRAIN_START = date(2022, 1, 1)
TRAIN_END = date(2023, 12, 31)
HOLD_START = date(2024, 1, 1)
HOLD_END = date(2025, 12, 31)
STRESS_A = 1.5
STRESS_B = 3.0
OI_THRESH = 0.015
RET_LOOKBACK = 5
ATR_MULT = 1.5
PIP = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01}

# Market name substrings -> (symbol, sign_for_spec_to_fx_direction)
# EUR/GBP: +spec_net change => long spot FX
# JPY futures: +spec on JPY => long JPY => short USDJPY
MARKET_MAP = (
    (("EURO FX",), "EURUSD", 1),
    (("BRITISH POUND",), "GBPUSD", 1),
    (("JAPANESE YEN",), "USDJPY", -1),
)


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
    exit_reason: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date:
    return date.fromisoformat(s.strip()[:10])


def match_market(name: str) -> tuple[str, int] | None:
    u = name.upper()
    for keys, symbol, sign in MARKET_MAP:
        if any(k in u for k in keys) and "CHICAGO MERCANTILE" in u:
            return symbol, sign
    return None


def load_cot_series() -> dict[str, list[dict]]:
    """Return per-symbol sorted list of {report_date, available_at, spec_net, oi}."""
    by_sym: dict[str, dict[date, dict]] = {s: {} for _, s, _ in MARKET_MAP}
    for year in YEARS:
        path = COT_DIR / f"FinFutYY_{year}.txt"
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Market_and_Exchange_Names") or ""
                mapped = match_market(name)
                if mapped is None:
                    continue
                symbol, _sign = mapped
                rd = parse_ymd(row["Report_Date_as_YYYY-MM-DD"])
                am_l = float(row["Asset_Mgr_Positions_Long_All"] or 0)
                am_s = float(row["Asset_Mgr_Positions_Short_All"] or 0)
                lm_l = float(row["Lev_Money_Positions_Long_All"] or 0)
                lm_s = float(row["Lev_Money_Positions_Short_All"] or 0)
                oi = float(row["Open_Interest_All"] or 0)
                spec_net = (am_l - am_s) + (lm_l - lm_s)
                by_sym[symbol][rd] = {
                    "report_date": rd,
                    "available_at": rd + timedelta(days=3),
                    "spec_net": spec_net,
                    "oi": oi,
                }
    out: dict[str, list[dict]] = {}
    for symbol, mp in by_sym.items():
        rows = [mp[k] for k in sorted(mp)]
        out[symbol] = rows
        if len(rows) < 10:
            raise RuntimeError(f"insufficient_cot_rows:{symbol}:{len(rows)}")
    return out


def build_signals(cot: dict[str, list[dict]]) -> list[dict]:
    """Decision events: available_at, symbol, direction_candidate, d_spec_oi."""
    events: list[dict] = []
    for symbol, rows in cot.items():
        sign = next(m[2] for m in MARKET_MAP if m[1] == symbol)
        for i in range(1, len(rows)):
            prev, cur = rows[i - 1], rows[i]
            oi = max(cur["oi"], 1.0)
            d_spec = cur["spec_net"] - prev["spec_net"]
            d_oi = d_spec / oi
            if abs(d_oi) < OI_THRESH:
                direction = 0
            else:
                direction = sign if d_spec > 0 else -sign
            events.append(
                {
                    "symbol": symbol,
                    "available_at": cur["available_at"],
                    "report_date": cur["report_date"],
                    "direction": direction,
                    "d_spec_oi": d_oi,
                }
            )
    events.sort(key=lambda e: (e["available_at"], e["symbol"]))
    return events


def mt5_init() -> str:
    if not mt5.initialize():
        raise RuntimeError(f"mt5_init_failed:{mt5.last_error()}")
    info = mt5.account_info()
    server = info.server if info else "UNKNOWN"
    return server


def copy_d1(symbol: str, start: date, end: date):
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_D1,
        datetime(start.year, start.month, start.day, tzinfo=timezone.utc),
        datetime(end.year, end.month, end.day, 23, 59, tzinfo=timezone.utc),
    )
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"no_rates:{symbol}:{mt5.last_error()}")
    return rates


def bar_date(ts: int) -> date:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()


def atr14(closes_high_low: list[tuple[float, float, float]], i: int) -> float:
    """Wilder-ish simple mean TR over prior 14 bars ending at i-1 (closed)."""
    if i < 15:
        return float("nan")
    trs = []
    for j in range(i - 14, i):
        h, l, c_prev = closes_high_low[j][0], closes_high_low[j][1], closes_high_low[j - 1][2]
        trs.append(max(h - l, abs(h - c_prev), abs(l - c_prev)))
    return sum(trs) / 14.0


def first_bar_on_or_after(dates: list[date], d: date) -> int | None:
    for i, bd in enumerate(dates):
        if bd >= d:
            return i
    return None


def friday_on_or_before(d: date) -> date:
    # Flatten Friday of the week containing d if d is Mon-Fri; if weekend, previous Friday
    wd = d.weekday()  # Mon=0
    if wd <= 4:
        return d - timedelta(days=wd - 4) if wd > 4 else d + timedelta(days=(4 - wd))
    # Sat/Sun -> previous Friday
    return d - timedelta(days=wd - 4)


def simulate(events: list[dict], family: str) -> list[Trade]:
    """family=candidate uses event direction; family=control uses 5d return sign."""
    # Load bars per symbol covering full window
    bars: dict[str, any] = {}
    dates: dict[str, list[date]] = {}
    ohlc: dict[str, list[tuple[float, float, float]]] = {}
    for symbol in PIP:
        rates = copy_d1(symbol, date(2021, 12, 1), HOLD_END + timedelta(days=10))
        bars[symbol] = rates
        dates[symbol] = [bar_date(int(r["time"])) for r in rates]
        ohlc[symbol] = [(float(r["high"]), float(r["low"]), float(r["close"])) for r in rates]

    # Next decision dates per symbol for time-stop
    next_decision: dict[str, list[date]] = {s: [] for s in PIP}
    for e in events:
        next_decision[e["symbol"]].append(e["available_at"])

    trades: list[Trade] = []
    open_pos: dict[str, dict | None] = {s: None for s in PIP}

    for idx, e in enumerate(events):
        symbol = e["symbol"]
        avail = e["available_at"]
        # Close existing if this is a new decision for same symbol
        pos = open_pos[symbol]
        if pos is not None:
            # exit at first D1 on/after avail (or earlier friday already handled in entry path)
            exit_i = first_bar_on_or_after(dates[symbol], avail)
            if exit_i is not None and exit_i > pos["entry_i"]:
                _close_trade(trades, open_pos, symbol, exit_i, "next_cot", bars, dates, ohlc)

        direction = e["direction"]
        if family == "control":
            entry_i = first_bar_on_or_after(dates[symbol], avail)
            if entry_i is None or entry_i < RET_LOOKBACK:
                continue
            c_now = ohlc[symbol][entry_i - 1][2]
            c_prev = ohlc[symbol][entry_i - 1 - RET_LOOKBACK][2]
            if c_prev <= 0:
                continue
            ret = math.log(c_now / c_prev)
            direction = 1 if ret > 0 else (-1 if ret < 0 else 0)
            # still require candidate threshold episode existence (same calendar)
            if e["direction"] == 0 and abs(e["d_spec_oi"]) < OI_THRESH:
                # Contract: same COT calendar AND threshold machinery
                # Control only fires when threshold would have fired for candidate calendar
                # Re-read: "Same COT calendar and threshold machinery, but direction = sign of prior 5d returns"
                # So threshold still applies for control eligibility
                pass
            if abs(e["d_spec_oi"]) < OI_THRESH:
                continue
        else:
            if direction == 0:
                continue

        entry_i = first_bar_on_or_after(dates[symbol], avail)
        if entry_i is None or entry_i < 15:
            continue
        # Skip weekend entry: if available_at is Fri/Sat/Sun, first bar may be Monday — OK
        entry_px = float(bars[symbol][entry_i]["open"])  # enter at open of first bar after release
        # Contract says "first closed D1 bar at or after available_at" — use that bar's close as decision,
        # enter next open to avoid same-bar lookahead. Safer closed-bar: signal on completed bar,
        # fill at next open.
        # If entry_i bar date == avail and bar not yet "closed" in backtest sense we use next bar open.
        if dates[symbol][entry_i] < avail:
            continue
        # Use close of signal bar as decision; fill next open
        if entry_i + 1 >= len(bars[symbol]):
            continue
        signal_i = entry_i
        fill_i = entry_i + 1
        atr = atr14(ohlc[symbol], signal_i + 1)  # ATR known at signal close
        if not math.isfinite(atr) or atr <= 0:
            continue
        fill_px = float(bars[symbol][fill_i]["open"])
        stop_dist = ATR_MULT * atr
        if direction > 0:
            stop_px = fill_px - stop_dist
        else:
            stop_px = fill_px + stop_dist

        # Next COT available_at for this symbol after this one
        future = [d for d in next_decision[symbol] if d > avail]
        next_cot = future[0] if future else HOLD_END + timedelta(days=7)
        # Friday flatten: Friday on or before next_cot - 1 day? Contract: exit next COT or Friday flatten
        # Hold from fill until earlier of: stop, next COT decision bar, Friday close before weekend
        open_pos[symbol] = {
            "direction": direction,
            "entry_i": fill_i,
            "entry_px": fill_px,
            "stop_px": stop_px,
            "next_cot": next_cot,
            "d_spec_oi": e["d_spec_oi"],
            "family": family,
        }
        # Walk forward to resolve exit immediately for sequential clarity
        _resolve_open(trades, open_pos, symbol, bars, dates, ohlc)

    # Flatten any leftover
    for symbol in list(open_pos):
        if open_pos[symbol] is not None:
            last_i = len(bars[symbol]) - 1
            _close_trade(trades, open_pos, symbol, last_i, "eod_flatten", bars, dates, ohlc)
    return trades


def _resolve_open(trades, open_pos, symbol, bars, dates, ohlc):
    pos = open_pos[symbol]
    if pos is None:
        return
    for i in range(pos["entry_i"], len(bars[symbol])):
        bd = dates[symbol][i]
        h = float(bars[symbol][i]["high"])
        l = float(bars[symbol][i]["low"])
        c = float(bars[symbol][i]["close"])
        direction = pos["direction"]
        # Stop
        if direction > 0 and l <= pos["stop_px"]:
            _close_at(trades, open_pos, symbol, i, pos["stop_px"], "stop", bars, dates)
            return
        if direction < 0 and h >= pos["stop_px"]:
            _close_at(trades, open_pos, symbol, i, pos["stop_px"], "stop", bars, dates)
            return
        # Friday flatten: if weekday==Friday, exit at close
        if bd.weekday() == 4:
            _close_at(trades, open_pos, symbol, i, c, "friday_flat", bars, dates)
            return
        # Next COT
        if bd >= pos["next_cot"]:
            _close_at(trades, open_pos, symbol, i, c, "next_cot", bars, dates)
            return


def _close_at(trades, open_pos, symbol, i, exit_px, reason, bars, dates):
    pos = open_pos[symbol]
    if pos is None:
        return
    direction = pos["direction"]
    entry_px = pos["entry_px"]
    pip = PIP[symbol]
    gross = direction * (exit_px - entry_px) / pip
    trades.append(
        Trade(
            symbol=symbol,
            direction=direction,
            entry_date=dates[symbol][pos["entry_i"]].isoformat(),
            exit_date=dates[symbol][i].isoformat(),
            gross_pips=gross,
            net_a_pips=gross - STRESS_A,
            net_b_pips=gross - STRESS_B,
            family=pos["family"],
            d_spec_oi=pos["d_spec_oi"],
            exit_reason=reason,
        )
    )
    open_pos[symbol] = None


def _close_trade(trades, open_pos, symbol, i, reason, bars, dates, ohlc):
    pos = open_pos[symbol]
    if pos is None:
        return
    c = float(bars[symbol][i]["close"])
    _close_at(trades, open_pos, symbol, i, c, reason, bars, dates)


def metrics(trades: list[Trade], start: date, end: date) -> dict:
    subset = [
        t
        for t in trades
        if start <= date.fromisoformat(t.entry_date) <= end
    ]
    n = len(subset)
    weeks = max((end - start).days / 7.0, 1e-9)
    if n == 0:
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

    def pf(vals: list[float]) -> float:
        wins = sum(v for v in vals if v > 0)
        losses = -sum(v for v in vals if v < 0)
        if losses <= 0:
            return 99.0 if wins > 0 else 0.0
        return wins / losses

    g = [t.gross_pips for t in subset]
    a = [t.net_a_pips for t in subset]
    b = [t.net_b_pips for t in subset]
    return {
        "trades": n,
        "trades_per_week": n / weeks,
        "expectancy_gross_pips": sum(g) / n,
        "expectancy_a_pips": sum(a) / n,
        "pf_gross": pf(g),
        "pf_stress_a": pf(a),
        "pf_stress_b": pf(b),
        "sum_net_a_pips": sum(a),
        "sum_net_b_pips": sum(b),
    }


def year_concentration(trades: list[Trade], start: date, end: date) -> float | None:
    subset = [t for t in trades if start <= date.fromisoformat(t.entry_date) <= end]
    by_year: dict[int, float] = {}
    for t in subset:
        y = date.fromisoformat(t.entry_date).year
        by_year[y] = by_year.get(y, 0.0) + t.net_a_pips
    pos = {y: v for y, v in by_year.items() if v > 0}
    total_pos = sum(pos.values())
    if total_pos <= 0:
        return None
    return max(pos.values()) / total_pos


def main() -> int:
    server = mt5_init()
    try:
        cot = load_cot_series()
        events = build_signals(cot)
        cand = simulate(events, "candidate")
        ctrl = simulate(events, "control")

        train_c = metrics(cand, TRAIN_START, TRAIN_END)
        train_k = metrics(ctrl, TRAIN_START, TRAIN_END)
        kill = []
        if train_c["trades"] < 80:
            kill.append("train_trades<80")
        if train_c["trades_per_week"] < 0.5:
            kill.append("train_cadence_below_structural_floor")
        if train_c["pf_stress_a"] < 1.05:
            kill.append("train_pf_stress_a<1.05")
        beat_pf = train_c["pf_stress_a"] > train_k["pf_stress_a"]
        beat_exp = train_c["expectancy_a_pips"] > train_k["expectancy_a_pips"]
        if not (beat_pf and beat_exp):
            kill.append("fail_beat_control_pf_and_expectancy")
        conc = year_concentration(cand, TRAIN_START, TRAIN_END)
        if conc is not None and conc > 0.55:
            kill.append("year_concentration>0.55")

        hold_c = hold_k = None
        train_pass = len(kill) == 0
        if train_pass:
            hold_c = metrics(cand, HOLD_START, HOLD_END)
            hold_k = metrics(ctrl, HOLD_START, HOLD_END)

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
                    "exit_reason",
                ],
            )
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        status = "PROBE_SURVIVOR_TRAIN" if train_pass else "KILL_AT_OFFLINE_PROBE"
        result = {
            "schema": "v8_cot_tff_spec_net_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "mt5_server": server,
            "contract": "03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_COT_TFF_PROBE_CONTRACT_V1.md",
            "note": "MetaQuotes-Demo falsification only. Not Strategy Tester. Not EA/Model 0 unless survivor + prereg/cost.",
            "design_frozen": {
                "symbols": list(PIP.keys()),
                "oi_threshold": OI_THRESH,
                "available_at": "report_date+3d_00:00Z",
                "stress_a_pips": STRESS_A,
                "stress_b_pips": STRESS_B,
                "train": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
                "holdout": [HOLD_START.isoformat(), HOLD_END.isoformat()],
                "control": "same_calendar_threshold_5d_return_sign",
                "cot_events": len(events),
                "cot_rows": {s: len(v) for s, v in cot.items()},
            },
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "train_pass": train_pass,
            "kill_reasons": kill,
            "train_year_concentration_pos_net_a": conc,
            "trades_csv": str(trades_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "trades_csv_sha256": sha256_file(trades_path),
            "authority_flags": {
                "registry_append_authorized": False,
                "prereg_freeze_authorized": False,
                "ea_build_authorized": False,
                "compile_authorized": False,
                "backtest_authorized": False,
                "model_0_authorized": False,
            },
        }
        out = OUT_DIR / RESULT_NAME
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"status": status, "kill": kill, "train_c": train_c, "path": str(out)}, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
