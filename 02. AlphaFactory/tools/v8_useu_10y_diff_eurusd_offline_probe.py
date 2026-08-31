#!/usr/bin/env python3
"""V8 offline probe: lagged US−EU 10Y bond yield differential → EURUSD.

Frozen contract:
  03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/
  20260713_V8_USEU_10Y_DIFF_EURUSD_PROBE_CONTRACT_V1.md

Authority: Owner data-state change after V8 fail-closed. Discovery-only.
Demo falsification. Not Strategy Tester / Model 0.
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
PANEL = RESEARCH / "preflight" / "v8_exogenous" / "panels" / "us_eu_bond_yield_diff_d1_v1.csv"
OUT_DIR = RESEARCH / "preflight" / "v8_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CONTRACT = (
    "03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/"
    "20260713_V8_USEU_10Y_DIFF_EURUSD_PROBE_CONTRACT_V1.md"
)

SYMBOL = "EURUSD"
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
RESULT_NAME = "20260713_V8_USEU_10Y_DIFF_EURUSD_PROBE_RESULT_V1.json"
TRADES_NAME = "20260713_V8_USEU_10Y_DIFF_EURUSD_PROBE_TRADES_V1.csv"
PROBE_ID = "V8_USEU_10Y_DIFF_EURUSD_V1"
READOUT_NAME = "20260713_V8_USEU_10Y_DIFF_EURUSD_OFFLINE_PROBE_READOUT.md"

TRAIN_MIN_TRADES = 80
TRAIN_MIN_TPW = 0.5
TRAIN_MIN_PF_A = 1.05
MAX_YEAR_CONC = 0.55


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
    return h.hexdigest().upper()


def parse_ymd(s: str) -> date:
    s = s.strip()
    if "/" in s:
        m, d, y = s.split("/")
        return date(int(y), int(m), int(d))
    return date.fromisoformat(s.replace(".", "-")[:10])


def load_diff_available() -> tuple[dict[date, float], dict]:
    """Return diff keyed by available_at date (already lagged in panel)."""
    avail: dict[date, float] = {}
    with PANEL.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            avail_s = (row.get("available_at_utc") or "").strip()
            diff_s = (row.get("diff_us_eu_10y") or "").strip()
            if not avail_s or not diff_s:
                continue
            ad = date.fromisoformat(avail_s[:10])
            avail[ad] = float(diff_s)
    meta = {
        "panel_path": str(PANEL.relative_to(WORKSPACE)).replace("\\", "/"),
        "panel_sha256": sha256_file(PANEL),
        "panel_bytes": PANEL.stat().st_size,
        "available_obs": len(avail),
    }
    return avail, meta


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
        window = []
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


def mom_ret(rows: list[dict], i: int) -> float | None:
    if i < MOM_LOOKBACK:
        return None
    c0 = rows[i - MOM_LOOKBACK]["close"]
    c1 = rows[i]["close"]
    if c0 <= 0:
        return None
    return (c1 / c0) - 1.0


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


def simulate(
    rows: list[dict],
    atrs: list[float | None],
    idx_by_date: dict[date, int],
    direction_fn,
    family: str,
) -> list[Trade]:
    dates = sorted(d for d in idx_by_date if d.weekday() < 5)
    trades: list[Trade] = []
    pos = 0
    entry_time: datetime | None = None
    entry_i = -1
    entry_px = 0.0
    stop_px = 0.0
    bars_held = 0
    pip = 0.0001

    def close_pos(d: date, reason: str, exit_px: float | None = None) -> None:
        nonlocal pos, entry_time, entry_i, entry_px, stop_px, bars_held
        if pos == 0 or entry_time is None:
            return
        px = exit_px if exit_px is not None else rows[idx_by_date[d]]["close"]
        gross = pos * (px - entry_px) / pip
        trades.append(
            Trade(
                symbol=SYMBOL,
                direction=pos,
                entry_time=entry_time.isoformat(),
                exit_time=rows[idx_by_date[d]]["time"].isoformat(),
                gross_pips=gross,
                net_a_pips=gross - STRESS_A,
                net_b_pips=gross - STRESS_B,
                family=family,
                exit_reason=reason,
            )
        )
        pos = 0
        entry_time = None
        entry_i = -1
        bars_held = 0

    for d in dates:
        i = idx_by_date[d]
        bar = rows[i]
        # Intrabar stop check while in position
        if pos != 0:
            bars_held += 1
            hit = False
            if pos > 0 and bar["low"] <= stop_px:
                close_pos(d, "stop", stop_px)
                hit = True
            elif pos < 0 and bar["high"] >= stop_px:
                close_pos(d, "stop", stop_px)
                hit = True
            if not hit and bars_held >= TIME_STOP_BARS:
                close_pos(d, "time_stop")
            elif not hit and d.weekday() == 4:
                close_pos(d, "friday_flat")

        if d.weekday() == 4:
            continue  # no new entries Friday

        desired = direction_fn(d)
        if desired is None:
            continue
        if desired == 0:
            if pos != 0:
                close_pos(d, "signal_flat")
            continue
        if desired == pos:
            continue
        if pos != 0:
            close_pos(d, "flip")
        atr = atrs[i]
        if atr is None or atr <= 0:
            continue
        pos = desired
        entry_time = bar["time"]
        entry_i = i
        entry_px = bar["close"]
        bars_held = 0
        stop_px = entry_px - pos * SL_ATR * atr

    # force flat at end
    if pos != 0 and dates:
        close_pos(dates[-1], "end")
    return trades


def evaluate(cand: list[Trade], ctrl: list[Trade]) -> dict:
    train_c = metrics(cand, TRAIN_START, TRAIN_END_EXCL)
    train_k = metrics(ctrl, TRAIN_START, TRAIN_END_EXCL)
    yc = year_concentration(cand, TRAIN_START, TRAIN_END_EXCL)
    kills = []
    if train_c["trades"] < TRAIN_MIN_TRADES:
        kills.append(f"train_trades<{TRAIN_MIN_TRADES}")
    if (train_c["trades_per_week"] or 0) < TRAIN_MIN_TPW:
        kills.append(f"train_tpw<{TRAIN_MIN_TPW}")
    pf_a = train_c["pf_stress_a"]
    if pf_a is None or pf_a < TRAIN_MIN_PF_A:
        kills.append(f"pf_stress_a<{TRAIN_MIN_PF_A}")
    ctrl_pf = train_k["pf_stress_a"]
    if pf_a is not None and ctrl_pf is not None and pf_a <= ctrl_pf:
        kills.append("fail_beat_control_pf_a")
    exp_a = train_c["expectancy_a_pips"]
    exp_k = train_k["expectancy_a_pips"]
    if exp_a is not None and exp_k is not None and exp_a <= exp_k:
        kills.append("fail_beat_control_expectancy_a")
    if yc is not None and yc > MAX_YEAR_CONC:
        kills.append(f"year_concentration>{MAX_YEAR_CONC}")

    train_pass = len(kills) == 0
    hold_c = metrics(cand, HOLDOUT_START, HOLDOUT_END_EXCL) if train_pass else None
    hold_k = metrics(ctrl, HOLDOUT_START, HOLDOUT_END_EXCL) if train_pass else None
    verdict = "SURVIVE_AT_OFFLINE_PROBE" if train_pass else "KILL_AT_OFFLINE_PROBE"
    return {
        "verdict": verdict,
        "kill_reasons": kills,
        "train_candidate": train_c,
        "train_control": train_k,
        "train_year_concentration_pos_net_a": yc,
        "holdout_candidate": hold_c,
        "holdout_control": hold_k,
        "holdout_gated": not train_pass,
    }


def write_readout(result: dict) -> Path:
    path = RESEARCH / "readouts" / READOUT_NAME
    tc = result["train_candidate"]
    tk = result["train_control"]
    lines = [
        f"# {PROBE_ID} Offline Probe Readout — 2026-07-13",
        "",
        f"Status: `{result['verdict']}`",
        "",
        "## Contract",
        "",
        f"- Probe: `{PROBE_ID}`",
        f"- Panel SHA256: `{result['panel']['panel_sha256']}`",
        f"- Contract: `{CONTRACT}`",
        "",
        "## Train (2019–2022)",
        "",
        f"| Metric | Candidate | Control |",
        f"|---|---:|---:|",
        f"| Trades | {tc['trades']} | {tk['trades']} |",
        f"| Trades/week | {tc['trades_per_week']:.3f} | {tk['trades_per_week']:.3f} |",
        f"| PF stress-A | {tc['pf_stress_a']} | {tk['pf_stress_a']} |",
        f"| Expectancy-A (pips) | {tc['expectancy_a_pips']} | {tk['expectancy_a_pips']} |",
        f"| Year conc. pos net-A | {result['train_year_concentration_pos_net_a']} | n/a |",
        "",
        "## Kill reasons",
        "",
    ]
    if result["kill_reasons"]:
        for k in result["kill_reasons"]:
            lines.append(f"- `{k}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Authority",
            "",
            "Offline falsification only. No registry / prereg / EA / Model 0 "
            "unless verdict is survive (it is not, if kill reasons non-empty).",
            "Do not retune z-threshold or tenors from this readout.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        avail, panel_meta = load_diff_available()
        zmap = build_z(avail)
        rows = fetch_d1(SYMBOL)
        atrs = wilder_atr(rows)
        idx = {r["date"]: i for i, r in enumerate(rows)}

        def cand_dir(d: date) -> int | None:
            # z keyed by available_at date; use asof on decision date
            # Rebuild: zmap keys are available_at dates from panel
            # Use latest z with available_at <= d and gap check on underlying diff
            if asof_strict(avail, d) is None:
                return None
            # find latest z date <= d
            best = None
            for zd in zmap:
                if zd <= d and (best is None or zd > best):
                    best = zd
            if best is None:
                return None
            if (d - best).days > MAX_GAP_DAYS:
                return None
            z = zmap[best]
            if z >= Z_THRESH:
                return -1  # short EURUSD
            if z <= -Z_THRESH:
                return 1
            return 0

        def ctrl_dir(d: date) -> int | None:
            # Same density gate as candidate: only trade when |bond z| would fire
            gate = cand_dir(d)
            if gate is None or gate == 0:
                return gate
            if d not in idx:
                return None
            r = mom_ret(rows, idx[d])
            if r is None or r == 0:
                return 0
            # Momentum-follow control (bond unused for direction).
            return 1 if r > 0 else -1

        cand = simulate(rows, atrs, idx, cand_dir, "candidate_bond_diff")
        ctrl = simulate(rows, atrs, idx, ctrl_dir, "control_mom_fade")
        ev = evaluate(cand, ctrl)

        # write trades
        trades_path = OUT_DIR / TRADES_NAME
        with trades_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=list(asdict(cand[0]).keys()) if cand else [
                    "symbol", "direction", "entry_time", "exit_time",
                    "gross_pips", "net_a_pips", "net_b_pips", "family", "exit_reason",
                ],
            )
            w.writeheader()
            for t in cand + ctrl:
                w.writerow(asdict(t))

        result = {
            "schema": "v8_useu_10y_diff_eurusd_offline_probe.v1",
            "probe_id": PROBE_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "contract": CONTRACT,
            "panel": panel_meta,
            "constants": {
                "z_thresh": Z_THRESH,
                "z_lookback": Z_LOOKBACK,
                "stress_a": STRESS_A,
                "stress_b": STRESS_B,
                "sl_atr": SL_ATR,
                "time_stop_bars": TIME_STOP_BARS,
                "max_gap_days": MAX_GAP_DAYS,
            },
            "mt5_account_info": {
                "server": mt5.account_info().server if mt5.account_info() else None,
                "note": "Demo falsification only; not QFSI Real cost provenance",
            },
            **ev,
            "trades_path": str(trades_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "trades_sha256": sha256_file(trades_path),
            "candidate_trade_count_all": len(cand),
            "control_trade_count_all": len(ctrl),
        }
        out = OUT_DIR / RESULT_NAME
        out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
        readout = write_readout(result)
        print(json.dumps({
            "verdict": result["verdict"],
            "kill_reasons": result["kill_reasons"],
            "train_trades": result["train_candidate"]["trades"],
            "train_tpw": result["train_candidate"]["trades_per_week"],
            "pf_a": result["train_candidate"]["pf_stress_a"],
            "result": str(out),
            "readout": str(readout),
        }, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
