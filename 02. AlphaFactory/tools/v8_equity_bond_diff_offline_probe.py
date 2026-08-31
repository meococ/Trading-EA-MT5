#!/usr/bin/env python3
"""V8 equity–bond differential → USD basket offline probe.

Contract:
  research/preflight/v8_exogenous/20260713_V8_EQUITY_BOND_DIFF_JOIN_CONTRACT_V1.md

Owner skip-GPT self-research. MetaQuotes-Demo falsification only. Not Model 0.
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
EB = RESEARCH / "preflight" / "v8_exogenous" / "raw" / "equity_bond"
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROBE_ID = "V8_EQUITY_BOND_DIFF_V1"
RESULT_NAME = "20260713_V8_EQUITY_BOND_DIFF_PROBE_RESULT_V1.json"
TRADES_NAME = "20260713_V8_EQUITY_BOND_DIFF_PROBE_TRADES_V1.csv"

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")
TRAIN_START = date(2019, 1, 1)
TRAIN_END_EXCL = date(2023, 1, 1)
HOLDOUT_START = date(2023, 1, 1)
HOLDOUT_END_EXCL = date(2026, 1, 1)

STRESS_A = 1.5
STRESS_B = 3.0
ATR_PERIOD = 14
SL_ATR = 1.5
TIME_STOP_BARS = 5
Z_LOOKBACK = 60
Z_MIN_OBS = 40
Z_THRESH = 0.75
MAX_GAP_DAYS = 3
MOD_DUR = 7.0

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
    leg_gross_json: str = "{}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date:
    s = s.strip().replace("/", "-").replace(".", "-")
    return date.fromisoformat(s[:10])


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def load_fred_series(path: Path, value_key: str) -> dict[date, float]:
    out: dict[date, float] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            raw_d = row.get("observation_date") or row.get("DATE") or row.get("date")
            raw_v = row.get(value_key)
            if raw_v is None:
                # second column fallback
                keys = list(row.keys())
                if len(keys) >= 2:
                    raw_v = row.get(keys[1])
            if not raw_d or raw_v in (None, "", ".", "NA", "ND"):
                continue
            try:
                d = parse_ymd(str(raw_d))
                v = float(raw_v)
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def series_returns(levels: dict[date, float]) -> dict[date, float]:
    dates = sorted(levels)
    out: dict[date, float] = {}
    for i in range(1, len(dates)):
        d0, d1 = dates[i - 1], dates[i]
        p0, p1 = levels[d0], levels[d1]
        if p0 > 0 and math.isfinite(p0) and math.isfinite(p1):
            out[d1] = p1 / p0 - 1.0
    return out


def yield_bond_returns(yields_pct: dict[date, float]) -> dict[date, float]:
    """Bond return proxy from yield change in percent points: -MOD_DUR * Δy/100? 

    DGS10 is stored as percent (e.g. 4.06). Δy in decimal = (y_t - y_{t-1}) / 100.
    Contract: r_bond = -7.0 * Δy with Δy in decimal yield.
    """
    dates = sorted(yields_pct)
    out: dict[date, float] = {}
    for i in range(1, len(dates)):
        d0, d1 = dates[i - 1], dates[i]
        y0, y1 = yields_pct[d0], yields_pct[d1]
        if not (math.isfinite(y0) and math.isfinite(y1)):
            continue
        dy_decimal = (y1 - y0) / 100.0
        out[d1] = -MOD_DUR * dy_decimal
    return out


def align_diff(r_eq: dict[date, float], r_bond: dict[date, float]) -> dict[date, float]:
    common = sorted(set(r_eq) & set(r_bond))
    return {d: r_eq[d] - r_bond[d] for d in common}


def lag_available(series: dict[date, float]) -> dict[date, float]:
    return {d + timedelta(days=1): v for d, v in series.items()}


def asof_strict(series: dict[date, float], d: date, max_gap: int = MAX_GAP_DAYS) -> float | None:
    best_d = None
    best_v = None
    for ad, v in series.items():
        if ad <= d and (best_d is None or ad > best_d):
            best_d = ad
            best_v = v
    if best_d is None or best_v is None:
        return None
    if (d - best_d).days > max_gap:
        return None
    return best_v


def build_z(avail: dict[date, float]) -> dict[date, float]:
    dates = sorted(avail)
    zmap: dict[date, float] = {}
    for i, d in enumerate(dates):
        window: list[float] = []
        j = i - 1
        while j >= 0 and len(window) < Z_LOOKBACK:
            window.append(avail[dates[j]])
            j -= 1
        if len(window) < Z_MIN_OBS:
            continue
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / len(window)
        if var <= 0:
            continue
        zmap[d] = (avail[d] - mean) / math.sqrt(var)
    return zmap


def fetch_d1(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_D1,
        datetime(2018, 1, 1),
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
    first = sum(trs[:period]) / period
    atr[period] = first
    prev = first
    for i in range(period + 1, len(rows)):
        prev = (prev * (period - 1) + trs[i - 1]) / period
        atr[i] = prev
    return atr


def metrics(trades: list[Trade], start: date, end_excl: date) -> dict:
    subset = [t for t in trades if start <= parse_ymd(t.entry_time[:10]) < end_excl]
    n = len(subset)
    weeks = max((end_excl - start).days / 7.0, 1e-9)

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


def year_concentration(trades: list[Trade], start: date, end_excl: date) -> float | None:
    subset = [
        t
        for t in trades
        if start <= parse_ymd(t.entry_time[:10]) < end_excl and t.net_a_pips > 0
    ]
    pos_by_year: dict[int, float] = {}
    for t in subset:
        y = parse_ymd(t.entry_time[:10]).year
        pos_by_year[y] = pos_by_year.get(y, 0.0) + t.net_a_pips
    total = sum(pos_by_year.values())
    if total <= 0:
        return None
    return max(pos_by_year.values()) / total


def simulate_basket(
    d1: dict[str, list[dict]],
    atrs: dict[str, list[float | None]],
    idx_by_date: dict[str, dict[date, int]],
    direction_fn,
    family: str,
) -> list[Trade]:
    common = None
    for sym in SYMBOLS:
        s = set(idx_by_date[sym].keys())
        common = s if common is None else (common & s)
    dates = sorted(d for d in (common or set()) if d.weekday() < 5)

    trades: list[Trade] = []
    pos_dir = 0
    entry_time: datetime | None = None
    entry_px: dict[str, float] = {}
    stop_px: dict[str, float] = {}
    bars_held = 0
    leg_dirs: dict[str, int] = {}

    def leg_direction(usd_dir: int) -> dict[str, int]:
        if usd_dir > 0:
            return {"EURUSD": -1, "GBPUSD": -1, "USDJPY": 1}
        return {"EURUSD": 1, "GBPUSD": 1, "USDJPY": -1}

    def close_basket(d: date, reason: str, exit_px: dict[str, float] | None = None) -> None:
        nonlocal pos_dir, entry_time, entry_px, stop_px, bars_held, leg_dirs
        if pos_dir == 0 or entry_time is None:
            return
        leg_gross: dict[str, float] = {}
        for sym in SYMBOLS:
            px = (exit_px or {}).get(sym, d1[sym][idx_by_date[sym][d]]["close"])
            ps = pip_size(sym)
            leg_gross[sym] = leg_dirs[sym] * (px - entry_px[sym]) / ps
        mean_gross = sum(leg_gross.values()) / 3.0
        mean_a = sum(g - STRESS_A for g in leg_gross.values()) / 3.0
        mean_b = sum(g - STRESS_B for g in leg_gross.values()) / 3.0
        t_exit = d1[SYMBOLS[0]][idx_by_date[SYMBOLS[0]][d]]["time"]
        trades.append(
            Trade(
                symbol="BASKET",
                direction=pos_dir,
                entry_time=entry_time.isoformat(),
                exit_time=t_exit.isoformat(),
                gross_pips=mean_gross,
                net_a_pips=mean_a,
                net_b_pips=mean_b,
                family=family,
                exit_reason=reason,
                leg_gross_json=json.dumps(leg_gross, sort_keys=True),
            )
        )
        pos_dir = 0
        entry_time = None
        entry_px = {}
        stop_px = {}
        bars_held = 0
        leg_dirs = {}

    for d in dates:
        weekday = d.weekday()
        idxs = {s: idx_by_date[s][d] for s in SYMBOLS}

        if pos_dir != 0:
            bars_held += 1
            hit_stop = False
            stop_exit_px: dict[str, float] = {}
            for sym in SYMBOLS:
                row = d1[sym][idxs[sym]]
                ld = leg_dirs[sym]
                if ld > 0 and row["low"] <= stop_px[sym]:
                    stop_exit_px[sym] = stop_px[sym]
                    hit_stop = True
                elif ld < 0 and row["high"] >= stop_px[sym]:
                    stop_exit_px[sym] = stop_px[sym]
                    hit_stop = True
                else:
                    stop_exit_px[sym] = row["close"]
            if hit_stop:
                close_basket(d, "stop", stop_exit_px)
            elif bars_held >= TIME_STOP_BARS:
                close_basket(d, "time_stop")

        if weekday == 4:
            if pos_dir != 0:
                close_basket(d, "friday_flat")
            continue

        D = direction_fn(d)
        if D is None:
            continue
        D = int(D)
        if D == 0:
            if pos_dir != 0:
                close_basket(d, "flat_signal")
            continue

        if pos_dir == D:
            continue
        if pos_dir != 0:
            close_basket(d, "rebalance")

        atr_ok = True
        for sym in SYMBOLS:
            atr = atrs[sym][idxs[sym]]
            if atr is None or atr <= 0:
                atr_ok = False
                break
        if not atr_ok:
            continue

        pos_dir = D
        leg_dirs = leg_direction(D)
        entry_time = d1[SYMBOLS[0]][idxs[SYMBOLS[0]]]["time"]
        bars_held = 0
        for sym in SYMBOLS:
            entry_px[sym] = d1[sym][idxs[sym]]["close"]
            atr = atrs[sym][idxs[sym]]
            assert atr is not None
            if leg_dirs[sym] > 0:
                stop_px[sym] = entry_px[sym] - SL_ATR * atr
            else:
                stop_px[sym] = entry_px[sym] + SL_ATR * atr

    if pos_dir != 0 and dates:
        close_basket(dates[-1], "end")
    return trades


def z_to_usd_dir(z: float | None) -> int | None:
    if z is None:
        return None
    if z >= Z_THRESH:
        return -1  # risk-on → USD weakness
    if z <= -Z_THRESH:
        return 1  # risk-off → USD strength
    return 0


def main() -> int:
    spx_path = EB / "fred_sp500.csv"
    dgs_path = EB / "mirror_us_dgs10_DGS10.csv"
    file_meta = []
    for p in (spx_path, dgs_path):
        if p.is_file():
            file_meta.append(
                {
                    "path": str(p.relative_to(WORKSPACE)).replace("\\", "/"),
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                }
            )

    spx = load_fred_series(spx_path, "SP500")
    dgs = load_fred_series(dgs_path, "DGS10")
    if len(spx) < 100 or len(dgs) < 100:
        result = {
            "schema": "v8_equity_bond_diff_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "DATA_MISSING",
            "kill_reasons": ["equity_or_bond_series_missing"],
            "authority_flags": {
                "registry_append_authorized": False,
                "prereg_freeze_authorized": False,
                "ea_build_authorized": False,
                "compile_authorized": False,
                "backtest_authorized": False,
                "model_0_authorized": False,
            },
        }
        (OUT_DIR / RESULT_NAME).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 3

    r_eq = series_returns(spx)
    r_bond = yield_bond_returns(dgs)
    diff = align_diff(r_eq, r_bond)

    # Bond-strength series for bond-only control: -r_bond (bond rally = positive)
    bond_strength = {d: -r_bond[d] for d in r_bond}

    diff_avail = lag_available(diff)
    eq_avail = lag_available(r_eq)
    bond_avail = lag_available(bond_strength)

    z_diff = build_z(diff_avail)
    z_eq = build_z(eq_avail)
    z_bond = build_z(bond_avail)

    if not mt5.initialize():
        raise SystemExit(f"mt5_init_failed:{mt5.last_error()}")
    try:
        info = mt5.account_info()
        server = getattr(info, "server", None) if info else None

        d1 = {s: fetch_d1(s) for s in SYMBOLS}
        atrs = {s: wilder_atr(d1[s]) for s in SYMBOLS}
        idx_by_date: dict[str, dict[date, int]] = {
            s: {row["date"]: i for i, row in enumerate(rows)} for s, rows in d1.items()
        }

        def make_dir_fn(zmap: dict[date, float]):
            def _fn(d: date) -> int | None:
                z = zmap[d] if d in zmap else asof_strict(zmap, d, MAX_GAP_DAYS)
                return z_to_usd_dir(z)

            return _fn

        cand = simulate_basket(d1, atrs, idx_by_date, make_dir_fn(z_diff), "candidate")
        eq_ctrl = simulate_basket(d1, atrs, idx_by_date, make_dir_fn(z_eq), "equity_only_control")
        bond_ctrl = simulate_basket(d1, atrs, idx_by_date, make_dir_fn(z_bond), "bond_only_control")

        train_c = metrics(cand, TRAIN_START, TRAIN_END_EXCL)
        train_eq = metrics(eq_ctrl, TRAIN_START, TRAIN_END_EXCL)
        train_bond = metrics(bond_ctrl, TRAIN_START, TRAIN_END_EXCL)
        train_conc = year_concentration(cand, TRAIN_START, TRAIN_END_EXCL)

        reasons: list[str] = []
        train_pass = True
        if (train_c["trades"] or 0) < TRAIN_MIN_TRADES:
            train_pass = False
            reasons.append("train_trades<80")
        if (train_c["trades_per_week"] or 0) < TRAIN_MIN_TPW:
            train_pass = False
            reasons.append("train_tpw<0.5")
        pf_a = train_c["pf_stress_a"]
        if pf_a is None or pf_a < TRAIN_MIN_PF_A:
            train_pass = False
            reasons.append("train_pf_stress_a<1.10")
        eq_pf = train_eq["pf_stress_a"]
        eq_exp = train_eq["expectancy_a_pips"]
        c_exp = train_c["expectancy_a_pips"]
        beat_pf = pf_a is not None and eq_pf is not None and pf_a > eq_pf
        beat_exp = c_exp is not None and eq_exp is not None and c_exp > eq_exp
        if not (beat_pf and beat_exp):
            train_pass = False
            reasons.append("train_did_not_beat_equity_only_pf_and_exp")
        if train_conc is not None and train_conc > 0.55:
            train_pass = False
            reasons.append("train_year_concentration>0.55")

        hold_c = hold_eq = None
        hold_pass = None
        hold_reasons: list[str] = []
        hold_conc = None
        if train_pass:
            hold_c = metrics(cand, HOLDOUT_START, HOLDOUT_END_EXCL)
            hold_eq = metrics(eq_ctrl, HOLDOUT_START, HOLDOUT_END_EXCL)
            hold_conc = year_concentration(cand, HOLDOUT_START, HOLDOUT_END_EXCL)
            hold_pass = True
            if (hold_c["pf_stress_b"] or 0) < 1.00:
                hold_pass = False
                hold_reasons.append("holdout_pf_stress_b<1.00")
            if (hold_c["expectancy_a_pips"] or 0) <= 0:
                hold_pass = False
                hold_reasons.append("holdout_exp_a<=0")
            tpw = hold_c["trades_per_week"] or 0
            if tpw < 0.5 or tpw > 8.0:
                hold_pass = False
                hold_reasons.append("holdout_tpw_outside_[0.5,8]")
            if hold_conc is not None and hold_conc > 0.55:
                hold_pass = False
                hold_reasons.append("holdout_year_concentration>0.55")

        status = "PASS_TRAIN" if train_pass else "KILL_AT_OFFLINE_PROBE"
        if train_pass and hold_pass is False:
            status = "KILL_AT_HOLDOUT"
        elif train_pass and hold_pass is True:
            status = "PASS_HOLDOUT_GATES"

        authority = {
            "registry_append_authorized": bool(train_pass and hold_pass),
            "prereg_freeze_authorized": bool(train_pass and hold_pass),
            "ea_build_authorized": False,
            "compile_authorized": False,
            "backtest_authorized": False,
            "model_0_authorized": False,
        }

        result = {
            "schema": "v8_equity_bond_diff_offline_probe.v1",
            "probe_id": PROBE_ID,
            "working_hypothesis_id": "HYP-SR-FX-EQUITY-BOND-DIFF-001",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "mt5_server_observed": server,
            "falsification_note": "MetaQuotes-Demo falsification only; not FivePercentOnline-Real cost provenance",
            "contract_path": (
                "03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/"
                "20260713_V8_EQUITY_BOND_DIFF_JOIN_CONTRACT_V1.md"
            ),
            "inputs": {
                "files": file_meta,
                "mod_dur": MOD_DUR,
                "z_thresh": Z_THRESH,
                "z_lookback": Z_LOOKBACK,
                "diff_obs_count": len(diff),
                "spx_obs_count": len(spx),
                "dgs10_obs_count": len(dgs),
            },
            "train": {
                "window": [TRAIN_START.isoformat(), TRAIN_END_EXCL.isoformat()],
                "candidate": train_c,
                "equity_only_control": train_eq,
                "bond_only_control": train_bond,
                "year_concentration_pos_net_a": train_conc,
                "pass": train_pass,
                "kill_reasons": reasons,
            },
            "holdout": {
                "window": [HOLDOUT_START.isoformat(), HOLDOUT_END_EXCL.isoformat()],
                "candidate": hold_c,
                "equity_only_control": hold_eq,
                "year_concentration_pos_net_a": hold_conc,
                "pass": hold_pass,
                "kill_reasons": hold_reasons,
                "gated_shut": not train_pass,
            },
            "authority_flags": authority,
            "non_rescue": [
                "Do not retune z_thresh, MOD_DUR, ATR, or add VIX/ECB from this readout",
                "Do not reopen killed carry/COT books",
                "US bill-slope→USD-basket remains intake-blocked pending separate de-dup",
            ],
        }

        trades_path = OUT_DIR / TRADES_NAME
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "family",
                    "symbol",
                    "direction",
                    "entry_time",
                    "exit_time",
                    "gross_pips",
                    "net_a_pips",
                    "net_b_pips",
                    "exit_reason",
                    "leg_gross_json",
                ],
            )
            w.writeheader()
            for t in cand + eq_ctrl + bond_ctrl:
                w.writerow(asdict(t))

        result["trades_csv"] = str(trades_path.relative_to(WORKSPACE)).replace("\\", "/")
        result["trades_csv_sha256"] = sha256_file(trades_path)

        out = OUT_DIR / RESULT_NAME
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        result["result_sha256"] = sha256_file(out)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

        print(json.dumps(result, indent=2))
        return 0 if train_pass else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
