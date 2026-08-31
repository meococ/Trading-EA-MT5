#!/usr/bin/env python3
"""V8 Carry × global FX vol innovation offline probe (Menkhoff-style).

Authority: Owner skip-GPT self-research + 1A fail-closed (2026-07-13).
Contract: research/preflight/v8_exogenous/20260713_V8_CARRY_VOL_JOIN_CONTRACT_V1.md
Discovery-only. Not Strategy Tester. Not promotion.
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
EXO = RESEARCH / "data" / "exogenous"
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROBE_ID = "CARRY_VOL_REGIME_V1"
RESULT_NAME = "20260713_V8_CARRY_VOL_PROBE_RESULT_V1.json"
TRADES_NAME = "20260713_V8_CARRY_VOL_PROBE_TRADES_V1.csv"

SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY")
TRAIN_START = date(2021, 1, 1)
TRAIN_END = date(2023, 12, 31)  # [2021-01-01, 2024-01-01)
HOLD_START = date(2024, 1, 1)
HOLD_END = date(2025, 12, 31)
STRESS_A = 1.5
STRESS_B = 2.5
CARRY_DEADBAND = 0.25
ATR_PERIOD = 14
ATR_STOP = 1.5
TIME_STOP_BARS = 6
VOL_MIN_DAYS = 60
LOOKBACK_MOM = 20

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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date:
    s = s.strip().replace("/", "-")
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        for fmt in ("%d %b %Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    raise ValueError(s)


def load_fred_series(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        cols = r.fieldnames or []
        for row in r:
            try:
                d = parse_ymd(row[cols[0]])
                v = float(row[cols[1]])
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def load_treasury_13w() -> dict[date, float]:
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
                    "4 WEEKS COUPON EQUIVALENT",
                ):
                    if key in row and row[key] not in (None, ""):
                        try:
                            val = float(row[key])
                            break
                        except ValueError:
                            pass
                if val is not None and math.isfinite(val):
                    out[d] = val
    return out


def load_ecb_dfr() -> dict[date, float]:
    path = RAW / "ecb_dfr_daily.csv"
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                d = parse_ymd(row["TIME_PERIOD"])
                v = float(row["OBS_VALUE"])
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def load_boe() -> dict[date, float]:
    path = RAW / "boe_bank_rate.csv"
    out: dict[date, float] = {}
    if not path.is_file():
        return load_fred_series(EXO / "gbp_sonia_IUDSOIA.csv")
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            vals = list(row.values())
            try:
                d = parse_ymd(row.get("DATE") or row.get("Date") or vals[0])
            except Exception:
                continue
            v = None
            for raw in vals[1:]:
                try:
                    v = float(raw)
                    break
                except (TypeError, ValueError):
                    continue
            if v is not None and math.isfinite(v):
                out[d] = v
    return out


def load_jpy() -> dict[date, float]:
    path = RAW / "jpy_boj_uncollateralized_overnight_call_daily.csv"
    out: dict[date, float] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            raw = row.get("BOJ_CALL_ON") or row.get("value") or row.get("OBS_VALUE")
            draw = row.get("observation_date") or row.get("date") or row.get("DATE")
            if raw in (None, "", "NA", "n.a.", "ND"):
                continue
            try:
                d = parse_ymd(draw)
                v = float(raw)
            except Exception:
                continue
            if math.isfinite(v):
                out[d] = v
    return out


def lag_series(series: dict[date, float], lag_days: int = 1) -> dict[date, float]:
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


def fetch_h4(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_H4,
        datetime(2020, 1, 1),
        datetime(2026, 7, 1),
    )
    if rates is None:
        raise RuntimeError(f"no H4 for {symbol}: {mt5.last_error()}")
    rows = []
    for r in rates:
        ts = datetime.utcfromtimestamp(int(r["time"]))
        rows.append(
            {
                "time": ts,
                "date": ts.date(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            }
        )
    return rows


def fetch_d1(symbol: str) -> list[dict]:
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_D1,
        datetime(2020, 1, 1),
        datetime(2026, 7, 1),
    )
    if rates is None:
        raise RuntimeError(f"no D1 for {symbol}: {mt5.last_error()}")
    rows = []
    for r in rates:
        d = datetime.utcfromtimestamp(int(r["time"])).date()
        rows.append({"date": d, "close": float(r["close"])})
    return rows


def build_vol_innovation(d1_by_sym: dict[str, list[dict]]) -> dict[date, float]:
    """sigma_t = mean abs daily log returns across 3 pairs; AR(1) residual."""
    closes: dict[str, dict[date, float]] = {}
    all_dates: set[date] = set()
    for s, rows in d1_by_sym.items():
        closes[s] = {r["date"]: r["close"] for r in rows}
        all_dates |= set(closes[s])
    dates = sorted(all_dates)
    sigma: dict[date, float] = {}
    for i, d in enumerate(dates):
        if i == 0:
            continue
        abs_rets = []
        prev = dates[i - 1]
        for s in SYMBOLS:
            c0 = closes[s].get(prev)
            c1 = closes[s].get(d)
            if c0 and c1 and c0 > 0:
                abs_rets.append(abs(math.log(c1 / c0)))
        if len(abs_rets) == 3:
            sigma[d] = sum(abs_rets) / 3.0

    # expanding AR(1): residual = sigma_t - beta*sigma_{t-1}
    sig_dates = sorted(sigma)
    innov: dict[date, float] = {}
    xs: list[float] = []
    ys: list[float] = []
    for i in range(1, len(sig_dates)):
        d0, d1 = sig_dates[i - 1], sig_dates[i]
        x, y = sigma[d0], sigma[d1]
        xs.append(x)
        ys.append(y)
        if len(xs) < VOL_MIN_DAYS:
            continue
        # OLS through origin-ish with intercept: beta = cov/var
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        varx = sum((a - mx) ** 2 for a in xs)
        if varx <= 0:
            continue
        beta = sum((xs[j] - mx) * (ys[j] - my) for j in range(n)) / varx
        alpha = my - beta * mx
        innov[d1] = y - (alpha + beta * x)
    return innov


def atr_h4(bars: list[dict], idx: int) -> float | None:
    if idx < ATR_PERIOD:
        return None
    trs = []
    for i in range(idx - ATR_PERIOD + 1, idx + 1):
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / ATR_PERIOD


def summarize(trades: list[Trade], weeks: float) -> dict:
    if not trades:
        return {
            "trades": 0,
            "trades_per_week": 0.0,
            "expectancy_gross_pips": 0.0,
            "expectancy_a_pips": 0.0,
            "pf_gross": 0.0,
            "pf_stress_a": 0.0,
            "pf_stress_b": 0.0,
        }

    def pf(xs: list[float]) -> float:
        wins = sum(x for x in xs if x > 0)
        losses = -sum(x for x in xs if x < 0)
        if losses <= 0:
            return 999.0 if wins > 0 else 0.0
        return wins / losses

    gp = [t.gross_pips for t in trades]
    na = [t.net_a_pips for t in trades]
    nb = [t.net_b_pips for t in trades]
    return {
        "trades": len(trades),
        "trades_per_week": len(trades) / max(weeks, 1e-9),
        "expectancy_gross_pips": sum(gp) / len(gp),
        "expectancy_a_pips": sum(na) / len(na),
        "pf_gross": pf(gp),
        "pf_stress_a": pf(na),
        "pf_stress_b": pf(nb),
    }


def simulate(
    symbol: str,
    bars: list[dict],
    lagged_usd: dict[date, float],
    lagged_eur: dict[date, float],
    lagged_gbp: dict[date, float],
    lagged_jpy: dict[date, float],
    innov: dict[date, float],
    family: str,
) -> list[Trade]:
    trades: list[Trade] = []
    ps = pip_size(symbol)
    i = LOOKBACK_MOM + ATR_PERIOD + 1
    while i < len(bars) - 1:
        bar = bars[i]
        d = bar["date"]
        # Mon-Thu only; Friday flatten handled via no new entries Fri + exit
        if bar["time"].weekday() >= 4:  # Fri=4, Sat=5, Sun=6
            i += 1
            continue
        # Vol gate: need innovation <= 0 for candidate; control ignores vol
        if family == "candidate":
            # use last available innovation as of decision date
            innov_val = None
            for ad in sorted(innov):
                if ad <= d:
                    innov_val = innov[ad]
                else:
                    break
            if innov_val is None or innov_val > 0:
                i += 1
                continue

        if family == "candidate":
            usd = asof(lagged_usd, d)
            eur = asof(lagged_eur, d)
            gbp = asof(lagged_gbp, d)
            jpy = asof(lagged_jpy, d)
            if None in (usd, eur, gbp, jpy):
                i += 1
                continue
            carry = pair_carry(symbol, usd, eur, gbp, jpy)  # type: ignore[arg-type]
            if carry > CARRY_DEADBAND:
                direction = 1
            elif carry < -CARRY_DEADBAND:
                direction = -1
            else:
                i += 1
                continue
        else:
            # momentum sign of prior 20 H4 returns
            c0 = bars[i - LOOKBACK_MOM]["close"]
            c1 = bars[i]["close"]
            if c0 <= 0:
                i += 1
                continue
            mom = math.log(c1 / c0)
            if mom == 0:
                i += 1
                continue
            direction = 1 if mom > 0 else -1

        atr = atr_h4(bars, i)
        if atr is None or atr <= 0:
            i += 1
            continue
        entry_px = bar["close"]
        stop_px = entry_px - direction * ATR_STOP * atr
        exit_i = None
        exit_px = None
        for j in range(i + 1, min(i + 1 + TIME_STOP_BARS, len(bars))):
            b = bars[j]
            if direction > 0 and b["low"] <= stop_px:
                exit_i, exit_px = j, stop_px
                break
            if direction < 0 and b["high"] >= stop_px:
                exit_i, exit_px = j, stop_px
                break
            if b["time"].weekday() == 4:  # Friday flatten
                exit_i, exit_px = j, b["close"]
                break
        if exit_i is None:
            j = min(i + TIME_STOP_BARS, len(bars) - 1)
            if j <= i:
                i += 1
                continue
            exit_i, exit_px = j, bars[j]["close"]

        gross = direction * (exit_px - entry_px) / ps
        trades.append(
            Trade(
                symbol=symbol,
                direction=direction,
                entry_time=bar["time"].isoformat(),
                exit_time=bars[exit_i]["time"].isoformat(),
                gross_pips=gross,
                net_a_pips=gross - STRESS_A,
                net_b_pips=gross - STRESS_B,
                family=family,
            )
        )
        # no overlapping: jump to exit
        i = exit_i + 1
    return trades


def in_train(t: Trade) -> bool:
    d = date.fromisoformat(t.entry_time[:10])
    return TRAIN_START <= d <= TRAIN_END


def in_hold(t: Trade) -> bool:
    d = date.fromisoformat(t.entry_time[:10])
    return HOLD_START <= d <= HOLD_END


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(f"mt5 init failed: {mt5.last_error()}")
    try:
        info = mt5.account_info()
        server = info.server if info else "UNKNOWN"
        usd = lag_series(load_treasury_13w(), 1)
        eur = lag_series(load_ecb_dfr(), 1)
        gbp = lag_series(load_boe(), 1)
        jpy = lag_series(load_jpy(), 2)
        d1 = {s: fetch_d1(s) for s in SYMBOLS}
        innov = build_vol_innovation(d1)
        h4 = {s: fetch_h4(s) for s in SYMBOLS}

        cand: list[Trade] = []
        ctrl: list[Trade] = []
        for s in SYMBOLS:
            cand.extend(simulate(s, h4[s], usd, eur, gbp, jpy, innov, "candidate"))
            ctrl.extend(simulate(s, h4[s], usd, eur, gbp, jpy, innov, "control"))

        train_weeks = (TRAIN_END - TRAIN_START).days / 7.0
        hold_weeks = (HOLD_END - HOLD_START).days / 7.0
        tc = [t for t in cand if in_train(t)]
        tk = [t for t in ctrl if in_train(t)]
        sc = summarize(tc, train_weeks)
        sk = summarize(tk, train_weeks)

        kills: list[str] = []
        if sc["trades"] < TRAIN_MIN_TRADES:
            kills.append("train_trades<80")
        if sc["trades_per_week"] < TRAIN_MIN_TPW:
            kills.append("train_cadence_below_structural_floor")
        if sc["pf_stress_a"] < TRAIN_MIN_PF_A:
            kills.append("train_pf_stress_a<1.10")
        if not (
            sc["pf_stress_a"] > sk["pf_stress_a"]
            and sc["expectancy_a_pips"] > sk["expectancy_a_pips"]
        ):
            kills.append("fail_beat_control_pf_and_expectancy")

        train_pass = len(kills) == 0
        hold_c = hold_k = None
        if train_pass:
            hc = [t for t in cand if in_hold(t)]
            hk = [t for t in ctrl if in_hold(t)]
            hold_c = summarize(hc, hold_weeks)
            hold_k = summarize(hk, hold_weeks)
            # holdout gates from contract
            if hold_c["pf_stress_b"] < 1.00:
                kills.append("holdout_pf_stress_b<1.00")
            if hold_c["expectancy_a_pips"] <= 0:
                kills.append("holdout_expectancy_a<=0")
            if not (0.5 <= hold_c["trades_per_week"] <= 8.0):
                kills.append("holdout_tpw_outside_[0.5,8]")
            if not (
                hold_c["pf_stress_a"] > hold_k["pf_stress_a"]
                and hold_c["expectancy_a_pips"] > hold_k["expectancy_a_pips"]
            ):
                kills.append("holdout_fail_beat_control")
            train_pass = len(kills) == 0

        trades_path = OUT_DIR / TRADES_NAME
        fields = [
            "symbol",
            "direction",
            "entry_time",
            "exit_time",
            "gross_pips",
            "net_a_pips",
            "net_b_pips",
            "family",
        ]
        with trades_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "v8_carry_vol_regime_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PROBE_SURVIVOR" if train_pass else "KILL_AT_OFFLINE_PROBE",
            "mt5_server": server,
            "note": (
                "MetaQuotes-Demo falsification only. Frozen "
                "20260713_V8_CARRY_VOL_JOIN_CONTRACT_V1.md. Not a post-hoc "
                "rescue of D1 carry weekly/daily/event kills — H4 + vol gate + "
                "time-stop is a distinct Menkhoff-style design."
            ),
            "design_frozen": {
                "symbols": list(SYMBOLS),
                "timeframe": "H4",
                "carry_deadband": CARRY_DEADBAND,
                "vol_gate": "AR1_innovation_nonpositive",
                "time_stop_bars": TIME_STOP_BARS,
                "stress_a_pips": STRESS_A,
                "stress_b_pips": STRESS_B,
                "train": [str(TRAIN_START), str(TRAIN_END)],
                "holdout": [str(HOLD_START), str(HOLD_END)],
                "control": "sign_prior_20_H4_log_return",
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
                "model_0_authorized": False,
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
