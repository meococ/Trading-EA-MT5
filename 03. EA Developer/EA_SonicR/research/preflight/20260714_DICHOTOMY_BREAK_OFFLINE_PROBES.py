#!/usr/bin/env python3
"""Dichotomy-break offline probes — cost-resilience / exo gate / CorrCap book.

A priori (frozen; GPT waived; no densify / no Phase-0 ceremony):
  D1 HYP-RR2-EXIT-BE1R-M15PATH-001  — BE@1R exit path on frozen RR2 (not T1 cost-arm)
  D2 HYP-RR2-USJP-YIELD-ZGATE-001   — US-JP yield z allow-gate on RR2 (not bond signal)
  D3 HYP-BOOK-CORRCAP-RR2-SPARK-001 — max concurrent=1 RR2+Spark (not equal-join)

Model 0 withheld unless PROBE_SURVIVOR.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"
EXO = PRE / "v8_exogenous" / "panels" / "us_jp_bond_yield_diff_d1_v1.csv"

RR2_RUN = "20260714_194548"
SPARK_RUN = "20260714_193358"
RR2_DIR = RUNS / "EA_SilverBullet" / RR2_RUN
SPARK_DIR = RUNS / "EA_M15SparkAsian" / SPARK_RUN

OUT_JSON = PRE / "20260714_DICHOTOMY_BREAK_OFFLINE_PROBES.json"
OUT_MD = READ / "20260714_DICHOTOMY_BREAK_OFFLINE_PROBES.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0

# A priori frozen (do not mine)
BE_AT_R = 1.0
YIELD_Z_ABS = 0.75
YIELD_LOOKBACK = 60
YIELD_MIN_OBS = 40


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = BASE_COST) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    tpw = n / WEEKS if WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(m: dict, hc: dict, baseline_x15: float | None = None) -> tuple[str, list[str]]:
    notes = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.0 <= tpw <= 6.5):
        notes.append("cadence_fail")
    if pf < 1.05:
        notes.append("pf_fail")
    if x15 < 1.10:
        notes.append("stress_fail")
    if baseline_x15 is not None and x15 <= baseline_x15 + 1e-9:
        notes.append("no_stress_lift_vs_baseline")
    # survivor bar (probe)
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
        and (baseline_x15 is None or x15 > baseline_x15 + 0.01)
    ):
        return "PROBE_SURVIVOR", notes
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    return "KILLED_AT_OFFLINE_PROBE", ["joint_screen_miss"]


def find_trades_csv(run_dir: Path) -> Path:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    if not hits:
        raise FileNotFoundError(f"no trades csv under {run_dir}")
    return sorted(hits)[0]


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def load_closed_trades(path: Path) -> list[dict]:
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in ("1", "true", "True"):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                entry = float(op.get("entry_price") or op.get("price") or 0)
                sl = float(op.get("sl") or op.get("initial_sl") or 0)
                tp = float(op.get("tp") or op.get("initial_tp") or 0)
                vol = float(op.get("volume") or row.get("volume") or 0)
                side = str(op.get("order_type") or "").upper()
                # DEAL_TYPE_BUY = long open? In CSV OPEN sell means short
                if "SELL" in side:
                    direction = -1
                elif "BUY" in side:
                    direction = 1
                else:
                    direction = 0
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                px = entry if entry else 150.0
                risk_usd = (vol * 100_000.0 * risk_pts) / px if px > 0 and vol > 0 and risk_pts > 0 else 0.0
                ot = parse_dt(op.get("event_time") or "")
                ct = parse_dt(row.get("event_time") or "")
                closed.append(
                    {
                        "position_id": pid,
                        "tag": op.get("tag") or "",
                        "open_time": ot,
                        "close_time": ct,
                        "pnl": pnl,
                        "entry": entry,
                        "sl": sl,
                        "tp": tp,
                        "volume": vol,
                        "direction": direction,
                        "risk_pts": risk_pts,
                        "risk_usd": risk_usd,
                        "sleeve": "RR2",
                    }
                )
    return closed


def load_spark_trades() -> list[dict]:
    """Parse Spark deals from report.html via proven compose parser."""
    spec = importlib.util.spec_from_file_location(
        "rr2_spark_cap",
        str(PRE / "20260714_OFFLINE_SB_RR2_SPARK_CAPACITY_COMPOSE_PROBE_V1.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    report = SPARK_DIR / "report.html"
    deals = mod.parse_deals_html(report)
    raw = mod.deals_to_trades(deals)
    out = []
    for t in raw:
        out.append(
            {
                "position_id": f"SPARK-{t['entry_time']}",
                "tag": "SPARK",
                "open_time": t["entry_time"],
                "close_time": t["exit_time"],
                "pnl": float(t["pnl"]),
                "entry": 0.0,
                "sl": 0.0,
                "tp": 0.0,
                "volume": 0.0,
                "direction": 1 if t.get("side") == "buy" else -1,
                "risk_pts": 0.0,
                "risk_usd": 0.0,
                "sleeve": "SPARK",
            }
        )
    return out


def load_yield_z() -> dict[datetime, float]:
    """available_at_utc date -> z of diff using prior lookback only."""
    rows = []
    with EXO.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            obs = datetime.strptime(row["observation_date"], "%Y-%m-%d")
            avail = datetime.strptime(row["available_at_utc"][:10], "%Y-%m-%d")
            diff = float(row["diff_us_jp_10y"])
            rows.append((obs, avail, diff))
    rows.sort(key=lambda x: x[0])
    # map decision_date (calendar day) -> latest available z
    z_by_avail: list[tuple[datetime, float]] = []
    hist = []
    for obs, avail, diff in rows:
        hist.append(diff)
        if len(hist) < YIELD_MIN_OBS:
            continue
        window = hist[-(YIELD_LOOKBACK):]
        mu = sum(window) / len(window)
        var = sum((x - mu) ** 2 for x in window) / max(1, len(window) - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        z = (diff - mu) / sd if sd > 1e-12 else 0.0
        z_by_avail.append((avail, z))

    # build lookup: for any decision day d, take last avail <= d
    lookup: dict[datetime, float] = {}
    last_z = None
    idx = 0
    day = FROM
    while day <= TO:
        while idx < len(z_by_avail) and z_by_avail[idx][0] <= day:
            last_z = z_by_avail[idx][1]
            idx += 1
        if last_z is not None:
            lookup[day.date()] = last_z  # type: ignore
        day += timedelta(days=1)
    # fix: store by date object
    out: dict = {}
    last_z = None
    idx = 0
    day = FROM
    while day <= TO:
        while idx < len(z_by_avail) and z_by_avail[idx][0] <= day:
            last_z = z_by_avail[idx][1]
            idx += 1
        if last_z is not None:
            out[day.date()] = last_z
        day += timedelta(days=1)
    return out


def mt5_bars_m15(symbol: str = "USDJPY"):
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError(f"MT5_INIT_FAIL:{mt5.last_error()}")
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, FROM, TO)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise RuntimeError("no M15 rates")
    bars = []
    for r in rates:
        bars.append(
            {
                "t": datetime.fromtimestamp(int(r["time"])),
                "o": float(r["open"]),
                "h": float(r["high"]),
                "l": float(r["low"]),
                "c": float(r["close"]),
            }
        )
    return bars


def resim_be_exit(trade: dict, bars: list[dict], bar_index: dict) -> float | None:
    """Resimulate BE@1R then original TP/SL. Returns new pnl in cash using risk_usd scale."""
    if trade["open_time"] is None or trade["direction"] == 0:
        return None
    if trade["risk_pts"] <= 0 or trade["risk_usd"] <= 0:
        return trade["pnl"]
    entry = trade["entry"]
    sl0 = trade["sl"]
    tp0 = trade["tp"]
    d = trade["direction"]
    R = abs(entry - sl0)
    if R <= 0:
        return trade["pnl"]
    # If TP missing, infer RR2 from risk
    if not tp0 or tp0 <= 0:
        tp0 = entry + d * 2.0 * R
    ot = trade["open_time"]
    # find first bar at/after open
    # coarse: scan from binary search via bar_index minute key
    key = ot.replace(second=0, microsecond=0)
    # walk forward from open to close+buffer
    end = trade["close_time"] or (ot + timedelta(hours=48))
    be_armed = False
    sl = sl0
    # find start index
    i0 = None
    # linear from estimated: use timestamp map floored to 15m
    t15 = ot.replace(second=0, microsecond=0)
    minute = (t15.minute // 15) * 15
    t15 = t15.replace(minute=minute)
    i0 = bar_index.get(t15)
    if i0 is None:
        # search nearby
        for k in range(0, 8):
            cand = t15 + timedelta(minutes=15 * k)
            if cand in bar_index:
                i0 = bar_index[cand]
                break
            cand = t15 - timedelta(minutes=15 * k)
            if cand in bar_index:
                i0 = bar_index[cand]
                break
    if i0 is None:
        return trade["pnl"]  # fail-closed to original
    for i in range(i0, len(bars)):
        b = bars[i]
        if b["t"] < ot:
            continue
        if b["t"] > end + timedelta(hours=2):
            break
        h, l = b["h"], b["l"]
        # check SL hit first (conservative)
        if d > 0:
            if l <= sl:
                # loss or BE scratch
                r_mult = (sl - entry) / R
                return r_mult * trade["risk_usd"]
            if (not be_armed) and h >= entry + BE_AT_R * R:
                be_armed = True
                sl = entry
            if h >= tp0:
                r_mult = (tp0 - entry) / R
                return r_mult * trade["risk_usd"]
        else:
            if h >= sl:
                r_mult = (entry - sl) / R
                return r_mult * trade["risk_usd"]
            if (not be_armed) and l <= entry - BE_AT_R * R:
                be_armed = True
                sl = entry
            if l <= tp0:
                r_mult = (entry - tp0) / R
                return r_mult * trade["risk_usd"]
    # timed out — use original pnl as proxy
    return trade["pnl"]


def probe_d1(trades: list[dict]) -> dict:
    baseline_pnls = [t["pnl"] for t in trades]
    base_m = metrics(baseline_pnls)
    base_hc = haircuts(baseline_pnls)
    try:
        bars = mt5_bars_m15("USDJPY")
        bar_index = {b["t"]: i for i, b in enumerate(bars)}
        mt5_status = "OK"
    except Exception as e:
        return {
            "hypothesis_id": "HYP-RR2-EXIT-BE1R-M15PATH-001",
            "verdict": "KILLED_AT_OFFLINE_PROBE",
            "kill_notes": [f"mt5_unavailable:{e}"],
            "baseline": {"metrics": base_m, "cost_stress": base_hc},
            "model0": "WITHHELD",
        }
    new_pnls = []
    n_changed = 0
    for t in trades:
        npnl = resim_be_exit(t, bars, bar_index)
        if npnl is None:
            npnl = t["pnl"]
        if abs(npnl - t["pnl"]) > 1e-6:
            n_changed += 1
        new_pnls.append(npnl)
    m = metrics(new_pnls)
    hc = haircuts(new_pnls)
    verdict, notes = joint_verdict(m, hc, baseline_x15=base_hc["x1_5"]["pf"])
    return {
        "hypothesis_id": "HYP-RR2-EXIT-BE1R-M15PATH-001",
        "thesis": "exit_architecture_BE_at_1R_on_frozen_RR2",
        "de_dup": "NOT T1 cost-arm; NOT MaxKZ/RR densify; exit path only",
        "a_priori": {"BE_AT_R": BE_AT_R, "keep_original_TP": True},
        "mt5_status": mt5_status,
        "n_pnl_changed": n_changed,
        "baseline": {"metrics": base_m, "cost_stress": base_hc},
        "metrics": m,
        "cost_stress": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
    }


def probe_d2(trades: list[dict]) -> dict:
    baseline_pnls = [t["pnl"] for t in trades]
    base_m = metrics(baseline_pnls)
    base_hc = haircuts(baseline_pnls)
    zmap = load_yield_z()
    kept = []
    skipped = 0
    missing = 0
    for t in trades:
        if t["open_time"] is None:
            missing += 1
            continue
        z = zmap.get(t["open_time"].date())
        if z is None:
            missing += 1
            continue
        if abs(z) >= YIELD_Z_ABS:
            kept.append(t["pnl"])
        else:
            skipped += 1
    m = metrics(kept)
    hc = haircuts(kept)
    verdict, notes = joint_verdict(m, hc, baseline_x15=base_hc["x1_5"]["pf"])
    # additional: must beat baseline stress to claim gate value
    if (hc["x1_5"]["pf"] or 0) <= (base_hc["x1_5"]["pf"] or 0) + 0.01:
        if "no_stress_lift_vs_baseline" not in notes:
            notes.append("no_stress_lift_vs_baseline")
        verdict = "KILLED_AT_OFFLINE_PROBE"
    return {
        "hypothesis_id": "HYP-RR2-USJP-YIELD-ZGATE-001",
        "thesis": "us_jp_yield_z_allow_gate_on_frozen_RR2",
        "de_dup": "GATE not signal; not USEU/USUK/EU-curve/VIX directional",
        "a_priori": {"YIELD_Z_ABS": YIELD_Z_ABS, "lookback": YIELD_LOOKBACK, "panel": str(EXO)},
        "panel_sha": sha256_file(EXO),
        "funnel": {"n_base": len(trades), "kept": len(kept), "skipped": skipped, "missing_z": missing},
        "baseline": {"metrics": base_m, "cost_stress": base_hc},
        "metrics": m,
        "cost_stress": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
    }


def probe_d3(rr2: list[dict], spark: list[dict]) -> dict:
    # equal-join diagnostic reference
    eq = [t["pnl"] for t in rr2] + [t["pnl"] for t in spark]
    eq_m = metrics(eq)
    eq_hc = haircuts(eq)
    # CorrCap: max concurrent=1 — greedy by open_time, reject overlaps
    events = []
    for t in rr2 + spark:
        if t["open_time"] is None or t["close_time"] is None:
            continue
        events.append(t)
    events.sort(key=lambda x: x["open_time"])
    accepted = []
    rejected = 0
    for t in events:
        overlap = False
        for a in accepted:
            # overlap if open < other.close and close > other.open
            if t["open_time"] < a["close_time"] and t["close_time"] > a["open_time"]:
                overlap = True
                break
        if overlap:
            rejected += 1
            continue
        accepted.append(t)
    pnls = [t["pnl"] for t in accepted]
    m = metrics(pnls)
    hc = haircuts(pnls)
    best_sleeve_pf = max(metrics([t["pnl"] for t in rr2])["pf"] or 0, metrics([t["pnl"] for t in spark])["pf"] or 0)
    verdict, notes = joint_verdict(m, hc)
    if (m["pf"] or 0) < best_sleeve_pf - 0.02:
        notes.append("book_pf_below_best_sleeve")
        verdict = "KILLED_AT_OFFLINE_PROBE"
    # sleeve mix
    mix = defaultdict(int)
    for t in accepted:
        mix[t["sleeve"]] += 1
    return {
        "hypothesis_id": "HYP-BOOK-CORRCAP-RR2-SPARK-001",
        "thesis": "max_concurrent_1_corr_cap_book_not_phase0",
        "de_dup": "NOT Phase-0 equal-join ceremony; NOT SBSparkBook scaffold; overlap reject",
        "a_priori": {"max_concurrent": 1, "rr2": RR2_RUN, "spark": SPARK_RUN},
        "contamination": {
            "status": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
            "ceremony_legal": False,
            "note": "offline CorrCap diagnostic only; not Phase-0 compose claim",
        },
        "equal_join_ref": {"metrics": eq_m, "cost_stress": eq_hc},
        "funnel": {
            "n_rr2": len(rr2),
            "n_spark": len(spark),
            "accepted": len(accepted),
            "rejected_overlap": rejected,
            "mix": dict(mix),
        },
        "best_sleeve_pf": best_sleeve_pf,
        "metrics": m,
        "cost_stress": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
    }


def main() -> int:
    trades_csv = find_trades_csv(RR2_DIR)
    rr2 = load_closed_trades(trades_csv)
    spark = load_spark_trades()
    d1 = probe_d1(rr2)
    d2 = probe_d2(rr2)
    d3 = probe_d3(rr2, spark)
    probes = [d1, d2, d3]
    survivors = [p["hypothesis_id"] for p in probes if p.get("verdict") == "PROBE_SURVIVOR"]
    payload = {
        "schema": "dichotomy_break_offline_probes.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "panel_merge": "readouts/20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md",
        "dedup": "readouts/20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md",
        "best_shelf": f"RR2 {RR2_RUN}",
        "phase0": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
        "rr2_trades_csv": str(trades_csv),
        "rr2_trades_sha": sha256_file(trades_csv),
        "exo_panel_sha": sha256_file(EXO),
        "probes": probes,
        "survivors": survivors,
        "model0_authorized": bool(survivors),
    }
    raw = json.dumps(payload, indent=2, default=str).encode("utf-8")
    payload["receipt_sha256"] = sha256_bytes(raw)
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    # rewrite with sha of final? keep receipt of body without sha field
    receipt = sha256_file(OUT_JSON)

    lines = [
        "# Dichotomy-break offline probes",
        "",
        f"Generated: {payload['generated_at_utc']}",
        "Mandate: break thick↔cadence; no sweep/ORB/IB/ATR%ile clones.",
        f"De-dup: `20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md`",
        f"Merge: `20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md`",
        f"Receipt SHA (json file): `{receipt}`",
        "",
        "| ID | N | PF | tpw | cost×1.5 PF | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for p in probes:
        m = p.get("metrics") or {}
        hc = p.get("cost_stress") or {}
        x15 = (hc.get("x1_5") or {}).get("pf")
        lines.append(
            f"| `{p['hypothesis_id']}` | {m.get('n')} | {m.get('pf')} | {m.get('tpw')} | {x15} | **{p['verdict']}** |"
        )
    lines += [
        "",
        f"Survivors: `{survivors}`",
        f"Model 0 authorized: `{bool(survivors)}`",
        "",
        "## Notes",
        "",
    ]
    for p in probes:
        lines.append(f"- `{p['hypothesis_id']}`: notes={p.get('kill_notes')} funnel={p.get('funnel')}")
    lines += [
        "",
        "Best shelf RR2 `194548` unchanged unless survivor. Phase-0 still BLOCKED. No densify.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"survivors": survivors, "receipt": receipt, "out": str(OUT_JSON)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
