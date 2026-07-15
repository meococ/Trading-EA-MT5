#!/usr/bin/env python3
"""Track B — ≤2 cost-resilient architecture rebuilds on parked RR2 shelf.

Authority: Owner STRATEGY PIVOT 2026-07-15. EXO_FRED_DISPLACE_SPAM_PAUSED.
NOT densify. NOT BE@1R clone. NOT new FRED series.

A priori frozen objects (probe offline first; Model 0 only on survivor):
  1) HYP-RR2-VOLTARGET-ATRRISK-001
     Vol-targeted sizing: scale each frozen RR2 trade to constant risk_usd
     = book median(risk_usd), clip scale∈[0.50, 2.00]. Cadence unchanged.
  2) HYP-RR2-H4-REGIME-ALIGN-GATE-001
     Multi-TF regime switch: keep RR2 open only if closed H4 bar at entry
     has (a) ATR14 percentile∈[20,80] over prior 60 H4 bars AND
     (b) sign(close−EMA20) aligns with trade direction.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"

RR2_RUN = "20260714_194548"
RR2_DIR = RUNS / "EA_SilverBullet" / RR2_RUN
SYMBOL = "USDJPY"

OUT_JSON = PRE / "20260715_ARCH_REBUILD_COST_RESILIENT_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_ARCH_REBUILD_COST_RESILIENT_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_ARCH_REBUILD_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_ARCH_REBUILD_DESIGN_MEMO.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0

# Frozen a priori — do not mine from readout
VOL_SCALE_LO = 0.50
VOL_SCALE_HI = 2.00
H4_ATR_LEN = 14
H4_EMA_LEN = 20
H4_PCT_LOOKBACK = 60
H4_PCT_LO = 20.0
H4_PCT_HI = 80.0


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
    notes: list[str] = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.5 <= tpw <= 6.0):
        notes.append("cadence_fail")
    if pf <= 1.20:
        notes.append("pf_fail")
    if x15 < 1.15:
        notes.append("stress_fail")
    if baseline_x15 is not None and x15 <= baseline_x15 + 0.01:
        notes.append("no_stress_lift_vs_baseline")
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
        and (baseline_x15 is None or x15 > baseline_x15 + 0.01)
    ):
        return "PROBE_SURVIVOR", notes
    if not notes:
        notes.append("joint_screen_miss")
    return "KILLED_AT_OFFLINE_PROBE", notes


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def find_trades_csv(run_dir: Path) -> Path:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    if not hits:
        raise FileNotFoundError(f"no trades csv under {run_dir}")
    return sorted(hits)[0]


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
                vol = float(op.get("volume") or row.get("volume") or 0)
                side = str(op.get("order_type") or "").upper()
                direction = -1 if "SELL" in side else (1 if "BUY" in side else 0)
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                px = entry if entry else 150.0
                risk_usd = (vol * 100_000.0 * risk_pts) / px if px > 0 and vol > 0 and risk_pts > 0 else 0.0
                ot = parse_dt(op.get("event_time") or "")
                closed.append(
                    {
                        "position_id": pid,
                        "tag": op.get("tag") or "",
                        "open_time": ot,
                        "pnl": pnl,
                        "entry": entry,
                        "sl": sl,
                        "volume": vol,
                        "direction": direction,
                        "risk_pts": risk_pts,
                        "risk_usd": risk_usd,
                    }
                )
    return closed


def ema(xs: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(xs)
    if length <= 1 or len(xs) < length:
        return out
    k = 2.0 / (length + 1)
    seed = sum(xs[:length]) / length
    out[length - 1] = seed
    prev = seed
    for i in range(length, len(xs)):
        prev = xs[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def atr_wilder(high: list[float], low: list[float], close: list[float], length: int) -> list[float | None]:
    n = len(close)
    tr = [0.0] * n
    for i in range(n):
        if i == 0:
            tr[i] = high[i] - low[i]
        else:
            tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    out: list[float | None] = [None] * n
    if n < length:
        return out
    seed = sum(tr[:length]) / length
    out[length - 1] = seed
    prev = seed
    for i in range(length, n):
        prev = (prev * (length - 1) + tr[i]) / length
        out[i] = prev
    return out


def percentile_rank(window: list[float], value: float) -> float:
    if not window:
        return 50.0
    below = sum(1 for x in window if x < value)
    equal = sum(1 for x in window if x == value)
    return 100.0 * (below + 0.5 * equal) / len(window)


def load_h4(symbol: str) -> tuple[list[datetime], list[float], list[float], list[float], list[float]]:
    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    try:
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, FROM, TO)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"no H4 rates: {mt5.last_error()}")
        times = [datetime.utcfromtimestamp(int(r["time"])) for r in rates]
        opens = [float(r["open"]) for r in rates]
        highs = [float(r["high"]) for r in rates]
        lows = [float(r["low"]) for r in rates]
        closes = [float(r["close"]) for r in rates]
        return times, opens, highs, lows, closes
    finally:
        mt5.shutdown()


def h4_index_at_or_before(times: list[datetime], t: datetime) -> int | None:
    # closed-bar: last H4 with time <= trade open
    lo, hi = 0, len(times) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return ans


def probe_voltarget(trades: list[dict], baseline_x15: float) -> dict:
    risks = [t["risk_usd"] for t in trades if t["risk_usd"] > 0]
    if not risks:
        return {
            "hypothesis_id": "HYP-RR2-VOLTARGET-ATRRISK-001",
            "verdict": "KILLED_AT_OFFLINE_PROBE",
            "notes": ["no_risk_usd"],
        }
    risks_sorted = sorted(risks)
    target = risks_sorted[len(risks_sorted) // 2]
    scaled: list[float] = []
    scales: list[float] = []
    for t in trades:
        ru = t["risk_usd"]
        if ru <= 0:
            scaled.append(t["pnl"])
            scales.append(1.0)
            continue
        scale = max(VOL_SCALE_LO, min(VOL_SCALE_HI, target / ru))
        scales.append(scale)
        scaled.append(t["pnl"] * scale)
    m = metrics(scaled)
    # Stress: size-proportional friction (spread scales) — use cost * scale
    # Conservative vs flat $12 for upsized legs.
    hc_scaled_cost = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult * s for p, s in zip(scaled, scales)]
        hc_scaled_cost[key] = {
            "pf": round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2),
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    hc_flat = haircuts(scaled)
    # Primary stress = size-aware (more honest for vol-target)
    verdict, notes = joint_verdict(m, hc_scaled_cost, baseline_x15=baseline_x15)
    # Also require flat-$12 diagnostic not silently ignored
    if (hc_flat.get("x1_5") or {}).get("pf", 0) < 1.15:
        if "stress_fail" not in notes:
            notes.append("flat12_stress_diag_fail")
        if verdict == "PROBE_SURVIVOR":
            verdict = "KILLED_AT_OFFLINE_PROBE"
            notes.append("survivor_revoked_flat12")
    return {
        "hypothesis_id": "HYP-RR2-VOLTARGET-ATRRISK-001",
        "family": "architecture_rebuild_voltarget",
        "contract": {
            "target_risk_usd": "median_book_risk_usd",
            "scale_clip": [VOL_SCALE_LO, VOL_SCALE_HI],
            "cadence": "unchanged_all_trades_kept",
            "not": "BE@1R / MaxKZ partial / RR densify / FRED gate",
        },
        "target_risk_usd": round(target, 4),
        "scale_p50": round(sorted(scales)[len(scales) // 2], 4),
        "scale_mean": round(sum(scales) / len(scales), 4),
        "metrics": m,
        "haircut_size_aware": hc_scaled_cost,
        "haircut_flat12_diagnostic": hc_flat,
        "baseline_x15": baseline_x15,
        "stress_lift_vs_baseline_size_aware": round(
            ((hc_scaled_cost.get("x1_5") or {}).get("pf") or 0) - baseline_x15, 4
        ),
        "verdict": verdict,
        "notes": notes,
    }


def probe_h4_regime(trades: list[dict], baseline_x15: float) -> dict:
    times, _o, highs, lows, closes = load_h4(SYMBOL)
    atr = atr_wilder(highs, lows, closes, H4_ATR_LEN)
    ema20 = ema(closes, H4_EMA_LEN)
    kept: list[float] = []
    n_skip_data = 0
    n_skip_pct = 0
    n_skip_align = 0
    for t in trades:
        if t["open_time"] is None:
            n_skip_data += 1
            continue
        idx = h4_index_at_or_before(times, t["open_time"])
        if idx is None or atr[idx] is None or ema20[idx] is None:
            n_skip_data += 1
            continue
        # need lookback window of prior ATR values (exclude current for closed-bar purity:
        # use atr[idx] vs atr[idx-lookback:idx] — current bar is last closed H4 <= entry
        start = max(0, idx - H4_PCT_LOOKBACK)
        window = [atr[i] for i in range(start, idx) if atr[i] is not None]
        if len(window) < max(20, H4_PCT_LOOKBACK // 2):
            n_skip_data += 1
            continue
        pr = percentile_rank(window, float(atr[idx]))  # type: ignore[arg-type]
        if not (H4_PCT_LO <= pr <= H4_PCT_HI):
            n_skip_pct += 1
            continue
        slope_sign = 1 if closes[idx] >= float(ema20[idx]) else -1  # type: ignore[arg-type]
        if t["direction"] == 0 or slope_sign != t["direction"]:
            n_skip_align += 1
            continue
        kept.append(t["pnl"])
    m = metrics(kept)
    hc = haircuts(kept)
    verdict, notes = joint_verdict(m, hc, baseline_x15=baseline_x15)
    return {
        "hypothesis_id": "HYP-RR2-H4-REGIME-ALIGN-GATE-001",
        "family": "architecture_rebuild_multitf_regime",
        "contract": {
            "h4_atr_len": H4_ATR_LEN,
            "h4_ema_len": H4_EMA_LEN,
            "pct_lookback": H4_PCT_LOOKBACK,
            "atr_pctile_band": [H4_PCT_LO, H4_PCT_HI],
            "align": "sign(H4_close - H4_EMA20) == trade_direction",
            "closed_bar": True,
            "not": "BE@1R / RR densify / FRED / yield-z twin",
        },
        "funnel": {
            "n_in": len(trades),
            "n_kept": len(kept),
            "n_skip_data": n_skip_data,
            "n_skip_atr_pctile": n_skip_pct,
            "n_skip_align": n_skip_align,
        },
        "metrics": m,
        "haircut_flat12": hc,
        "baseline_x15": baseline_x15,
        "stress_lift_vs_baseline": round(((hc.get("x1_5") or {}).get("pf") or 0) - baseline_x15, 4),
        "verdict": verdict,
        "notes": notes,
    }


def write_dedup() -> None:
    text = """# De-dup clearance — architecture rebuild Track B

Date: 2026-07-15  
Authority: Owner STRATEGY PIVOT; EXO_FRED_DISPLACE_SPAM_PAUSED

## Objects

| ID | Class | Independence claim |
|---|---|---|
| `HYP-RR2-VOLTARGET-ATRRISK-001` | Sizing architecture on frozen RR2 `194548` | Reweights risk_usd to book median; **not** MaxKZ partial, **not** BE@1R, **not** RR/session densify, **not** COT/FRED gate |
| `HYP-RR2-H4-REGIME-ALIGN-GATE-001` | Multi-TF regime allow-gate on frozen RR2 | H4 ATR%ile band + EMA align; **not** M15 BE path, **not** USJP yield-z, **not** WALCL/PD/MMF/6J/ECB/Brent |

## Banned collisions

- Dichotomy BE@1R (`HYP-RR2-EXIT-BE1R-M15PATH-001`) — killed; this board does not revive BE.
- MaxKZ2 partial / RR retune / Spark MaxPerDay / session cuts.
- FRED displace/ToT / exo gate densify (spam paused).
- Wave1–9 price-twin reopen.

## Survivor bar

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 ∧ stress lift vs RR2 baseline x1.5.
Model 0 withheld unless `PROBE_SURVIVOR`.

## Clearance

**CLEARED** for offline probe only.
"""
    OUT_DEDUP.write_text(text, encoding="utf-8")


def write_design() -> None:
    text = """# Design memo — ≤2 cost-resilient architecture rebuilds

Date: 2026-07-15  
Lane: single; no-Git; offline-first

## Problem

Parked RR2 `194548` hits research PF~1.38 / ~2/wk but dies under +$12 x1.5
(stress ~1.01). Exo gate spam (FRED displace/ToT) exhausted. Need architecture
that raises **post-friction $/trade** without densifying signal params.

## Rejected tonight (a priori)

- BE@1R / trail-from-BE readout rescue (already falsified).
- New FRED series / exo densify (`EXO_FRED_DISPLACE_SPAM_PAUSED`).
- RR/MaxKZ/session threshold mining from this board.

## Design 1 — Vol-targeted ATR risk (`HYP-RR2-VOLTARGET-ATRRISK-001`)

**Thesis:** Fixed 0.5-lot RR2 makes `risk_usd` path-dependent on SL distance.
Flat friction taxes small-risk legs disproportionately. Normalizing each trade
to median book risk (clip 0.5–2.0×) should stabilize R and lift expectancy after
size-aware cost.

**Frozen formula:** `scale = clip(median(risk_usd)/risk_usd, 0.5, 2.0)`;
`pnl' = pnl * scale`; stress cost `=$12 * scale` (spread scales with size).

**Cadence:** unchanged (all trades kept) → stays in 2–5/wk band if baseline does.

## Design 2 — H4 regime align gate (`HYP-RR2-H4-REGIME-ALIGN-GATE-001`)

**Thesis:** RR2 entries in extreme H4 vol or counter-H4 drift are friction
traps. Allow only mid-vol H4 (ATR%ile 20–80) with EMA20 alignment.

**Frozen:** ATR14, EMA20, lookback 60, band [20,80], closed H4 ≤ entry time.

**Cadence risk:** will thin; kill if tpw leaves [1.5,6].

## Deferred (not in ≤2)

- State-machine Asia-coil→London-fire entry (needs new signal object).
- Path-dependent MFE stall-cut exit (separate from BE@1R; next board if both kill).

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold.
"""
    OUT_DESIGN.write_text(text, encoding="utf-8")


def main() -> int:
    write_dedup()
    write_design()
    trades_path = find_trades_csv(RR2_DIR)
    trades = load_closed_trades(trades_path)
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    baseline_x15 = float((base_hc.get("x1_5") or {}).get("pf") or 0.0)

    r1 = probe_voltarget(trades, baseline_x15)
    r2 = probe_h4_regime(trades, baseline_x15)
    results = [r1, r2]
    survivors = [r for r in results if r.get("verdict") == "PROBE_SURVIVOR"]

    payload = {
        "schema": "arch_rebuild_cost_resilient_offline_probes.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "Owner STRATEGY PIVOT 2026-07-15; Track B; EXO_FRED_DISPLACE_SPAM_PAUSED",
        "rr2_sleeve": RR2_RUN,
        "trades_csv": str(trades_path.relative_to(ROOT)).replace("\\", "/"),
        "n_trades": len(trades),
        "baseline": {"metrics": base_m, "haircut_flat12": base_hc},
        "results": results,
        "any_survivor": bool(survivors),
        "survivors": [s["hypothesis_id"] for s in survivors],
        "model0": "WITHHELD" if not survivors else "ARMED_NOT_AUTO",
        "bans": [
            "no_BE@1R_revive",
            "no_FRED_spam",
            "no_RR_MaxKZ_densify",
            "no_invent_cost_surface",
        ],
        "best_shelf": "RR2_20260714_194548",
        "dedup": str(OUT_DEDUP.relative_to(ROOT)).replace("\\", "/"),
        "design_memo": str(OUT_DESIGN.relative_to(ROOT)).replace("\\", "/"),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    receipt = sha256_file(OUT_JSON)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Offline probes — architecture rebuild cost-resilient (Track B)",
        "",
        "Date: 2026-07-15",
        f"Status: `{'PROBE_SURVIVOR' if survivors else 'OFFLINE_ALL_KILL / NO_MODEL0'}`",
        f"Receipt SHA: `{receipt}`",
        "",
        "## Baseline RR2 `194548`",
        "",
        f"- N={base_m['n']} PF={base_m['pf']} tpw={base_m['tpw']} "
        f"x1.5={(base_hc.get('x1_5') or {}).get('pf')}",
        "",
        "## Board",
        "",
        "| ID | N | PF | tpw | stress x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        m = r.get("metrics") or {}
        if "haircut_size_aware" in r:
            x15 = (r["haircut_size_aware"].get("x1_5") or {}).get("pf")
        else:
            x15 = (r.get("haircut_flat12") or {}).get("x1_5", {}).get("pf")
        lines.append(
            f"| `{r['hypothesis_id']}` | {m.get('n')} | {m.get('pf')} | {m.get('tpw')} | {x15} | **{r['verdict']}** |"
        )
    lines += [
        "",
        "## Notes",
        "",
    ]
    for r in results:
        lines.append(f"- `{r['hypothesis_id']}`: notes={r.get('notes')} funnel={r.get('funnel')}")
    lines += [
        "",
        "## Model 0",
        "",
        "Withheld." if not survivors else f"Armed for: {survivors}",
        "",
        "## Artifacts",
        "",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_DEDUP.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_DESIGN.relative_to(ROOT).as_posix()}`",
        "",
        "Do not densify vol clip / H4 ATR%ile / EMA from this readout.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": receipt, "any_survivor": bool(survivors), "results": [
        {"id": r["hypothesis_id"], "verdict": r["verdict"], "metrics": r.get("metrics"), "notes": r.get("notes")}
        for r in results
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
