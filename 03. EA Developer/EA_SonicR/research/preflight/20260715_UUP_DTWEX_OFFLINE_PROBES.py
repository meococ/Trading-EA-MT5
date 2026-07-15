#!/usr/bin/env python3
"""Dollar TWI UUP + DTWEXBGS — offline probes (HARD PIVOT W27 exo).

A priori frozen (do not mine / do not densify):
  O1 HYP-AUDUSD-H1-UUP-TWUSD-STRENGTH-001
  O2 HYP-AUDUSD-H1-DTWEXBGS-TWI-STRENGTH-001  (if panel present)
  O3 HYP-BOOK-UUP-DTWEX-APRIORI-001            (if both present; else skip)

Surface: Yahoo UUP TW-USD ETF + FRED DTWEXBGS broad-goods TWI (lag +1d).
Owner W27: promote W26 UUP spare; acquire DTWEX-style TWI.
FORBIDDEN: commodity→AUD ToT densify · credit-MOVE densify · VIXCLS retune.

USD strength ↑ → short AUDUSD (invert). Joint +$12 screen. Model 0 only survivors.
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
UUP_PANEL = EXO / "panels" / "yahoo_uup_twusd_d1_v1.csv"
DTWEX_PANEL = EXO / "panels" / "fred_dtwexbgs_d1_v1.csv"
ACQ_MANIFEST = EXO / "manifests" / "20260715_UUP_DTWEX_ACQUISITION_V1.json"
CONTRACT = EXO / "contracts" / "20260715_UUP_DTWEX_AVAILABLE_AT_UTC_CONTRACT_V1.json"

OUT_JSON = PRE / "20260715_UUP_DTWEX_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_UUP_DTWEX_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_UUP_DTWEX_DEDUP_CLEARANCE.md"
OUT_CLOSE = READ / "20260715_UUP_DTWEX_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_UUP_DTWEX_VN_ACTION_BRIEF.md"
OUT_ACQ = READ / "20260715_UUP_DTWEX_ACQUISITION_READOUT.md"
OUT_DESIGN = READ / "20260715_UUP_DTWEX_DESIGN_MEMO.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK = 0.005
COST12 = 12.0

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


def probe_z_cont(
    h1: dict,
    z_lookup: dict[date, float],
    *,
    hypothesis_id: str,
    class_name: str,
    thesis: str,
    value_name: str,
    invert: bool = True,
    bias_rule: str = "",
) -> dict[str, Any]:
    """USD-strength invert: high z → short AUDUSD."""
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
        raw_sign = +1 if z >= Z_ABS else -1
        bias = -raw_sign if invert else raw_sign
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
    default_rule = (
        "z>=+thr short AUDUSD; z<=-thr long AUDUSD (USD-strength invert)"
        if invert
        else "z>=+thr long AUDUSD; z<=-thr short AUDUSD"
    )
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
            "bias_rule": bias_rule or default_rule,
            "invert": invert,
            "lag": "observation+1d (frozen panel available_at)",
            "range_atr": RANGE_ATR,
            "body_atr": BODY_ATR,
            "close_frac": CLOSE_FRAC,
            "sl_atr": SL_ATR,
            "rr": RR,
            "max_hold": MAX_HOLD,
            "not_commodity_tot": True,
            "not_credit_move_densify": True,
            "not_vixcls_retune": True,
            "not_w1_w26_ohlc": True,
            "owner_authorized_w27": True,
        },
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def probe_book(o1: dict, o2: dict) -> dict[str, Any]:
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
        "hypothesis_id": "HYP-BOOK-UUP-DTWEX-APRIORI-001",
        "class": "nested_uup_dtwex_apriori_book",
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
            "lane": "uup_dtwex_exo_w27_20260715",
            "setup_type": o["hypothesis_id"],
            "symbol": o.get("symbol") or "AUDUSD",
            "timeframe": o.get("tf") or "H1",
            "window": "2021.01.01-2025.12.31",
            "model": None,
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_UUP_DTWEX_OFFLINE_PROBES.md",
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
    has_dtwex = "dtwex" in (payload.get("panel_sha256") or {})
    OUT_DEDUP.write_text(
        f"""# De-dup clearance — UUP TW-USD + DTWEXBGS TWI (W27)

Status: `INTAKE_CLEARED / INDEPENDENT` (a priori; Owner-authorized W27)

| Object | Vs killed shelf |
|---|---|
| O1 AUDUSD UUP TW-USD strength | ≠ commodity ToT; ≠ HYG/LQD credit densify; ≠ MOVE densify; ≠ VIXCLS; W26 spare promoted |
| O2 AUDUSD DTWEXBGS broad-goods TWI | {"present; ≠ VIX sibling shopping retune; Owner dollar-TWI reopen" if has_dtwex else "unavailable this pass"} |
| O3 nested book UUP∪DTWEX | a priori union; not post-hoc sleeve mine |

Banned densify: UUP/DTWEX z thr · displace ATR/RR · commodity→AUD ToT · credit-MOVE · VIXCLS · W1–W26 / R10–R31 / FVG.
""",
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        f"""# Design memo — UUP TW-USD + DTWEXBGS dollar TWI (W27 exo)

## Surface acquisition

1. **Selected:** Yahoo `UUP` (W26 spare → W27 primary) + FRED `DTWEXBGS`
   (broad-goods dollar TWI). SHA-frozen panels lag `observation_date + 1d`.
2. DTWEX status: {"ACQUIRED" if has_dtwex else "UNAVAILABLE this pass"}.
3. Outside killboard: W26 credit-MOVE · W23–W25 commodity ToT · OHLC densify.

## Mechanisms (a priori)

1. **UUP USD-strength invert:** UUP↑ → USD strength → short AUDUSD H1 displace
   (z≥+0.75); UUP↓ → long AUDUSD.
2. **DTWEXBGS TWI invert:** same USD-strength → AUDUSD short on high z.
3. **Nested book:** day-union prefer larger |z| (when both present).

## Explicit non-twins

Not HYG/LQD / MOVE densify, not NG/ZW/TIO/Cu/Gold/oil ToT, not VIXCLS,
not killed FRED/COT boards, not OHLC HARD PIVOT densify.
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
    panel_lines = "\n".join(
        f"- `{k}`: `{v}`" for k, v in (payload.get("panel_sha256") or {}).items()
    )
    OUT_MD.write_text(
        f"""# Offline probes — UUP TW-USD + DTWEXBGS dollar TWI

Date: 2026-07-15  
Status: `{status}`  
Panels:
{panel_lines}
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
    next_ev = (
        "Model 0 for survivors."
        if survivors
        else (
            "If ALL_KILL → ONE SB/RR2 quality-thickness rebuild child "
            "(not FVG densify, not exit densify) offline first."
        )
    )
    OUT_CLOSE.write_text(
        f"""# Session closeout — UUP + DTWEX dollar TWI exo (W27)

Date: 2026-07-15  
Status: `{status}`  
Lane: single checkout; no-Git; ChatGPT login wall is parallel Owner action only

## Acquisition

Yahoo UUP TW-USD + FRED DTWEXBGS (lag +1d).  
Manifest: `v8_exogenous/manifests/20260715_UUP_DTWEX_ACQUISITION_V1.json`

## Probes

| ID | Verdict |
|---|---|
{kill_table}

Receipt: `{payload["receipt_sha256"]}`  
Artifacts: `preflight/20260715_UUP_DTWEX_OFFLINE_PROBES.json`

## Model 0

{"AUTHORIZED for: " + ", ".join(o["hypothesis_id"] for o in survivors) if survivors else "Withheld (no PROBE_SURVIVOR)."}

## Next autonomous EV

1. Do **not** densify UUP/DTWEX z / displace ATR/RR.
2. Do **not** densify commodity→AUD ToT or credit-MOVE (HYG/LQD/MOVE).
3. Keep R-series / W1–W26 densify paused.
4. Keep Real QFSI accumulate for cost frontier (still GAP).
5. {next_ev}

Best shelf unchanged: RR2 `20260714_194548` / clean book PF@$12=1.184. Phase-0 still BLOCKED. GOAL unmet.
""",
        encoding="utf-8",
    )

    OUT_VN.write_text(
        f"""# VN — UUP TW-USD + DTWEXBGS TWI (W27 exo) + cost note

## Surface
- Đã SHA-freeze: Yahoo UUP (W26 spare → primary) + FRED DTWEXBGS (lag +1d).
- DTWEX: {"OK" if has_dtwex else "UNAVAILABLE"}.
- CẤM densify commodity→AUD ToT và credit-MOVE (HYG/LQD/^MOVE).

## Probe
- Status: `{status}`.
- Model 0: {"có survivor — chạy Model 0" if survivors else "không — withheld"}.
- Cost: vẫn **GAP** (deals~11). Không invent.

## Không làm
- Densify UUP/DTWEX z / ATR/RR.
- Densify commodity ToT / credit-MOVE / VIXCLS / W1–W26 / R-series.
- Chờ ChatGPT login (Owner parallel only).

## Next
- {"Model 0 survivors." if survivors else "ALL_KILL → ONE SB/RR2 quality-thickness rebuild child (không FVG/exit densify), offline trước."}
- Best shelf RR2 `194548`; clean book PF@$12=1.184.
""",
        encoding="utf-8",
    )

    OUT_ACQ.write_text(
        f"""# Acquisition readout — UUP TW-USD + DTWEXBGS dollar TWI

Manifest: `v8_exogenous/manifests/20260715_UUP_DTWEX_ACQUISITION_V1.json`  
Contract: `v8_exogenous/contracts/20260715_UUP_DTWEX_AVAILABLE_AT_UTC_CONTRACT_V1.json`

## OK

- Yahoo UUP TW-USD ETF daily → panel lag +1d  
  SHA `{(payload.get("panel_sha256") or {}).get("uup")}`
- FRED DTWEXBGS broad-goods TWI → {"panel lag +1d SHA `" + str((payload.get("panel_sha256") or {}).get("dtwex")) + "`" if has_dtwex else "UNAVAILABLE"}

## Explicit non-use

- Not HYG/LQD credit or ^MOVE densify (W26 ALL_KILL frozen).
- Not NG/ZW/TIO/Cu/Gold/WTI/Brent commodity→AUD ToT densify.
- Not VIXCLS equity-vol densify retune.
- Not WALCL/ECB/MMF/G10 overnight / COT FRED densify.
""",
        encoding="utf-8",
    )


def main() -> None:
    assert UUP_PANEL.is_file(), "run acquire_freeze_uup_dtwex_v1.py first"
    has_dtwex = DTWEX_PANEL.is_file()
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init fail: {mt5.last_error()}")
    try:
        h1 = load_h1("AUDUSD")
        uup_z = build_z_lookup(UUP_PANEL, "uup_close")
        o1 = probe_z_cont(
            h1,
            uup_z,
            hypothesis_id="HYP-AUDUSD-H1-UUP-TWUSD-STRENGTH-001",
            class_name="uup_twusd_strength",
            thesis="UUP_TWUSD_ETF_AUD_USD_strength_invert",
            value_name="uup",
            invert=True,
        )
        objects_full = [o1]
        if has_dtwex:
            dtwex_z = build_z_lookup(DTWEX_PANEL, "dtwexbgs_close")
            o2 = probe_z_cont(
                h1,
                dtwex_z,
                hypothesis_id="HYP-AUDUSD-H1-DTWEXBGS-TWI-STRENGTH-001",
                class_name="dtwexbgs_twi_strength",
                thesis="DTWEXBGS_broad_goods_TWI_AUD_USD_strength_invert",
                value_name="dtwex",
                invert=True,
            )
            o3 = probe_book(o1, o2)
            objects_full.extend([o2, o3])
        objects = [strip_trades(o) for o in objects_full]
        survivors = [o for o in objects if o["verdict"] == "PROBE_SURVIVOR"]
        status = (
            "OFFLINE_HAS_SURVIVOR / MODEL0_ARMED"
            if survivors
            else "OFFLINE_ALL_KILL / NO_MODEL0"
        )
        panel_sha = {"uup": sha256_file(UUP_PANEL)}
        if has_dtwex:
            panel_sha["dtwex"] = sha256_file(DTWEX_PANEL)
        payload = {
            "schema": "uup_dtwex_offline_probes.v1",
            "created_at_utc": utc_now(),
            "campaign_status": status,
            "wave": "W27_UUP_DTWEX_DOLLAR_TWI_EXO",
            "window": {
                "from": FROM.isoformat(),
                "to": TO.isoformat(),
                "elapsed_weeks": round(ELAPSED_WEEKS, 4),
            },
            "cost_proxy_usd_per_trade": COST12,
            "panel_sha256": panel_sha,
            "contract_sha256": sha256_file(CONTRACT) if CONTRACT.is_file() else None,
            "acquisition_manifest_sha256": (
                sha256_file(ACQ_MANIFEST) if ACQ_MANIFEST.is_file() else None
            ),
            "dtwex_present": has_dtwex,
            "objects": objects,
            "survivors": [o["hypothesis_id"] for o in survivors],
            "model0": "AUTHORIZED_IF_SURVIVOR" if survivors else "WITHHELD",
            "banned": [
                "commodity_yahoo_aud_tot_clones_NG_ZW_TIO_Cu_Gold_WTI_Brent",
                "HYG_LQD_credit_z_densify",
                "MOVE_bondvol_z_densify",
                "VIXCLS_riskoff_retune",
                "SPX_DGS10_retune",
                "WALCL_ECB_MMF_G10_fred_retune",
                "COT_size_z_retune",
                "UUP_z_mine",
                "DTWEX_z_mine",
                "W1_W26_OHLC_densify",
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
                    "dtwex_present": has_dtwex,
                    "summary": [
                        {
                            "id": o["hypothesis_id"],
                            "n": o["metrics"]["n"],
                            "pf": o["metrics"]["pf"],
                            "tpw": o["metrics"]["tpw"],
                            "pf12": (o["haircuts"].get("x1") or {}).get("pf"),
                            "x15": (o["haircuts"].get("x1_5") or {}).get("pf"),
                            "verdict": o["verdict"],
                            "notes": o.get("kill_notes"),
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
