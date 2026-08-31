#!/usr/bin/env python3
"""V8 offline probe: lagged US Treasury bill slope -> USD basket.

Frozen contract:
  03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_CONTRACT_V1.md

Authority: Owner self-research / no-GPT (2026-07-13). Discovery-only.
MetaQuotes-Demo falsification. Not Strategy Tester / Model 0.

Independent of HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001 (no FX-return factor /
pullback-break) and of killed V8 carry / COT / carryxvol books.
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
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CONTRACT = (
    "03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/"
    "20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_CONTRACT_V1.md"
)

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
MOM_LOOKBACK = 20
MAX_GAP_DAYS = 3
RESULT_NAME = "20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_RESULT_V1.json"
TRADES_NAME = "20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_TRADES_V1.csv"
PROBE_ID = "V8_USBILL_SLOPE_USD_BASKET_V1"

TRAIN_MIN_TRADES = 80
TRAIN_MIN_TPW = 0.5
TRAIN_MIN_PF_A = 1.05


@dataclass
class Trade:
    symbol: str  # BASKET for equal-weight USD basket
    direction: int  # +1 USD strength / -1 USD weakness
    entry_time: str
    exit_time: str
    gross_pips: float
    net_a_pips: float
    net_b_pips: float
    family: str
    exit_reason: str
    leg_gross_json: str = ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date:
    s = s.strip()
    # Treasury archives: MM/DD/YYYY
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 3:
            m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
            return date(y, m, d)
    s2 = s.replace(".", "-")
    return date.fromisoformat(s2[:10])


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_bill_slope() -> tuple[dict[date, float], str, list[dict]]:
    """Return slope series keyed by observation date, tenor label, file hashes."""
    long_keys = (
        "26 WEEKS COUPON EQUIVALENT",
        "26 WEEKS BANK DISCOUNT",
    )
    short_keys = (
        "4 WEEKS COUPON EQUIVALENT",
        "4 WEEKS BANK DISCOUNT",
    )
    fallback_long = (
        "13 WEEKS COUPON EQUIVALENT",
        "13 WEEKS BANK DISCOUNT",
    )

    slopes: dict[date, float] = {}
    used_fallback = 0
    used_primary = 0
    file_meta: list[dict] = []

    for year in range(2018, 2027):
        path = RAW / f"us_treasury_bill_rates_{year}.csv"
        if not path.is_file():
            continue
        file_meta.append(
            {
                "path": str(path.relative_to(WORKSPACE)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
        with path.open(encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                raw_d = row.get("Date") or row.get("date")
                if not raw_d:
                    continue
                try:
                    d = parse_ymd(raw_d)
                except Exception:
                    continue

                def first_float(keys: tuple[str, ...]) -> float | None:
                    for k in keys:
                        if k in row and row[k] not in (None, "", "N/A", "NA"):
                            try:
                                v = float(row[k])
                            except ValueError:
                                continue
                            if math.isfinite(v):
                                return v
                    return None

                short_v = first_float(short_keys)
                long_v = first_float(long_keys)
                tenor = "26W-4W"
                if long_v is None:
                    long_v = first_float(fallback_long)
                    tenor = "13W-4W"
                    if long_v is not None and short_v is not None:
                        used_fallback += 1
                elif short_v is not None:
                    used_primary += 1
                if short_v is None or long_v is None:
                    continue
                slopes[d] = long_v - short_v
                # stash last tenor used as attribute via side channel below
                slopes_meta_tenor = tenor  # noqa: F841 — overwritten; see return

    if not slopes:
        return {}, "MISSING", file_meta

    # Prefer primary tenor label if majority used 26W-4W
    label = "26W-4W" if used_primary >= used_fallback else "13W-4W_FALLBACK_DOMINANT"
    if used_primary == 0 and used_fallback > 0:
        label = "13W-4W_ONLY"
    return slopes, label, file_meta


def lag_available(series: dict[date, float]) -> dict[date, float]:
    """available_at = observation_date + 1 calendar day."""
    return {d + timedelta(days=1): v for d, v in series.items()}


def asof_strict(series: dict[date, float], d: date, max_gap: int = MAX_GAP_DAYS) -> float | None:
    """Most recent available observation with lag already applied; fail if gap > max_gap."""
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


def build_z(slope_avail: dict[date, float]) -> dict[date, float]:
    """z_t using mean/stdev of prior 60 available slope obs (exclude t); need >=40."""
    dates = sorted(slope_avail)
    zmap: dict[date, float] = {}
    for i, d in enumerate(dates):
        window = []
        j = i - 1
        while j >= 0 and len(window) < Z_LOOKBACK:
            window.append(slope_avail[dates[j]])
            j -= 1
        if len(window) < Z_MIN_OBS:
            continue
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / len(window)
        if var <= 0:
            continue
        zmap[d] = (slope_avail[d] - mean) / math.sqrt(var)
    return zmap


def usd_proxy_ret(d1: dict[str, list[dict]], idx_by_date: dict[str, dict[date, int]], d: date) -> float | None:
    """(-ret_EUR - ret_GBP + ret_JPY) / 3 over MOM_LOOKBACK closed D1 bars ending at d."""
    rets = []
    for sym, sign in (("EURUSD", -1.0), ("GBPUSD", -1.0), ("USDJPY", 1.0)):
        m = idx_by_date[sym]
        if d not in m:
            return None
        i = m[d]
        if i < MOM_LOOKBACK:
            return None
        c0 = d1[sym][i - MOM_LOOKBACK]["close"]
        c1 = d1[sym][i]["close"]
        if c0 <= 0:
            return None
        rets.append(sign * ((c1 / c0) - 1.0))
    return sum(rets) / 3.0


def metrics(trades: list[Trade], start: date, end_excl: date) -> dict:
    subset = [
        t
        for t in trades
        if start <= parse_ymd(t.entry_time[:10]) < end_excl
    ]
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
    """Equal-weight USD basket on completed D1 Mon-Thu; Friday flatten.

    direction_fn(d) -> +1 USD strength / -1 USD weakness / 0 flat / None skip.
    Legs: D=+1 short EURUSD, short GBPUSD, long USDJPY; D=-1 opposite.
    """
    # Common trading dates (intersection).
    common = None
    for sym in SYMBOLS:
        s = set(idx_by_date[sym].keys())
        common = s if common is None else (common & s)
    dates = sorted(d for d in (common or set()) if d.weekday() < 5)

    trades: list[Trade] = []
    pos_dir = 0
    entry_time: datetime | None = None
    entry_idx: dict[str, int] = {}
    entry_px: dict[str, float] = {}
    stop_px: dict[str, float] = {}
    bars_held = 0
    leg_dirs: dict[str, int] = {}

    def leg_direction(usd_dir: int) -> dict[str, int]:
        # USD strength (+1): short EURUSD, short GBPUSD, long USDJPY
        if usd_dir > 0:
            return {"EURUSD": -1, "GBPUSD": -1, "USDJPY": 1}
        return {"EURUSD": 1, "GBPUSD": 1, "USDJPY": -1}

    def close_basket(d: date, reason: str, exit_px: dict[str, float] | None = None) -> None:
        nonlocal pos_dir, entry_time, entry_idx, entry_px, stop_px, bars_held, leg_dirs
        if pos_dir == 0 or entry_time is None:
            return
        leg_gross: dict[str, float] = {}
        for sym in SYMBOLS:
            px = (exit_px or {})[sym] if exit_px and sym in (exit_px or {}) else d1[sym][idx_by_date[sym][d]]["close"]
            ps = pip_size(sym)
            leg_gross[sym] = leg_dirs[sym] * (px - entry_px[sym]) / ps
        mean_gross = sum(leg_gross.values()) / 3.0
        # Stress applied per leg then mean-aggregated (contract).
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
        entry_idx = {}
        entry_px = {}
        stop_px = {}
        bars_held = 0
        leg_dirs = {}

    for d in dates:
        weekday = d.weekday()
        idxs = {s: idx_by_date[s][d] for s in SYMBOLS}

        # Manage open basket: stop / time-stop on this bar's extremes.
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
                # Any-leg stop closes full basket at stop for hit legs / close for others.
                close_basket(d, "stop", stop_exit_px)
            elif bars_held >= TIME_STOP_BARS:
                close_basket(d, "time_stop")

        # Friday flatten.
        if weekday == 4:
            if pos_dir != 0:
                close_basket(d, "friday_flat")
            continue

        # Mon-Thu decision on completed bar.
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

        # Open new basket at close.
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
            entry_idx[sym] = idxs[sym]
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


def main() -> int:
    slopes, tenor_label, file_meta = load_bill_slope()
    if not slopes:
        result = {
            "schema": "v8_usbill_slope_usd_basket_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "DATA_MISSING",
            "kill_reasons": ["us_treasury_bill_rates_csv_missing_or_empty"],
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
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 3

    if not mt5.initialize():
        raise SystemExit(f"mt5_init_failed:{mt5.last_error()}")
    try:
        info = mt5.account_info()
        server = getattr(info, "server", None) if info else None

        slope_avail = lag_available(slopes)
        zmap = build_z(slope_avail)

        d1 = {s: fetch_d1(s) for s in SYMBOLS}
        atrs = {s: wilder_atr(d1[s]) for s in SYMBOLS}
        idx_by_date: dict[str, dict[date, int]] = {
            s: {row["date"]: i for i, row in enumerate(rows)} for s, rows in d1.items()
        }

        def candidate_dir(d: date) -> int | None:
            # Use z available on decision date (lag already in slope_avail keys).
            # asof_strict on zmap dates: z is keyed by available_at date.
            if d not in zmap:
                # allow small calendar gap on z availability
                z = asof_strict(zmap, d, MAX_GAP_DAYS)
            else:
                z = zmap[d]
            if z is None:
                return None
            if z >= Z_THRESH:
                return 1
            if z <= -Z_THRESH:
                return -1
            return 0

        def control_dir(d: date) -> int | None:
            # Same |z| machinery for cadence parity: only trade when |z|>=thresh,
            # but direction from spot USD proxy momentum (bills unused for sign).
            if d not in zmap:
                z = asof_strict(zmap, d, MAX_GAP_DAYS)
            else:
                z = zmap[d]
            if z is None:
                return None
            if abs(z) < Z_THRESH:
                return 0
            proxy = usd_proxy_ret(d1, idx_by_date, d)
            if proxy is None:
                return None
            if proxy > 0:
                return 1
            if proxy < 0:
                return -1
            return 0

        cand = simulate_basket(d1, atrs, idx_by_date, candidate_dir, "candidate")
        ctrl = simulate_basket(d1, atrs, idx_by_date, control_dir, "control")

        train_c = metrics(cand, TRAIN_START, TRAIN_END_EXCL)
        train_k = metrics(ctrl, TRAIN_START, TRAIN_END_EXCL)
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
            reasons.append("train_pf_stress_a<1.05")
        kpf = train_k["pf_stress_a"]
        kexp = train_k["expectancy_a_pips"]
        cexp = train_c["expectancy_a_pips"]
        # Contract: fail beat control PF-A AND expectancy-A
        beat_pf = pf_a is not None and kpf is not None and pf_a > kpf
        beat_exp = cexp is not None and kexp is not None and cexp > kexp
        if not (beat_pf and beat_exp):
            train_pass = False
            reasons.append("train_did_not_beat_control_pf_and_exp")
        if train_conc is not None and train_conc > 0.55:
            train_pass = False
            reasons.append("train_year_concentration>0.55")

        hold_c = hold_k = None
        hold_pass = None
        hold_reasons: list[str] = []
        hold_conc = None
        if train_pass:
            hold_c = metrics(cand, HOLDOUT_START, HOLDOUT_END_EXCL)
            hold_k = metrics(ctrl, HOLDOUT_START, HOLDOUT_END_EXCL)
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
            hpf = hold_c["pf_stress_a"]
            hkpf = hold_k["pf_stress_a"]
            hexp = hold_c["expectancy_a_pips"]
            hkexp = hold_k["expectancy_a_pips"]
            if not (
                hpf is not None
                and hkpf is not None
                and hpf > hkpf
                and hexp is not None
                and hkexp is not None
                and hexp > hkexp
            ):
                hold_pass = False
                hold_reasons.append("holdout_did_not_beat_control_pf_and_exp")
            if hold_conc is not None and hold_conc > 0.55:
                hold_pass = False
                hold_reasons.append("holdout_year_concentration>0.55")

        status = "PROBE_SURVIVOR" if (train_pass and hold_pass) else "KILL_AT_OFFLINE_PROBE"

        trades_path = OUT_DIR / TRADES_NAME
        fields = list(asdict(cand[0]).keys()) if cand else [
            "symbol",
            "direction",
            "entry_time",
            "exit_time",
            "gross_pips",
            "net_a_pips",
            "net_b_pips",
            "family",
            "exit_reason",
            "leg_gross_json",
        ]
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        # Cost provenance: synthetic pip stress only — not broker-true cost.
        cost_note = (
            "COST_PROVENANCE_GAP: stress A/B are synthetic pip round-trip haircuts "
            "(1.5/3.0 per leg, mean-aggregated). Not FivePercentOnline-Real bid/ask/"
            "commission/slippage. Missing broker cost fields must not be treated as zero."
        )

        result = {
            "schema": "v8_usbill_slope_usd_basket_offline_probe.v1",
            "probe_id": PROBE_ID,
            "working_hypothesis_id": "HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "mt5_server": server,
            "note": (
                "MetaQuotes-Demo falsification only. Not Strategy Tester. "
                "Not EA/Model0 authority unless PROBE_SURVIVOR + separate prereg/cost."
            ),
            "cost_provenance": cost_note,
            "contract_path": CONTRACT,
            "dedup": {
                "vs_HYP_SR_FX_CROSS_SECTIONAL_USD_FACTOR_001": (
                    "independent: lagged US bill slope only; no FX-return factor, "
                    "no pullback-break, no strongest-pair routing"
                ),
                "vs_V8_carry_cot_carryvol": "independent causal surface (US bill curve shape)",
            },
            "design_frozen": {
                "symbols": list(SYMBOLS),
                "timeframe": "D1",
                "signal": f"z({tenor_label}) threshold {Z_THRESH}",
                "lag": "observation_date+1_calendar_day",
                "rebalance": "MonThu_D1_close_Friday_flat",
                "basket": "equal_weight_EURUSD_GBPUSD_USDJPY_USD_direction",
                "stop": f"{SL_ATR}*ATR{ATR_PERIOD}_D1",
                "time_stop_bars": TIME_STOP_BARS,
                "stress_a_pips_per_leg": STRESS_A,
                "stress_b_pips_per_leg": STRESS_B,
                "aggregation": "mean_of_legs",
                "train": [TRAIN_START.isoformat(), TRAIN_END_EXCL.isoformat()],
                "holdout": [HOLDOUT_START.isoformat(), HOLDOUT_END_EXCL.isoformat()],
                "control": "same_|z|_gate_sign_of_20d_USD_spot_proxy",
            },
            "data_coverage": {
                "bill_obs_dates": len(slopes),
                "slope_available_dates": len(slope_avail),
                "z_dates": len(zmap),
                "tenor_label": tenor_label,
                "bill_files": file_meta,
                "d1_bars": {s: len(d1[s]) for s in SYMBOLS},
            },
            "train_candidate": train_c,
            "train_control": train_k,
            "train_year_concentration_pos_net_a": train_conc,
            "holdout_candidate": hold_c,
            "holdout_control": hold_k,
            "holdout_year_concentration_pos_net_a": hold_conc,
            "train_pass": train_pass,
            "holdout_pass": hold_pass,
            "kill_reasons": reasons + hold_reasons,
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
        print(
            json.dumps(
                {
                    "status": status,
                    "train": train_c,
                    "control": train_k,
                    "kill_reasons": result["kill_reasons"],
                    "out": str(out),
                },
                indent=2,
            )
        )
        return 0 if status == "PROBE_SURVIVOR" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
