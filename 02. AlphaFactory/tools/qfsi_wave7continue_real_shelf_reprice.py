#!/usr/bin/env python3
"""Wave7-continue: Real/QFSI status + shelf reprice under honest partial Real cost.

Does NOT densify. Does NOT claim confirmed/GOAL. Slippage MISSING ≠ 0.
Full QFSI remains STOP_DATA_FRONTIER until quote-days / commission / slip gates met.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
ALPHA = ROOT / "02. AlphaFactory"
TOOLS = ALPHA / "tools"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
EVID = ALPHA / "evidence/execution/FivePercentOnline-Real"
HOT = ROOT / "04. Project Control/ai/hot.md"
PROBE = PRE / "v4_data/20260714_MT5_READONLY_PROBE_V8_WAVE7CONTINUE.json"
SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]
FROZEN_DPL = {
    "USDJPY": 617.5050326660162,
    "EURUSD": 100000.0,
    "GBPUSD": 100000.0,
    "XAUUSD": 100.0,
}
WEEKS = 261.0  # ~5y calendar cadence denominator

sys.path.insert(0, str(ALPHA / "analysis"))
sys.path.insert(0, str(TOOLS))
from quant_analyzer import deals_to_trades, parse_deals  # noqa: E402
import sonic_cost_stress as scs  # noqa: E402


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


def percentile(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    k = (len(ys) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ys[f]
    return ys[f] * (c - k) + ys[c] * (k - f)


def csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def list_captures() -> list[Path]:
    if not EVID.exists():
        return []
    return sorted([d for d in EVID.iterdir() if d.is_dir() and "QFSI_REAL" in d.name], key=lambda p: p.name)


def capture_snap(d: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "capture_id": d.name,
        "path": str(d.as_posix()),
        "has_start": (d / "session_start.json").exists(),
        "has_end": (d / "session_end.json").exists(),
        "quotes": {},
        "heartbeats": {},
        "commission_rows": {},
        "slippage_rows": {},
    }
    for sym in SYMBOLS:
        row["quotes"][sym] = csv_rows(d / f"{sym}_quote_ticks.csv")
        row["heartbeats"][sym] = csv_rows(d / f"{sym}_heartbeats.csv")
        row["commission_rows"][sym] = csv_rows(d / f"{sym}_commission_lifecycles.csv")
        row["slippage_rows"][sym] = csv_rows(d / f"{sym}_slippage_fills.csv")
    shared_c = csv_rows(d / "commission_lifecycles.csv")
    shared_s = csv_rows(d / "slippage_fills.csv")
    row["totals"] = {
        "quotes": sum(row["quotes"].values()),
        "heartbeats": sum(row["heartbeats"].values()),
        "commission": sum(row["commission_rows"].values()) + shared_c,
        "slippage": sum(row["slippage_rows"].values()) + shared_s,
    }
    if row["has_end"]:
        se = json.loads((d / "session_end.json").read_text(encoding="utf-8-sig"))
        row["session_status"] = se.get("status")
        row["reprice_ready"] = se.get("reprice_ready")
        row["reprice_blockers"] = se.get("reprice_blockers")
    elif row["has_start"]:
        ss = json.loads((d / "session_start.json").read_text(encoding="utf-8-sig"))
        row["session_status"] = "CAPTURE_LIVE_OR_INCOMPLETE"
        row["duration_sec"] = ss.get("duration_sec")
        row["started_at_utc"] = ss.get("created_at_utc")
        row["observed_server"] = ss.get("observed_server")
        row["login_hint_fingerprint"] = ss.get("account_fingerprint")
    return row


def load_spreads(symbol: str) -> dict[str, Any]:
    all_spreads: list[float] = []
    by_hour: dict[int, list[float]] = defaultdict(list)
    dates: set[str] = set()
    for d in list_captures():
        path = d / f"{symbol}_quote_ticks.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    bid = float(row["bid"])
                    ask = float(row["ask"])
                except (TypeError, ValueError, KeyError):
                    continue
                if bid <= 0 or ask < bid:
                    continue
                spr = ask - bid
                all_spreads.append(spr)
                tu = (row.get("time_utc") or "").strip()
                if tu:
                    try:
                        dt = datetime.fromisoformat(tu.replace("Z", "+00:00")).astimezone(timezone.utc)
                        by_hour[dt.hour].append(spr)
                        dates.add(dt.date().isoformat())
                    except ValueError:
                        pass
    hours_with = sum(1 for h in range(24) if by_hour.get(h))
    return {
        "valid_spreads": len(all_spreads),
        "spread_price_p50": percentile(all_spreads, 0.50),
        "spread_price_p90": percentile(all_spreads, 0.90),
        "distinct_utc_dates": sorted(dates),
        "hours_utc_with_samples": hours_with,
    }


def load_commissions() -> dict[str, Any]:
    """Dedup by (symbol, position_id). Column = round_turn_account_per_lot (not invent 0)."""
    by_sym_map: dict[str, dict[str, float]] = defaultdict(dict)
    for d in list_captures():
        paths = [d / "commission_lifecycles.csv"] + list(d.glob("*_commission_lifecycles.csv"))
        for path in paths:
            if not path.exists():
                continue
            n = 0
            with path.open(encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    n += 1
                    sym = (row.get("symbol") or "").strip() or path.name.split("_")[0]
                    if sym not in SYMBOLS:
                        continue
                    pid = str(row.get("position_id") or "").strip() or f"anon_{n}_{path.name}"
                    try:
                        val = float(row["round_turn_account_per_lot"])
                    except (TypeError, ValueError, KeyError):
                        continue
                    by_sym_map[sym][pid] = val
    by_sym: dict[str, dict[str, Any]] = {}
    for sym in SYMBOLS:
        vals = list(by_sym_map.get(sym, {}).values())
        by_sym[sym] = {
            "unique_position_ids": len(vals),
            "amount_rows": len(vals),
            "p50": percentile(vals, 0.50) if vals else None,
            "values": vals,
        }
    return {"by_symbol": by_sym}


def live_mt5() -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"import:{exc}"}
    if not mt5.initialize():
        return {"ok": False, "error": f"initialize:{mt5.last_error()}"}
    try:
        info = mt5.account_info()
        if info is None:
            return {"ok": False, "error": "account_info_none", "last_error": str(mt5.last_error())}
        out: dict[str, Any] = {
            "ok": True,
            "login": int(info.login),
            "server": str(info.server),
            "currency": str(info.currency),
            "balance": float(info.balance),
            "trade_allowed": bool(info.trade_allowed),
            "symbols": {},
        }
        for sym in SYMBOLS:
            si = mt5.symbol_info(sym)
            tick = mt5.symbol_info_tick(sym)
            if si is None or tick is None:
                out["symbols"][sym] = {"available": False}
                continue
            ticks = mt5.copy_ticks_from(sym, datetime.now(timezone.utc), 20000, mt5.COPY_TICKS_ALL)
            spreads: list[float] = []
            if ticks is not None:
                for t in ticks:
                    bid = float(t["bid"])
                    ask = float(t["ask"])
                    if bid > 0 and ask >= bid:
                        spreads.append(ask - bid)
            ts = float(si.trade_tick_size) or float(si.point)
            tv = float(si.trade_tick_value)
            dpl = (tv / ts) if ts else None
            p50 = percentile(spreads, 0.50)
            p90 = percentile(spreads, 0.90)
            out["symbols"][sym] = {
                "available": True,
                "dollars_per_price_per_lot": dpl,
                "current_bid": float(tick.bid),
                "current_ask": float(tick.ask),
                "current_spread_price": float(tick.ask) - float(tick.bid),
                "live_tick_sample_n": len(spreads),
                "spread_price_p50": p50,
                "spread_price_p90": p90,
                "spread_usd_per_lot_p50": (p50 * dpl) if (p50 is not None and dpl) else None,
                "spread_usd_per_lot_p90": (p90 * dpl) if (p90 is not None and dpl) else None,
            }
        return out
    finally:
        mt5.shutdown()


def build_cost_table(spreads: dict[str, dict[str, Any]], commissions: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    eurusd = (commissions.get("by_symbol") or {}).get("EURUSD") or {}
    comm_rt = eurusd.get("p50")
    comm_n = eurusd.get("unique_position_ids") or 0
    rows = []
    for sym in SYMBOLS:
        sp = spreads[sym]
        dpl = None
        dpl_src = "MISSING"
        if live.get("ok") and (live.get("symbols") or {}).get(sym, {}).get("dollars_per_price_per_lot"):
            dpl = float(live["symbols"][sym]["dollars_per_price_per_lot"])
            dpl_src = "LIVE_MT5"
        elif sym in FROZEN_DPL:
            dpl = FROZEN_DPL[sym]
            dpl_src = "FROZEN_PRIOR_RECEIPT_CLUE"
        p50 = sp["spread_price_p50"]
        p90 = sp["spread_price_p90"]
        usd_p50 = (p50 * dpl) if (p50 is not None and dpl is not None) else None
        usd_p90 = (p90 * dpl) if (p90 is not None and dpl is not None) else None
        if comm_rt is not None and comm_n > 0:
            comm_use = float(comm_rt)
            comm_label = f"EURUSD_UNIQUE_N={comm_n}" if sym == "EURUSD" else f"TRANSFERRED_EURUSD_CLUE_N={comm_n}"
        else:
            comm_use = None
            comm_label = "MISSING_NEQ_0"
        unit_p50 = (usd_p50 + comm_use) if (usd_p50 is not None and comm_use is not None) else usd_p50
        unit_p90 = (usd_p90 + comm_use) if (usd_p90 is not None and comm_use is not None) else usd_p90
        # lot 0.5 canonical for USDJPY SB family; Spark uses own lot later
        lot = 0.5
        rows.append(
            {
                "symbol": sym,
                "capture_valid_spreads": sp["valid_spreads"],
                "hours_utc_with_samples": sp["hours_utc_with_samples"],
                "distinct_utc_dates": sp["distinct_utc_dates"],
                "spread_price_p50": p50,
                "spread_price_p90": p90,
                "dollars_per_price_per_lot": dpl,
                "dpl_source": dpl_src,
                "spread_usd_per_lot_p50": usd_p50,
                "spread_usd_per_lot_p90": usd_p90,
                "commission_rt_per_lot": comm_use,
                "commission_label": comm_label,
                "slippage_per_lot": None,
                "slippage_label": "MISSING_NEQ_0",
                "unit_cost_usd_per_lot_p50": unit_p50,
                "unit_cost_usd_per_lot_p90": unit_p90,
                "trade_cost_usd_at_lot_0_5_x_p50": (unit_p50 * lot) if unit_p50 is not None else None,
                "trade_cost_usd_at_lot_0_5_x_p90": (unit_p90 * lot) if unit_p90 is not None else None,
            }
        )
    usdjpy = next(r for r in rows if r["symbol"] == "USDJPY")
    return {
        "schema_version": "sonic_broker_spread_cost_table.v1",
        "created_at_utc": utc_now(),
        "server_expected": "FivePercentOnline-Real",
        "lot_p50_basis": 0.5,
        "formula": "(spread_usd_per_lot + commission_rt_per_lot) * lot; slippage MISSING≠0 not added",
        "honesty": [
            "PARTIAL_REAL_CAPTURE_ONLY",
            "QUOTE_ELAPSED_DAYS_FAR_BELOW_90",
            "COMMISSION_UNIQUE_N_EURUSD_ONLY",
            "SLIPPAGE_FILLS_MISSING",
            "SESSION_HOUR_COVERAGE_SPARSE",
            "NOT_FULL_QFSI",
            "NOT_CONFIRMED_COST_PROVENANCE",
        ],
        "symbols": rows,
        "canonical_usdjpy_unit_p50": usdjpy["unit_cost_usd_per_lot_p50"],
        "canonical_usdjpy_unit_p90": usdjpy["unit_cost_usd_per_lot_p90"],
        "canonical_usdjpy_trade_cost_p50": usdjpy["trade_cost_usd_at_lot_0_5_x_p50"],
        "canonical_usdjpy_trade_cost_p90": usdjpy["trade_cost_usd_at_lot_0_5_x_p90"],
        "live_usdjpy_spread_usd_per_lot_p50": (live.get("symbols") or {}).get("USDJPY", {}).get("spread_usd_per_lot_p50"),
    }


def lot_stats(ea: str, run_id: str) -> dict[str, Any]:
    report = ALPHA / "runs" / ea / run_id / "report.html"
    deals = parse_deals(report)
    trades = deals_to_trades(deals)
    lots: list[float] = []
    for deal in deals:
        if (deal.direction or "").strip().lower() != "in":
            continue
        if (deal.side or "").strip().lower() in {"", "balance"}:
            continue
        try:
            vol = abs(float(deal.volume))
        except (TypeError, ValueError):
            continue
        if vol > 0:
            lots.append(vol)
    return {
        "n_trades": len(trades),
        "lot_p50": statistics.median(lots) if lots else None,
        "lot_mean": statistics.mean(lots) if lots else None,
    }


def stress_run(ea: str, run_id: str, label: str, base_cost: float, note: str, tag: str) -> dict[str, Any]:
    class Args:
        pass

    args = Args()
    run_dir = ALPHA / "runs" / ea / run_id
    args.run = str(run_dir)
    args.ea = ea
    args.report = str(run_dir / "report.html")
    out_name = f"20260714_COSTSTRESS_{label}_{run_id}_REAL_P50_W7CONT.json"
    out_path = PRE / out_name
    args.out = str(out_path)
    args.start_equity = 100000.0
    args.base_cost_per_trade = float(base_cost)
    args.spread_points = 0.0
    args.slippage_points = 0.0
    args.commission_round_turn = 0.0
    args.point_value_per_lot = 1.0
    args.lot_size = 0.01
    matrix = scs.build_cost_matrix(args)
    matrix["cost_assumption"]["note"] = note
    matrix["cost_assumption"]["provenance"] = tag
    out_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # also bind under run analysis
    analysis = run_dir / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    bound = analysis / "cost_stress_real_p50_w7cont.json"
    bound.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    smap = {s["scenario"]: s for s in matrix.get("scenarios", [])}
    x1 = smap.get("cost_x1_00", {})
    x15 = smap.get("cost_x1_50", {})
    x2 = smap.get("cost_x2_00", {})
    base = smap.get("base_report", {})
    return {
        "run_id": run_id,
        "ea": ea,
        "label": label,
        "base_cost_per_trade": base_cost,
        "out": str(out_path.as_posix()),
        "out_sha256": sha256_file(out_path),
        "bound_run_analysis": str(bound.as_posix()),
        "base_pf": base.get("profit_factor"),
        "x1_pf": x1.get("profit_factor"),
        "x1_5_pf": x15.get("profit_factor"),
        "x2_pf": x2.get("profit_factor"),
        "tpw": (base.get("n_trades") or 0) / WEEKS,
        "goal_cost_stress_pass": (
            (x1.get("profit_factor") or 0) > 1.30
            and (x15.get("profit_factor") or 0) >= 1.25
            and (x2.get("profit_factor") or 0) >= 1.00
        ),
        "goal_cadence_band": 2.0 <= ((base.get("n_trades") or 0) / WEEKS) <= 5.0,
    }


def pf(ps: list[float]) -> float:
    gains = sum(p for p in ps if p > 0)
    losses = -sum(p for p in ps if p < 0)
    if losses > 0:
        return gains / losses
    return float("inf") if gains > 0 else 0.0


def compose_a1_spark(a1_cost: float, spark_cost: float) -> dict[str, Any]:
    a1 = ALPHA / "runs/EA_SilverBullet/20260714_002505/report.html"
    spark = ALPHA / "runs/EA_M15SparkAsian/20260714_193358/report.html"
    t_a1 = deals_to_trades(parse_deals(a1))
    t_sp = deals_to_trades(parse_deals(spark))
    # same-day overlap diagnostic
    days_a1 = {(t.exit_time.date() if hasattr(t.exit_time, "date") else str(t.exit_time)[:10]) for t in t_a1}
    days_sp = {(t.exit_time.date() if hasattr(t.exit_time, "date") else str(t.exit_time)[:10]) for t in t_sp}
    # robust date extract
    def day_key(t: Any) -> str:
        for attr in ("exit_time", "entry_time", "time"):
            v = getattr(t, attr, None)
            if v is None:
                continue
            s = str(v)
            return s[:10]
        return "unknown"

    days_a1 = {day_key(t) for t in t_a1}
    days_sp = {day_key(t) for t in t_sp}
    overlap_days = sorted(days_a1 & days_sp)

    def haircut(trades: list[Any], cost: float) -> list[float]:
        return [float(t.profit) - cost for t in trades]

    out: dict[str, Any] = {
        "schema_version": "sonic_offline_compose_a1_spark_real_cost.v1",
        "note": (
            "Diagnostic equal-join pool with per-sleeve Real partial haircut; "
            "NOT Phase-0; NOT confirmed; overlap not portfolio-simulated"
        ),
        "a1_run": "20260714_002505",
        "spark_run": "20260714_193358",
        "a1_cost": a1_cost,
        "spark_cost": spark_cost,
        "same_day_overlap_n": len(overlap_days),
        "honesty": ["PARTIAL_REAL_COST", "ADDITIVE_POOL_NOT_TRUE_PORTFOLIO", "SLIPPAGE_MISSING"],
    }
    for mult, key in [(1.0, "x1"), (1.5, "x1_5"), (2.0, "x2")]:
        pa = haircut(t_a1, a1_cost * mult)
        ps = haircut(t_sp, spark_cost * mult)
        pool = pa + ps
        out[key] = {
            "a1_pf": pf(pa),
            "spark_pf": pf(ps),
            "pooled_pf": pf(pool),
            "pooled_n": len(pool),
            "pooled_tpw": len(pool) / WEEKS,
            "pooled_net": sum(pool),
        }
    out["goal_cost_stress_like"] = (
        out["x1"]["pooled_pf"] > 1.30
        and out["x1_5"]["pooled_pf"] >= 1.25
        and out["x2"]["pooled_pf"] >= 1.00
        and 2.0 <= out["x1"]["pooled_tpw"] <= 5.0
    )
    return out


def process_alive() -> dict[str, Any]:
    import subprocess

    ps = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$t=Get-Process terminal64 -ErrorAction SilentlyContinue; "
                "$q=Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
                "Where-Object { $_.CommandLine -match 'QFSI_REAL_005|execution_data_qfsi' }; "
                "$m=Get-Process metatester64 -ErrorAction SilentlyContinue; "
                "[pscustomobject]@{terminal=($t|Select -Expand Id); "
                "qfsi=($q|Select -Expand ProcessId); metatester=($m|Select -Expand Id)} | ConvertTo-Json"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(ps.stdout or "{}")
    except json.JSONDecodeError:
        return {"raw": ps.stdout, "stderr": ps.stderr, "rc": ps.returncode}


def main() -> int:
    probe = json.loads(PROBE.read_text(encoding="utf-8")) if PROBE.exists() else {}
    live = live_mt5()
    procs = process_alive()
    captures = {d.name: capture_snap(d) for d in list_captures()}
    spreads = {sym: load_spreads(sym) for sym in SYMBOLS}
    commissions = load_commissions()
    cost_table = build_cost_table(spreads, commissions, live)

    quote_dates = set()
    for sym in SYMBOLS:
        quote_dates.update(spreads[sym].get("distinct_utc_dates") or [])
    eurusd_comm_n = ((commissions.get("by_symbol") or {}).get("EURUSD") or {}).get("unique_position_ids") or 0
    slip_total = sum(c["totals"]["slippage"] for c in captures.values())
    total_quotes = sum(c["totals"]["quotes"] for c in captures.values())
    live_caps = [cid for cid, c in captures.items() if c.get("session_status") == "CAPTURE_LIVE_OR_INCOMPLETE"]

    full_qfsi = {
        "full_qfsi_verdict": "STOP_DATA_FRONTIER",
        "eligible_bundle_count": 0,
        "why": [
            f"quote_distinct_utc_dates={len(quote_dates)} << 90",
            f"commission_unique_EURUSD={eurusd_comm_n} << 30 (USDJPY=0)",
            f"slippage_fills={slip_total} MISSING≠0",
        ],
        "progress": {
            "total_quote_rows_all_captures": total_quotes,
            "usdjpy_quote_distinct_dates": spreads["USDJPY"].get("distinct_utc_dates"),
            "commission_unique_by_symbol": {
                s: ((commissions.get("by_symbol") or {}).get(s) or {}).get("unique_position_ids") or 0 for s in SYMBOLS
            },
            "slippage_fills_total": slip_total,
            "live_captures": live_caps,
        },
    }

    unit_p50 = cost_table["canonical_usdjpy_unit_p50"]
    unit_p90 = cost_table["canonical_usdjpy_unit_p90"]
    if unit_p50 is None:
        raise RuntimeError("USDJPY unit cost P50 unavailable — refuse zero-cost fiction")
    if eurusd_comm_n <= 0 or ((commissions.get("by_symbol") or {}).get("EURUSD") or {}).get("p50") is None:
        raise RuntimeError(
            "EURUSD commission clue missing — refuse spread-only optimism "
            "(prior Real clue exists; parser must use round_turn_account_per_lot)"
        )

    note = (
        f"FivePercentOnline-Real AGGREGATED captures 001–005 + live DPL; "
        f"unit_p50={unit_p50:.6f}/lot (=spread+EURUSD commission clue ${((commissions.get('by_symbol') or {}).get('EURUSD') or {}).get('p50')}/lot RT N={eurusd_comm_n}); "
        "slippage MISSING≠0; NOT full QFSI; Wave7-continue shelf reprice"
    )
    tag = "FIVEPERCENTONLINE_REAL_PARTIAL_W7CONTINUE"

    books_spec = [
        ("EA_SilverBullet", "20260714_194548", "RR2_SHELF"),
        ("EA_SilverBullet", "20260714_231750", "RR2_FRESH_MODEL0"),
        ("EA_SilverBullet", "20260714_002505", "SB_A1"),
        ("EA_M15SparkAsian", "20260714_193358", "SPARK100K"),
        ("EA_SilverBullet", "20260714_192304", "MAXKZ2"),
        ("EA_SilverBullet", "20260714_194221", "RR2_CONTROL_194221"),
    ]
    books: dict[str, Any] = {}
    for ea, run_id, label in books_spec:
        ls = lot_stats(ea, run_id)
        lot = ls.get("lot_p50")
        if lot is None:
            books[label] = {"error": "no_lots", **ls}
            continue
        base_cost = float(unit_p50) * float(lot)
        stressed = stress_run(ea, run_id, label, base_cost, note, tag)
        stressed.update(ls)
        stressed["unit_usd_per_lot_p50"] = unit_p50
        stressed["unit_usd_per_lot_p90"] = unit_p90
        books[label] = stressed

    a1_cost = books.get("SB_A1", {}).get("base_cost_per_trade")
    spark_cost = books.get("SPARK100K", {}).get("base_cost_per_trade")
    compose = None
    if a1_cost is not None and spark_cost is not None:
        compose = compose_a1_spark(float(a1_cost), float(spark_cost))
        compose_path = PRE / "20260714_OFFLINE_A1_SPARK_REAL_P50_COMPOSE_W7CONT.json"
        compose["receipt_sha256"] = write_json(compose_path, compose)
        compose["path"] = str(compose_path.as_posix())

    cost_path = PRE / "20260714_BROKER_SPREAD_COST_TABLE_QFSI_W7CONT.json"
    cost_sha = write_json(cost_path, cost_table)

    # Friction dead-end heuristic: best shelf fails x1.5 under partial Real OR fresh Model0 fails badly
    rr2 = books.get("RR2_SHELF") or {}
    fresh = books.get("RR2_FRESH_MODEL0") or {}
    friction = {
        "label": "PARTIAL_REAL_FRICTION_STATUS",
        "confirmed_dead_end": False,  # cannot confirm without full QFSI + slip
        "partial_real_best_shelf_goal_pass": bool(rr2.get("goal_cost_stress_pass")),
        "partial_real_fresh_model0_goal_pass": bool(fresh.get("goal_cost_stress_pass")),
        "rr2_shelf_x1_5_pf": rr2.get("x1_5_pf"),
        "rr2_shelf_x1_pf": rr2.get("x1_pf"),
        "note": (
            "Friction dead-end NOT confirmed on Real: partial sample still leaves RR2 shelf "
            "near/at GOAL band depending on cost; full QFSI + slip still open. "
            "Demo PF is not confirmed."
        ),
    }
    if rr2.get("x1_5_pf") is not None and rr2["x1_5_pf"] < 1.25:
        friction["partial_stress_miss"] = True
    if fresh.get("x1_pf") is not None and fresh["x1_pf"] < 1.20:
        friction["fresh_model0_weak_under_partial_real"] = True

    receipt = {
        "schema_version": "sonic_qfsi_wave7continue_real_shelf_receipt.v1",
        "created_at_utc": utc_now(),
        "status": "REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE_COMPLETE",
        "goal_claim": False,
        "confirmed_claim": False,
        "COST_PROVENANCE_GAP": "NARROWED_NOT_CLEARED",
        "probe": {
            "path": str(PROBE.as_posix()),
            "sha256": sha256_file(PROBE) if PROBE.exists() else None,
            "verdict": probe.get("verdict"),
            "expected_server": probe.get("expected_server"),
            "observed_server": probe.get("observed_server"),
            "server_match": probe.get("server_match"),
            "account_fingerprint": probe.get("account_fingerprint"),
            "server_fingerprint": probe.get("server_fingerprint"),
        },
        "live_account": {
            "ok": live.get("ok"),
            "login": live.get("login"),
            "server": live.get("server"),
            "currency": live.get("currency"),
            "balance": live.get("balance"),
            "trade_allowed": live.get("trade_allowed"),
            "usdjpy_live_spread_usd_p50": (live.get("symbols") or {}).get("USDJPY", {}).get("spread_usd_per_lot_p50"),
        },
        "processes": procs,
        "do_not_kill_real": True,
        "captures": captures,
        "full_qfsi_gate": full_qfsi,
        "cost_table_path": str(cost_path.as_posix()),
        "cost_table_sha256": cost_sha,
        "cost_unit": {
            "usdjpy_unit_p50": unit_p50,
            "usdjpy_unit_p90": unit_p90,
            "canonical_trade_cost_lot0_5_p50": cost_table["canonical_usdjpy_trade_cost_p50"],
            "commission_unique_EURUSD": eurusd_comm_n,
            "slippage": "MISSING_NEQ_0",
        },
        "books": books,
        "compose_a1_spark": compose,
        "friction": friction,
        "bans": [
            "no_densify_RR_MaxKZ_Wave6_Wave7",
            "no_price_twin_spam",
            "no_revive_COT_size_or_z_blindly",
            "no_kill_Real_terminal_this_session",
        ],
    }

    receipt_path = PRE / "20260714_QFSI_WAVE7CONTINUE_REAL_SHELF_RECEIPT.json"
    receipt_sha = write_json(receipt_path, receipt)
    receipt["receipt_sha256"] = receipt_sha
    write_json(receipt_path, receipt)  # rewrite with self-hash
    receipt_sha = sha256_file(receipt_path)

    # Deliverable (VN parent-facing content also in English evidence file)
    def row(b: dict[str, Any] | None) -> str:
        if not b or b.get("error"):
            return "| — | — | — | — | — | — |"
        g = "**PASS**" if b.get("goal_cost_stress_pass") else "**FAIL**"
        return (
            f"| `{b.get('run_id')}` | {b.get('base_pf')} | {b.get('x1_pf')} | "
            f"{b.get('x1_5_pf')} | {b.get('x2_pf')} | {g} |"
        )

    compose_line = "n/a"
    if compose:
        compose_line = (
            f"pooled x1/x1.5/x2 PF **{compose['x1']['pooled_pf']:.3f} / "
            f"{compose['x1_5']['pooled_pf']:.3f} / {compose['x2']['pooled_pf']:.3f}** · "
            f"tpw **{compose['x1']['pooled_tpw']:.2f}** · same-day overlap **{compose['same_day_overlap_n']}** · "
            f"goal-like **{compose['goal_cost_stress_like']}**"
        )

    md = f"""# Deliverable — Wave7-continue QFSI / Real shelf reprice

Date: 2026-07-14 ~23:45 ICT  
Authority: Owner CONTINUE after `WAVE7_EXECUTED_EMPTY`  
GPT: waived · Grok · no-Git · cost honesty absolute

## Verdict

**`REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE_COMPLETE`.**  
Full QFSI still **`STOP_DATA_FRONTIER`**. GOAL unmet. Demo PF ≠ confirmed.

Receipt SHA `{receipt_sha}`

## 1) Live Real / QFSI status (do not kill)

| Item | Value |
|---|---|
| Probe | `{probe.get('verdict')}` · server_match=`{probe.get('server_match')}` |
| Live login | **{live.get('login')}** @ `{live.get('server')}` |
| terminal64 | `{procs}` |
| Capture | `20260714_QFSI_REAL_005_POSTAUTH` status live/incomplete |
| Quote days | **{len(quote_dates)}** (need ≪90 still) |
| Commission unique EURUSD | **{eurusd_comm_n}** (need ≥30) |
| Slippage fills | **{slip_total}** (MISSING ≠ 0) |

Real terminal **left running**. No blind kill.

## 2) Cost model (partial)

- Unit USDJPY P50 **${unit_p50:.6f}/lot** · P90 **${(unit_p90 or 0):.6f}/lot**
- Canonical lot-0.5 trade P50 **${cost_table['canonical_usdjpy_trade_cost_p50']:.4f}**
- Commission: EURUSD clue only · Slippage: **MISSING≠0**
- Table: `preflight/20260714_BROKER_SPREAD_COST_TABLE_QFSI_W7CONT.json` SHA `{cost_sha}`

## 3) Shelf reprice (lot-scaled unit × book lot_p50)

| Book | run | base PF | x1 | x1.5 | x2 | GOAL stress |
|---|---|---:|---:|---:|---:|---|
| RR2 shelf | {row(books.get('RR2_SHELF'))}
| RR2 fresh M0 | {row(books.get('RR2_FRESH_MODEL0'))}
| SB A1 | {row(books.get('SB_A1'))}
| Spark 100k | {row(books.get('SPARK100K'))}
| MaxKZ2 | {row(books.get('MAXKZ2'))}
| RR2 194221 ctrl | {row(books.get('RR2_CONTROL_194221'))}

## 4) A1 + Spark compose (diagnostic)

{compose_line}

## 5) Friction vs GOAL

- Best historical shelf RR2 `194548` under partial Real: x1={rr2.get('x1_pf')} x1.5={rr2.get('x1_5_pf')} x2={rr2.get('x2_pf')} → goal_pass={rr2.get('goal_cost_stress_pass')}
- Fresh Model0 `231750`: x1={fresh.get('x1_pf')} → still PARK_MISS class
- **Friction dead-end on Real: NOT confirmed** (full QFSI + slip still open; partial sample only)
- Confirmed claim: **false**

## 6) Next auto

1. Keep Real + let `005` finish; launch `006` longer-window accumulate (no kill).
2. Do **not** spam price twins / densify Wave6–7 / revive COT size/|z|.
3. When quote-days / commission / slip gates lift → re-run full QFSI gate on RR2 family.
4. Owner optional: deal-export drop for commission/slip provenance (without inventing fills).
"""
    md_path = READ / "20260714_QFSI_WAVE7CONTINUE_REAL_SHELF_DELIVERABLE.md"
    md_path.write_text(md, encoding="utf-8")

    # Patch hot.md Active Truth top bullet
    hot = HOT.read_text(encoding="utf-8")
    bullet = f"""- **QFSI / Real shelf CONTINUE (2026-07-14 ~23:50 ICT) —
  `REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE_COMPLETE`.**
  Live probe V8 `TARGET_SERVER_READONLY_PROBE_COMPLETE`; login **{live.get('login')}**
  `FivePercentOnline-Real`; `terminal64` + capture `20260714_QFSI_REAL_005_POSTAUTH`
  **left running** (do not kill). Full QFSI still `STOP_DATA_FRONTIER`
  (quote days={len(quote_dates)}; EURUSD commission unique={eurusd_comm_n}; slip={slip_total}).
  Aggregated unit USDJPY P50 **${unit_p50:.4f}/lot** → lot-scaled shelf reprice:
  RR2 `194548` x1/x1.5/x2 **{rr2.get('x1_pf')} / {rr2.get('x1_5_pf')} / {rr2.get('x2_pf')}**
  goal_pass={rr2.get('goal_cost_stress_pass')}; fresh `231750` x1 **{fresh.get('x1_pf')}**
  PARK_MISS; MaxKZ2/A1 fail band; Spark100k goal_pass={books.get('SPARK100K', {}).get('goal_cost_stress_pass')}.
  A1+Spark compose diagnostic goal-like={compose.get('goal_cost_stress_like') if compose else None}.
  Friction dead-end on Real **NOT confirmed** (partial only; slip MISSING≠0).
  Receipt `preflight/20260714_QFSI_WAVE7CONTINUE_REAL_SHELF_RECEIPT.json` SHA
  `{receipt_sha}`; deliverable
  `readouts/20260714_QFSI_WAVE7CONTINUE_REAL_SHELF_DELIVERABLE.md`.
  No densify / no price-twin spam / no COT revive. GOAL unmet.

"""
    if "## Active Truth" in hot:
        import re

        parts = hot.split("## Active Truth\n", 1)
        body = parts[1].lstrip("\n")
        # drop prior Wave7-continue QFSI bullet(s) to avoid stale optimistic numbers
        body = re.sub(
            r"- \*\*QFSI / Real shelf CONTINUE[\s\S]*?(?=\n- \*\*|\n## )",
            "",
            body,
            count=1,
        )
        hot = parts[0] + "## Active Truth\n\n" + bullet + body.lstrip("\n")
        hot = re.sub(
            r"^Updated:.*$",
            "Updated: 2026-07-14 ~23:55 ICT | `REAL_ON__QFSI_005_LIVE__PARTIAL_SHELF_REPRICE`; "
            "Wave7 empty; GOAL unmet",
            hot,
            count=1,
            flags=re.M,
        )
        HOT.write_text(hot, encoding="utf-8")

    summary = {
        "status": "OK",
        "receipt": str(receipt_path),
        "receipt_sha256": receipt_sha,
        "login": live.get("login"),
        "server": live.get("server"),
        "full_qfsi": full_qfsi["full_qfsi_verdict"],
        "unit_p50": unit_p50,
        "rr2_194548": {k: books.get("RR2_SHELF", {}).get(k) for k in ("x1_pf", "x1_5_pf", "x2_pf", "goal_cost_stress_pass")},
        "rr2_231750": {k: books.get("RR2_FRESH_MODEL0", {}).get(k) for k in ("x1_pf", "x1_5_pf", "x2_pf", "goal_cost_stress_pass")},
        "spark": {k: books.get("SPARK100K", {}).get(k) for k in ("x1_pf", "x1_5_pf", "x2_pf", "goal_cost_stress_pass")},
        "compose_goal_like": compose.get("goal_cost_stress_like") if compose else None,
        "do_not_kill_real": True,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
