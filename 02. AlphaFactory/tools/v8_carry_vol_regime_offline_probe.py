#!/usr/bin/env python3
"""V8 offline probe: carry exposure gated by FX vol innovation (Menkhoff-style).

Frozen contract:
  03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_CARRY_VOL_JOIN_CONTRACT_V1.md

Authority: Owner self-research / no-GPT (2026-07-13 night) + prior V8 rates surface.
Discovery-only. MetaQuotes-Demo falsification. Not Strategy Tester / Model 0.

Independent of killed weekly/daily/rate-event carry rank books and of
HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001.
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
RAW = RESEARCH / "preflight" / "v8_exogenous" / "raw"
EXO = RESEARCH / "preflight" / "v8_exogenous"
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")
TRAIN_START = date(2021, 1, 1)
TRAIN_END = date(2023, 12, 31)  # train half-open end exclusive in contract; inclusive close for metrics
HOLDOUT_START = date(2024, 1, 1)
HOLDOUT_END = date(2025, 12, 31)
STRESS_A = 1.5
STRESS_B = 2.5
CARRY_DEADBAND = 0.25
ATR_PERIOD = 14
SL_ATR = 1.5
TIME_STOP_BARS = 6
MOM_LOOKBACK = 20
VOL_MIN_DAYS = 60
RESULT_NAME = "20260713_V8_CARRY_VOL_REGIME_PROBE_RESULT_V1.json"
TRADES_NAME = "20260713_V8_CARRY_VOL_REGIME_PROBE_TRADES_V1.csv"
PROBE_ID = "V8_CARRY_VOL_REGIME_V1"

TRAIN_MIN_TRADES = 80
TRAIN_MIN_TPW = 0.5
TRAIN_MIN_PF_A = 1.10


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
    s = s.strip().replace("/", "-").replace(".", "-")
    return date.fromisoformat(s[:10])


def load_csv_series(path: Path, date_keys: tuple[str, ...], val_keys: tuple[str, ...]) -> dict[date, float]:
    out: dict[date, float] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        keys = list(r.fieldnames or [])
        for row in r:
            d_raw = None
            for k in date_keys:
                if k in row and row[k]:
                    d_raw = row[k]
                    break
            if d_raw is None and keys:
                d_raw = row.get(keys[0])
            v_raw = None
            for k in val_keys:
                if k in row and row[k] not in (None, "", "NA", "n.a.", "ND"):
                    v_raw = row[k]
                    break
            if v_raw is None and len(keys) > 1:
                v_raw = row.get(keys[1])
            if d_raw is None or v_raw in (None, "", "NA", "n.a.", "ND"):
                continue
            try:
                d = parse_ymd(str(d_raw))
                v = float(v_raw)
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def load_treasury_13w_proxy() -> dict[date, float]:
    """Prefer 13-week coupon equivalent; fall back to 4-week / 8-week."""
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
                    "13 WEEKS COUPON EQUIVALENT",
                    "13 WEEKS BANK DISCOUNT",
                    "8 WEEKS COUPON EQUIVALENT",
                    "4 WEEKS COUPON EQUIVALENT",
                    "4 WEEKS BANK DISCOUNT",
                ):
                    if key in row and row[key] not in (None, ""):
                        try:
                            val = float(row[key])
                            break
                        except ValueError:
                            pass
                if val is not None and math.isfinite(val):
                    out[d] = val
    if not out:
        # FRED FEDFUNDS fallback as last resort (same lag applied later).
        out = load_csv_series(EXO / "fedfunds.csv", ("DATE", "observation_date", "date"), ("FEDFUNDS", "value", "OBS_VALUE"))
    return out


def lag_series(series: dict[date, float], lag_days: int) -> dict[date, float]:
    return {d + timedelta(days=lag_days): v for d, v in series.items()}


def asof(series: dict[date, float], d: date) -> float | None:
    best = None
    best_d = None
    for ad, v in series.items():
        if ad <= d and (best_d is None or ad > best_d):
            best_d = ad
            best = v
    return best


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def pair_carry(symbol: str, usd: float, eur: float, gbp: float, jpy: float) -> float:
    if symbol == "EURUSD":
        return eur - usd
    if symbol == "GBPUSD":
        return gbp - usd
    if symbol == "USDJPY":
        return usd - jpy
    raise KeyError(symbol)


def fetch_bars(symbol: str, timeframe: int) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol,
        timeframe,
        datetime(2019, 1, 1),
        datetime(2026, 7, 1),
    )
    if rates is None:
        raise RuntimeError(f"no rates for {symbol}: {mt5.last_error()}")
    rows = []
    for r in rates:
        t = datetime.utcfromtimestamp(int(r["time"])).replace(tzinfo=timezone.utc)
        rows.append(
            {
                "time": t,
                "date": t.date(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            }
        )
    return rows


def wilder_atr(rows: list[dict], period: int = ATR_PERIOD) -> list[float | None]:
    atr: list[float | None] = [None] * len(rows)
    if len(rows) < period + 1:
        return atr
    trs: list[float] = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i]["high"], rows[i]["low"], rows[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    # first ATR at index period (using trs[0:period])
    first = sum(trs[:period]) / period
    atr[period] = first
    prev = first
    for i in range(period + 1, len(rows)):
        # trs index is i-1
        prev = (prev * (period - 1) + trs[i - 1]) / period
        atr[i] = prev
    return atr


def build_daily_sigma(d1: dict[str, list[dict]]) -> dict[date, float]:
    """sigma_t = mean abs daily log returns across three pairs."""
    by_date: dict[date, dict[str, float]] = {}
    for sym, rows in d1.items():
        prev = None
        for row in rows:
            if prev is not None and prev > 0 and row["close"] > 0:
                lr = math.log(row["close"] / prev)
                by_date.setdefault(row["date"], {})[sym] = abs(lr)
            prev = row["close"]
    sigma: dict[date, float] = {}
    for d, m in by_date.items():
        if all(s in m for s in SYMBOLS):
            sigma[d] = sum(m[s] for s in SYMBOLS) / 3.0
    return sigma


def build_vol_innovation(sigma: dict[date, float]) -> dict[date, float]:
    """AR(1) expanding residual of sigma; min 60 days. Positive => risk-off."""
    dates = sorted(sigma)
    innov: dict[date, float] = {}
    if len(dates) < VOL_MIN_DAYS + 1:
        return innov
    # Expanding OLS of sigma_t = a + b * sigma_{t-1}
    for i in range(VOL_MIN_DAYS, len(dates)):
        ys = [sigma[dates[j]] for j in range(1, i + 1)]
        xs = [sigma[dates[j - 1]] for j in range(1, i + 1)]
        n = len(ys)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        var_x = sum((x - mean_x) ** 2 for x in xs)
        if var_x <= 0:
            continue
        cov = sum((xs[k] - mean_x) * (ys[k] - mean_y) for k in range(n))
        b = cov / var_x
        a = mean_y - b * mean_x
        pred = a + b * sigma[dates[i - 1]]
        innov[dates[i]] = sigma[dates[i]] - pred
    return innov


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


def year_concentration(trades: list[Trade], start: date, end: date) -> float | None:
    subset = [t for t in trades if start <= parse_ymd(t.entry_time[:10]) <= end]
    pos_by_year: dict[int, float] = {}
    for t in subset:
        if t.net_a_pips > 0:
            y = parse_ymd(t.entry_time[:10]).year
            pos_by_year[y] = pos_by_year.get(y, 0.0) + t.net_a_pips
    total = sum(pos_by_year.values())
    if total <= 0:
        return None
    return max(pos_by_year.values()) / total


def simulate(
    h4: dict[str, list[dict]],
    atrs: dict[str, list[float | None]],
    signal_dir_fn,
    family: str,
) -> list[Trade]:
    """Mon-Thu H4 decisions; Friday flatten. One symbol book at a time (highest |carry|)."""
    # Align by timestamp across symbols.
    by_time: dict[datetime, dict[str, int]] = {}
    for sym, rows in h4.items():
        for i, row in enumerate(rows):
            by_time.setdefault(row["time"], {})[sym] = i

    times = sorted(t for t, m in by_time.items() if all(s in m for s in SYMBOLS))
    trades: list[Trade] = []
    pos_sym: str | None = None
    pos_dir = 0
    entry_px = 0.0
    entry_time: datetime | None = None
    entry_idx = -1
    stop_px = 0.0
    bars_held = 0

    def close(sym: str, t: datetime, px: float, reason: str) -> None:
        nonlocal pos_sym, pos_dir, entry_px, entry_time, entry_idx, stop_px, bars_held
        if pos_sym is None or entry_time is None:
            return
        ps = pip_size(sym)
        gross = pos_dir * (px - entry_px) / ps
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
        entry_idx = -1
        stop_px = 0.0
        bars_held = 0

    for t in times:
        d = t.date()
        weekday = t.weekday()  # Mon=0 .. Fri=4
        idxs = by_time[t]

        # Intrabar stop / time-stop on open of new bar using prior path extremes:
        # use this bar's high/low vs stop (conservative closed-bar approx).
        if pos_sym is not None:
            i = idxs[pos_sym]
            row = h4[pos_sym][i]
            bars_held += 1
            hit_stop = False
            if pos_dir > 0 and row["low"] <= stop_px:
                close(pos_sym, t, stop_px, "stop")
                hit_stop = True
            elif pos_dir < 0 and row["high"] >= stop_px:
                close(pos_sym, t, stop_px, "stop")
                hit_stop = True
            if not hit_stop and bars_held >= TIME_STOP_BARS:
                close(pos_sym, t, row["close"], "time_stop")

        # Friday flatten at decision bar close.
        if weekday == 4:
            if pos_sym is not None:
                i = idxs[pos_sym]
                close(pos_sym, t, h4[pos_sym][i]["close"], "friday_flat")
            continue

        if weekday > 4:
            continue

        # Decision only Mon-Thu on completed bar close.
        dirs = {s: signal_dir_fn(s, d, idxs[s], h4) for s in SYMBOLS}
        if any(v is None for v in dirs.values()):
            continue

        # Choose the pair with strongest |carry-or-mom signal| among non-zero dirs.
        # For candidate, signal_dir_fn returns signed direction; strength from abs carry embedded.
        candidates = [(s, dirs[s]) for s in SYMBOLS if dirs[s] not in (0, None)]
        if not candidates:
            if pos_sym is not None:
                i = idxs[pos_sym]
                close(pos_sym, t, h4[pos_sym][i]["close"], "flat_signal")
            continue

        # Prefer existing position if still valid; else pick first by fixed symbol order of max abs intent.
        # Strength: for candidate we pass strength via secondary lookup in closure.
        best_sym, best_dir = max(
            candidates,
            key=lambda x: (abs(x[1]), -SYMBOLS.index(x[0])),
        )
        # dirs store +/-1 only for control; for candidate we store signed strength.
        target_dir = 1 if best_dir > 0 else -1
        target_sym = best_sym

        if pos_sym == target_sym and pos_dir == target_dir:
            continue
        if pos_sym is not None:
            i = idxs[pos_sym]
            close(pos_sym, t, h4[pos_sym][i]["close"], "rebalance")

        i = idxs[target_sym]
        atr = atrs[target_sym][i]
        if atr is None or atr <= 0:
            continue
        entry_px = h4[target_sym][i]["close"]
        pos_sym = target_sym
        pos_dir = target_dir
        entry_time = t
        entry_idx = i
        bars_held = 0
        if target_dir > 0:
            stop_px = entry_px - SL_ATR * atr
        else:
            stop_px = entry_px + SL_ATR * atr

    if pos_sym is not None and times:
        t = times[-1]
        i = by_time[t][pos_sym]
        close(pos_sym, t, h4[pos_sym][i]["close"], "end")
    return trades


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"mt5_init_failed:{mt5.last_error()}")
    try:
        info = mt5.account_info()
        server = getattr(info, "server", None) if info else None

        usd = lag_series(load_treasury_13w_proxy(), 1)
        eur = lag_series(
            load_csv_series(
                RAW / "ecb_dfr_daily.csv",
                ("TIME_PERIOD", "DATE", "date"),
                ("OBS_VALUE", "value"),
            )
            or load_csv_series(EXO / "ecbdfr.csv", ("DATE", "observation_date"), ("ECBDFR", "value")),
            1,
        )
        gbp = lag_series(
            load_csv_series(RAW / "boe_bank_rate.csv", ("DATE", "Date", "date"), ("Bank Rate", "IUDBEDR", "value", "OBS_VALUE"))
            or load_csv_series(EXO / "iudsoia.csv", ("DATE", "observation_date"), ("IUDSOIA", "value")),
            1,
        )
        jpy = lag_series(
            load_csv_series(
                RAW / "jpy_boj_uncollateralized_overnight_call_daily.csv",
                ("observation_date", "date", "DATE", "TIME_PERIOD"),
                ("BOJ_CALL_ON", "value", "OBS_VALUE", "rate"),
            ),
            2,
        )
        if not usd or not eur or not gbp or not jpy:
            raise SystemExit(
                f"rates_incomplete usd={len(usd)} eur={len(eur)} gbp={len(gbp)} jpy={len(jpy)}"
            )

        d1 = {s: fetch_bars(s, mt5.TIMEFRAME_D1) for s in SYMBOLS}
        h4 = {s: fetch_bars(s, mt5.TIMEFRAME_H4) for s in SYMBOLS}
        atrs = {s: wilder_atr(h4[s]) for s in SYMBOLS}
        sigma = build_daily_sigma(d1)
        innov = build_vol_innovation(sigma)

        # Cache carry by date for strength ranking.
        carry_by: dict[date, dict[str, float]] = {}

        def carry_dirs(sym: str, d: date, idx: int, bars: dict[str, list[dict]]) -> float | None:
            u, e, g, j = asof(usd, d), asof(eur, d), asof(gbp, d), asof(jpy, d)
            if None in (u, e, g, j):
                return None
            vol_i = asof(innov, d)
            if vol_i is None:
                return None
            if vol_i > 0:
                return 0.0  # flatten regime
            c = pair_carry(sym, u, e, g, j)  # type: ignore[arg-type]
            carry_by.setdefault(d, {})[sym] = c
            if c > CARRY_DEADBAND:
                return c  # positive strength + long
            if c < -CARRY_DEADBAND:
                return c  # negative strength + short
            return 0.0

        def mom_dirs(sym: str, d: date, idx: int, bars: dict[str, list[dict]]) -> float | None:
            rows = bars[sym]
            if idx < MOM_LOOKBACK:
                return None
            c0 = rows[idx - MOM_LOOKBACK]["close"]
            c1 = rows[idx]["close"]
            if c0 <= 0:
                return None
            ret = (c1 / c0) - 1.0
            if ret > 0:
                return 1.0
            if ret < 0:
                return -1.0
            return 0.0

        cand = simulate(h4, atrs, carry_dirs, "candidate")
        ctrl = simulate(h4, atrs, mom_dirs, "control")

        train_c = metrics(cand, TRAIN_START, TRAIN_END)
        train_k = metrics(ctrl, TRAIN_START, TRAIN_END)

        reasons: list[str] = []
        train_pass = True
        if (train_c["trades"] or 0) < TRAIN_MIN_TRADES:
            train_pass = False
            reasons.append("train_trades<80")
        if (train_c["trades_per_week"] or 0) < TRAIN_MIN_TPW:
            train_pass = False
            reasons.append("train_cadence_below_structural_floor")
        pf_a = train_c["pf_stress_a"]
        if pf_a is None or pf_a < TRAIN_MIN_PF_A:
            train_pass = False
            reasons.append("train_pf_stress_a<1.10")
        kpf = train_k["pf_stress_a"]
        if pf_a is not None and kpf is not None and pf_a <= kpf:
            train_pass = False
            reasons.append("train_did_not_beat_control_pf")

        hold_c = hold_k = None
        hold_pass = None
        hold_reasons: list[str] = []
        if train_pass:
            hold_c = metrics(cand, HOLDOUT_START, HOLDOUT_END)
            hold_k = metrics(ctrl, HOLDOUT_START, HOLDOUT_END)
            hold_pass = True
            if (hold_c["pf_stress_b"] or 0) < 1.00:
                hold_pass = False
                hold_reasons.append("holdout_pf_stress_b<1.00")
            if (hold_c["expectancy_a_pips"] or 0) <= 0:
                hold_pass = False
                hold_reasons.append("holdout_exp<=0")
            tpw = hold_c["trades_per_week"] or 0
            if tpw < 0.5 or tpw > 8.0:
                hold_pass = False
                hold_reasons.append("holdout_tpw_outside_[0.5,8]")
            if (hold_c["pf_stress_a"] or 0) <= (hold_k["pf_stress_a"] or 0):
                hold_pass = False
                hold_reasons.append("holdout_did_not_beat_control_pf")
            if (hold_c["expectancy_a_pips"] or 0) <= (hold_k["expectancy_a_pips"] or 0):
                hold_pass = False
                hold_reasons.append("holdout_did_not_beat_control_exp")
            conc = year_concentration(cand, HOLDOUT_START, HOLDOUT_END)
            if conc is not None and conc > 0.55:
                hold_pass = False
                hold_reasons.append("holdout_year_concentration>0.55")

        status = "PROBE_SURVIVOR" if (train_pass and hold_pass) else "KILL_AT_OFFLINE_PROBE"
        if not train_pass:
            status = "KILL_AT_OFFLINE_PROBE"

        trades_path = OUT_DIR / TRADES_NAME
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=list(asdict(cand[0]).keys()) if cand else [
                    "symbol",
                    "direction",
                    "entry_time",
                    "exit_time",
                    "gross_pips",
                    "net_a_pips",
                    "net_b_pips",
                    "family",
                    "exit_reason",
                ],
            )
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "v8_carry_vol_regime_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "mt5_server": server,
            "note": "MetaQuotes-Demo falsification only. Not Strategy Tester. Not EA/Model0 authority unless PROBE_SURVIVOR + separate prereg/cost.",
            "contract_path": "03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_CARRY_VOL_JOIN_CONTRACT_V1.md",
            "design_frozen": {
                "symbols": list(SYMBOLS),
                "timeframe": "H4",
                "rebalance": "MonThu_H4_close_Friday_flat",
                "carry_deadband": CARRY_DEADBAND,
                "vol_gate": "AR1_expanding_residual_sigma_positive_flat",
                "stop": f"{SL_ATR}*ATR{ATR_PERIOD}_H4",
                "time_stop_bars": TIME_STOP_BARS,
                "stress_a_pips": STRESS_A,
                "stress_b_pips": STRESS_B,
                "train": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
                "holdout": [HOLDOUT_START.isoformat(), HOLDOUT_END.isoformat()],
                "control": "sign_prior_20_H4_returns_same_stops_costs_weekend",
            },
            "rates_coverage": {
                "usd": len(usd),
                "eur": len(eur),
                "gbp": len(gbp),
                "jpy": len(jpy),
                "sigma_days": len(sigma),
                "innov_days": len(innov),
            },
            "train_candidate": train_c,
            "train_control": train_k,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "train_pass": train_pass,
            "holdout_pass": hold_pass,
            "kill_reasons": reasons + (hold_reasons if hold_reasons else []),
            "trades_csv": str(trades_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "trades_csv_sha256": sha256_file(trades_path),
            "authority_flags": {
                "registry_append_authorized": bool(status == "PROBE_SURVIVOR"),
                "prereg_freeze_authorized": bool(status == "PROBE_SURVIVOR"),
                "ea_build_authorized": False,
                "compile_authorized": False,
                "backtest_authorized": False,
                "model_0_authorized": False,
            },
        }
        out = OUT_DIR / RESULT_NAME
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": status, "train": train_c, "kill_reasons": result["kill_reasons"], "out": str(out)}, indent=2))
        return 0 if status == "PROBE_SURVIVOR" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
