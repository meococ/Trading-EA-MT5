#!/usr/bin/env python3
"""Sector relative + copper-gold ratio — offline probes (HARD PIVOT W23 exo).

A priori frozen (do not mine / do not densify):
  O1 HYP-AUDUSD-H1-XLKXLF-GROWTHLEAD-CONT-001
  O2 HYP-AUDUSD-H1-CUGOLD-RATIO-CONT-001
  O3 HYP-BOOK-SECTOR-CUGOLD-APRIORI-001

Surface: Yahoo XLK/XLF ratio + HG/GC copper-gold ratio (lag +1d panels).
EVZ FX-vol proved unavailable this pass → picked sector+cugold next.

Independent of: VIX risk-off · SPX−DGS10 · WTI/Brent oil ToT · WALCL/ECB ·
MOVE/HY/DTWEX · COT · W1–W22 OHLC densify · R-series.

Joint screen: N, PF, tpw, +$12 (x1), x1.5. Model 0 only PROBE_SURVIVOR.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
EXO = PRE / "v8_exogenous"
SECTOR_PANEL = EXO / "panels" / "yahoo_xlk_xlf_ratio_d1_v1.csv"
CUGOLD_PANEL = EXO / "panels" / "yahoo_hg_gc_cugold_ratio_d1_v1.csv"
ACQ_MANIFEST = EXO / "manifests" / "20260715_SECTOR_CUGOLD_ACQUISITION_V1.json"
CONTRACT = EXO / "contracts" / "20260715_SECTOR_CUGOLD_AVAILABLE_AT_UTC_CONTRACT_V1.json"

OUT_JSON = PRE / "20260715_SECTOR_CUGOLD_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_SECTOR_CUGOLD_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_SECTOR_CUGOLD_DEDUP_CLEARANCE.md"
OUT_CLOSE = READ / "20260715_SECTOR_CUGOLD_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_SECTOR_CUGOLD_VN_ACTION_BRIEF.md"
OUT_ACQ = READ / "20260715_SECTOR_CUGOLD_ACQUISITION_READOUT.md"
OUT_DESIGN = READ / "20260715_SECTOR_CUGOLD_DESIGN_MEMO.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK = 0.005
COST12 = 12.0

# A priori — structural exo displace template (frozen; do not mine)
RANGE_ATR = 1.2
BODY_ATR = 0.55
CLOSE_FRAC = 0.60
SL_ATR = 1.0
RR = 2.0
MAX_HOLD = 12
Z_ABS = 0.75
LOOKBACK = 60
MIN_OBS = 40


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = COST12) -> dict:
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
    tpw = n / ELAPSED_WEEKS if ELAPSED_WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(m: dict, hc: dict) -> tuple[str, list[str]]:
    notes: list[str] = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    pf12 = (hc.get("x1") or {}).get("pf") or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0 or tpw > 5.0:
        notes.append("cadence_fail")
    if pf12 < 1.30:
        notes.append("pf12_fail")
    if x15 < 1.25:
        notes.append("stress_fail")
    if not notes:
        return "PROBE_SURVIVOR", []
    return "KILLED_AT_OFFLINE_PROBE", notes


def atr14(h, l, c):
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.full(n, np.nan)
    if n < 14:
        return out
    out[13] = tr[:14].mean()
    for i in range(14, n):
        out[i] = (out[i - 1] * 13 + tr[i]) / 14
    return out


def load_h1(symbol: str) -> dict:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"rates fail {symbol}: {mt5.last_error()}")
    return {
        k: rates[k].astype(float) if k != "time" else rates[k].astype(np.int64)
        for k in ("time", "open", "high", "low", "close")
    }


def mt5_dow(ts: int) -> int:
    return (datetime.fromtimestamp(ts, timezone.utc).weekday() + 1) % 7


def hour_u(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def tradeable(ts: int) -> bool:
    return mt5_dow(ts) in (1, 2, 3, 4) and hour_u(ts) < 22


def resolve_trade(direction, entry, sl, tp, i_entry, h, l, c, max_hold, rr):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i_entry, min(i_entry + max_hold, len(c))):
        hi, lo = h[j], l[j]
        hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
        hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
        if hit_sl:
            return -1.0
        if hit_tp:
            return rr
    j = min(i_entry + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def sim_r(trades_spec: list[dict]) -> list[float]:
    bal = DEPOSIT
    pnls = []
    for t in trades_spec:
        risk_cash = bal * RISK
        pnl = risk_cash * t["r"]
        pnls.append(pnl)
        bal += pnl
    return pnls


def build_z_lookup(panel: Path, value_col: str) -> dict[date, float]:
    rows: list[tuple[date, float]] = []
    with panel.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            avail = date.fromisoformat(row["available_at_utc"][:10])
            val = float(row[value_col])
            rows.append((avail, val))
    rows.sort(key=lambda x: x[0])
    z_by_avail: list[tuple[date, float]] = []
    hist: list[float] = []
    for avail, val in rows:
        hist.append(val)
        if len(hist) < MIN_OBS:
            continue
        window = hist[-LOOKBACK:]
        mu = sum(window) / len(window)
        var = sum((x - mu) ** 2 for x in window) / max(1, len(window) - 1)
        sd = math.sqrt(var) if var > 0 else 0.0
        z = (val - mu) / sd if sd > 1e-12 else 0.0
        z_by_avail.append((avail, z))
    out: dict[date, float] = {}
    last_z = None
    idx = 0
    day = FROM.date()
    end = TO.date()
    while day <= end:
        while idx < len(z_by_avail) and z_by_avail[idx][0] <= day:
            last_z = z_by_avail[idx][1]
            idx += 1
        if last_z is not None:
            out[day] = last_z
        day += timedelta(days=1)
    return out


def probe_ratio_cont(
    h1: dict,
    z_lookup: dict[date, float],
    *,
    hypothesis_id: str,
    class_name: str,
    thesis: str,
    value_name: str,
) -> dict[str, Any]:
    """z>=+thr → long AUDUSD displace; z<=-thr → short (growth/factor follow)."""
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades: list[dict] = []
    funnel = {"n_bias": 0, "n_displace": 0, "n_trades": 0, "days_used": 0, "n_no_z": 0}
    used_day: set[str] = set()
    i = 20
    while i < len(c) - MAX_HOLD - 1:
        if math.isnan(atr[i]) or atr[i] <= 0 or not tradeable(int(t[i])):
            i += 1
            continue
        dkey = datetime.fromtimestamp(int(t[i]), timezone.utc).strftime("%Y-%m-%d")
        if dkey in used_day:
            i += 1
            continue
        d = date.fromisoformat(dkey)
        z = z_lookup.get(d)
        if z is None:
            funnel["n_no_z"] += 1
            i += 1
            continue
        if abs(z) < Z_ABS:
            i += 1
            continue
        bias = +1 if z >= Z_ABS else -1
        funnel["n_bias"] += 1
        rng = h[i] - l[i]
        body = abs(c[i] - o[i])
        if rng < RANGE_ATR * atr[i] or body < BODY_ATR * atr[i]:
            i += 1
            continue
        if bias > 0:
            if c[i] < l[i] + CLOSE_FRAC * rng:
                i += 1
                continue
        else:
            if c[i] > h[i] - CLOSE_FRAC * rng:
                i += 1
                continue
        funnel["n_displace"] += 1
        entry = float(c[i])
        if bias > 0:
            sl = entry - SL_ATR * atr[i]
            tp = entry + RR * (entry - sl)
        else:
            sl = entry + SL_ATR * atr[i]
            tp = entry - RR * (sl - entry)
        r = resolve_trade(bias, entry, sl, tp, i + 1, h, l, c, MAX_HOLD, RR)
        if r is None:
            i += 1
            continue
        trades.append(
            {
                "r": float(r),
                "t": int(t[i]),
                "z": z,
                "bias": bias,
                "day": dkey,
                "src": value_name,
            }
        )
        used_day.add(dkey)
        funnel["n_trades"] += 1
        i += MAX_HOLD
    funnel["days_used"] = len(used_day)
    pnls = sim_r(trades)
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hypothesis_id,
        "class": class_name,
        "symbol": "AUDUSD",
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "trades": trades,
        "a_priori": {
            "z_abs": Z_ABS,
            "lookback": LOOKBACK,
            "thesis": thesis,
            "bias_rule": "z>=+thr long AUDUSD; z<=-thr short AUDUSD",
            "lag": "observation+1d (frozen panel available_at)",
            "range_atr": RANGE_ATR,
            "body_atr": BODY_ATR,
            "close_frac": CLOSE_FRAC,
            "sl_atr": SL_ATR,
            "rr": RR,
            "max_hold": MAX_HOLD,
            "not_vix_riskoff": True,
            "not_wti_brent_oil": True,
            "not_w1_w22_ohlc": True,
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def probe_book(o1: dict, o2: dict) -> dict[str, Any]:
    """A priori nested book: union by day, prefer larger |z| when same day conflict."""
    by_day: dict[str, dict] = {}
    for tr in o1.get("trades") or []:
        by_day[tr["day"]] = tr
    for tr in o2.get("trades") or []:
        prev = by_day.get(tr["day"])
        if prev is None or abs(tr["z"]) > abs(prev["z"]):
            by_day[tr["day"]] = tr
    trades = sorted(by_day.values(), key=lambda x: x["t"])
    pnls = sim_r(trades)
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": "HYP-BOOK-SECTOR-CUGOLD-APRIORI-001",
        "class": "nested_sector_cugold_apriori_book",
        "symbol": "AUDUSD",
        "tf": "H1",
        "funnel": {
            "n_o1": o1["metrics"]["n"],
            "n_o2": o2["metrics"]["n"],
            "n_union_days": len(trades),
            "n_trades": len(trades),
        },
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "a_priori": {
            "composition": "union_by_day_prefer_larger_abs_z",
            "parents": [o1["hypothesis_id"], o2["hypothesis_id"]],
            "nested_ok": True,
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def strip_trades(o: dict) -> dict:
    out = dict(o)
    out.pop("trades", None)
    return out


def append_registry(objects: list[dict], receipt: str) -> None:
    lines = []
    for o in objects:
        state = "killed" if "KILL" in o["verdict"] else "probed"
        if o["verdict"] == "PROBE_SURVIVOR":
            state = "probe_survivor"
        rec = {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": o["hypothesis_id"],
            "state": state,
            "verdict": o["verdict"],
            "reason": ",".join(o.get("kill_notes") or []) or o["verdict"],
            "updated_at": "2026-07-15",
            "feature_family": o.get("class"),
            "lane": "sector_cugold_exo_20260715",
            "setup_type": o["hypothesis_id"],
            "symbol": o.get("symbol") or "AUDUSD",
            "timeframe": o.get("tf") or "H1",
            "window": "2021.01.01-2025.12.31",
            "model": None,
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_SECTOR_CUGOLD_OFFLINE_PROBES.md",
            "run_ids": [],
            "metrics": o.get("metrics"),
            "validation": {
                "offline_probe": o["verdict"],
                "kill_notes": o.get("kill_notes"),
                "receipt_sha256": receipt,
            },
            "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
        }
        lines.append(json.dumps(rec, ensure_ascii=False))
    with REG.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def write_docs(payload: dict, objects: list[dict]) -> None:
    o1, o2, o3 = objects
    OUT_DEDUP.write_text(
        """# De-dup clearance — XLK/XLF sector + Cu/Gold ratio

Status: `INTAKE_CLEARED / INDEPENDENT` (a priori)

| Object | Vs killed shelf |
|---|---|
| O1 AUDUSD XLK/XLF growth-lead CONT | ≠ VIXCLS→USDJPY risk-off; ≠ SPX−DGS10 equity-bond; ≠ MOVE/HY/DTWEX siblings; ≠ W1–W22 OHLC densify |
| O2 AUDUSD HG/GC copper-gold CONT | ≠ WTI-USDCAD ToT; ≠ Brent-EURUSD importer; ≠ AUDCOM3 H1 basket residual (ratio factor ≠ multi-metal resid MR) |
| O3 nested book sector∪cugold | a priori union; not post-hoc sleeve mine |

Banned densify: XLK/XLF z thr · Cu/Gold z thr · displace ATR/RR · VIX/MOVE shopping · WTI/Brent revive · W1–W22 / R10–R31 / FVG.
""",
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        """# Design memo — Sector relative + copper-gold (W23 exo)

## Surface acquisition

1. **Tried EVZCLS (CBOE euro FX vol)** — FRED timeout; DBnomics 404; Yahoo EVZ unusable →
   `PROVE_UNAVAILABLE_PICK_NEXT`.
2. **Selected:** Yahoo `XLK`/`XLF` sector relative + `HG=F`/`GC=F` copper-gold ratio.
   SHA-frozen panels lag `observation_date + 1 calendar day`.

## Mechanisms (a priori)

1. **XLK/XLF growth-lead:** tech vs financials leadership = growth risk-on → AUDUSD
   follow H1 displace (long if z≥+0.75; short if z≤−0.75).
2. **Cu/Gold ratio:** industrial copper vs haven gold = real-activity/growth factor
   beyond oil curve → same AUDUSD CONT displace contract.
3. **Nested book:** day-union prefer larger |z|.

## Explicit non-twins

Not VIX level risk-off, not SPX−bond, not WTI/Brent oil ToT, not OHLC HARD PIVOT densify.
""",
        encoding="utf-8",
    )

    rows = []
    for o in objects:
        m = o["metrics"]
        hc = o["haircuts"]
        rows.append(
            f"| `{o['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{(hc.get('x1') or {}).get('pf')} | {(hc.get('x1_5') or {}).get('pf')} | "
            f"{o['verdict']} | {','.join(o.get('kill_notes') or [])} |"
        )

    status = payload["campaign_status"]
    OUT_MD.write_text(
        f"""# Offline probes — XLK/XLF sector + Cu/Gold ratio

Date: 2026-07-15  
Status: `{status}`  
Sector panel SHA: `{payload["panel_sha256"]["sector"]}`  
CuGold panel SHA: `{payload["panel_sha256"]["cugold"]}`  
Receipt: `{payload["receipt_sha256"]}`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Joint screen

N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (deals~11). Offline stress uses +$12 proxy only. Do not invent.
""",
        encoding="utf-8",
    )

    survivors = [o for o in objects if o["verdict"] == "PROBE_SURVIVOR"]
    kill_table = "\n".join(
        f"| `{o['hypothesis_id']}` | **{o['verdict']}** |" for o in objects
    )
    OUT_CLOSE.write_text(
        f"""# Session closeout — Sector + Cu/Gold exo (W23)

Date: 2026-07-15  
Status: `{status}`  
Lane: single checkout; no-Git; ChatGPT login wall is parallel Owner action only

## Acquisition

Yahoo XLK/XLF ratio + HG/GC copper-gold ratio (lag +1d).  
EVZ FX-vol: unavailable this pass (FRED timeout / DBnomics 404) → pick-next executed.  
Manifest: `v8_exogenous/manifests/20260715_SECTOR_CUGOLD_ACQUISITION_V1.json`

## Probes

| ID | Verdict |
|---|---|
{kill_table}

Receipt: `{payload["receipt_sha256"]}`  
Artifacts: `preflight/20260715_SECTOR_CUGOLD_OFFLINE_PROBES.json`

## Model 0

{"AUTHORIZED for: " + ", ".join(o["hypothesis_id"] for o in survivors) if survivors else "Withheld (no PROBE_SURVIVOR)."}

## Next autonomous EV

1. Do **not** densify XLK/XLF z / CuGold z / displace ATR/RR.
2. Keep R-series / W1–W22 densify paused.
3. Keep Real QFSI accumulate for cost frontier (still GAP).
4. Next object outside sector-cugold / oil / VIX-sibling / W1–W22 killboard —
   or Owner ChatGPT login for Deep Research (parallel, not stop).

Best shelf unchanged: RR2 `20260714_194548` / clean book PF@$12=1.184. Phase-0 still BLOCKED. GOAL unmet.
""",
        encoding="utf-8",
    )

    OUT_VN.write_text(
        f"""# VN — Sector + Cu/Gold (W23 exo) + cost note

## Surface
- EVZ FX-vol: **không lấy được** (FRED timeout / DBnomics 404) → chuyển surface tiếp.
- Đã SHA-freeze: Yahoo XLK/XLF ratio + HG/GC copper-gold (lag +1d).

## Probe
- Status: `{status}`.
- Model 0: {"có survivor — chạy Model 0" if survivors else "không — withheld"}.
- Cost: vẫn **GAP** (deals~11). Không invent.

## Không làm
- Densify XLK/XLF / CuGold z / ATR/RR.
- Densify W14/FVG/W1–W22 / R-series.
- Chờ ChatGPT login (Owner parallel only).

## Next
- Object exo mới ngoài killboard, hoặc Owner login ChatGPT + QFSI deals.
- Best shelf RR2 `194548`; clean book PF@$12=1.184.
""",
        encoding="utf-8",
    )

    OUT_ACQ.write_text(
        f"""# Acquisition readout — XLK/XLF + Cu/Gold

Manifest: `v8_exogenous/manifests/20260715_SECTOR_CUGOLD_ACQUISITION_V1.json`  
Contract: `v8_exogenous/contracts/20260715_SECTOR_CUGOLD_AVAILABLE_AT_UTC_CONTRACT_V1.json`

## OK

- Yahoo XLK/XLF daily → ratio panel lag +1d  
  SHA `{payload["panel_sha256"]["sector"]}`
- Yahoo HG=F / GC=F → copper-gold ratio panel lag +1d  
  SHA `{payload["panel_sha256"]["cugold"]}`

## Unavailable this pass

- EVZCLS / FX vol index (FRED timeout; DBnomics 404; Yahoo EVZ unusable) —
  documented in contract `unavailable_this_pass`; pick-next = sector+cugold.

## Explicit non-use

- Not VIXCLS risk-off twin.
- Not SPX−DGS10 equity-bond twin.
- Not WTI/Brent oil ToT densify.
- Not MOVE/HY/DTWEX shopping.
""",
        encoding="utf-8",
    )


def main() -> None:
    assert SECTOR_PANEL.is_file(), "run acquire_freeze_sector_cugold_v1.py first"
    assert CUGOLD_PANEL.is_file(), "run acquire_freeze_sector_cugold_v1.py first"
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init fail: {mt5.last_error()}")
    try:
        h1 = load_h1("AUDUSD")
        sector_z = build_z_lookup(SECTOR_PANEL, "xlk_xlf_ratio")
        cugold_z = build_z_lookup(CUGOLD_PANEL, "cu_gold_ratio")
        o1 = probe_ratio_cont(
            h1,
            sector_z,
            hypothesis_id="HYP-AUDUSD-H1-XLKXLF-GROWTHLEAD-CONT-001",
            class_name="equity_sector_relative_growth_lead_cont",
            thesis="XLK_vs_XLF_growth_leadership_risk_on_AUD",
            value_name="xlk_xlf",
        )
        o2 = probe_ratio_cont(
            h1,
            cugold_z,
            hypothesis_id="HYP-AUDUSD-H1-CUGOLD-RATIO-CONT-001",
            class_name="copper_gold_ratio_growth_factor_cont",
            thesis="HG_GC_industrial_vs_haven_growth_AUD",
            value_name="cugold",
        )
        o3 = probe_book(o1, o2)
        objects_full = [o1, o2, o3]
        objects = [strip_trades(o) for o in objects_full]
        survivors = [o for o in objects if o["verdict"] == "PROBE_SURVIVOR"]
        status = (
            "OFFLINE_HAS_SURVIVOR / MODEL0_ARMED"
            if survivors
            else "OFFLINE_ALL_KILL / NO_MODEL0"
        )
        payload = {
            "schema": "sector_cugold_offline_probes.v1",
            "created_at_utc": utc_now(),
            "campaign_status": status,
            "wave": "W23_SECTOR_CUGOLD_EXO",
            "window": {
                "from": FROM.isoformat(),
                "to": TO.isoformat(),
                "elapsed_weeks": round(ELAPSED_WEEKS, 4),
            },
            "cost_proxy_usd_per_trade": COST12,
            "panel_sha256": {
                "sector": sha256_file(SECTOR_PANEL),
                "cugold": sha256_file(CUGOLD_PANEL),
            },
            "contract_sha256": sha256_file(CONTRACT) if CONTRACT.is_file() else None,
            "acquisition_manifest_sha256": (
                sha256_file(ACQ_MANIFEST) if ACQ_MANIFEST.is_file() else None
            ),
            "evz_status": "UNAVAILABLE_THIS_PASS__PICK_NEXT_SECTOR_CUGOLD",
            "objects": objects,
            "survivors": [o["hypothesis_id"] for o in survivors],
            "model0": "AUTHORIZED_IF_SURVIVOR" if survivors else "WITHHELD",
            "banned": [
                "VIXCLS_riskoff_retune",
                "SPX_DGS10_retune",
                "HY_MOVE_DTWEX_vix_sibling",
                "WTI_BRENT_oil_retune",
                "XLKXLF_z_mine",
                "CUGOLD_z_mine",
                "W1_W22_OHLC_densify",
                "R_series_densify",
                "invent_spreads",
                "Phase0_without_clear",
            ],
            "best_shelf": "RR2_20260714_194548",
            "clean_book_pf12": 1.184,
            "cost_surface": "GAP_UNCHANGED",
            "chatgpt": "AUTH_BLOCKED__LOGIN_WALL__PARALLEL_OWNER_ONLY",
        }
        write_json(OUT_JSON, payload)
        payload["receipt_sha256"] = sha256_file(OUT_JSON)
        write_json(OUT_JSON, payload)
        write_docs(payload, objects)
        append_registry(objects, payload["receipt_sha256"])
        print(
            json.dumps(
                {
                    "status": status,
                    "receipt": payload["receipt_sha256"],
                    "panels": payload["panel_sha256"],
                    "summary": [
                        {
                            "id": o["hypothesis_id"],
                            "n": o["metrics"]["n"],
                            "pf": o["metrics"]["pf"],
                            "tpw": o["metrics"]["tpw"],
                            "pf12": (o["haircuts"].get("x1") or {}).get("pf"),
                            "x15": (o["haircuts"].get("x1_5") or {}).get("pf"),
                            "verdict": o["verdict"],
                            "notes": o["kill_notes"],
                        }
                        for o in objects
                    ],
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
