#!/usr/bin/env python3
"""Post-login QFSI pass: probe-bound partial Real cost reprice for MaxKZ2 + A1.

Honesty:
- Full QFSI gates (90d quotes / commission>=30/symbol / slippage>=100) unmet
  => primary verdict CAPTURE_INCOMPLETE.
- Partial diagnostic uses USDJPY live spread P50/P90 + EURUSD commission clue
  N=2 transferred; slippage MISSING (not zero). Not confirmed / not GOAL.
- Never places orders. Fail-closed on MetaQuotes-Demo / server mismatch.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
ALPHA = ROOT / "02. AlphaFactory"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
RUNS = ALPHA / "runs/EA_SilverBullet"
CAP = ALPHA / "evidence/execution/FivePercentOnline-Real/20260714_QFSI_REAL_002"
DEAL = ALPHA / "evidence/execution/FivePercentOnline-Real/20260714_DEAL_HISTORY_IMPORT_POSTLOGIN"
PROBE = PRE / "v4_data/20260714_MT5_READONLY_PROBE_V5_POSTLOGIN.json"
INV = PRE / "v4_data/20260714_EXECUTION_DATA_INVENTORY_V5.json"
EXPECTED = "FivePercentOnline-Real"

sys.path.insert(0, str(ALPHA / "analysis"))
sys.path.insert(0, str(ALPHA / "tools"))
from quant_analyzer import deals_to_trades, parse_deals  # noqa: E402
import sonic_cost_stress as scs  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def percentile(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(round((len(xs) - 1) * p))))
    return xs[i]


def load_commission_clue() -> tuple[list[float], str]:
    samples: list[float] = []
    for path in (
        DEAL / "EURUSD_commission_lifecycles.csv",
        CAP / "commission_lifecycles.csv",
        CAP / "EURUSD_commission_lifecycles.csv",
    ):
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                try:
                    val = float(row["round_turn_account_per_lot"])
                except (TypeError, ValueError, KeyError):
                    continue
                if val > 0:
                    samples.append(val)
        if samples:
            return samples, str(path)
    return [], "MISSING"


def mt5_usdjpy_cost(terminal_path: str | None = None) -> dict[str, Any]:
    import MetaTrader5 as mt5

    init_args: dict[str, Any] = {}
    if terminal_path:
        init_args["path"] = terminal_path
    if not mt5.initialize(**init_args):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        acc = mt5.account_info()
        term = mt5.terminal_info()
        if acc is None or term is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        observed = str(acc.server or "")
        if "MetaQuotes" in observed or "Demo" in observed:
            raise RuntimeError(f"WRONG_ACCOUNT Demo/MetaQuotes: {observed}")
        if observed != EXPECTED:
            raise RuntimeError(f"WRONG_ACCOUNT server mismatch: {observed}")
        info = mt5.symbol_info("USDJPY")
        tick = mt5.symbol_info_tick("USDJPY")
        if info is None or tick is None:
            raise RuntimeError("USDJPY unavailable")
        ticks = mt5.copy_ticks_from("USDJPY", datetime.now(timezone.utc), 50000, mt5.COPY_TICKS_ALL)
        spreads: list[float] = []
        if ticks is not None:
            for t in ticks:
                bid = float(t["bid"])
                ask = float(t["ask"])
                if bid > 0 and ask >= bid:
                    spreads.append(ask - bid)
        pip = float(info.point) * (10 if int(info.digits) in (3, 5) else 1)
        tv = float(info.trade_tick_value)
        ts = float(info.trade_tick_size) or float(info.point)
        dollars = (tv / ts) if ts else None
        p50 = percentile(spreads, 0.50)
        p90 = percentile(spreads, 0.90)
        return {
            "observed_server": observed,
            "trade_allowed": bool(term.trade_allowed),
            "connected": bool(term.connected),
            "terminal_build": int(term.build),
            "digits": int(info.digits),
            "point": float(info.point),
            "pip_size": pip,
            "tick_value": tv,
            "tick_size": ts,
            "current_bid": float(tick.bid),
            "current_ask": float(tick.ask),
            "live_tick_sample_n": len(spreads),
            "spread_price_p50": p50,
            "spread_price_p90": p90,
            "dollars_per_price_per_lot": dollars,
            "spread_usd_per_lot_p50": (p50 * dollars) if (p50 is not None and dollars) else None,
            "spread_usd_per_lot_p90": (p90 * dollars) if (p90 is not None and dollars) else None,
            "orders": int(mt5.orders_total() or 0),
            "positions": int(mt5.positions_total() or 0),
        }
    finally:
        mt5.shutdown()


def trade_lots(run_id: str) -> dict[str, Any]:
    report = RUNS / run_id / "report.html"
    deals = parse_deals(report)
    trades = deals_to_trades(deals)
    lots: list[float] = []
    for deal in deals:
        direction = (deal.direction or "").strip().lower()
        side = (deal.side or "").strip().lower()
        if direction != "in" or side in {"", "balance"}:
            continue
        try:
            vol = abs(float(deal.volume))
        except (TypeError, ValueError):
            continue
        if vol > 0:
            lots.append(vol)
    # elapsed weeks for 2021-01-01 .. 2025-12-31 ≈ 260.857 weeks (5y incl leap)
    elapsed_weeks = 260.857
    return {
        "n_trades": len(trades),
        "n_lots_observed": len(lots),
        "lot_p50": statistics.median(lots) if lots else None,
        "lot_mean": statistics.mean(lots) if lots else None,
        "lot_p90": percentile(lots, 0.90) if lots else None,
        "tpw_elapsed": (len(trades) / elapsed_weeks) if trades else None,
    }


def run_stress(run_id: str, base_cost: float, out_name: str, note: str) -> dict[str, Any]:
    class Args:
        pass

    args = Args()
    args.run = str(RUNS / run_id)
    args.ea = "EA_SilverBullet"
    args.report = str(RUNS / run_id / "report.html")
    args.out = str(PRE / out_name)
    args.start_equity = 100000.0
    args.base_cost_per_trade = float(base_cost)
    args.spread_points = 0.0
    args.slippage_points = 0.0
    args.commission_round_turn = 0.0
    args.point_value_per_lot = 1.0
    args.lot_size = 0.01
    result = scs.build_cost_matrix(args)
    result["cost_assumption"]["note"] = note
    result["cost_assumption"]["provenance"] = "FIVEPERCENTONLINE_REAL_PARTIAL_POSTLOGIN"
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def scenario_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["scenario"]: s for s in result.get("scenarios", [])}


def gate_eval(smap: dict[str, dict[str, Any]]) -> dict[str, Any]:
    x1 = smap.get("cost_x1_00", {})
    x15 = smap.get("cost_x1_50", {})
    x2 = smap.get("cost_x2_00", {})
    base = smap.get("base_report", {})
    return {
        "base_pf": base.get("profit_factor"),
        "x1_pf": x1.get("profit_factor"),
        "x1_5_pf": x15.get("profit_factor"),
        "x2_pf": x2.get("profit_factor"),
        "goal_x1_pf_gt_1_30": (x1.get("profit_factor") or 0) > 1.30,
        "goal_x1_5_pf_ge_1_25": (x15.get("profit_factor") or 0) >= 1.25,
        "goal_x2_pf_ge_1_00": (x2.get("profit_factor") or 0) >= 1.00,
        "goal_cost_stress_pass": (
            (x1.get("profit_factor") or 0) > 1.30
            and (x15.get("profit_factor") or 0) >= 1.25
            and (x2.get("profit_factor") or 0) >= 1.00
        ),
    }


def book_block(
    label: str,
    hyp: str,
    run_id: str,
    lots: dict[str, Any],
    p50: dict[str, Any],
    p90: dict[str, Any],
) -> dict[str, Any]:
    g50 = gate_eval(scenario_map(p50))
    g90 = gate_eval(scenario_map(p90))
    return {
        "label": label,
        "hypothesis_id": hyp,
        "run_id": run_id,
        "symbol": "USDJPY",
        "trades": lots.get("n_trades"),
        "tpw_elapsed": lots.get("tpw_elapsed"),
        "lot_p50": lots.get("lot_p50"),
        "real_p50": g50,
        "real_p90": g90,
        "stress_artifacts": {
            "p50": str((PRE / f"20260714_COSTSTRESS_{label}_{run_id}_REAL_P50_POSTLOGIN.json").as_posix()),
            "p90": str((PRE / f"20260714_COSTSTRESS_{label}_{run_id}_REAL_P90_POSTLOGIN.json").as_posix()),
        },
    }


def main() -> int:
    terminal = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    live = mt5_usdjpy_cost(terminal)
    probe = json.loads(PROBE.read_text(encoding="utf-8")) if PROBE.exists() else {}
    inv = json.loads(INV.read_text(encoding="utf-8")) if INV.exists() else {}
    deal_manifest = json.loads((DEAL / "import_manifest.json").read_text(encoding="utf-8"))

    eurusd_comm, comm_src = load_commission_clue()
    if not eurusd_comm:
        raise RuntimeError("commission clue missing; refuse missing-as-zero")
    commission_rt = statistics.median(eurusd_comm)

    books = [
        ("MAXKZ2", "HYP-SB-MAXKZ2-DENSITY-002", "20260714_192304"),
        ("A1", "HYP-SB-WEEKEND-FLAT-001", "20260714_002505"),
        ("RR2", "HYP-SB-MAXKZ2-RR2-FRICTION-001", "20260714_194221"),
    ]
    lots_map = {label: trade_lots(run_id) for label, _, run_id in books}
    lot_p50 = lots_map["MAXKZ2"].get("lot_p50") or lots_map["A1"].get("lot_p50")
    if lot_p50 is None:
        raise RuntimeError("could not observe lot sizes")

    spread_p50 = live.get("spread_usd_per_lot_p50")
    spread_p90 = live.get("spread_usd_per_lot_p90") or spread_p50
    if spread_p50 is None:
        raise RuntimeError("USDJPY Real spread unavailable")

    base_p50 = (float(spread_p50) + float(commission_rt)) * float(lot_p50)
    base_p90 = (float(spread_p90) + float(commission_rt)) * float(lot_p50)
    note = (
        "FivePercentOnline-Real POSTLOGIN partial: USDJPY live tick spread P50/P90 "
        f"+ EURUSD commission clue ${commission_rt:.2f}/lot RT (N={len(eurusd_comm)}, transferred). "
        "Slippage MISSING (not 0). Full QFSI gates unmet — CAPTURE_INCOMPLETE."
    )

    reprice: dict[str, Any] = {}
    for label, hyp, run_id in books:
        p50 = run_stress(
            run_id,
            base_p50,
            f"20260714_COSTSTRESS_{label}_{run_id}_REAL_P50_POSTLOGIN.json",
            note + " scenario=spread_p50+comm_clue",
        )
        p90 = run_stress(
            run_id,
            base_p90,
            f"20260714_COSTSTRESS_{label}_{run_id}_REAL_P90_POSTLOGIN.json",
            note + " scenario=spread_p90+comm_clue",
        )
        reprice[label] = book_block(label, hyp, run_id, lots_map[label], p50, p90)

    missing = {
        "usdJPY_commission_lifecycles": {
            "have": deal_manifest.get("commission_lifecycle_counts", {}).get("USDJPY", 0),
            "need": 30,
        },
        "eurusd_commission_lifecycles": {
            "have": deal_manifest.get("commission_lifecycle_counts", {}).get("EURUSD", 0),
            "need": 30,
        },
        "slippage_fills_per_symbol": {
            "have": deal_manifest.get("slippage_fills", 0),
            "need": 100,
            "status": "MISSING_NOT_ZERO_CANNOT_MINT_FROM_PASSIVE_QUOTES",
        },
        "quote_elapsed_days": {
            "have_estimate": "<1 day across captures 001-004_EXTENSION",
            "need": 90,
        },
        "eligible_hash_bound_bundles": {
            "have": inv.get("eligible_bundle_count", 0),
            "need": 1,
            "inventory_verdict": (inv.get("qfsi") or {}).get("verdict"),
        },
    }

    max_pass = bool(reprice["MAXKZ2"]["real_p50"]["goal_cost_stress_pass"])
    a1_pass = bool(reprice["A1"]["real_p50"]["goal_cost_stress_pass"])
    rr2_pass = bool(reprice["RR2"]["real_p50"]["goal_cost_stress_pass"])

    # Primary mission verdict: verified-cost path incomplete.
    primary = "CAPTURE_INCOMPLETE"
    partial_label = (
        "PARTIAL_DIAGNOSTIC_MAXKZ2_FAIL"
        if not max_pass
        else "PARTIAL_DIAGNOSTIC_MAXKZ2_PASS"
    )

    receipt = {
        "schema_version": "sonic_qfsi_postlogin_reprice_receipt.v1",
        "created_at_utc": utc_now(),
        "owner_signal": "da_login",
        "primary_verdict": primary,
        "partial_diagnostic_label": partial_label,
        "goal_claim": False,
        "confirmed_claim": False,
        "validate_full_recommended": False,
        "full_qfsi_gate": "STOP_DATA_FRONTIER",
        "server": {
            "expected": EXPECTED,
            "observed": live["observed_server"],
            "server_match": True,
            "probe_path": str(PROBE.as_posix()),
            "probe_sha256": sha256_file(PROBE),
            "probe_verdict": probe.get("verdict"),
            "account_fingerprint": probe.get("account_fingerprint"),
            "server_fingerprint": probe.get("server_fingerprint"),
            "trade_allowed": live["trade_allowed"],
            "orders": live["orders"],
            "positions": live["positions"],
        },
        "inventory": {
            "path": str(INV.as_posix()),
            "sha256": sha256_file(INV),
            "eligible_bundle_count": inv.get("eligible_bundle_count"),
            "capture_manifest_count": inv.get("capture_manifest_count"),
            "qfsi_verdict": (inv.get("qfsi") or {}).get("verdict"),
        },
        "deal_history_import": {
            "path": str((DEAL / "import_manifest.json").as_posix()),
            "sha256": sha256_file(DEAL / "import_manifest.json"),
            "status": deal_manifest.get("status"),
            "raw_deal_count": deal_manifest.get("raw_deal_count"),
            "commission_lifecycle_counts": deal_manifest.get("commission_lifecycle_counts"),
            "slippage_fills": deal_manifest.get("slippage_fills"),
        },
        "capture_active": {
            "capture_id": "20260714_QFSI_REAL_004_EXTENSION",
            "note": "Passive quote/heartbeat accumulation still RUNNING; not eligible bundle.",
        },
        "cost_model": {
            "symbol": "USDJPY",
            "lot_p50": lot_p50,
            "usdjpy_live": live,
            "commission_rt_per_lot_usd": commission_rt,
            "commission_samples_eurusd": eurusd_comm,
            "commission_source": comm_src,
            "commission_status": "EURUSD_N2_PRELIMINARY_CLUE_TRANSFERRED_TO_USDJPY",
            "slippage_status": "MISSING_NOT_ZERO",
            "base_round_turn_cost_per_trade_p50": base_p50,
            "base_round_turn_cost_per_trade_p90": base_p90,
            "caveat": "Additive haircut may double-count tester spread already in report PnL.",
        },
        "missing_for_verified_reprice": missing,
        "reprice": reprice,
        "owner_next_actions": [
            "Keep FivePercentOnline-Real connected; let 004_EXTENSION finish or continue overnight for quotes.",
            "Drop MT5 Account History export (All History, HTML/CSV with Commission) covering >=90d into owner_deal_export_drop — need >=30 commission lifecycles per FX symbol especially USDJPY.",
            "Slippage cannot be minted from quotes: need broker execution report or side-referenced fills with pre-send BID/ASK (>=100/symbol).",
            "Do NOT authorize validate-full / confirmed claims until eligible hash-bound bundle exists.",
            "Do NOT densify MaxKZ2 from partial FAIL.",
        ],
        "safety": {"orders_sent": 0, "positions_opened": 0, "read_only": True, "live_trading": False},
    }

    out_receipt = PRE / "20260714_QFSI_POSTLOGIN_REPRICE_MAXKZ2_A1_RECEIPT.json"
    write_json(out_receipt, receipt)

    def row(b: dict[str, Any]) -> str:
        g = b["real_p50"]
        return (
            f"| {b['label']} | `{b['run_id']}` | {b['trades']} | "
            f"{(b['tpw_elapsed'] or 0):.2f} | {g['base_pf']} | "
            f"**{g['x1_pf']:.3f}** | **{g['x1_5_pf']:.3f}** | **{g['x2_pf']:.3f}** | "
            f"{'PASS' if g['goal_cost_stress_pass'] else 'FAIL'} |"
        )

    md = f"""# Deliverable — Post-login QFSI / MaxKZ2+A1 cost reprice

Created: {receipt['created_at_utc']}
Owner signal: `đã login`
Primary verdict: **`{primary}`**
Partial diagnostic: `{partial_label}`
GOAL / confirmed claims: **false**
Validate-full recommended: **false**

## Account probe

| Field | Value |
|---|---|
| Expected | `{EXPECTED}` |
| Observed | `{live['observed_server']}` |
| Match | true |
| Probe | `{probe.get('verdict')}` |
| Probe SHA256 | `{receipt['server']['probe_sha256']}` |
| Trade allowed | {live['trade_allowed']} |
| Orders / positions | {live['orders']} / {live['positions']} |
| MetaQuotes-Demo | **rejected** (fail-closed path unused) |

## Capture / inventory status

| Gate | Have | Need |
|---|---|---|
| Eligible hash-bound bundles | {inv.get('eligible_bundle_count')} | >=1 |
| Inventory QFSI | `{(inv.get('qfsi') or {}).get('verdict')}` | not STOP |
| USDJPY commission lifecycles | {missing['usdJPY_commission_lifecycles']['have']} | 30 |
| EURUSD commission lifecycles | {missing['eurusd_commission_lifecycles']['have']} | 30 |
| Slippage fills / symbol | {missing['slippage_fills_per_symbol']['have']} | 100 |
| Quote elapsed days | {missing['quote_elapsed_days']['have_estimate']} | 90 |

Active passive capture: `20260714_QFSI_REAL_004_EXTENSION` (quotes accumulating; commission/slippage still empty for USDJPY).

## Partial Real cost model (diagnostic only)

| Component | Value |
|---|---|
| Symbol | USDJPY |
| Lot P50 | {lot_p50} |
| Spread USD/lot P50 | {spread_p50:.6f} |
| Spread USD/lot P90 | {spread_p90:.6f} |
| Commission clue | ${commission_rt:.2f}/lot RT (EURUSD N={len(eurusd_comm)}, transferred) |
| Slippage | MISSING ≠ 0 |
| Base RT $/trade P50 | **${base_p50:.4f}** |
| Base RT $/trade P90 | **${base_p90:.4f}** |

Caveat: additive haircut on tester-current reports may double-count spread already in PnL → conservative.

## Metrics (Real P50 haircut)

| Book | Run | Trades | /wk | Base PF | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---|---|---|---|---|---|---|---|
{row(reprice['MAXKZ2'])}
{row(reprice['A1'])}
{row(reprice['RR2'])}

Campaign survivor MaxKZ2 remains **HIT_RESEARCH_BAR** under tester `current` only; under this partial Real model it does **not** clear GOAL cost-stress (x1 PF must >1.30). A1 weekend-flat reference included same pass. RR2 remains the stronger partial-Real friction sleeve but is **not confirmed**.

## Artifacts

- Receipt: `{out_receipt.as_posix()}`
- Inventory V5: `{INV.as_posix()}` SHA `{receipt['inventory']['sha256']}`
- Deal import: `{(DEAL / 'import_manifest.json').as_posix()}`
- Probe V5: `{PROBE.as_posix()}`

## Next Owner actions

1. Keep Real logged in; continue quote capture overnight.
2. Export Account History (All History) with Commission → `owner_deal_export_drop` until USDJPY/EURUSD commission ≥30 each.
3. Provide side-referenced slippage fills (≥100/symbol) — cannot invent from quotes.
4. Do **not** run validate-full / claim confirmed until inventory eligible ≥1.
"""
    out_md = READ / "20260714_QFSI_POSTLOGIN_REPRICE_MAXKZ2_A1_DELIVERABLE.md"
    out_md.write_text(md, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "OK",
                "primary_verdict": primary,
                "partial_diagnostic_label": partial_label,
                "maxkz2_p50_pass": max_pass,
                "a1_p50_pass": a1_pass,
                "rr2_p50_pass": rr2_pass,
                "base_cost_p50": base_p50,
                "receipt": str(out_receipt),
                "deliverable": str(out_md),
                "receipt_sha256": sha256_file(out_receipt),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
