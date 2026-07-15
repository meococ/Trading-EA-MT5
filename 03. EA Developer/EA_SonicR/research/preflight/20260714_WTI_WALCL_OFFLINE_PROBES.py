#!/usr/bin/env python3
"""Post size-budget campaign — WTI ToT USDCAD + WALCL QT gate on RR2.

A priori frozen (do not mine):
  O1 HYP-USDCAD-H1-WTI-TOT-CONT-001
  O2 HYP-RR2-WALCL-QT-ALLOW-GATE-001

Joint screen: N, PF, tpw, +$12 x1.5. Model 0 only if PROBE_SURVIVOR.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
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
WTI_PANEL = EXO / "panels" / "fred_wti_dcoilwtico_d1_v1.csv"
WALCL_PANEL = EXO / "panels" / "fred_walcl_wow_w1_v1.csv"
RR2_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SilverBullet" / "20260714_194548"

OUT_JSON = PRE / "20260714_WTI_WALCL_OFFLINE_PROBES.json"
OUT_MD = READ / "20260714_WTI_WALCL_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260714_WTI_WALCL_DEDUP_CLEARANCE.md"
OUT_MEMO = READ / "20260714_POST_SIZEBUDGET_LEAD_MEMO.md"
OUT_CLOSE = READ / "20260714_WTI_WALCL_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260714_WTI_WALCL_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK = 0.005
COST12 = 12.0

# A priori — do not mine
WTI_Z_ABS = 0.75
WTI_LOOKBACK = 60
WTI_MIN_OBS = 40
BODY_ATR = 0.50
RANGE_ATR = 1.00
SL_ATR = 1.20
RR = 2.0
MAX_HOLD = 12  # H1 bars
# WALCL: allow RR2 trade only when latest available WoW change is negative (QT)
# Fail-closed if no WALCL available.


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def build_wti_z_lookup() -> dict[date, float]:
    rows = []
    with WTI_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            obs = date.fromisoformat(row["observation_date"])
            avail = date.fromisoformat(row["available_at_utc"][:10])
            val = float(row["wti_usd"])
            rows.append((obs, avail, val))
    rows.sort(key=lambda x: x[0])
    z_by_avail: list[tuple[date, float]] = []
    hist: list[float] = []
    for obs, avail, val in rows:
        hist.append(val)
        if len(hist) < WTI_MIN_OBS:
            continue
        window = hist[-WTI_LOOKBACK:]
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


def build_walcl_qt_lookup() -> dict[date, bool]:
    """True = QT (wow_pct < 0) allow; False = expand skip; missing = None."""
    events: list[tuple[date, float]] = []
    with WALCL_PANEL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            wow = (row.get("wow_pct") or "").strip()
            if not wow:
                continue
            avail = date.fromisoformat(row["available_at_utc"][:10])
            events.append((avail, float(wow)))
    events.sort(key=lambda x: x[0])
    out: dict[date, bool] = {}
    last = None
    idx = 0
    day = FROM.date()
    end = TO.date()
    while day <= end:
        while idx < len(events) and events[idx][0] <= day:
            last = events[idx][1] < 0.0
            idx += 1
        if last is not None:
            out[day] = last
        day += timedelta(days=1)
    return out


def probe_oil_tot(h1: dict, wti_z: dict[date, float]) -> dict[str, Any]:
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
        z = wti_z.get(d)
        if z is None or abs(z) < WTI_Z_ABS:
            i += 1
            continue
        # oil up → CAD strength → short USDCAD; oil down → long USDCAD
        bias = -1 if z >= WTI_Z_ABS else +1
        funnel["n_bias"] += 1
        rng = h[i] - l[i]
        body = abs(c[i] - o[i])
        if rng < RANGE_ATR * atr[i] or body < BODY_ATR * atr[i]:
            i += 1
            continue
        # close location confirms direction
        if bias > 0:
            if c[i] < l[i] + 0.60 * rng:
                i += 1
                continue
        else:
            if c[i] > h[i] - 0.60 * rng:
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
    verdict, notes = joint_verdict(m, hc, baseline_x15=None)
    return {
        "hypothesis_id": "HYP-USDCAD-H1-WTI-TOT-CONT-001",
        "class": "commodity_terms_of_trade_structural",
        "symbol": "USDCAD",
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "a_priori": {
            "wti_z_abs": WTI_Z_ABS,
            "lookback": WTI_LOOKBACK,
            "body_atr": BODY_ATR,
            "range_atr": RANGE_ATR,
            "sl_atr": SL_ATR,
            "rr": RR,
            "max_hold": MAX_HOLD,
            "lag": "observation+1d",
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


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


def load_rr2_closed() -> list[dict]:
    path = find_trades_csv(RR2_DIR)
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
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
                ot = parse_dt(op.get("event_time") or "")
                ct = parse_dt(row.get("event_time") or "")
                if ot is None or not (FROM <= ot <= TO):
                    continue
                closed.append({"open_time": ot, "close_time": ct, "pnl": pnl})
    return closed


def probe_walcl_gate(trades: list[dict], qt_allow: dict[date, bool]) -> dict[str, Any]:
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    base_x15 = (base_hc.get("x1_5") or {}).get("pf")

    kept = []
    skipped = 0
    no_data = 0
    for t in trades:
        d = t["open_time"].date()
        allow = qt_allow.get(d)
        if allow is None:
            no_data += 1
            skipped += 1
            continue
        if allow:
            kept.append(t["pnl"])
        else:
            skipped += 1
    m = metrics(kept)
    hc = haircuts(kept)
    verdict, notes = joint_verdict(m, hc, baseline_x15=base_x15)
    return {
        "hypothesis_id": "HYP-RR2-WALCL-QT-ALLOW-GATE-001",
        "class": "fed_liquidity_qt_allow_gate",
        "sleeve": "RR2_194548",
        "funnel": {
            "n_baseline": len(trades),
            "n_kept": len(kept),
            "n_skipped": skipped,
            "n_no_walcl": no_data,
            "keep_frac": round(len(kept) / len(trades), 4) if trades else 0.0,
        },
        "baseline": {"metrics": base_m, "haircuts": base_hc},
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "a_priori": {
            "rule": "allow_only_when_latest_available_WALCL_wow_pct < 0 (QT)",
            "lag": "observation+2d",
            "fail_closed_missing": True,
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "stress_lift_vs_baseline_x15": None
        if base_x15 is None
        else round(((hc.get("x1_5") or {}).get("pf") or 0.0) - base_x15, 4),
    }


def write_docs(payload: dict) -> None:
    o1 = payload["objects"][0]
    o2 = payload["objects"][1]
    OUT_MEMO.write_text(
        f"""# Lead memo — post COT size-budget / Wave7 empty

Date: 2026-07-14  
Status: `SOLO_LEAD / OFFLINE_PROBE_AUTHORIZED`  
Lane: single checkout; no-Git; Real/QFSI parallel hygiene only

## Kill shelf (binding)

Banned: Wave1–9 clones · dichotomy D1–D3 retunes · COT |z| + size-budget ·
MaxKZ/RR densify · Phase-0 compose without clear · HY OAS/MOVE/DTWEX as VIX
siblings · T10YIE-as-RR2-zgate (twin of D2).

## Legal object classes remaining

| Class | Tonight use |
|---|---|
| Newly acquired lagged exo as **structural driver** (not bond/COT twin) | O1 WTI→USDCAD ToT |
| Newly acquired lagged exo as **GATE/SIZE/ROUTE** on parked sleeve (≠ yield-z) | O2 WALCL QT allow-gate |
| Cost-resilient architecture ≠ BE@1R / MaxKZ partial | deferred |
| Multi-year session×symbol cost ROUTE | **GAP** (QFSI 1-day) |
| True FX forwards / signed flow | not on disk |

## Shortlist (executed)

| ID | Mechanism | De-dup |
|---|---|---|
| `HYP-USDCAD-H1-WTI-TOT-CONT-001` | Lagged WTI z shock → CAD ToT → USDCAD H1 displace cont | ≠ VIX risk-off; ≠ Wave7; ≠ COT |
| `HYP-RR2-WALCL-QT-ALLOW-GATE-001` | Fed assets WoW&lt;0 (QT) allow-gate on frozen RR2 | ≠ D2 USJP yield-z; ≠ COT size |

## Decision

Probe both offline with joint thick+cadence+$12×1.5. Model 0 only if
`PROBE_SURVIVOR`. Best shelf RR2 `194548` until survivor.
""",
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        f"""# De-dup clearance — WTI ToT + WALCL QT gate

Date: 2026-07-14  
Status: `INTAKE_CLEARED / INDEPENDENT`

| Candidate | vs banned / killed | Clearance |
|---|---|---|
| O1 WTI→USDCAD | Wave1–9 price geometry; VIX→USDJPY; equity−bond; COT FinFut JPY; carry | **CLEARED** — commodity ToT on USDCAD |
| O2 WALCL QT gate | D2 USJP yield-z gate; COT |z|/size; USBILL directional | **CLEARED** — Fed liquidity WoW sign gate, not rate z |
| T10YIE zgate | D2 twin | **DENIED** this session |
| HY OAS / MOVE / DTWEX | VIX sibling | **DENIED** |

Panel SHA:
- WTI `{payload["panel_sha"]["wti"]}`
- WALCL `{payload["panel_sha"]["walcl"]}`

Joint survivor bar: PF&gt;1.20 ∧ tpw∈[1.5,6] ∧ x1.5≥1.15 ∧ (gates: stress lift vs baseline).
Model 0 withheld unless PROBE_SURVIVOR.
""",
        encoding="utf-8",
    )

    def row(o: dict) -> str:
        m = o["metrics"]
        hc = o["haircuts"]
        return (
            f"| `{o['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{(hc.get('x1_5') or {}).get('pf')} | {o['verdict']} | {','.join(o['kill_notes']) or '—'} |"
        )

    OUT_MD.write_text(
        f"""# Offline probes — WTI ToT + WALCL QT gate

Date: {payload["created_at_utc"]}  
Status: `{payload["campaign_status"]}`  
Receipt SHA: `{payload["receipt_sha256"]}`

## Results

| ID | N | PF | tpw | x1.5 | Verdict | Notes |
|---|---:|---:|---:|---:|---|---|
{row(o1)}
{row(o2)}

Baseline RR2 (O2 ungated): N={o2['baseline']['metrics']['n']} PF={o2['baseline']['metrics']['pf']}
x1.5={o2['baseline']['haircuts']['x1_5']['pf']}

## Funnel

### O1
```json
{json.dumps(o1['funnel'], indent=2)}
```

### O2
```json
{json.dumps(o2['funnel'], indent=2)}
```

## Model 0

{"AUTHORIZED for survivor(s)." if payload.get("any_survivor") else "WITHHELD — zero PROBE_SURVIVOR."}

## Non-rescues

No WTI z densify · no WALCL threshold mine · no T10YIE twin · no MaxKZ/RR densify.
""",
        encoding="utf-8",
    )

    OUT_CLOSE.write_text(
        f"""# Session closeout — WTI/WALCL post size-budget EV

Date: 2026-07-14  
Status: `{payload["campaign_status"]}`  
Lane: single checkout; no-Git

## Executed

1. Solo lead memo: legal classes under kill shelf.
2. Acquired+froze FRED `DCOILWTICO` + `WALCL` (T10YIE raw only — no gate).
3. De-dup cleared two new objects.
4. Offline joint probe (thick+cadence+$12×1.5).

| ID | Verdict |
|---|---|
| `HYP-USDCAD-H1-WTI-TOT-CONT-001` | **{o1['verdict']}** |
| `HYP-RR2-WALCL-QT-ALLOW-GATE-001` | **{o2['verdict']}** |

Receipt: `{payload["receipt_sha256"]}`  
Artifacts: `preflight/20260714_WTI_WALCL_OFFLINE_PROBES.json`

## Model 0

{"Run survivor only." if payload.get("any_survivor") else "Withheld (no PROBE_SURVIVOR)."}

## Next autonomous EV

1. Do not densify WTI z / WALCL sign / USDCAD displace params.
2. Keep Real QFSI accumulate for session×symbol cost surface (still GAP).
3. Next object must be outside Wave1–9 / dichotomy / COT size+|z| / WTI-ToT /
   WALCL-QT — prefer true forwards or signed flow if Owner can source.

Best shelf unchanged: RR2 `20260714_194548`. Phase-0 still BLOCKED. GOAL unmet.
""",
        encoding="utf-8",
    )

    OUT_VN.write_text(
        f"""# Brief hành động (VN) — sau size-budget / WTI+WALCL

## Kết quả
- O1 Oil→USDCAD ToT: **{o1['verdict']}** (N={o1['metrics']['n']}, PF={o1['metrics']['pf']}, tpw={o1['metrics']['tpw']}, x1.5={(o1['haircuts'].get('x1_5') or {}).get('pf')})
- O2 WALCL QT gate trên RR2: **{o2['verdict']}** (N={o2['metrics']['n']}, PF={o2['metrics']['pf']}, x1.5={(o2['haircuts'].get('x1_5') or {}).get('pf')}; lift={o2.get('stress_lift_vs_baseline_x15')})
- Model 0: {"chỉ survivor" if payload.get("any_survivor") else "**không chạy** (0 survivor)"}

## Việc làm / không làm
- Không densify WTI/WALCL/MaxKZ/RR; không Phase-0.
- Giữ Real chỉ để tích lũy cost (không phải headline discovery).
- Shelf tốt nhất vẫn RR2 `194548`. GOAL chưa đạt.

## Next
Object mới ngoài Wave/dichotomy/COT/WTI/WALCL — hoặc acquire forwards/flow hợp pháp.
""",
        encoding="utf-8",
    )


def append_registry(objects: list[dict], receipt: str) -> None:
    lines = []
    for o in objects:
        rec = {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": o["hypothesis_id"],
            "state": "killed" if "KILL" in o["verdict"] else ("parked" if "PARK" in o["verdict"] else "probed"),
            "verdict": o["verdict"],
            "reason": ",".join(o.get("kill_notes") or []) or o["verdict"],
            "updated_at": "2026-07-14",
            "feature_family": o.get("class"),
            "lane": "post_sizebudget_wti_walcl_20260714",
            "setup_type": o["hypothesis_id"],
            "symbol": o.get("symbol") or "USDJPY",
            "timeframe": o.get("tf") or "M15",
            "window": "2021.01.01-2025.12.31",
            "model": None,
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_WTI_WALCL_OFFLINE_PROBES.md",
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


def main() -> None:
    assert WTI_PANEL.is_file() and WALCL_PANEL.is_file(), "run acquire_freeze first"
    if not mt5.initialize():
        raise SystemExit(f"MT5_INIT_FAIL:{mt5.last_error()}")
    try:
        usdcad = load_h1("USDCAD")
        wti_z = build_wti_z_lookup()
        qt = build_walcl_qt_lookup()
        rr2 = load_rr2_closed()
        o1 = probe_oil_tot(usdcad, wti_z)
        o2 = probe_walcl_gate(rr2, qt)
    finally:
        mt5.shutdown()

    panel_sha = {
        "wti": sha256_file(WTI_PANEL),
        "walcl": sha256_file(WALCL_PANEL),
    }
    any_surv = o1["verdict"] == "PROBE_SURVIVOR" or o2["verdict"] == "PROBE_SURVIVOR"
    status = (
        "PROBE_SURVIVOR_PRESENT"
        if any_surv
        else "OFFLINE_BOTH_KILL / NO_MODEL0"
    )
    payload = {
        "schema": "wti_walcl_offline_probes.v1",
        "created_at_utc": utc_now(),
        "campaign_status": status,
        "panel_sha": panel_sha,
        "objects": [o1, o2],
        "any_survivor": any_surv,
        "best_shelf": "20260714_194548",
        "model0": "WITHHELD" if not any_surv else "AUTHORIZED_FOR_SURVIVOR",
    }
    raw = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    receipt = sha256_bytes(raw.encode("utf-8"))
    payload["receipt_sha256"] = receipt
    raw = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    # re-hash with receipt field included
    receipt = sha256_bytes(raw.encode("utf-8"))
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_docs(payload)
    append_registry([o1, o2], receipt)
    print(json.dumps({
        "status": status,
        "receipt": receipt,
        "o1": {"verdict": o1["verdict"], "m": o1["metrics"], "x15": o1["haircuts"]["x1_5"]["pf"]},
        "o2": {"verdict": o2["verdict"], "m": o2["metrics"], "x15": o2["haircuts"]["x1_5"]["pf"], "lift": o2.get("stress_lift_vs_baseline_x15")},
    }, indent=2))


if __name__ == "__main__":
    main()
