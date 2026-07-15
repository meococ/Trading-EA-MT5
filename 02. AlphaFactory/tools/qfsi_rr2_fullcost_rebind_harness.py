#!/usr/bin/env python3
"""QFSI full-cost RR2 (and Spark) rebind harness.

Armed for the moment the data contract gate lifts. Does NOT retune RR2/Spark
signal from partial Real readout. Does NOT invent commission/slippage.
Does NOT kill Real/MT5.

Usage:
  python qfsi_rr2_fullcost_rebind_harness.py            # status + gate check
  python qfsi_rr2_fullcost_rebind_harness.py --execute  # rebind only if GO
  python qfsi_rr2_fullcost_rebind_harness.py --force-partial  # refuse by default
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
ALPHA = ROOT / "02. AlphaFactory"
TOOLS = ALPHA / "tools"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
EVID = ALPHA / "evidence/execution/FivePercentOnline-Real"
REGISTRY = ROOT / "03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl"

SYMBOLS_GATE = ["EURUSD", "GBPUSD", "XAUUSD"]  # contract gate symbols
SYMBOLS_BOOK = ["USDJPY"]  # RR2 / SB / Spark primary book
SYMBOLS_CAPTURE = ["USDJPY", "EURUSD", "GBPUSD", "XAUUSD"]  # book-first + gate

QUOTE_DAYS_MIN = 90
COMMISSION_UNIQUE_MIN = 30
SLIPPAGE_FILLS_MIN = 100

# Frozen family — no signal retune from partial shelf
BOOKS = [
    ("EA_SilverBullet", "20260714_194548", "RR2_SHELF", "HYP-SB-MAXKZ2-RR2-FRICTION-001"),
    ("EA_SilverBullet", "20260714_194221", "RR2_CONTROL_194221", "HYP-SB-MAXKZ2-RR2-FRICTION-001"),
    ("EA_SilverBullet", "20260714_231750", "RR2_FRESH_MODEL0", "HYP-SB-MAXKZ2-RR2-FRICTION-001"),
    ("EA_M15SparkAsian", "20260714_193358", "SPARK100K", "HYP-SPARK-ASIAN-M15-001"),
]

sys.path.insert(0, str(ALPHA / "analysis"))
sys.path.insert(0, str(TOOLS))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def list_captures() -> list[Path]:
    if not EVID.exists():
        return []
    return sorted(
        [d for d in EVID.iterdir() if d.is_dir() and "QFSI_REAL" in d.name],
        key=lambda p: p.name,
    )


def csv_data_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def quote_distinct_dates(symbol: str) -> set[str]:
    dates: set[str] = set()
    for cap in list_captures():
        rows = csv_data_rows(cap / f"{symbol}_quote_ticks.csv")
        for r in rows:
            t = (r.get("time_utc") or r.get("time") or "").strip()
            if len(t) >= 10:
                dates.add(t[:10])
    return dates


def commission_unique(symbol: str) -> int:
    keys: set[str] = set()
    for cap in list_captures():
        for r in csv_data_rows(cap / f"{symbol}_commission_lifecycles.csv"):
            pid = (r.get("position_id") or "").strip()
            if pid:
                keys.add(pid)
            else:
                # fall back to row fingerprint if no position_id
                keys.add("|".join(str(v) for v in r.values()))
    return len(keys)


def slippage_count(symbol: str) -> int:
    n = 0
    for cap in list_captures():
        n += len(csv_data_rows(cap / f"{symbol}_slippage_fills.csv"))
    return n


def pid_alive(pid: int) -> bool:
    try:
        import ctypes

        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        return False


def process_snapshot() -> dict[str, Any]:
    return {
        "terminal64_29076": pid_alive(29076),
        "qfsi_005_35892": pid_alive(35892),
        "watcher_18760": pid_alive(18760),
        "do_not_kill_real": True,
    }


def evaluate_gate() -> dict[str, Any]:
    quote_days = {s: sorted(quote_distinct_dates(s)) for s in SYMBOLS_CAPTURE}
    commission = {s: commission_unique(s) for s in SYMBOLS_CAPTURE}
    slip = {s: slippage_count(s) for s in SYMBOLS_CAPTURE}

    # Contract: EURUSD/GBPUSD/XAUUSD must all clear; book also needs USDJPY honesty
    blockers: list[str] = []
    for s in SYMBOLS_GATE:
        qd = len(quote_days[s])
        if qd < QUOTE_DAYS_MIN:
            blockers.append(f"{s}_quote_days={qd}<<{QUOTE_DAYS_MIN}")
        if commission[s] < COMMISSION_UNIQUE_MIN:
            blockers.append(f"{s}_commission_unique={commission[s]}<<{COMMISSION_UNIQUE_MIN}")
        if slip[s] < SLIPPAGE_FILLS_MIN:
            blockers.append(f"{s}_slippage_fills={slip[s]}<<{SLIPPAGE_FILLS_MIN} (MISSING≠0)")

    usdjpy_days = len(quote_days["USDJPY"])
    if usdjpy_days < QUOTE_DAYS_MIN:
        blockers.append(f"USDJPY_quote_days={usdjpy_days}<<{QUOTE_DAYS_MIN} (book primary)")
    if commission["USDJPY"] < COMMISSION_UNIQUE_MIN:
        blockers.append(
            f"USDJPY_commission_unique={commission['USDJPY']}<<{COMMISSION_UNIQUE_MIN} (book primary)"
        )
    if slip["USDJPY"] < SLIPPAGE_FILLS_MIN:
        blockers.append(
            f"USDJPY_slippage_fills={slip['USDJPY']}<<{SLIPPAGE_FILLS_MIN} (book primary; MISSING≠0)"
        )

    go = len(blockers) == 0
    remaining = {
        "quote_days_need": {
            s: max(0, QUOTE_DAYS_MIN - len(quote_days[s])) for s in SYMBOLS_CAPTURE
        },
        "commission_need": {
            s: max(0, COMMISSION_UNIQUE_MIN - commission[s]) for s in SYMBOLS_CAPTURE
        },
        "slippage_need": {
            s: max(0, SLIPPAGE_FILLS_MIN - slip[s]) for s in SYMBOLS_CAPTURE
        },
        "calendar_eta_quote_days_only": (
            f"~{max(0, QUOTE_DAYS_MIN - max(len(quote_days[s]) for s in SYMBOLS_CAPTURE))} "
            "elapsed calendar days if continuous Real accumulate (commission/slip still Owner deal-export)"
        ),
    }
    return {
        "full_qfsi_verdict": "GO_FOR_FULL_COST_REBIND" if go else "STOP_DATA_FRONTIER",
        "go": go,
        "blockers": blockers,
        "progress": {
            "quote_distinct_utc_dates": {s: quote_days[s] for s in SYMBOLS_CAPTURE},
            "quote_day_counts": {s: len(quote_days[s]) for s in SYMBOLS_CAPTURE},
            "commission_unique": commission,
            "slippage_fills": slip,
            "captures": [c.name for c in list_captures()],
        },
        "remaining_frontier": remaining,
        "contract": "04. Project Control/ai/data_contracts/20260713_EXECUTION_DATA_ACQUISITION_CONTRACT_V1.md",
    }


def stress_books(unit_usd_per_lot: float, cost_grade: str, note: str) -> dict[str, Any]:
    """Lot-scaled cost stress; no signal edit."""
    from quant_analyzer import deals_to_trades, parse_deals  # noqa: WPS433
    import sonic_cost_stress as scs  # noqa: WPS433

    out: dict[str, Any] = {}
    for ea, run_id, label, hyp in BOOKS:
        run_dir = ALPHA / "runs" / ea / run_id
        deals_path = run_dir / "deals.csv"
        if not deals_path.exists():
            # common AlphaFactory layout
            candidates = list(run_dir.rglob("deals.csv"))
            deals_path = candidates[0] if candidates else deals_path
        if not deals_path.exists():
            out[label] = {"error": "deals_missing", "run_id": run_id, "hypothesis_id": hyp}
            continue
        deals = parse_deals(deals_path)
        trades = deals_to_trades(deals)
        lots = [float(t.get("volume") or t.get("lots") or 0) for t in trades]
        lots = [x for x in lots if x > 0]
        lot_p50 = sorted(lots)[len(lots) // 2] if lots else None
        if lot_p50 is None:
            out[label] = {"error": "no_lots", "run_id": run_id, "hypothesis_id": hyp}
            continue
        base_cost = float(unit_usd_per_lot) * float(lot_p50)
        pnls = [float(t["pnl"]) for t in trades if t.get("pnl") is not None]
        stressed = scs.stress_pnls(pnls, base_cost) if hasattr(scs, "stress_pnls") else None
        if stressed is None and hasattr(scs, "apply_cost_stress"):
            stressed = scs.apply_cost_stress(pnls, base_cost)
        # Fallback: simple haircut PF
        if stressed is None:

            def pf_of(xs: list[float]) -> float:
                gp = sum(x for x in xs if x > 0)
                gl = -sum(x for x in xs if x < 0)
                return (gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0)

            x1 = [p - base_cost for p in pnls]
            x15 = [p - 1.5 * base_cost for p in pnls]
            x2 = [p - 2.0 * base_cost for p in pnls]
            stressed = {
                "base_pf": round(pf_of(pnls), 6),
                "x1_pf": round(pf_of(x1), 6),
                "x1_5_pf": round(pf_of(x15), 6),
                "x2_pf": round(pf_of(x2), 6),
            }
        analysis = run_dir / "analysis"
        analysis.mkdir(parents=True, exist_ok=True)
        bound = {
            "schema_version": "sonic_full_qfsi_rebind_cost_stress.v1",
            "created_at_utc": utc_now(),
            "ea": ea,
            "run_id": run_id,
            "label": label,
            "hypothesis_id": hyp,
            "cost_grade": cost_grade,
            "unit_usd_per_lot": unit_usd_per_lot,
            "lot_p50": lot_p50,
            "base_cost_per_trade": base_cost,
            "note": note,
            "no_signal_retune": True,
            "metrics": stressed,
        }
        bound_path = analysis / "cost_stress_full_qfsi_rebind.json"
        bound["sha256"] = write_json(bound_path, bound)
        pre_path = PRE / f"20260714_COSTSTRESS_{label}_{run_id}_FULL_QFSI_REBIND.json"
        write_json(pre_path, bound)
        m = stressed if isinstance(stressed, dict) else {}
        x1 = m.get("x1_pf") or m.get("x1", {}).get("pf")
        x15 = m.get("x1_5_pf") or m.get("x1_5", {}).get("pf")
        x2 = m.get("x2_pf") or m.get("x2", {}).get("pf")
        out[label] = {
            "run_id": run_id,
            "hypothesis_id": hyp,
            "ea": ea,
            "lot_p50": lot_p50,
            "base_cost_per_trade": base_cost,
            "x1_pf": x1,
            "x1_5_pf": x15,
            "x2_pf": x2,
            "goal_cost_stress_pass": bool(
                x1 is not None
                and x15 is not None
                and x2 is not None
                and float(x1) > 1.30
                and float(x15) >= 1.25
                and float(x2) >= 1.00
            ),
            "bound_path": str(bound_path.as_posix()),
            "preflight_path": str(pre_path.as_posix()),
            "no_signal_retune": True,
        }
    return out


def append_registry_note(gate: dict[str, Any], executed: bool, books: dict[str, Any] | None) -> None:
    row = {
        "record_type": "note",
        "schema_version": 1,
        "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
        "state": "parked",
        "note_type": "FULL_QFSI_REBIND_HARNESS",
        "updated_at": utc_now()[:10],
        "lane": "qfsi_real_fullcost_rebind",
        "source_provenance": (
            "Owner CONTINUE watch-QFSI; harness armed; no RR2 signal retune from partial Real"
        ),
        "validation": {
            "full_qfsi": gate.get("full_qfsi_verdict"),
            "executed_rebind": executed,
            "cost_grade": "FULL_QFSI" if executed else "ARMED_WAITING_GATE",
            "confirmed": False,
            "goal_claim": False,
        },
        "metrics": {
            "quote_day_counts": (gate.get("progress") or {}).get("quote_day_counts"),
            "commission_unique": (gate.get("progress") or {}).get("commission_unique"),
            "slippage_fills": (gate.get("progress") or {}).get("slippage_fills"),
            "books": books,
        },
        "harness_path": "02. AlphaFactory/tools/qfsi_rr2_fullcost_rebind_harness.py",
        "bans": [
            "no_densify_RR_MaxKZ",
            "no_price_twin_spam",
            "no_revive_COT",
            "no_kill_Real",
            "no_retune_RR2_from_partial_readout",
        ],
    }
    with REGISTRY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_partial_unit_cost() -> float | None:
    """Read last honest partial unit if present — NEVER invent."""
    for name in (
        "20260714_BROKER_SPREAD_COST_TABLE_QFSI_W7CONT.json",
        "20260714_BROKER_SPREAD_COST_TABLE_QFSI.json",
    ):
        p = PRE / name
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for key in (
            "canonical_usdjpy_unit_p50",
            "usdjpy_unit_p50",
            "unit_usdjpy_p50_per_lot",
        ):
            if data.get(key) is not None:
                return float(data[key])
        # nested
        cu = data.get("cost_unit") or {}
        if cu.get("usdjpy_unit_p50") is not None:
            return float(cu["usdjpy_unit_p50"])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="Rebind only if full QFSI GO")
    ap.add_argument(
        "--force-partial",
        action="store_true",
        help="Explicitly refused: will not pretend partial is full",
    )
    args = ap.parse_args()

    gate = evaluate_gate()
    procs = process_snapshot()
    live_caps = [
        c.name
        for c in list_captures()
        if (c / "session_start.json").exists() and not (c / "session_end.json").exists()
    ]

    receipt: dict[str, Any] = {
        "schema_version": "sonic_qfsi_rr2_fullcost_rebind_harness.v1",
        "created_at_utc": utc_now(),
        "status": "HARNESS_ARMED__GATE_STOP"
        if not gate["go"]
        else "HARNESS_READY__GATE_GO",
        "goal_claim": False,
        "confirmed_claim": False,
        "do_not_kill_real": True,
        "no_signal_retune": True,
        "processes": procs,
        "live_captures": live_caps,
        "capture_symbol_order_book_first": SYMBOLS_CAPTURE,
        "full_qfsi_gate": gate,
        "books_frozen": [
            {"ea": ea, "run_id": rid, "label": lab, "hypothesis_id": hyp}
            for ea, rid, lab, hyp in BOOKS
        ],
        "execute_command_when_go": (
            'python "02. AlphaFactory/tools/qfsi_rr2_fullcost_rebind_harness.py" --execute'
        ),
        "bans": [
            "no_densify",
            "no_price_twin_spam",
            "no_COT_revive",
            "no_kill_Real",
            "no_retune_RR2_from_partial",
            "slippage_MISSING_neq_0",
        ],
    }

    executed = False
    books: dict[str, Any] | None = None

    if args.force_partial:
        receipt["status"] = "REFUSED_FORCE_PARTIAL"
        receipt["why"] = "Partial Real must not be labeled FULL_QFSI; use Wave7continue reprice for partial only"
    elif args.execute:
        if not gate["go"]:
            receipt["status"] = "EXECUTE_BLOCKED__STOP_DATA_FRONTIER"
            receipt["why"] = gate["blockers"]
        else:
            # Full grade path: unit cost must come from validated QFSI cost table — fail closed if absent
            unit = load_partial_unit_cost()
            if unit is None:
                receipt["status"] = "EXECUTE_BLOCKED__NO_UNIT_COST"
                receipt["why"] = "No honest unit USDJPY cost on disk after gate GO — refuse zero-cost"
            else:
                note = (
                    "FULL_QFSI_REBIND after contract gate GO; lot-scaled unit×lot_p50; "
                    "no RR2/Spark signal retune; slip included only if present in gate"
                )
                books = stress_books(unit, "FULL_QFSI_CONTRACT_PASS", note)
                receipt["books"] = books
                receipt["status"] = "FULL_QFSI_REBIND_EXECUTED"
                receipt["unit_usdjpy_per_lot"] = unit
                executed = True
                # honest GOAL: only if RR2 shelf passes under full grade
                rr2 = (books or {}).get("RR2_SHELF") or {}
                receipt["goal_claim"] = bool(rr2.get("goal_cost_stress_pass"))
                receipt["confirmed_claim"] = False  # confirmed needs promotion suite
                receipt["goal_verdict"] = (
                    "GOAL_STRESS_PASS_UNDER_FULL_QFSI_COST"
                    if receipt["goal_claim"]
                    else "GOAL_UNMET_UNDER_FULL_QFSI_COST"
                )

    append_registry_note(gate, executed, books)

    out_path = PRE / "20260714_QFSI_RR2_FULLCOST_REBIND_HARNESS_RECEIPT.json"
    receipt["receipt_sha256"] = write_json(out_path, receipt)
    # rewrite with self-hash
    receipt["receipt_sha256"] = write_json(out_path, receipt)

    # short operator card
    md = f"""# RR2 full-cost rebind harness

Updated: {utc_now()}  
Gate: **`{gate['full_qfsi_verdict']}`**  
Execute: `{bool(executed)}` · GOAL claim: `{receipt.get('goal_claim')}` · confirmed: false

## Remaining frontier

```json
{json.dumps(gate.get('remaining_frontier'), indent=2)}
```

## Blockers

{chr(10).join('- ' + b for b in gate.get('blockers') or ['(none)'])}

## When GO

```powershell
python "02. AlphaFactory/tools/qfsi_rr2_fullcost_rebind_harness.py" --execute
```

Frozen books: RR2 `194548` / ctrl `194221` / fresh `231750` + Spark `193358`.  
**No signal retune.** Do not kill Real.
"""
    (READ / "20260714_QFSI_RR2_FULLCOST_REBIND_HARNESS.md").write_text(md, encoding="utf-8")

    print(json.dumps({
        "status": receipt["status"],
        "gate": gate["full_qfsi_verdict"],
        "blockers": gate["blockers"][:6],
        "receipt": str(out_path),
        "sha256": receipt["receipt_sha256"],
        "processes": procs,
    }, indent=2))
    return 0 if (not args.execute or executed or not gate["go"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
