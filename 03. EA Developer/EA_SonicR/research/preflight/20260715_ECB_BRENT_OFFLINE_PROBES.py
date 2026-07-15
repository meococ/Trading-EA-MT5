#!/usr/bin/env python3
"""ECB balance-sheet primary + Brent importer ToT — offline probes.

A priori frozen (do not mine / do not densify):
  O1 HYP-EURUSD-H1-ECB-BS-EXPAND-DISPLACE-001
  O2 HYP-EURUSD-H1-ECB-BS-CONTRACT-DISPLACE-001
  O3 HYP-EURUSD-H1-BRENT-IMPORTER-TOT-001

Independent of: WALCL RR2 QT gate · WTI-USDCAD ToT · PD-primary displace ·
VIX/HY/MOVE/DTWEX risk-off siblings · Wave1–9 · COT.

Displace / ToT params frozen from WTI structural exo template.
Joint screen: N, PF, tpw, +$12 x1.5. Model 0 only if PROBE_SURVIVOR.
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
ECB_PANEL = EXO / "panels" / "fred_ecbassetsw_wow_w1_v1.csv"
BRENT_PANEL = EXO / "panels" / "fred_brent_dcoilbrenteu_d1_v1.csv"
ACQ_MANIFEST = EXO / "manifests" / "20260715_ECB_BRENT_ACQUISITION_V1.json"
CONTRACT = EXO / "contracts" / "20260715_ECB_BRENT_AVAILABLE_AT_UTC_CONTRACT_V1.json"

OUT_JSON = PRE / "20260715_ECB_BRENT_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_ECB_BRENT_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_ECB_BRENT_DEDUP_CLEARANCE.md"
OUT_CLOSE = READ / "20260715_ECB_BRENT_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_ECB_BRENT_VN_ACTION_BRIEF.md"
OUT_ACQ = READ / "20260715_ECB_BRENT_ACQUISITION_READOUT.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK = 0.005
COST12 = 12.0

# A priori — WTI structural exo template (frozen; do not mine)
RANGE_ATR = 1.2
BODY_ATR = 0.55
CLOSE_FRAC = 0.60
SL_ATR = 1.0
RR = 2.0
MAX_HOLD = 12
BRENT_Z_ABS = 0.75
BRENT_LOOKBACK = 60
BRENT_MIN_OBS = 40


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
    if n >= 80 and pf > 1.20 and 1.5 <= tpw <= 6.0 and x15 >= 1.15:
        return "PROBE_SURVIVOR", notes
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    return "KILLED_AT_OFFLINE_PROBE", ["joint_screen_miss"]


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


def build_ecb_expand_lookup() -> dict[date, bool]:
    """True = expand (wow_pct > 0); False = contract."""
    events: list[tuple[date, float]] = []
    with ECB_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            wow = (row.get("wow_pct") or "").strip()
            if not wow:
                continue
            avail = date.fromisoformat(row["available_at_utc"][:10])
            events.append((avail, float(wow)))
    events.sort(key=lambda x: x[0])
    out: dict[date, bool] = {}
    last: bool | None = None
    idx = 0
    day = FROM.date()
    end = TO.date()
    while day <= end:
        while idx < len(events) and events[idx][0] <= day:
            last = events[idx][1] > 0.0
            idx += 1
        if last is not None:
            out[day] = last
        day += timedelta(days=1)
    return out


def build_brent_z_lookup() -> dict[date, float]:
    rows = []
    with BRENT_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            avail = date.fromisoformat(row["available_at_utc"][:10])
            val = float(row["brent_usd"])
            rows.append((avail, val))
    rows.sort(key=lambda x: x[0])
    z_by_avail: list[tuple[date, float]] = []
    hist: list[float] = []
    for avail, val in rows:
        hist.append(val)
        if len(hist) < BRENT_MIN_OBS:
            continue
        window = hist[-BRENT_LOOKBACK:]
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


def probe_ecb_displace(
    h1: dict,
    ecb_expand: dict[date, bool],
    *,
    hypothesis_id: str,
    require_expand: bool,
) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades: list[dict] = []
    funnel = {"n_regime": 0, "n_displace": 0, "n_trades": 0, "days_used": 0, "n_no_ecb": 0}
    used_day: set[str] = set()
    bias = +1 if require_expand else -1
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
        regime = ecb_expand.get(d)
        if regime is None:
            funnel["n_no_ecb"] += 1
            i += 1
            continue
        if require_expand and not regime:
            i += 1
            continue
        if (not require_expand) and regime:
            i += 1
            continue
        funnel["n_regime"] += 1
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
        trades.append({"r": float(r), "t": int(t[i]), "bias": bias, "expand": bool(regime)})
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
        "class": "ecb_bs_primary_structural_displace",
        "symbol": "EURUSD",
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "a_priori": {
            "ecb_rule": "wow_pct > 0 expand / <=0 contract",
            "lag": "observation+5d (frozen panel available_at)",
            "require_expand": require_expand,
            "bias": "long_only_if_expand" if require_expand else "short_only_if_contract",
            "range_atr": RANGE_ATR,
            "body_atr": BODY_ATR,
            "close_frac": CLOSE_FRAC,
            "sl_atr": SL_ATR,
            "rr": RR,
            "max_hold": MAX_HOLD,
            "fail_closed_missing_ecb": True,
            "not_walcl_rr2_gate": True,
            "not_pd_primary_clone": True,
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def probe_brent_importer_tot(h1: dict, brent_z: dict[date, float]) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_bias": 0, "n_displace": 0, "n_trades": 0, "days_used": 0}
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
        z = brent_z.get(d)
        if z is None or abs(z) < BRENT_Z_ABS:
            i += 1
            continue
        # oil up → EUR importer stress → short EURUSD; oil down → long EURUSD
        bias = -1 if z >= BRENT_Z_ABS else +1
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
        trades.append({"r": float(r), "t": int(t[i]), "z": z, "bias": bias})
        used_day.add(dkey)
        funnel["n_trades"] += 1
        i += MAX_HOLD
    funnel["days_used"] = len(used_day)
    pnls = sim_r(trades)
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": "HYP-EURUSD-H1-BRENT-IMPORTER-TOT-001",
        "class": "brent_importer_terms_of_trade_structural",
        "symbol": "EURUSD",
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "a_priori": {
            "brent_z_abs": BRENT_Z_ABS,
            "lookback": BRENT_LOOKBACK,
            "thesis": "EUR_oil_importer_ToT",
            "bias_rule": "z>=+thr short EURUSD; z<=-thr long EURUSD",
            "lag": "observation+1d",
            "range_atr": RANGE_ATR,
            "body_atr": BODY_ATR,
            "close_frac": CLOSE_FRAC,
            "sl_atr": SL_ATR,
            "rr": RR,
            "max_hold": MAX_HOLD,
            "not_wti_usdcad_clone": True,
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def append_registry(objects: list[dict], receipt: str) -> None:
    lines = []
    for o in objects:
        state = "killed" if "KILL" in o["verdict"] else ("parked" if "PARK" in o["verdict"] else "probed")
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
            "lane": "ecb_brent_structural_20260715",
            "setup_type": o["hypothesis_id"],
            "symbol": o.get("symbol") or "EURUSD",
            "timeframe": o.get("tf") or "H1",
            "window": "2021.01.01-2025.12.31",
            "model": None,
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_ECB_BRENT_OFFLINE_PROBES.md",
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
        """# De-dup clearance — ECB BS primary + Brent importer ToT

Status: `INTAKE_CLEARED / INDEPENDENT` (a priori)

| Object | Vs killed shelf |
|---|---|
| O1 EURUSD ECB-expand displace long | ≠ `HYP-RR2-WALCL-QT-ALLOW-GATE-001` (Fed WALCL RR2 keep/skip); ≠ PD-primary USDJPY/EURJPY; ≠ London-overlap MULTISYM |
| O2 EURUSD ECB-contract displace short | ≠ O1; ≠ WALCL sign densify; ≠ VIX risk-off |
| O3 EURUSD Brent importer ToT | ≠ `HYP-USDCAD-H1-WTI-TOT-CONT-001` (WTI+CAD producer); Brent≠WTI; EUR importer≠CAD producer |

Banned densify remains: WALCL wow sign · WTI z/USDCAD · PD/MMF/6J · PD-primary ATR/RR ·
HY/MOVE/DTWEX VIX siblings · Wave1–9 · COT size+|z| · invent spreads · Phase-0 without clear.
""",
        encoding="utf-8",
    )

    rows = []
    for o in objects:
        m = o["metrics"]
        hc = o["haircuts"]
        rows.append(
            f"| `{o['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{(hc.get('x1_5') or {}).get('pf')} | {o['verdict']} | {','.join(o.get('kill_notes') or [])} |"
        )

    status = payload["campaign_status"]
    OUT_MD.write_text(
        f"""# Offline probes — ECB BS primary + Brent importer ToT

Date: 2026-07-15  
Status: `{status}`  
ECB panel SHA: `{payload["panel_sha256"]["ecb"]}`  
Brent panel SHA: `{payload["panel_sha256"]["brent"]}`  
Receipt: `{payload["receipt_sha256"]}`

## Objects

| ID | N | PF | tpw | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Joint screen

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 → PROBE_SURVIVOR → Model 0 only.

## Cost

Cost surface still **GAP** (no invent). Offline stress uses +$12 proxy only.
""",
        encoding="utf-8",
    )

    survivors = [o for o in objects if o["verdict"] == "PROBE_SURVIVOR"]
    kill_table = "\n".join(
        f"| `{o['hypothesis_id']}` | **{o['verdict']}** |" for o in objects
    )
    OUT_CLOSE.write_text(
        f"""# Session closeout — ECB BS + Brent importer ToT

Date: 2026-07-15  
Status: `{status}`  
Lane: single checkout; no-Git

## Acquisition

FRED `ECBASSETSW` (lag +5d) + `DCOILBRENTEU` (lag +1d).  
JPNASSETS monthly kept **RAW_ONLY** (too coarse; not probed).  
Manifest: `v8_exogenous/manifests/20260715_ECB_BRENT_ACQUISITION_V1.json`

## Probes

| ID | Verdict |
|---|---|
{kill_table}

Receipt: `{payload["receipt_sha256"]}`  
Artifacts: `preflight/20260715_ECB_BRENT_OFFLINE_PROBES.json`

## Model 0

{"AUTHORIZED for: " + ", ".join(o["hypothesis_id"] for o in survivors) if survivors else "Withheld (no PROBE_SURVIVOR)."}

## Next autonomous EV

1. Do **not** densify ECB wow sign / Brent z / displace ATR/RR.
2. Keep Real QFSI accumulate for cost frontier (still GAP).
3. Next object outside Wave1–9 / dichotomy / COT / WTI / WALCL / PD-MMF-6J /
   PD-primary / ECB-Brent killboard — or Owner PIT/vendor surface.

Best shelf unchanged: RR2 `20260714_194548`. Phase-0 still BLOCKED. GOAL unmet.
""",
        encoding="utf-8",
    )

    OUT_VN.write_text(
        f"""# VN action brief — ECB + Brent session

## Kết quả
- Acquire hợp lệ: ECB balance sheet (`ECBASSETSW`, ngoài WALCL) + Brent (`DCOILBRENTEU`, ngoài WTI-USDCAD).
- Offline probe 3/3: xem bảng closeout. Status: `{status}`.
- Model 0: {"có survivor — chạy Model 0" if survivors else "không — withheld"}.
- Cost surface: vẫn **GAP** (không invent spread).

## Không làm
- Densify ECB WoW / Brent z / ATR/RR.
- Revive PD/MMF/6J / WALCL / WTI-USDCAD / Wave1–9 / COT.
- Phase-0 khi chưa clear.

## Next
- Object mới ngoài killboard, hoặc chờ QFSI multi-year cost.
- Shelf tốt nhất vẫn RR2 `194548`.
""",
        encoding="utf-8",
    )

    acq = json.loads(ACQ_MANIFEST.read_text(encoding="utf-8")) if ACQ_MANIFEST.is_file() else {}
    OUT_ACQ.write_text(
        f"""# Acquisition readout — ECBASSETSW + Brent

Manifest: `v8_exogenous/manifests/20260715_ECB_BRENT_ACQUISITION_V1.json`  
Contract: `v8_exogenous/contracts/20260715_ECB_BRENT_AVAILABLE_AT_UTC_CONTRACT_V1.json`

## OK

- FRED `ECBASSETSW` weekly Eurosystem assets → panel lag +5d + `wow_pct`
  SHA `{payload["panel_sha256"]["ecb"]}`
- FRED `DCOILBRENTEU` daily Brent → panel lag +1d
  SHA `{payload["panel_sha256"]["brent"]}`

## RAW_ONLY

- FRED `JPNASSETS` monthly BOJ assets — too coarse for this H1 campaign; not probed.

## Explicit non-use

- Not WALCL twin gate on RR2.
- Not WTI-USDCAD ToT clone.
- Not HY/MOVE/DTWEX VIX sibling.
- DTWEX not acquired this pass (VIX-sibling ban still binds for risk-off shopping).

Acquired_at: `{acq.get("created_at_utc", "see manifest")}`
""",
        encoding="utf-8",
    )


def main() -> None:
    assert ECB_PANEL.is_file(), "run acquire_freeze_ecb_brent_v1.py first"
    assert BRENT_PANEL.is_file(), "run acquire_freeze_ecb_brent_v1.py first"
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init fail: {mt5.last_error()}")
    try:
        h1 = load_h1("EURUSD")
        ecb = build_ecb_expand_lookup()
        brent_z = build_brent_z_lookup()
        o1 = probe_ecb_displace(
            h1,
            ecb,
            hypothesis_id="HYP-EURUSD-H1-ECB-BS-EXPAND-DISPLACE-001",
            require_expand=True,
        )
        o2 = probe_ecb_displace(
            h1,
            ecb,
            hypothesis_id="HYP-EURUSD-H1-ECB-BS-CONTRACT-DISPLACE-001",
            require_expand=False,
        )
        o3 = probe_brent_importer_tot(h1, brent_z)
        objects = [o1, o2, o3]
        survivors = [o for o in objects if o["verdict"] == "PROBE_SURVIVOR"]
        status = (
            "OFFLINE_HAS_SURVIVOR / MODEL0_ARMED"
            if survivors
            else "OFFLINE_ALL_KILL / NO_MODEL0"
        )
        payload = {
            "schema": "ecb_brent_offline_probes.v1",
            "created_at_utc": utc_now(),
            "campaign_status": status,
            "window": {"from": FROM.isoformat(), "to": TO.isoformat(), "elapsed_weeks": round(ELAPSED_WEEKS, 4)},
            "cost_proxy_usd_per_trade": COST12,
            "panel_sha256": {
                "ecb": sha256_file(ECB_PANEL),
                "brent": sha256_file(BRENT_PANEL),
            },
            "contract_sha256": sha256_file(CONTRACT) if CONTRACT.is_file() else None,
            "acquisition_manifest_sha256": sha256_file(ACQ_MANIFEST) if ACQ_MANIFEST.is_file() else None,
            "objects": objects,
            "survivors": [o["hypothesis_id"] for o in survivors],
            "model0": "AUTHORIZED_IF_SURVIVOR" if survivors else "WITHHELD",
            "banned": [
                "WALCL_sign_retune",
                "WTI_USDCAD_retune",
                "PD_MMF_6J_densify",
                "PD_primary_displace_retune",
                "HY_MOVE_DTWEX_vix_sibling",
                "Wave1_9_clones",
                "invent_spreads",
                "Phase0_without_clear",
            ],
            "best_shelf": "RR2_20260714_194548",
            "cost_surface": "GAP_UNCHANGED",
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
                    "summary": [
                        {
                            "id": o["hypothesis_id"],
                            "n": o["metrics"]["n"],
                            "pf": o["metrics"]["pf"],
                            "tpw": o["metrics"]["tpw"],
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
