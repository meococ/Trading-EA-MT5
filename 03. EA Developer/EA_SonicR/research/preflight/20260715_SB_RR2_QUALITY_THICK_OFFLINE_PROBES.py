#!/usr/bin/env python3
"""W27 child — SB/RR2 quality-thickness rebuild after UUP/DTWEX ALL_KILL.

ONE child only (a priori; offline first; Model 0 only PROBE_SURVIVOR):
  HYP-SB-RR2-QUALITY-THICK-DISP-001

Thesis: parent RR2 `20260714_194548` has cadence in-band (tpw~3) but PF@$12
fails (~1.18). Lift $/trade by a priori *entry displacement quality* filter
on frozen parent trades — thicker impulse at entry M15 — WITHOUT:
  - FVG densify (size/wait/params untouched)
  - exit densify (BE/trail/TP/RR untouched; keep parent exits)
  - MaxKZ densify
  - commodity ToT / credit-MOVE densify

Quality gate (frozen before metrics):
  entry M15 body/ATR >= 0.55
  body/range >= 0.75
  close in trade-direction extreme third (>=0.67 of range)

+$12 research screen. ChatGPT login wall remains Owner-parallel only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
RUNS = ROOT / "02. AlphaFactory" / "runs"

STEM = "20260715_SB_RR2_QUALITY_THICK"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"

PARENT = {
    "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
    "run_id": "20260714_194548",
    "ea": "EA_SilverBullet",
}
CHILD_ID = "HYP-SB-RR2-QUALITY-THICK-DISP-001"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0

# A priori quality-thickness (do not retune after readout)
Q_BODY_ATR = 0.55
Q_BODY_RANGE = 0.75
Q_CLOSE_FRAC = 0.67


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = BASE_COST) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [float(p) - base * mult for p in pnls]
        p = pf_of(cut)
        out[key] = {
            "pf": None if not cut else round(float(p or 0.0), 4),
            "net": round(float(sum(cut)), 2) if cut else 0.0,
            "exp": round(float(sum(cut) / len(cut)), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = float(sum(pnls)) if pnls else 0.0
    return {
        "n": int(n),
        "pf": None if p is None else round(float(p), 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(float(n / WEEKS), 4) if WEEKS else None,
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


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def find_trades_csv(run_dir: Path) -> Path | None:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    return sorted(hits)[0] if hits else None


def load_closed_from_px6(path: Path) -> list[dict]:
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in (
                "1",
                "true",
                "True",
            ):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                entry = float(op.get("entry_price") or op.get("price") or 0)
                sl = float(op.get("sl") or op.get("initial_sl") or 0)
                vol = float(op.get("volume") or row.get("volume") or 0)
                side_raw = str(op.get("order_type") or "").upper()
                side = "sell" if "SELL" in side_raw else "buy"
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                px = entry if entry else 150.0
                risk_usd = (
                    (vol * 100_000.0 * risk_pts) / px
                    if px > 0 and vol > 0 and risk_pts > 0
                    else 0.0
                )
                ot = parse_dt(op.get("event_time") or "")
                xt = parse_dt(row.get("event_time") or "")
                if ot is None or xt is None:
                    continue
                if ot < FROM or ot > TO:
                    continue
                closed.append(
                    {
                        "entry_time": ot,
                        "exit_time": xt,
                        "side": side,
                        "pnl": pnl,
                        "symbol": str(op.get("symbol") or row.get("symbol") or ""),
                        "tag": str(op.get("tag") or ""),
                        "risk_usd": float(risk_usd),
                        "entry_price": entry,
                    }
                )
    return closed


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


def load_m15(symbol: str) -> dict:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"M15 rates fail {symbol}: {mt5.last_error()}")
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def bar_index_at(times: np.ndarray, ts: datetime) -> int | None:
    """Index of M15 bar with open_time <= entry (tester wall-clock as UTC epoch)."""
    epoch = int(
        datetime(
            ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second, tzinfo=timezone.utc
        ).timestamp()
    )
    i = int(np.searchsorted(times, epoch, side="right") - 1)
    if i < 0 or i >= len(times):
        return None
    return i


def quality_pass(m15: dict, atr: np.ndarray, trade: dict) -> tuple[bool, dict]:
    """Entry-bar displacement quality (closed-bar features of bar at entry)."""
    i = bar_index_at(m15["time"], trade["entry_time"])
    meta = {"bar_i": i, "pass": False}
    if i is None or i < 14:
        meta["reason"] = "no_bar"
        return False, meta
    # Prefer prior closed bar (i-1) for non-repaint: entry may be mid-bar on open fill.
    # Use max(i-1, 14) as signal bar available at fill.
    j = max(i - 1, 14)
    o, h, l, c = m15["open"][j], m15["high"][j], m15["low"][j], m15["close"][j]
    a = atr[j]
    if math.isnan(a) or a <= 0:
        meta["reason"] = "no_atr"
        return False, meta
    rng = h - l
    body = abs(c - o)
    if rng <= 0:
        meta["reason"] = "zero_range"
        return False, meta
    body_atr = body / a
    body_rng = body / rng
    side = trade["side"]
    if side == "buy":
        close_frac = (c - l) / rng
    else:
        close_frac = (h - c) / rng
    meta.update(
        {
            "body_atr": round(body_atr, 4),
            "body_range": round(body_rng, 4),
            "close_frac": round(close_frac, 4),
            "signal_bar_i": j,
        }
    )
    ok = (
        body_atr >= Q_BODY_ATR
        and body_rng >= Q_BODY_RANGE
        and close_frac >= Q_CLOSE_FRAC
    )
    meta["pass"] = ok
    if not ok:
        meta["reason"] = "quality_fail"
    return ok, meta


def result_block(hyp_id: str, family: str, trades: list[dict], extra: dict | None = None) -> dict:
    pnls = [float(t["pnl"]) for t in trades]
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    out = {
        "hypothesis_id": hyp_id,
        "family": family,
        "metrics": m,
        "haircuts": hc,
        "verdict": verdict,
        "kill_notes": notes,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "n_trades": len(trades),
    }
    if extra:
        out["contract"] = extra
    return out


def append_registry(obj: dict, receipt: str) -> None:
    state = "killed" if "KILL" in obj["verdict"] else "probed"
    if obj["verdict"] == "PROBE_SURVIVOR":
        state = "probe_survivor"
    rec = {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": obj["hypothesis_id"],
        "state": state,
        "verdict": obj["verdict"],
        "reason": ",".join(obj.get("kill_notes") or []) or obj["verdict"],
        "updated_at": "2026-07-15",
        "feature_family": obj.get("family"),
        "lane": "sb_rr2_quality_thick_w27_20260715",
        "setup_type": obj["hypothesis_id"],
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": None,
        "parent_hypothesis_id": PARENT["hypothesis_id"],
        "parent_run_id": PARENT["run_id"],
        "readout_path": f"03. EA Developer/EA_SonicR/research/readouts/{STEM}_OFFLINE_PROBES.md",
        "run_ids": [PARENT["run_id"]],
        "metrics": obj.get("metrics"),
        "validation": {
            "offline_probe": obj["verdict"],
            "kill_notes": obj.get("kill_notes"),
            "receipt_sha256": receipt,
        },
        "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
    }
    with REG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_docs(payload: dict, parent_blk: dict, child_blk: dict) -> None:
    status = payload["campaign_status"]
    OUT_FREEZE.write_text(
        f"""# A priori freeze — SB/RR2 quality-thickness (W27 child)

Child: `{CHILD_ID}`  
Parent: `{PARENT["hypothesis_id"]}` / run `{PARENT["run_id"]}`

## Problem
Clean/RR2 shelf PF@$12≈1.184 with tpw in [2,5]. Need thicker $/trade
without FVG densify or exit densify. UUP/DTWEX W27 exo ALL_KILL.

## Contract (frozen before metrics)
Keep parent RR2 trade iff entry-signal M15 (bar before fill) satisfies:
- body/ATR ≥ `{Q_BODY_ATR}`
- body/range ≥ `{Q_BODY_RANGE}`
- close in trade-direction extreme ≥ `{Q_CLOSE_FRAC}` of range

Exits = parent (unchanged). FVG params = parent (unchanged). MaxKZ = parent.

## Banned
FVG size/wait mine · BE/trail/TP/RR exit densify · MaxKZ densify ·
commodity ToT · credit-MOVE · UUP/DTWEX z mine · W1–W26 OHLC densify.
""",
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        f"""# De-dup — SB/RR2 quality-thickness (W27 child)

Status: `INTAKE_CLEARED / INDEPENDENT` (a priori child of frozen RR2)

| Object | Vs killed shelf |
|---|---|
| `{CHILD_ID}` | ≠ FVG densify; ≠ exit/MaxKZ densify; ≠ W22 sameday/seqslot arch; ≠ W9 thick-rare book; ≠ UUP/DTWEX exo; entry-quality thickness on frozen parent only |

Banned densify: FVG · exit · MaxKZ · commodity ToT · credit-MOVE · UUP/DTWEX z · W1–W26.
""",
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        f"""# Design — SB/RR2 quality-thickness rebuild child (W27)

## Why this child
W27 UUP+DTWEX dollar-TWI exo ALL_KILL. Owner mandate: if both fail, immediately
design ONE SB/RR2 quality-thickness rebuild aimed at lifting $/trade into
cadence band — offline first. Not FVG densify. Not exit densify.

## Mechanism
Parent RR2 already has structural SL + RR2 + MaxKZ2. Edge dies under +$12
because many fills are thin-impulse. Filter to thicker displacement quality
at the signal M15 bar (body/ATR, body/range, directional close) a priori.

## Explicit non-twins
Not W22 architecture monetization (sameday/seqslot). Not W9 dual-loc thick-rare.
Not FVG parameter retune. Not TP/BE exit ladder.
""",
        encoding="utf-8",
    )

    def row(o: dict) -> str:
        m, hc = o["metrics"], o["haircuts"]
        return (
            f"| `{o['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{(hc.get('x1') or {}).get('pf')} | {(hc.get('x1_5') or {}).get('pf')} | "
            f"{o['verdict']} | {','.join(o.get('kill_notes') or [])} |"
        )

    OUT_MD.write_text(
        f"""# Offline probes — SB/RR2 quality-thickness (W27 child)

Date: 2026-07-15  
Status: `{status}`  
Receipt: `{payload["receipt_sha256"]}`  
Parent run: `{PARENT["run_id"]}`

## Objects

| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |
|---|---|---|---|---|---|---|---|
{row(parent_blk)}
{row(child_blk)}

## Funnel
Parent N={payload["funnel"]["parent_n"]} → quality keep={payload["funnel"]["kept"]} drop={payload["funnel"]["dropped"]}  
Gate: body/ATR≥{Q_BODY_ATR}, body/range≥{Q_BODY_RANGE}, close_frac≥{Q_CLOSE_FRAC}

## Joint screen
N≥80 ∧ PF≥1.30 ∧ tpw∈[2,5] ∧ PF@$12≥1.30 ∧ x1.5≥1.25 → PROBE_SURVIVOR → Model 0 only.
""",
        encoding="utf-8",
    )

    survivors = [child_blk] if child_blk["verdict"] == "PROBE_SURVIVOR" else []
    OUT_CLOSE.write_text(
        f"""# Session closeout — SB/RR2 quality-thickness (W27 child)

Date: 2026-07-15  
Status: `{status}`

## Context
W27 UUP+DTWEX ALL_KILL → this ONE child offline.

## Probe
| ID | Verdict |
|---|---|
| `{CHILD_ID}` | **{child_blk["verdict"]}** |

Receipt: `{payload["receipt_sha256"]}`

## Model 0
{"AUTHORIZED: " + CHILD_ID if survivors else "Withheld (no PROBE_SURVIVOR)."}

## Next
1. Do **not** densify FVG / exit / MaxKZ / quality thresholds after readout.
2. Do **not** densify UUP/DTWEX or commodity ToT / credit-MOVE.
3. Keep QFSI cost accumulate (still GAP).
4. Next independent surface OR Owner ChatGPT login (parallel).

Best shelf RR2 `194548` / clean PF@$12=1.184. GOAL unmet.
""",
        encoding="utf-8",
    )

    OUT_VN.write_text(
        f"""# VN — SB/RR2 quality-thickness (W27 child) sau UUP/DTWEX ALL_KILL

## Bối cảnh
- W27 UUP + DTWEXBGS: ALL_KILL, không Model 0.
- Child duy nhất: `{CHILD_ID}` — lọc chất lượng displacement entry trên RR2 parent (không FVG densify, không exit densify).

## Kết quả
- Status: `{status}`.
- Child: N={child_blk["metrics"]["n"]} PF={child_blk["metrics"]["pf"]} tpw={child_blk["metrics"]["tpw"]} PF@$12={(child_blk["haircuts"].get("x1") or {}).get("pf")} → **{child_blk["verdict"]}**.
- Model 0: {"có — chạy Model 0" if survivors else "không — withheld"}.

## Không làm
- Densify FVG / exit / MaxKZ / ngưỡng quality sau readout.
- Densify UUP/DTWEX / commodity ToT / credit-MOVE.
- Chờ ChatGPT (Owner parallel).

## Next
- Surface độc lập mới hoặc QFSI deals / Owner login.
- Best shelf RR2 `194548`; clean PF@$12=1.184.
""",
        encoding="utf-8",
    )


def main() -> None:
    run_dir = RUNS / PARENT["ea"] / PARENT["run_id"]
    csv_path = find_trades_csv(run_dir)
    assert csv_path is not None, f"missing PX6 trades under {run_dir}"
    parent_trades = load_closed_from_px6(csv_path)
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init fail: {mt5.last_error()}")
    try:
        # Parent RR2 is USDJPY
        m15 = load_m15("USDJPY")
        atr = atr14(m15["high"], m15["low"], m15["close"])
        kept: list[dict] = []
        dropped = 0
        no_bar = 0
        for t in parent_trades:
            ok, meta = quality_pass(m15, atr, t)
            t["quality"] = meta
            if ok:
                kept.append(t)
            else:
                dropped += 1
                if meta.get("reason") == "no_bar":
                    no_bar += 1
        parent_blk = result_block(
            PARENT["hypothesis_id"],
            "rr2_parent_baseline_replay",
            parent_trades,
            extra={"role": "baseline_parent_replay", "not_candidate_reopen": True},
        )
        child_blk = result_block(
            CHILD_ID,
            "sb_rr2_quality_thick_disp",
            kept,
            extra={
                "parent": PARENT,
                "gate": {
                    "body_atr_min": Q_BODY_ATR,
                    "body_range_min": Q_BODY_RANGE,
                    "close_frac_min": Q_CLOSE_FRAC,
                    "signal_bar": "M15_bar_before_fill",
                },
                "not_fvg_densify": True,
                "not_exit_densify": True,
                "not_maxkz_densify": True,
            },
        )
        survivors = [child_blk] if child_blk["verdict"] == "PROBE_SURVIVOR" else []
        status = (
            "OFFLINE_HAS_SURVIVOR / MODEL0_ARMED"
            if survivors
            else "OFFLINE_ALL_KILL / NO_MODEL0"
        )
        payload = {
            "schema": "sb_rr2_quality_thick_offline_probes.v1",
            "created_at_utc": utc_now(),
            "campaign_status": status,
            "wave": "W27_SB_RR2_QUALITY_THICK_CHILD",
            "parent": {**PARENT, "trades_csv": str(csv_path), "csv_sha256": sha256_file(csv_path)},
            "window": {"from": FROM.isoformat(), "to": TO.isoformat(), "weeks": round(WEEKS, 4)},
            "cost_proxy_usd_per_trade": BASE_COST,
            "funnel": {
                "parent_n": len(parent_trades),
                "kept": len(kept),
                "dropped": dropped,
                "no_bar": no_bar,
            },
            "a_priori_gate": {
                "body_atr_min": Q_BODY_ATR,
                "body_range_min": Q_BODY_RANGE,
                "close_frac_min": Q_CLOSE_FRAC,
            },
            "parent_baseline": parent_blk,
            "objects": [child_blk],
            "survivors": [o["hypothesis_id"] for o in survivors],
            "model0": "AUTHORIZED_IF_SURVIVOR" if survivors else "WITHHELD",
            "banned": [
                "FVG_size_wait_densify",
                "exit_BE_trail_TP_RR_densify",
                "MaxKZ_densify",
                "UUP_DTWEX_z_mine",
                "commodity_tot_densify",
                "credit_MOVE_densify",
                "W1_W26_OHLC_densify",
                "quality_threshold_retune_after_readout",
            ],
            "best_shelf": "RR2_20260714_194548",
            "clean_book_pf12": 1.184,
            "cost_surface": "GAP_UNCHANGED",
            "chatgpt": "AUTH_BLOCKED__LOGIN_WALL__PARALLEL_OWNER_ONLY",
            "prior_w27_uup_dtwex": "OFFLINE_ALL_KILL",
        }
        write_json(OUT_JSON, payload)
        payload["receipt_sha256"] = sha256_file(OUT_JSON)
        write_json(OUT_JSON, payload)
        write_docs(payload, parent_blk, child_blk)
        append_registry(child_blk, payload["receipt_sha256"])
        print(
            json.dumps(
                {
                    "status": status,
                    "receipt": payload["receipt_sha256"],
                    "funnel": payload["funnel"],
                    "parent": {
                        "n": parent_blk["metrics"]["n"],
                        "pf": parent_blk["metrics"]["pf"],
                        "tpw": parent_blk["metrics"]["tpw"],
                        "pf12": (parent_blk["haircuts"].get("x1") or {}).get("pf"),
                    },
                    "child": {
                        "id": CHILD_ID,
                        "n": child_blk["metrics"]["n"],
                        "pf": child_blk["metrics"]["pf"],
                        "tpw": child_blk["metrics"]["tpw"],
                        "pf12": (child_blk["haircuts"].get("x1") or {}).get("pf"),
                        "x15": (child_blk["haircuts"].get("x1_5") or {}).get("pf"),
                        "verdict": child_blk["verdict"],
                        "notes": child_blk["kill_notes"],
                    },
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
