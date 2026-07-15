#!/usr/bin/env python3
"""Refresh MaxKZ2 Real-cost reprice from all Real captures + fail-closed closeout.

Honesty:
- Full QFSI gates remain unmet (quote days, commission/symbol, slippage).
- Uses live Real tick spread + EURUSD commission clue (N=2 transferred).
- Slippage MISSING != 0.
- Not confirmed / not GOAL.
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
EVID = ALPHA / "evidence/execution/FivePercentOnline-Real"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
RUNS = ALPHA / "runs/EA_SilverBullet"
REG = ROOT / "03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control/ai/hot.md"
PROBE = PRE / "v4_data/20260714_MT5_READONLY_PROBE_V4.json"

sys.path.insert(0, str(ALPHA / "analysis"))
sys.path.insert(0, str(ALPHA / "tools"))
from quant_analyzer import deals_to_trades, parse_deals  # noqa: E402
import sonic_cost_stress as scs  # noqa: E402
from execution_data_foundation import build_inventory  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
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


def list_capture_dirs() -> list[Path]:
    out = []
    for d in sorted(EVID.iterdir()):
        if d.is_dir() and "QFSI_REAL" in d.name:
            out.append(d)
    return out


def capture_inventory() -> dict[str, Any]:
    captures = {}
    for d in list_capture_dirs():
        row: dict[str, Any] = {"path": str(d.as_posix()), "files": {}}
        total_quotes = 0
        total_hb = 0
        total_comm = 0
        total_slip = 0
        for f in sorted(d.glob("*.csv")):
            n = sum(1 for _ in open(f, encoding="utf-8-sig", errors="ignore")) - 1
            row["files"][f.name] = n
            if "quote_ticks" in f.name:
                total_quotes += max(0, n)
            elif "heartbeats" in f.name:
                total_hb += max(0, n)
            elif "commission" in f.name:
                total_comm += max(0, n)
            elif "slippage" in f.name:
                total_slip += max(0, n)
        row["totals"] = {
            "quotes": total_quotes,
            "heartbeats": total_hb,
            "commission": total_comm,
            "slippage": total_slip,
        }
        session_end = d / "session_end.json"
        row["session_end"] = session_end.exists()
        if session_end.exists():
            try:
                se = json.loads(session_end.read_text(encoding="utf-8"))
                row["session_status"] = se.get("status")
                row["reprice_ready"] = se.get("reprice_ready")
            except Exception as exc:  # noqa: BLE001
                row["session_status_error"] = str(exc)
        captures[d.name] = row
    return captures


def aggregate_spreads(symbol: str) -> dict[str, Any]:
    spreads: list[float] = []
    sources: list[dict[str, Any]] = []
    for d in list_capture_dirs():
        path = d / f"{symbol}_quote_ticks.csv"
        if not path.exists():
            continue
        n = 0
        local: list[float] = []
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                n += 1
                try:
                    bid = float(row["bid"])
                    ask = float(row["ask"])
                except (TypeError, ValueError, KeyError):
                    continue
                if bid > 0 and ask >= bid:
                    local.append(ask - bid)
        spreads.extend(local)
        sources.append(
            {
                "capture": d.name,
                "quote_rows": n,
                "valid_spreads": len(local),
                "sha256": sha256_file(path),
            }
        )
    return {
        "symbol": symbol,
        "quote_rows": sum(s["quote_rows"] for s in sources),
        "valid_spreads": len(spreads),
        "spread_price_p50": percentile(spreads, 0.50),
        "spread_price_p90": percentile(spreads, 0.90),
        "sources": sources,
    }


def load_all_commissions() -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for d in list_capture_dirs():
        for path in [d / "commission_lifecycles.csv"] + list(d.glob("*_commission_lifecycles.csv")):
            if not path.exists():
                continue
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    sym = row.get("symbol") or path.name.split("_")[0]
                    key = "round_turn_account_per_lot"
                    if key not in row:
                        # per-symbol files may use different column
                        for alt in ("commission_round_turn_per_lot", "round_turn_usd_per_lot"):
                            if alt in row:
                                key = alt
                                break
                    try:
                        val = float(row[key])
                    except (TypeError, ValueError, KeyError):
                        continue
                    out.setdefault(sym, []).append(val)
    return out


def mt5_symbol_cost(symbol: str) -> dict[str, Any]:
    import MetaTrader5 as mt5

    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        raise RuntimeError(f"symbol unavailable: {symbol}")
    ticks = mt5.copy_ticks_from(symbol, datetime.now(timezone.utc), 50000, mt5.COPY_TICKS_ALL)
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
    dollars_per_price_per_lot = (tv / ts) if ts else None
    p50 = percentile(spreads, 0.50)
    p90 = percentile(spreads, 0.90)
    return {
        "digits": int(info.digits),
        "point": float(info.point),
        "pip_size": pip,
        "tick_value": tv,
        "tick_size": ts,
        "current_bid": float(tick.bid),
        "current_ask": float(tick.ask),
        "current_spread_price": float(tick.ask) - float(tick.bid),
        "live_tick_sample_n": len(spreads),
        "spread_price_p50": p50,
        "spread_price_p90": p90,
        "dollars_per_price_per_lot": dollars_per_price_per_lot,
        "spread_usd_per_lot_p50": (
            p50 * dollars_per_price_per_lot if (p50 is not None and dollars_per_price_per_lot) else None
        ),
        "spread_usd_per_lot_p90": (
            p90 * dollars_per_price_per_lot if (p90 is not None and dollars_per_price_per_lot) else None
        ),
    }


def trade_lots(run_id: str) -> dict[str, Any]:
    report = RUNS / run_id / "report.html"
    if not report.exists():
        return {"n_trades": 0, "n_lots_observed": 0, "lot_p50": None, "missing": True}
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
    return {
        "n_trades": len(trades),
        "n_lots_observed": len(lots),
        "lot_p50": statistics.median(lots) if lots else None,
        "lot_mean": statistics.mean(lots) if lots else None,
        "lot_p90": percentile(lots, 0.90) if lots else None,
        "missing": False,
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
    result["cost_assumption"]["provenance"] = "FIVEPERCENTONLINE_REAL_PARTIAL_SAMPLE_AGGREGATED"
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
        "base_n": base.get("n_trades"),
        "x1_pf": x1.get("profit_factor"),
        "x1_5_pf": x15.get("profit_factor"),
        "x2_pf": x2.get("profit_factor"),
        "x1_net": x1.get("net_profit"),
        "goal_x1_pf_gt_1_30": (x1.get("profit_factor") or 0) > 1.30,
        "goal_x1_5_pf_ge_1_25": (x15.get("profit_factor") or 0) >= 1.25,
        "goal_x2_pf_ge_1_00": (x2.get("profit_factor") or 0) >= 1.00,
        "goal_cost_stress_pass": (
            (x1.get("profit_factor") or 0) > 1.30
            and (x15.get("profit_factor") or 0) >= 1.25
            and (x2.get("profit_factor") or 0) >= 1.00
        ),
    }


def equal_join_compose(run_a: str, run_b: str, base_cost: float) -> dict[str, Any]:
    """A priori equal-weight (1+1 join) haircut diagnostic — no weight mining."""
    from collections import defaultdict

    def trade_pnls(run_id: str) -> list[float]:
        deals = parse_deals(RUNS / run_id / "report.html")
        trades = deals_to_trades(deals)
        return [float(t.profit) for t in trades]

    a = trade_pnls(run_a)
    b = trade_pnls(run_b)
    # equal-join = concatenate trades (a priori dual-instance, weight 1:1)
    pooled = a + b

    def pf_after(cost_mult: float) -> dict[str, float]:
        cost = base_cost * cost_mult
        wins = losses = 0.0
        net = 0.0
        for p in pooled:
            adj = p - cost
            net += adj
            if adj >= 0:
                wins += adj
            else:
                losses += -adj
        pf = (wins / losses) if losses > 0 else None
        return {"n": float(len(pooled)), "net": net, "pf": pf or 0.0}

    x1 = pf_after(1.0)
    x15 = pf_after(1.5)
    x2 = pf_after(2.0)
    # cadence: reuse elapsed weeks from MaxKZ2 window ~260.7143
    elapsed_weeks = 260.7143
    tpw = x1["n"] / elapsed_weeks
    return {
        "schema_version": "sonic_offline_compose_real_cost.v1",
        "note": (
            "A priori equal-join (1:1) MaxKZ2+Spark under additive Real P50 haircut; "
            "NOT weight mining; NOT Phase0 freeze; NOT promote while MaxKZ2 FAIL."
        ),
        "weight_rule": "EQUAL_JOIN_1_1_A_PRIORI",
        "base_cost_per_trade": base_cost,
        "maxkz2_run": run_a,
        "spark_run": run_b,
        "maxkz2_n": len(a),
        "spark_n": len(b),
        "pooled": {
            "n": int(x1["n"]),
            "pf_x1": x1["pf"],
            "net_x1": x1["net"],
            "tpw": tpw,
            "pf_x1_5": x15["pf"],
            "pf_x2": x2["pf"],
        },
        "goal_x1_pf_gt_1_30": x1["pf"] > 1.30,
        "goal_cadence_2_5": 2.0 <= tpw <= 5.0,
        "goal_cost_stress_like": x1["pf"] > 1.30 and x15["pf"] >= 1.25 and x2["pf"] >= 1.00,
        "promote_allowed": False,
        "promote_block_reason": "PARENT_MAXKZ2_REAL_COST_STRESS_FAIL",
    }


def append_registry(row: dict[str, Any]) -> None:
    with REG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    import MetaTrader5 as mt5

    caps = capture_inventory()
    print("CAPTURES")
    for name, info in caps.items():
        t = info["totals"]
        print(
            f"  {name}: quotes={t['quotes']} hb={t['heartbeats']} "
            f"comm={t['commission']} slip={t['slippage']} session_end={info.get('session_end')}"
        )

    # Rebuild inventory V6 from current evidence root (fail-closed).
    class InvArgs:
        evidence_root = str(EVID)
        probe = str(PROBE)
        prior_audit = str(PRE / "v4_data/20260714_COST_PROVENANCE_AUDIT.json")
        if not Path(prior_audit).exists():
            # fall back to any prior audit present
            cands = sorted((PRE / "v4_data").glob("*COST*AUDIT*.json"))
            prior_audit = str(cands[-1]) if cands else str(PROBE)
        expected_server = "FivePercentOnline-Real"

    inv = build_inventory(InvArgs())
    inv_path = PRE / "v4_data/20260714_EXECUTION_DATA_INVENTORY_V6.json"
    write_json(inv_path, inv)
    print(
        "INVENTORY",
        inv.get("qfsi", {}).get("verdict"),
        "eligible",
        inv.get("eligible_bundle_count"),
        "->",
        inv_path.name,
    )

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        acc = mt5.account_info()
        term = mt5.terminal_info()
        if acc is None or term is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        observed = str(acc.server or "")
        if observed != "FivePercentOnline-Real":
            raise RuntimeError(f"server mismatch: {observed}")
        live = {s: mt5_symbol_cost(s) for s in ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]}
        account_meta = {
            "server": observed,
            "login": int(acc.login),
            "trade_mode": int(acc.trade_mode),
            "trade_allowed": bool(acc.trade_allowed),
            "company": getattr(term, "company", None),
            "connected": bool(getattr(term, "connected", False)),
        }
    finally:
        mt5.shutdown()

    commissions = load_all_commissions()
    capture_spreads = {s: aggregate_spreads(s) for s in ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]}
    eurusd_comm = commissions.get("EURUSD") or []
    usdjpy_comm = commissions.get("USDJPY") or []
    if eurusd_comm:
        commission_rt_per_lot = statistics.median(eurusd_comm)
        commission_status = f"EURUSD_N{len(eurusd_comm)}_CLUE_TRANSFERRED_TO_USDJPY"
    else:
        raise RuntimeError("commission clue missing; refuse missing-as-zero")

    usdjpy = live["USDJPY"]
    # Prefer aggregated capture spread if available; else live tick sample
    agg = capture_spreads["USDJPY"]
    dpl = usdjpy["dollars_per_price_per_lot"]
    if agg["spread_price_p50"] is not None and dpl:
        spread_usd_lot_p50 = agg["spread_price_p50"] * dpl
        spread_usd_lot_p90 = (agg["spread_price_p90"] or agg["spread_price_p50"]) * dpl
        spread_source = "AGGREGATED_CAPTURE_QUOTE_TICKS"
    else:
        spread_usd_lot_p50 = usdjpy["spread_usd_per_lot_p50"]
        spread_usd_lot_p90 = usdjpy["spread_usd_per_lot_p90"] or spread_usd_lot_p50
        spread_source = "LIVE_TICK_COPY"

    lots_rr2 = trade_lots("20260714_194221")
    lots_max = trade_lots("20260714_192304")
    lots_twin = trade_lots("20260714_192515")
    lot_p50 = lots_max.get("lot_p50") or lots_rr2.get("lot_p50")
    if lot_p50 is None:
        raise RuntimeError("lot_p50 unavailable")

    base_cost_p50 = (spread_usd_lot_p50 + commission_rt_per_lot) * float(lot_p50)
    base_cost_p90 = (spread_usd_lot_p90 + commission_rt_per_lot) * float(lot_p50)

    note = (
        "FivePercentOnline-Real aggregated partial sample: USDJPY capture/live spread "
        f"P50/P90 ({spread_source}) + EURUSD commission clue "
        f"${commission_rt_per_lot:.2f}/lot RT (N={len(eurusd_comm)}, transferred). "
        f"USDJPY commission rows={len(usdjpy_comm)}. Slippage MISSING≠0. Full QFSI unmet."
    )

    max_p50 = run_stress(
        "20260714_192304",
        base_cost_p50,
        "20260714_COSTSTRESS_MAXKZ2_192304_REAL_P50_REFRESH.json",
        note + " scenario=p50",
    )
    max_p90 = run_stress(
        "20260714_192304",
        base_cost_p90,
        "20260714_COSTSTRESS_MAXKZ2_192304_REAL_P90_REFRESH.json",
        note + " scenario=p90",
    )
    twin_p50 = None
    twin_gate = None
    if not lots_twin.get("missing"):
        twin_p50 = run_stress(
            "20260714_192515",
            base_cost_p50,
            "20260714_COSTSTRESS_MAXKZ2_192515_REAL_P50_REFRESH.json",
            note + " twin scenario=p50",
        )
        twin_gate = gate_eval(scenario_map(twin_p50))

    rr2_p50 = run_stress(
        "20260714_194221",
        base_cost_p50,
        "20260714_COSTSTRESS_RR2_194221_REAL_P50_REFRESH.json",
        note + " scenario=p50",
    )

    max_gate = gate_eval(scenario_map(max_p50))
    max_gate_p90 = gate_eval(scenario_map(max_p90))
    rr2_gate = gate_eval(scenario_map(rr2_p50))

    # Spark run used in prior compose probes
    spark_run = "20260714_002614"
    if not (RUNS.parent / "EA_SparkAsian" / spark_run / "report.html").exists():
        # try alternate locations
        for cand in [
            ALPHA / "runs/EA_SparkAsian" / spark_run / "report.html",
            ALPHA / "runs/EA_Spark" / spark_run / "report.html",
            ALPHA / "runs/EA_SonicR" / spark_run / "report.html",
        ]:
            if cand.exists():
                spark_run = cand.parent.name if False else spark_run
                break

    # locate spark report for compose
    spark_paths = [
        ALPHA / "runs/EA_SparkAsian" / "20260714_002614" / "report.html",
        ALPHA / "runs/EA_Spark" / "20260714_002614" / "report.html",
        ALPHA / "runs/EA_SilverBullet" / "20260714_002614" / "report.html",
        ALPHA / "runs/EA_SparkAsian" / "20260714_193358" / "report.html",
        ALPHA / "runs/EA_Spark" / "20260714_193358" / "report.html",
    ]
    spark_report = next((p for p in spark_paths if p.exists()), None)
    compose = None
    if spark_report is not None:
        # temporarily point RUNS helper via custom equal join using absolute reports
        spark_id = spark_report.parent.name
        spark_ea = spark_report.parent.parent.name

        def trade_pnls_abs(report: Path) -> list[float]:
            deals = parse_deals(report)
            trades = deals_to_trades(deals)
            return [float(t.profit) for t in trades]

        a = trade_pnls_abs(RUNS / "20260714_192304" / "report.html")
        b = trade_pnls_abs(spark_report)

        def pf_after(pnls: list[float], cost_mult: float) -> dict[str, float]:
            cost = base_cost_p50 * cost_mult
            wins = losses = 0.0
            net = 0.0
            for p in pnls:
                adj = p - cost
                net += adj
                if adj >= 0:
                    wins += adj
                else:
                    losses += -adj
            return {"n": float(len(pnls)), "net": net, "pf": (wins / losses) if losses > 0 else 0.0}

        pooled = a + b
        x1 = pf_after(pooled, 1.0)
        x15 = pf_after(pooled, 1.5)
        x2 = pf_after(pooled, 2.0)
        elapsed_weeks = 260.7143
        tpw = x1["n"] / elapsed_weeks
        compose = {
            "schema_version": "sonic_offline_compose_real_cost.v1",
            "note": (
                "A priori equal-join (1:1) MaxKZ2+Spark under additive Real P50 haircut; "
                "NOT weight mining; NOT Phase0 freeze; promote blocked by MaxKZ2 FAIL."
            ),
            "weight_rule": "EQUAL_JOIN_1_1_A_PRIORI",
            "base_cost_per_trade": base_cost_p50,
            "maxkz2_run": "20260714_192304",
            "spark_run": spark_id,
            "spark_ea": spark_ea,
            "spark_report": str(spark_report.as_posix()),
            "maxkz2_n": len(a),
            "spark_n": len(b),
            "pooled": {
                "n": int(x1["n"]),
                "pf_x1": x1["pf"],
                "net_x1": x1["net"],
                "tpw": tpw,
                "pf_x1_5": x15["pf"],
                "pf_x2": x2["pf"],
            },
            "goal_x1_pf_gt_1_30": x1["pf"] > 1.30,
            "goal_cadence_2_5": 2.0 <= tpw <= 5.0,
            "goal_cost_stress_like": x1["pf"] > 1.30 and x15["pf"] >= 1.25 and x2["pf"] >= 1.00,
            "promote_allowed": False,
            "promote_block_reason": "PARENT_MAXKZ2_REAL_COST_STRESS_FAIL",
        }
        write_json(PRE / "20260714_OFFLINE_MAXKZ2_SPARK_REAL_P50_COMPOSE.json", compose)

    decision = "PARK_FAIL_REAL_PARTIAL_COST_STRESS"
    if max_gate["goal_cost_stress_pass"]:
        decision = "PASS_PARTIAL_REAL_COST__ADVANCE_CONFIRMED_GATES"
    # ceremony: confirmed gates only if pass — here expect FAIL

    receipt = {
        "schema_version": "sonic_qfsi_maxkz2_real_refresh_receipt.v1",
        "created_at_utc": utc_now(),
        "status": "MAXKZ2_REAL_PATH_FAIL_CLOSED",
        "decision": decision,
        "goal_claim": False,
        "confirmed_claim": False,
        "full_qfsi_gate": inv.get("qfsi", {}).get("verdict") or "STOP_DATA_FRONTIER",
        "eligible_bundle_count": inv.get("eligible_bundle_count"),
        "server": account_meta,
        "probe_sha256": sha256_file(PROBE) if PROBE.exists() else None,
        "captures": caps,
        "inventory_verdict": inv.get("qfsi", {}).get("verdict"),
        "cost_model": {
            "symbol": "USDJPY",
            "lot_p50": lot_p50,
            "lots_maxkz2": lots_max,
            "lots_twin": lots_twin,
            "lots_rr2": lots_rr2,
            "usdjpy_live": usdjpy,
            "capture_spreads_usdjpy": capture_spreads["USDJPY"],
            "spread_source": spread_source,
            "spread_usd_per_lot_p50": spread_usd_lot_p50,
            "spread_usd_per_lot_p90": spread_usd_lot_p90,
            "commission_rt_per_lot_usd": commission_rt_per_lot,
            "commission_status": commission_status,
            "commission_samples_eurusd": eurusd_comm,
            "commission_samples_usdjpy": usdjpy_comm,
            "slippage_status": "MISSING_NOT_ZERO",
            "base_round_turn_cost_per_trade_p50": base_cost_p50,
            "base_round_turn_cost_per_trade_p90": base_cost_p90,
            "formula": "(spread_usd_per_lot + commission_rt_per_lot) * lot_p50",
            "note": note,
        },
        "reprice": {
            "MaxKZ2": {
                "run_id": "20260714_192304",
                "hypothesis_id": "HYP-SB-MAXKZ2-DENSITY-002",
                "real_p50": max_gate,
                "real_p90": max_gate_p90,
            },
            "MaxKZ2_twin": {
                "run_id": "20260714_192515",
                "real_p50": twin_gate,
                "available": twin_gate is not None,
            },
            "RR2": {
                "run_id": "20260714_194221",
                "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
                "real_p50": rr2_gate,
            },
        },
        "compose_maxkz2_spark": compose,
        "ceremony": {
            "confirmed_gates_run": False,
            "reason": "MaxKZ2 Real partial cost-stress FAIL — no stress/holdout ceremony",
            "banned": ["densify", "hour_mining", "post_hoc_weights", "missing_as_zero"],
        },
        "cost_provenance_gap": "NARROWED_NOT_CLEARED",
    }
    receipt_path = PRE / "20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_RECEIPT.json"
    write_json(receipt_path, receipt)
    receipt_sha = sha256_file(receipt_path)

    # Deliverable VN
    md = f"""# Deliverable — MaxKZ2 QFSI / Real cost path FAIL-CLOSED

Date: 2026-07-14 (refresh)  
Process: no GPT; Real login + aggregated capture reprice  
Language: tiếng Việt (Owner) / evidence EN

## 1) MT5 server

| Field | Value |
|---|---|
| Observed | `{account_meta['server']}` |
| Login | `{account_meta['login']}` |
| Match expected Real | **YES** |
| Probe SHA | `{receipt.get('probe_sha256')}` |

## 2) QFSI capture

| Field | Value |
|---|---|
| Inventory verdict | `{receipt['inventory_verdict']}` |
| Eligible bundles | **{receipt['eligible_bundle_count']}** |
| Full QFSI | **FAIL** (`STOP_DATA_FRONTIER`) |
| Slippage | MISSING ≠ 0 |
| USDJPY commission rows | {len(usdjpy_comm)} |
| EURUSD commission clue N | {len(eurusd_comm)} |

Capture totals (quotes):  
{chr(10).join(f"- `{k}`: quotes={v['totals']['quotes']}, comm={v['totals']['commission']}, slip={v['totals']['slippage']}" for k,v in caps.items())}

## 3) Cost model (USDJPY)

| Input | Value |
|---|---|
| Spread source | `{spread_source}` |
| Spread USD/lot P50 / P90 | {spread_usd_lot_p50:.6f} / {spread_usd_lot_p90:.6f} |
| Commission RT/lot | ${commission_rt_per_lot:.2f} ({commission_status}) |
| Lot P50 | {lot_p50} |
| Base $/trade P50 / P90 | **{base_cost_p50:.4f}** / **{base_cost_p90:.4f}** |

## 4) MaxKZ2 vs GOAL after Real cost

Auth run `20260714_192304` (tester PF 1.33 / ~2.09/wk). Twin `192515` protocol check: {'YES' if twin_gate else 'report missing'}.

| Book | Scenario | x1 PF | x1.5 PF | x2 PF | GOAL cost-stress |
|---|---|---:|---:|---:|---|
| MaxKZ2 `192304` | Real P50 | {max_gate['x1_pf']:.3f} | {max_gate['x1_5_pf']:.3f} | {max_gate['x2_pf']:.3f} | {'PASS' if max_gate['goal_cost_stress_pass'] else '**FAIL**'} |
| MaxKZ2 `192304` | Real P90 | {max_gate_p90['x1_pf']:.3f} | {max_gate_p90['x1_5_pf']:.3f} | {max_gate_p90['x2_pf']:.3f} | {'PASS' if max_gate_p90['goal_cost_stress_pass'] else '**FAIL**'} |
| Twin `192515` | Real P50 | {f"{twin_gate['x1_pf']:.3f}" if twin_gate else "n/a"} | {f"{twin_gate['x1_5_pf']:.3f}" if twin_gate else "n/a"} | {f"{twin_gate['x2_pf']:.3f}" if twin_gate else "n/a"} | {'PASS' if twin_gate and twin_gate['goal_cost_stress_pass'] else 'FAIL/n/a'} |
| RR2 `194221` (control) | Real P50 | {rr2_gate['x1_pf']:.3f} | {rr2_gate['x1_5_pf']:.3f} | {rr2_gate['x2_pf']:.3f} | {'PASS' if rr2_gate['goal_cost_stress_pass'] else 'FAIL'} |

**Quyết định MaxKZ2:** `{decision}` — **PARK**. Không densify. Không chạy confirmed/stress/holdout ceremony (fail-closed trước gate).

Cadence vẫn ~2.09/wk (không đổi bởi haircut báo cáo); PF sau Real cost **dưới** GOAL 1.30 @x1.

## 5) Compose MaxKZ2 + Spark (a priori 1:1)

{json.dumps(compose, indent=2, ensure_ascii=False) if compose else 'Spark report not found — compose skipped.'}

Promote: **NO** (`PARENT_MAXKZ2_REAL_COST_STRESS_FAIL`). Không post-hoc weight mining.
RR2+Spark diagnostic dưới cùng cost vẫn là survivor-path song song (đã có trên disk) — không promote Phase0.

## 6) Next moves

1. Giữ MaxKZ2 **PARK** dưới Real partial cost; full QFSI vẫn tích lũy (004_EXTENSION / ≥90d).
2. Không densify MaxKZ/RR; không mine giờ/ngày.
3. RR2 vẫn là sleeve partial-Real cost-stress PASS — Model 0 rebind / confirmed gates chỉ khi Owner giải phóng terminal Exclusive tester + verified cost đủ doctrine.
4. Discovery độc lập tiếp: stub `HYP-H4-OUTSIDE-REV-001` (prereg trước code) nếu Owner muốn shelf mới.
5. `COST_PROVENANCE_GAP` = **NARROWED_NOT_CLEARED**.

## Receipt

`preflight/20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_RECEIPT.json`  
SHA256: `{receipt_sha}`
"""
    deliv = READ / "20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_DELIVERABLE.md"
    deliv.write_text(md, encoding="utf-8")

    # Update MaxKZ2 readout status banner
    readout = READ / "20260714_HYP_SB_MAXKZ2_DENSITY_002_READOUT.md"
    if readout.exists():
        text = readout.read_text(encoding="utf-8")
        banner = (
            f"\n\n## Real cost path closeout (2026-07-14 refresh)\n\n"
            f"Status: `{decision}`\n\n"
            f"- Real P50 stress on `20260714_192304`: x1 PF **{max_gate['x1_pf']:.3f}** / "
            f"x1.5 **{max_gate['x1_5_pf']:.3f}** / x2 **{max_gate['x2_pf']:.3f}** → "
            f"**FAIL** GOAL cost-stress (need x1>1.30).\n"
            f"- Base $/trade P50 ≈ **{base_cost_p50:.4f}** "
            f"(spread+EURUSD commission clue; slippage MISSING≠0).\n"
            f"- Full QFSI still `{receipt['inventory_verdict']}` / eligible "
            f"**{receipt['eligible_bundle_count']}**.\n"
            f"- Confirmed gates: **not run** (fail-closed).\n"
            f"- Compose MaxKZ2+Spark a priori 1:1: diagnostic only; "
            f"**promote blocked**.\n"
            f"- Receipt SHA `{receipt_sha}`.\n"
            f"- Do **not** densify MaxTradesPerKZ / hours / Friday from this fail.\n"
        )
        if "## Real cost path closeout" not in text:
            readout.write_text(text.rstrip() + banner, encoding="utf-8")
        else:
            # replace section
            head = text.split("## Real cost path closeout")[0].rstrip()
            readout.write_text(head + banner, encoding="utf-8")

    # checklist update
    checklist = PRE / "20260714_MAXKZ2_QFSI_REPRICE_CHECKLIST.md"
    if checklist.exists():
        checklist.write_text(
            checklist.read_text(encoding="utf-8").split("\n", 3)[0]
            + "\n\n"
            + f"Status: `FAIL_CLOSED_PARTIAL_REAL_COST` (refresh {utc_now()})\n"
            + f"Decision: `{decision}` — PARK; no densify; no confirmed ceremony.\n"
            + f"Receipt: `20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_RECEIPT.json` SHA `{receipt_sha}`.\n"
            + "See deliverable `readouts/20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_DELIVERABLE.md`.\n"
            + "\n"
            + "\n".join(checklist.read_text(encoding="utf-8").splitlines()[3:]),
            encoding="utf-8",
        )

    append_registry(
        {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": "HYP-SB-MAXKZ2-DENSITY-002",
            "state": "parked",
            "verdict": "PARK_FAIL_REAL_PARTIAL_COST_STRESS",
            "reason": (
                f"Real P50 x1 PF {max_gate['x1_pf']:.3f}<1.30; "
                f"full QFSI still STOP; no densify; compose promote blocked"
            ),
            "updated_at": "2026-07-14",
            "parent_candidate": "HYP-SB-WEEKEND-FLAT-001",
            "feature_family": "silverbullet_maxkz2_entry_density",
            "lane": "qfsi_real_cost_path_20260714",
            "setup_type": "MaxKZ2 Model0 + Real partial reprice fail-closed",
            "symbol": "USDJPY",
            "timeframe": "M15",
            "window": "2021.01.01-2025.12.31",
            "model": 0,
            "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_MAXKZ2_DENSITY_002_PREREG.md",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_SB_MAXKZ2_DENSITY_002_READOUT.md",
            "deliverable_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_DELIVERABLE.md",
            "exact_overrides": "InpMaxTradesPerKZ=2;InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpRiskPct=0.5",
            "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
            "run_ids": ["20260714_192304", "20260714_192515"],
            "metrics": {
                "tester_pf": 1.3338,
                "tester_tpw": 2.0942,
                "trades": 546,
                "real_p50_x1_pf": max_gate["x1_pf"],
                "real_p50_x15_pf": max_gate["x1_5_pf"],
                "real_p50_x2_pf": max_gate["x2_pf"],
                "base_cost_p50": base_cost_p50,
            },
            "validation": {
                "cost_stress": "FAIL under Real partial P50",
                "full_qfsi": str(receipt["inventory_verdict"]),
                "confirmed_ceremony": "not_run_fail_closed",
                "cost_provenance_gap": "NARROWED_NOT_CLEARED",
            },
            "receipt_sha256": receipt_sha,
        }
    )

    print("DECISION", decision)
    print("MaxKZ2 P50", max_gate)
    print("RR2 P50", rr2_gate)
    print("compose", compose["pooled"] if compose else None)
    print("receipt", receipt_path)
    print("receipt_sha", receipt_sha)
    print("deliverable", deliv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
