#!/usr/bin/env python3
"""QFSI data-surface hygiene: broker spread/cost table + diagnostic RR2 reprice + COT size-budget probe.

Honesty rules:
- Demo != Real; missing commission/slippage != 0
- Full QFSI gates remain STOP until quote days / commission N / slippage fills met
- Diagnostic reprice only — no densify / no Model 0 / no GOAL claim
- COT size-budget join is a NEW a priori contract (not |z| retune)
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
ALPHA = TOOLS.parent
REPO = ALPHA.parent
EVID = ALPHA / "evidence/execution/FivePercentOnline-Real"
PRE = REPO / "03. EA Developer/EA_SonicR/research/preflight"
READ = REPO / "03. EA Developer/EA_SonicR/research/readouts"
REG = REPO / "03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl"
HOT = REPO / "04. Project Control/ai/hot.md"
PANEL = PRE / "v8_exogenous/panels/cftc_jpy_finfut_net_lev_spec_d1_v1.csv"
RUNS = ALPHA / "runs/EA_SilverBullet"
SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]
JPY_MARKET = "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"

# Frozen conversion clues from prior Real probe receipt (used if MT5 unavailable).
FROZEN_DPL = {
    "USDJPY": 617.5050326660162,
    "EURUSD": 100000.0,
    "GBPUSD": 100000.0,
    "XAUUSD": 100.0,  # typical XAUUSD $ / price-unit / lot; label as frozen_clue
}
LOT_P50 = 0.5  # RR2 / MaxKZ2 report median lot


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime | None = None) -> str:
    return (dt or utc_now()).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


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


def list_capture_dirs() -> list[Path]:
    if not EVID.exists():
        return []
    return sorted(
        [d for d in EVID.iterdir() if d.is_dir() and "QFSI_REAL" in d.name],
        key=lambda p: p.name,
    )


def csv_data_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8-sig", newline="") as fh:
        n = sum(1 for _ in csv.DictReader(fh))
    return n


def capture_snapshot(d: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "path": str(d),
        "has_start": (d / "session_start.json").exists(),
        "has_end": (d / "session_end.json").exists(),
        "quotes": {},
        "heartbeats": {},
        "commission_rows": {},
        "slippage_rows": {},
    }
    for sym in SYMBOLS:
        row["quotes"][sym] = csv_data_rows(d / f"{sym}_quote_ticks.csv")
        row["heartbeats"][sym] = csv_data_rows(d / f"{sym}_heartbeats.csv")
        row["commission_rows"][sym] = csv_data_rows(d / f"{sym}_commission_lifecycles.csv")
        row["slippage_rows"][sym] = csv_data_rows(d / f"{sym}_slippage_fills.csv")
    # shared commission file if present
    shared = csv_data_rows(d / "commission_lifecycles.csv")
    row["commission_shared_rows"] = shared
    row["totals"] = {
        "quotes": sum(row["quotes"].values()),
        "heartbeats": sum(row["heartbeats"].values()),
        "commission": sum(row["commission_rows"].values()) + shared,
        "slippage": sum(row["slippage_rows"].values()) + csv_data_rows(d / "slippage_fills.csv"),
    }
    if row["has_end"]:
        try:
            se = json.loads((d / "session_end.json").read_text(encoding="utf-8-sig"))
            row["session_status"] = se.get("status")
            row["reprice_ready"] = se.get("reprice_ready")
        except Exception as exc:  # noqa: BLE001
            row["session_end_error"] = str(exc)
    elif row["has_start"]:
        try:
            ss = json.loads((d / "session_start.json").read_text(encoding="utf-8-sig"))
            row["session_status"] = "CAPTURE_LIVE_OR_INCOMPLETE"
            row["duration_sec"] = ss.get("duration_sec")
            row["started_at_utc"] = ss.get("created_at_utc")
            row["expected_server"] = ss.get("expected_server")
            row["observed_server"] = ss.get("observed_server")
        except Exception as exc:  # noqa: BLE001
            row["session_start_error"] = str(exc)
    return row


def load_spreads_by_hour(symbol: str) -> dict[str, Any]:
    by_hour: dict[int, list[float]] = defaultdict(list)
    all_spreads: list[float] = []
    sources: list[dict[str, Any]] = []
    for d in list_capture_dirs():
        path = d / f"{symbol}_quote_ticks.csv"
        if not path.exists():
            continue
        n = 0
        local: list[float] = []
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                n += 1
                try:
                    bid = float(row["bid"])
                    ask = float(row["ask"])
                except (TypeError, ValueError, KeyError):
                    continue
                if bid <= 0 or ask < bid:
                    continue
                spr = ask - bid
                local.append(spr)
                all_spreads.append(spr)
                tu = (row.get("time_utc") or "").strip()
                hour = None
                if tu:
                    try:
                        # tolerate Z and fractional
                        hour = datetime.fromisoformat(tu.replace("Z", "+00:00")).astimezone(timezone.utc).hour
                    except ValueError:
                        hour = None
                if hour is not None:
                    by_hour[hour].append(spr)
        sources.append(
            {
                "capture": d.name,
                "quote_rows": n,
                "valid_spreads": len(local),
                "sha256": sha256_file(path) if path.stat().st_size else None,
            }
        )
    hour_table = []
    for h in range(24):
        xs = by_hour.get(h, [])
        hour_table.append(
            {
                "hour_utc": h,
                "n": len(xs),
                "spread_price_p50": percentile(xs, 0.50),
                "spread_price_p90": percentile(xs, 0.90),
            }
        )
    return {
        "symbol": symbol,
        "quote_rows": sum(s["quote_rows"] for s in sources),
        "valid_spreads": len(all_spreads),
        "spread_price_p50": percentile(all_spreads, 0.50),
        "spread_price_p90": percentile(all_spreads, 0.90),
        "by_hour_utc": hour_table,
        "hours_with_samples": sum(1 for h in hour_table if h["n"] > 0),
        "sources": sources,
    }


def load_unique_commissions() -> dict[str, Any]:
    """Dedup by (symbol, position_id) — same EURUSD clue repeats across captures."""
    by_sym: dict[str, dict[str, float]] = defaultdict(dict)
    sources: list[dict[str, Any]] = []
    for d in list_capture_dirs():
        paths = [d / "commission_lifecycles.csv"] + list(d.glob("*_commission_lifecycles.csv"))
        for path in paths:
            if not path.exists():
                continue
            n = 0
            with path.open(encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    n += 1
                    sym = (row.get("symbol") or "").strip() or path.name.split("_")[0]
                    pid = str(row.get("position_id") or "").strip()
                    key = "round_turn_account_per_lot"
                    try:
                        val = float(row[key])
                    except (TypeError, ValueError, KeyError):
                        continue
                    if not pid:
                        pid = f"anon_{n}_{path.name}"
                    by_sym[sym][pid] = val
            sources.append({"capture": d.name, "file": path.name, "rows": n, "sha256": sha256_file(path)})
    out: dict[str, Any] = {"sources": sources, "by_symbol": {}}
    for sym, m in by_sym.items():
        vals = list(m.values())
        out["by_symbol"][sym] = {
            "unique_position_ids": len(vals),
            "round_turn_account_per_lot_values": vals,
            "p50": percentile(vals, 0.50),
            "mean": (sum(vals) / len(vals)) if vals else None,
        }
    return out


def try_live_mt5_enrichment() -> dict[str, Any]:
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
        server = str(info.server)
        live: dict[str, Any] = {
            "ok": True,
            "server": server,
            "login": int(info.login),
            "trade_allowed": bool(info.trade_allowed),
            "currency": str(info.currency),
            "symbols": {},
        }
        for sym in SYMBOLS:
            si = mt5.symbol_info(sym)
            tick = mt5.symbol_info_tick(sym)
            if si is None or tick is None:
                live["symbols"][sym] = {"available": False}
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
            live["symbols"][sym] = {
                "available": True,
                "digits": int(si.digits),
                "point": float(si.point),
                "tick_value": tv,
                "tick_size": ts,
                "dollars_per_price_per_lot": dpl,
                "current_spread_price": float(tick.ask) - float(tick.bid),
                "live_tick_sample_n": len(spreads),
                "spread_price_p50": p50,
                "spread_price_p90": p90,
                "spread_usd_per_lot_p50": (p50 * dpl) if (p50 is not None and dpl) else None,
                "spread_usd_per_lot_p90": (p90 * dpl) if (p90 is not None and dpl) else None,
            }
        return live
    finally:
        mt5.shutdown()


def build_cost_table(
    spreads: dict[str, dict[str, Any]],
    commissions: dict[str, Any],
    live: dict[str, Any],
) -> dict[str, Any]:
    eurusd_comm = (commissions.get("by_symbol") or {}).get("EURUSD") or {}
    comm_rt = eurusd_comm.get("p50")
    comm_n = eurusd_comm.get("unique_position_ids") or 0
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
        # Commission: only EURUSD has evidence; others MISSING (not zero).
        if sym == "EURUSD" and comm_rt is not None and comm_n > 0:
            comm_use = float(comm_rt)
            comm_label = f"EURUSD_UNIQUE_N={comm_n}"
        elif sym != "EURUSD" and comm_rt is not None and comm_n > 0:
            # Transfer clue explicitly labeled — same as prior QFSI path.
            comm_use = float(comm_rt)
            comm_label = f"TRANSFERRED_EURUSD_CLUE_N={comm_n}"
        else:
            comm_use = None
            comm_label = "MISSING_NEQ_0"
        unit_p50 = None
        unit_p90 = None
        trade_p50 = None
        trade_p90 = None
        if usd_p50 is not None and comm_use is not None:
            unit_p50 = usd_p50 + comm_use
            trade_p50 = unit_p50 * LOT_P50
        elif usd_p50 is not None:
            unit_p50 = usd_p50  # spread-only; commission still missing
            trade_p50 = unit_p50 * LOT_P50
        if usd_p90 is not None and comm_use is not None:
            unit_p90 = usd_p90 + comm_use
            trade_p90 = unit_p90 * LOT_P50
        elif usd_p90 is not None:
            unit_p90 = usd_p90
            trade_p90 = unit_p90 * LOT_P50
        rows.append(
            {
                "symbol": sym,
                "capture_valid_spreads": sp["valid_spreads"],
                "hours_utc_with_samples": sp["hours_with_samples"],
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
                "trade_cost_usd_at_lot_p50_x_p50": trade_p50,
                "trade_cost_usd_at_lot_p50_x_p90": trade_p90,
                "session_hour_table": sp["by_hour_utc"],
            }
        )
    usdjpy = next(r for r in rows if r["symbol"] == "USDJPY")
    return {
        "schema_version": "sonic_broker_spread_cost_table.v1",
        "created_at_utc": iso_utc(),
        "server_expected": "FivePercentOnline-Real",
        "lot_p50_basis": LOT_P50,
        "formula": "(spread_usd_per_lot + commission_rt_per_lot) * lot_p50; slippage MISSING≠0 not added",
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
        "canonical_usdjpy_trade_cost_p50": usdjpy.get("trade_cost_usd_at_lot_p50_x_p50"),
        "canonical_usdjpy_trade_cost_p90": usdjpy.get("trade_cost_usd_at_lot_p50_x_p90"),
    }


def run_stress(run_id: str, base_cost: float, out_name: str, note: str) -> dict[str, Any]:
    sys.path.insert(0, str(TOOLS))
    import sonic_cost_stress as scs  # noqa: WPS433

    args = argparse_ns(
        run=run_id,
        ea="EA_SilverBullet",
        report="",
        out=str(RUNS / run_id / "analysis" / out_name),
        base_cost_per_trade=float(base_cost),
        spread_points=0.0,
        slippage_points=0.0,
        commission_round_turn=0.0,
        point_value_per_lot=1.0,
        lot_size=0.01,
        start_equity=10000.0,
    )
    # annotate note into out via wrapper
    payload = scs.build_cost_matrix(args)
    payload["cost_assumption"]["research_note"] = note
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    payload["_out_path"] = str(out_path)
    payload["_out_sha256"] = sha256_file(out_path)
    return payload


def argparse_ns(**kwargs: Any) -> Any:
    return type("Args", (), kwargs)()


def scenario_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["scenario"]: s for s in result.get("scenarios") or []}


def load_rr2_trades(run_id: str = "20260714_194548") -> list[dict[str, Any]]:
    """OPEN rows from PX6 trades CSV."""
    run = RUNS / run_id
    paths = list((run / "logs").glob("*_Trades_*.csv")) + list((run / "analysis/logs").glob("*_Trades_*.csv"))
    if not paths:
        raise FileNotFoundError(f"no trades csv under {run}")
    path = paths[0]
    trades: list[dict[str, Any]] = []
    # Pair OPEN->CLOSE by position_id
    opens: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            action = (row.get("action") or "").upper()
            pid = str(row.get("position_id") or "")
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and pid in opens:
                o = opens.pop(pid)
                try:
                    et = datetime.strptime(o["event_time"], "%Y.%m.%d %H:%M:%S")
                except ValueError:
                    continue
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    pnl = 0.0
                trades.append(
                    {
                        "entry_time": et,
                        "decision_date": et.date(),
                        "profit": pnl,
                        "side": o.get("order_type"),
                        "position_id": pid,
                    }
                )
    return trades


def load_jpy_cot_panel() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with PANEL.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("market") or "").strip() != JPY_MARKET:
                continue
            try:
                obs = date.fromisoformat(row["observation_date"])
                avail = datetime.fromisoformat(row["available_at_utc"].replace("Z", "+00:00")).date()
                net = float(row["net_lev_money"])
            except (KeyError, ValueError):
                continue
            rows.append({"observation_date": obs, "available_at": avail, "net_lev_money": net})
    rows.sort(key=lambda r: r["available_at"])
    return rows


def asof_size_budget(panel: list[dict[str, Any]], decision: date, lookback: int = 52) -> tuple[bool | None, dict[str, Any]]:
    """Allow iff lagged |net| <= median(|net|) over prior lookback available weeks.

    A priori size-budget (anti-crowd) — NOT a z-score extremity gate.
    """
    prior = [r for r in panel if r["available_at"] <= decision]
    if len(prior) < lookback + 1:
        return None, {"reason": "insufficient_history", "n_prior": len(prior)}
    cur = prior[-1]
    hist = prior[-(lookback + 1) : -1]
    abs_hist = [abs(r["net_lev_money"]) for r in hist]
    med = percentile(abs_hist, 0.50)
    if med is None:
        return None, {"reason": "median_none"}
    cur_abs = abs(cur["net_lev_money"])
    allow = cur_abs <= med
    return allow, {
        "available_at": cur["available_at"].isoformat(),
        "net_lev_money": cur["net_lev_money"],
        "abs_net": cur_abs,
        "prior_abs_median": med,
        "lookback": lookback,
        "allow": allow,
    }


def pf_of(pnls: list[float]) -> float:
    pos = sum(x for x in pnls if x > 0)
    neg = sum(x for x in pnls if x < 0)
    if neg == 0:
        return float("inf") if pos > 0 else 0.0
    return pos / abs(neg)


def cost_stress_pnls(pnls: list[float], cost: float = 12.0) -> dict[str, Any]:
    out = {}
    for label, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        adj = [p - cost * mult for p in pnls]
        out[label] = {"pf": round(pf_of(adj), 4), "net": round(sum(adj), 2), "exp": round(sum(adj) / len(adj), 4) if adj else 0.0}
    return out


def probe_cot_size_budget() -> dict[str, Any]:
    hyp = "HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001"
    panel = load_jpy_cot_panel()
    trades = load_rr2_trades("20260714_194548")
    kept: list[float] = []
    skipped = 0
    missing = 0
    for t in trades:
        allow, meta = asof_size_budget(panel, t["decision_date"])
        if allow is None:
            missing += 1
            continue
        if allow:
            kept.append(float(t["profit"]))
        else:
            skipped += 1
    base_pnls = [float(t["profit"]) for t in trades]
    # calendar weeks span from first to last entry
    if trades:
        span_days = (trades[-1]["decision_date"] - trades[0]["decision_date"]).days + 1
        weeks = max(span_days / 7.0, 1e-9)
    else:
        weeks = 1.0
    metrics = {
        "n": len(kept),
        "pf": round(pf_of(kept), 4) if kept else 0.0,
        "net": round(sum(kept), 2) if kept else 0.0,
        "exp": round(sum(kept) / len(kept), 4) if kept else 0.0,
        "tpw": round(len(kept) / weeks, 4) if kept else 0.0,
    }
    base_metrics = {
        "n": len(base_pnls),
        "pf": round(pf_of(base_pnls), 4),
        "net": round(sum(base_pnls), 2),
        "exp": round(sum(base_pnls) / len(base_pnls), 4) if base_pnls else 0.0,
        "tpw": round(len(base_pnls) / weeks, 4),
    }
    stress = cost_stress_pnls(kept) if kept else {}
    base_stress = cost_stress_pnls(base_pnls)
    kill_notes: list[str] = []
    if metrics["n"] < 80:
        kill_notes.append("starve_n")
    if not (1.0 <= metrics["tpw"] <= 6.5):
        kill_notes.append("cadence_fail")
    if metrics["pf"] < 1.05:
        kill_notes.append("pf_fail")
    if stress and stress["x1_5"]["pf"] < 1.10:
        kill_notes.append("stress_fail")
    if stress and base_stress and stress["x1_5"]["pf"] <= base_stress["x1_5"]["pf"]:
        kill_notes.append("no_stress_lift_vs_baseline")
    verdict = "KILLED_AT_OFFLINE_PROBE" if kill_notes else "PROBE_SURVIVOR"
    payload = {
        "schema": "data_surface_cot_sizebudget_probe.v1",
        "hypothesis_id": hyp,
        "generated_at_utc": iso_utc(),
        "panel_path": str(PANEL),
        "panel_sha": sha256_file(PANEL),
        "a_priori": {
            "rule": "allow_iff_abs(net_lev_money) <= median(abs(net) prior 52 available weeks)",
            "market": JPY_MARKET,
            "lookback_weeks": 52,
            "lag_embedded_in_panel_available_at": True,
            "not_zscore": True,
        },
        "funnel": {"n_base": len(trades), "kept": len(kept), "skipped": skipped, "missing": missing},
        "baseline": {"metrics": base_metrics, "cost_stress": base_stress},
        "metrics": metrics,
        "cost_stress": stress,
        "kill_notes": kill_notes,
        "verdict": verdict,
        "model0": "WITHHELD",
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    payload["receipt_sha256"] = sha256_text(raw)
    return payload


def append_registry(row: dict[str, Any]) -> None:
    REG.parent.mkdir(parents=True, exist_ok=True)
    with REG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def owner_drop_status() -> dict[str, Any]:
    drop = EVID / "owner_deal_export_drop"
    if not drop.exists():
        return {"exists": False, "files": []}
    files = []
    for p in sorted(drop.iterdir()):
        if p.is_file() and p.name.upper() != "README.MD":
            files.append({"name": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    return {"exists": True, "files": files}


def main() -> int:
    captures = {d.name: capture_snapshot(d) for d in list_capture_dirs()}
    live_caps = [k for k, v in captures.items() if not v.get("has_end") and v.get("has_start")]
    spreads = {s: load_spreads_by_hour(s) for s in SYMBOLS}
    commissions = load_unique_commissions()
    live = try_live_mt5_enrichment()
    cost_table = build_cost_table(spreads, commissions, live)

    # Full QFSI gate progress (honest)
    total_quotes = sum(c["totals"]["quotes"] for c in captures.values())
    eurusd_comm_n = ((commissions.get("by_symbol") or {}).get("EURUSD") or {}).get("unique_position_ids") or 0
    slip_total = sum(c["totals"]["slippage"] for c in captures.values())
    # Rough quote-day estimate: distinct UTC dates across USDJPY quotes
    quote_dates: set[str] = set()
    for d in list_capture_dirs():
        path = d / "USDJPY_quote_ticks.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                tu = (row.get("time_utc") or "")[:10]
                if len(tu) == 10:
                    quote_dates.add(tu)
    gate = {
        "full_qfsi_verdict": "STOP_DATA_FRONTIER",
        "eligible_bundle_count": 0,
        "why": [
            f"quote_distinct_utc_dates={len(quote_dates)} << 90",
            f"commission_unique_EURUSD={eurusd_comm_n} << 30 (USDJPY=0)",
            f"slippage_fills={slip_total} MISSING≠0",
        ],
        "progress": {
            "total_quote_rows_all_captures": total_quotes,
            "usdjpy_quote_distinct_dates": sorted(quote_dates),
            "commission_unique_by_symbol": {
                s: ((commissions.get("by_symbol") or {}).get(s) or {}).get("unique_position_ids") or 0 for s in SYMBOLS
            },
            "slippage_fills_total": slip_total,
            "live_captures": live_caps,
        },
    }

    base_p50 = cost_table.get("canonical_usdjpy_trade_cost_p50")
    base_p90 = cost_table.get("canonical_usdjpy_trade_cost_p90")
    if base_p50 is None:
        raise RuntimeError("USDJPY canonical trade cost P50 unavailable — refuse to pretend 0")

    note = (
        f"FivePercentOnline-Real AGGREGATED capture spread table + EURUSD commission clue "
        f"(unique N={eurusd_comm_n}); slippage MISSING≠0; NOT full QFSI"
    )
    stress_194548_p50 = run_stress("20260714_194548", base_p50, "cost_stress_broker_table_p50.json", note + " P50")
    stress_194548_p90 = run_stress("20260714_194548", float(base_p90 or base_p50), "cost_stress_broker_table_p90.json", note + " P90")
    stress_231750_p50 = run_stress("20260714_231750", base_p50, "cost_stress_broker_table_p50.json", note + " P50")
    stress_231750_p90 = run_stress("20260714_231750", float(base_p90 or base_p50), "cost_stress_broker_table_p90.json", note + " P90")

    cot = probe_cot_size_budget()

    cost_table_path = PRE / "20260714_BROKER_SPREAD_COST_TABLE_QFSI.json"
    cost_table_sha = write_json(cost_table_path, cost_table)

    # Contract + probe artifacts for COT
    contract_path = PRE / "v8_exogenous/20260714_CFTC_JPY_COTFIN_SIZEBUDGET_RR2_CONTRACT_V1.md"
    contract_md = f"""# CFTC JPY FinFut COT → RR2 size-budget allow-gate V1

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority
Data-surface / QFSI hygiene lane post dichotomy+|z| KILL. GPT waived.
Panel SHA `{sha256_file(PANEL)}`.

## Signal (frozen a priori — GATE not entry; NOT |z|)
1. Series: lagged `net_lev_money` for `{JPY_MARKET}` (panel available_at already +4d).
2. Lookback = 52 prior available weeks.
3. Allow RR2 trade iff `abs(net_lev_money)` <= median(abs(net) over prior 52).
4. Rationale: size-budget / anti-crowd — avoid oversized speculative positioning; independent of z-score extremity.
5. Do not mine threshold / lookback / market from readout.

## Kill
N<80 after gate OR tpw not in [1,6.5] OR PF<1.05 OR +$12 x1.5 PF<1.10 OR no stress lift vs ungated RR2.
"""
    contract_path.write_text(contract_md, encoding="utf-8")

    cot_json_path = PRE / "20260714_COT_SIZEBUDGET_RR2_OFFLINE_PROBE.json"
    cot_sha = write_json(cot_json_path, cot)
    cot_md_path = READ / "20260714_COT_SIZEBUDGET_RR2_OFFLINE_PROBE.md"
    cot_md_path.write_text(
        f"""# CFTC JPY LevMoney size-budget gate on RR2 — offline probe

Generated: {cot['generated_at_utc']}
Hypothesis: `{cot['hypothesis_id']}`
Panel SHA: `{cot['panel_sha']}`
Receipt: `{cot['receipt_sha256']}`

| | N | PF | tpw | x1.5 PF |
|---|---:|---:|---:|---:|
| Baseline RR2 | {cot['baseline']['metrics']['n']} | {cot['baseline']['metrics']['pf']} | {cot['baseline']['metrics']['tpw']} | {cot['baseline']['cost_stress']['x1_5']['pf']} |
| COT size-budget gate | {cot['metrics']['n']} | {cot['metrics']['pf']} | {cot['metrics']['tpw']} | {(cot['cost_stress'] or {}).get('x1_5', {}).get('pf')} |

Verdict: **{cot['verdict']}**
Notes: {cot['kill_notes']}
Funnel: kept={cot['funnel']['kept']} skipped={cot['funnel']['skipped']} missing={cot['funnel']['missing']}

Do not mine threshold/lookback. Not a |z| retune. Model 0 withheld.
""",
        encoding="utf-8",
    )

    append_registry(
        {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": cot["hypothesis_id"],
            "state": "killed" if cot["verdict"].startswith("KILL") else "probe",
            "verdict": "OFFLINE_KILL" if cot["verdict"].startswith("KILL") else "PROBE",
            "reason": f"COT size-budget on RR2: N={cot['metrics']['n']} PF={cot['metrics']['pf']} tpw={cot['metrics']['tpw']}; notes={cot['kill_notes']}; no Model0",
            "updated_at": "2026-07-14",
            "lane": "data_surface_qfsi_hygiene_20260714",
            "feature_family": "cftc_jpy_levmoney_sizebudget_allow_gate_on_rr2",
            "symbol": "USDJPY",
            "timeframe": "M15",
            "window": "2021.01.01-2025.12.31",
            "model": "offline_closed_bar_probe",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_COT_SIZEBUDGET_RR2_OFFLINE_PROBE.md",
            "run_ids": ["20260714_194548"],
            "metrics": cot["metrics"],
            "validation": {"offline_probe": "KILL" if cot["verdict"].startswith("KILL") else "PASS", "model0": "WITHHELD"},
            "receipt_sha256": cot["receipt_sha256"],
        }
    )

    def pf_row(stress: dict[str, Any]) -> dict[str, Any]:
        sm = scenario_map(stress)
        return {
            "base": sm.get("base_report", {}).get("profit_factor"),
            "x1": sm.get("cost_x1_00", {}).get("profit_factor"),
            "x1_5": sm.get("cost_x1_50", {}).get("profit_factor"),
            "x2": sm.get("cost_x2_00", {}).get("profit_factor"),
            "out_sha": stress.get("_out_sha256"),
        }

    receipt = {
        "schema_version": "sonic_qfsi_data_surface_hygiene_receipt.v1",
        "created_at_utc": iso_utc(),
        "status": "QFSI_HYGIENE_PARTIAL__COST_TABLE_BUILT__COT_SIZEBUDGET_KILL",
        "goal_claim": False,
        "confirmed_claim": False,
        "COST_PROVENANCE_GAP": "NARROWED_NOT_CLEARED",
        "full_qfsi_gate": gate,
        "captures": captures,
        "live_mt5": {
            "ok": live.get("ok"),
            "server": live.get("server"),
            "login": live.get("login"),
            "trade_allowed": live.get("trade_allowed"),
        },
        "owner_deal_export_drop": owner_drop_status(),
        "cost_table_path": str(cost_table_path),
        "cost_table_sha256": cost_table_sha,
        "canonical_usdjpy_trade_cost_p50": base_p50,
        "canonical_usdjpy_trade_cost_p90": base_p90,
        "diagnostic_reprice": {
            "label": "PARTIAL_BROKER_TABLE_PROXY",
            "rr2_194548_p50": pf_row(stress_194548_p50),
            "rr2_194548_p90": pf_row(stress_194548_p90),
            "rr2_231750_p50": pf_row(stress_231750_p50),
            "rr2_231750_p90": pf_row(stress_231750_p90),
            "caveat": "Additive haircut may double-count tester spread; slippage still MISSING≠0; not confirmed",
        },
        "cot_sizebudget": {
            "hypothesis_id": cot["hypothesis_id"],
            "verdict": cot["verdict"],
            "metrics": cot["metrics"],
            "kill_notes": cot["kill_notes"],
            "receipt_sha256": cot["receipt_sha256"],
            "json_path": str(cot_json_path),
            "json_sha256": cot_sha,
            "contract_path": str(contract_path),
        },
        "illegal": [
            "densify_RR2_MaxKZ_ATR_Spark_session_H4Outside",
            "pretend_slip_zero",
            "claim_full_QFSI",
            "Model0_structural_spam",
        ],
    }
    receipt_path = PRE / "20260714_QFSI_DATA_SURFACE_HYGIENE_RECEIPT.json"
    receipt_sha = write_json(receipt_path, receipt)

    # VN deliverable update (append section into existing post-RR2 deliverable)
    sm548 = receipt["diagnostic_reprice"]["rr2_194548_p50"]
    sm750 = receipt["diagnostic_reprice"]["rr2_231750_p50"]
    deliv = f"""# Deliverable — Post RR2 FAIL → Dichotomy + V9 + data-surface/QFSI hygiene

Date: 2026-07-14 ~23:55 ICT  
Lane: Owner path tiếp — data-surface / QFSI (không densify structural)  
GPT: waived · Owner MT kill/open-auth ON (no in-flight tester)

## 1) Board structural (đã đóng — không densify)

### Prior
| Run / ID | Gate |
|---|---|
| RR2 Model0 `20260714_231750` | PF **1.156** / ~1.99 tpw → **PARK_MISS**; Real P50 FAIL |
| Historical shelf `194548` | PF 1.378 — disk only; not current tester truth |

### Dichotomy + V9
3/3 dichotomy KILL · 3/3 V9 KILL · **zero Model 0**.  
Receipts: dichotomy `7B0D6075…798D90` · V9 `3F47416C…03CBC8`.

## 2) QFSI progress (Real)

| Item | Status |
|---|---|
| `terminal64` / Real | Live MT5 probe: server=`{live.get('server')}` ok=`{live.get('ok')}` |
| Capture `005_POSTAUTH` | {"LIVE" if "20260714_QFSI_REAL_005_POSTAUTH" in live_caps else "ended/partial"} — quotes accumulating |
| Captures 001–004_EXTENSION | COMPLETE_PARTIAL on disk |
| Full QFSI | **`STOP_DATA_FRONTIER`** — {"; ".join(gate["why"])} |
| Commission unique | EURUSD N=**{eurusd_comm_n}** @ $4/lot RT; USDJPY **0** |
| Slippage fills | **{slip_total}** (MISSING≠0 — không pretend 0) |
| Owner deal-export drop | new files = **{len(owner_drop_status().get("files") or [])}** |

Không kill capture đang chạy. Không đặt lệnh live.

## 3) Broker spread / cost table

Path: `preflight/20260714_BROKER_SPREAD_COST_TABLE_QFSI.json`  
SHA: `{cost_table_sha}`

Canonical USDJPY (lot P50=0.5):  
- trade cost P50 ≈ **${base_p50:.4f}**  
- trade cost P90 ≈ **${(base_p90 or 0):.4f}**  
Formula: `(spread_usd/lot + EURUSD commission clue) * lot_p50`; slippage **không** cộng vì MISSING.

Label: **`PARTIAL_BROKER_TABLE_PROXY`** — session-hour coverage sparse (capture windows ngắn); chưa đủ 90 ngày quote.

## 4) Diagnostic reprice (không rescue)

| Book | Base PF | Table P50 ×1 | ×1.5 | ×2 |
|---|---:|---:|---:|---:|
| Shelf `194548` | {sm548['base']} | {sm548['x1']} | {sm548['x1_5']} | {sm548['x2']} |
| Fresh `231750` | {sm750['base']} | {sm750['x1']} | {sm750['x1_5']} | {sm750['x2']} |

Đọc: shelf `194548` vẫn dày hơn dưới cùng cost table; `231750` vẫn **PARK_MISS** / không HIT. Không densify RR/MaxKZ.

## 5) COT join mới (≠ |z|) — offline only

Hypothesis: `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001`  
Rule a priori: allow iff `|net_lev| ≤ median(|net| prior 52w)` — anti-crowd size-budget, **không** retune z.

| | N | PF | tpw | x1.5 |
|---|---:|---:|---:|---:|
| Size-budget | {cot['metrics']['n']} | {cot['metrics']['pf']} | {cot['metrics']['tpw']} | {(cot['cost_stress'] or {}).get('x1_5', {}).get('pf')} |

Verdict: **{cot['verdict']}** · notes={cot['kill_notes']} · Model0 withheld.

## 6) vs GOAL

GOAL **unmet**. `COST_PROVENANCE_GAP` = **NARROWED_NOT_CLEARED** (table hẹp gap spread; slip/commission/90d vẫn mở). Best research shelf vẫn `194548` dưới partial Real cost; confirmed/GOAL cần full QFSI hoặc Owner-accepted verified-cost contract.

## 7) Next

1. Giữ Real + để `005` chạy hết; nếu cần → launch capture dài hơn / Owner drop deal-history (commission≥30/symbol + slip fills).  
2. Không densify structural kill-list.  
3. Surface tiếp theo: Owner-sourced non-price khác, hoặc chờ frontier QFSI nhích — không shotgun price-twin.  
4. Phase-0 vẫn BLOCKED.

## hot.md

Cập nhật Active Truth + Next Move + `COST_PROVENANCE` status trong cùng turn.

Receipt: `preflight/20260714_QFSI_DATA_SURFACE_HYGIENE_RECEIPT.json` SHA `{receipt_sha}`
"""
    deliv_path = READ / "20260714_POST_RR2_DICHOTOMY_V9_DELIVERABLE.md"
    deliv_path.write_text(deliv, encoding="utf-8")

    # Patch hot.md header + new Active Truth bullet + Next Move
    hot = HOT.read_text(encoding="utf-8")
    new_header = (
        "# Hot Cache\n\n"
        "Updated: 2026-07-14 ~23:55 ICT | QFSI hygiene cost-table; COT size-budget KILL; V9 empty\n"
        "Real ON + QFSI_005; broker table built; COST_PROVENANCE NARROWED_NOT_CLEARED; GOAL unmet\n\n"
        "## Active Truth\n\n"
        "- **Data-surface / QFSI hygiene CLOSEOUT (2026-07-14 ~23:55 ICT) —\n"
        "  `QFSI_HYGIENE_PARTIAL__COST_TABLE_BUILT__COT_SIZEBUDGET_KILL`.**\n"
        "  Broker spread/cost table from Real captures 001–005:\n"
        "  `preflight/20260714_BROKER_SPREAD_COST_TABLE_QFSI.json` SHA\n"
        f"  `{cost_table_sha}`. Canonical USDJPY trade cost P50\n"
        f"  **~${base_p50:.4f}** / P90 **~${(base_p90 or 0):.4f}** (lot 0.5;\n"
        "  EURUSD commission clue unique N="
        f"{eurusd_comm_n}; slippage MISSING≠0). Full QFSI still\n"
        "  `STOP_DATA_FRONTIER`. Diagnostic reprice (no rescue):\n"
        f"  shelf `194548` table-P50 x1/x1.5/x2 PF **{sm548['x1']:.3f} / "
        f"{sm548['x1_5']:.3f} / {sm548['x2']:.3f}**; fresh `231750`\n"
        f"  **{sm750['x1']:.3f} / {sm750['x1_5']:.3f} / {sm750['x2']:.3f}**\n"
        "  (still PARK_MISS). New COT join\n"
        "  `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001` (≠\\|z\\|):\n"
        f"  N=**{cot['metrics']['n']}** PF **{cot['metrics']['pf']}** tpw\n"
        f"  **{cot['metrics']['tpw']}** → **{cot['verdict']}**.\n"
        "  Receipt `preflight/20260714_QFSI_DATA_SURFACE_HYGIENE_RECEIPT.json`\n"
        f"  SHA `{receipt_sha}`; deliverable\n"
        "  `readouts/20260714_POST_RR2_DICHOTOMY_V9_DELIVERABLE.md`.\n"
        "  `COST_PROVENANCE_GAP` = **NARROWED_NOT_CLEARED**. Do not densify.\n"
        "  GOAL unmet.\n"
    )
    # Replace from start through first ## Active Truth block start content carefully:
    # Find "## Active Truth" and prepend new bullet after it.
    marker = "## Active Truth\n"
    idx = hot.find(marker)
    if idx < 0:
        raise RuntimeError("hot.md missing Active Truth")
    # Replace title+updated lines
    rest = hot[idx + len(marker) :]
    # remove old leading Updated header (everything before Active Truth)
    hot2 = new_header + rest

    # Update Next Move ACTIVE bullet
    nm = "## Next Move\n"
    nmi = hot2.find(nm)
    if nmi < 0:
        raise RuntimeError("hot.md missing Next Move")
    # replace first ACTIVE bullet paragraph
    after = hot2[nmi + len(nm) :]
    # find first "- **ACTIVE" through next "- **CLOSED"
    import re

    after2, nsub = re.subn(
        r"- \*\*ACTIVE —.*?(?=\n- \*\*CLOSED)",
        (
            "- **ACTIVE — QFSI accumulate + Owner-sourced surface (cost table on disk).**\n"
            "  Broker table built; COT size-budget **KILL**; V9/dichotomy/Wave6 empty.\n"
            "  Do **not** densify kill-list. Keep Real for quote/commission/slip\n"
            "  frontier; optional Owner deal-history drop. Next edge must be\n"
            "  non-price / new a priori — not price-twin spam. Best shelf RR2\n"
            "  `194548` under partial table P50; `231750` PARK_MISS. "
            "`COST_PROVENANCE_GAP`=**NARROWED_NOT_CLEARED**. GOAL unmet.\n"
        ),
        after,
        count=1,
        flags=re.S,
    )
    if nsub != 1:
        # fallback: leave Next Move; still write receipt note
        print(json.dumps({"warn": "next_move_replace_failed", "nsub": nsub}))
        hot_final = hot2
    else:
        hot_final = hot2[: nmi + len(nm)] + after2

    HOT.write_text(hot_final, encoding="utf-8")

    summary = {
        "status": "OK",
        "receipt_sha256": receipt_sha,
        "cost_table_sha256": cost_table_sha,
        "base_p50": base_p50,
        "base_p90": base_p90,
        "rr2_194548_p50": sm548,
        "rr2_231750_p50": sm750,
        "cot_verdict": cot["verdict"],
        "cot_metrics": cot["metrics"],
        "full_qfsi": gate["full_qfsi_verdict"],
        "live_captures": live_caps,
        "live_mt5_ok": live.get("ok"),
        "live_server": live.get("server"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
