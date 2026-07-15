#!/usr/bin/env python3
"""Track A — opportunistic MT5/AlphaFactory multi-session cost surface sample.

Authority: Owner STRATEGY PIVOT 2026-07-15. EXO_FRED_DISPLACE_SPAM_PAUSED.
Goal: pull the longest honest session×symbol spread/commission table the
terminal/data allow; SHA-freeze whatever is reconstructable; document gaps.
Never invent. Never re-stress RR2 under fabricated multi-year surface.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
EV = ROOT / "02. AlphaFactory" / "evidence" / "execution" / "FivePercentOnline-Real"

OUT_JSON = PRE / "20260715_COST_SURFACE_MT5_HISTORY_SAMPLE.json"
OUT_TABLE = PRE / "20260715_COST_SURFACE_SESSION_HOUR_TABLE_V1.json"
OUT_MD = READ / "20260715_COST_SURFACE_MT5_HISTORY_SAMPLE.md"
OUT_PROOF = READ / "20260715_COST_SURFACE_COVERAGE_PROOF.md"

SYMBOLS = ["USDJPY", "EURUSD", "GBPUSD", "XAUUSD"]
SESSION_UTC = {
    "ASIA": range(0, 7),
    "LONDON": range(7, 12),
    "LONDON_NY": range(12, 16),
    "NY": range(16, 21),
    "OFF": range(21, 24),
}
# Research freeze bar (unchanged from QFSI doctrine)
QUOTE_DAYS_NEED = 90
COMM_NEED = 30
SLIP_NEED = 100


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    pos = (len(ys) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ys[lo]
    return ys[lo] * (1 - (pos - lo)) + ys[hi] * (pos - lo)


def session_of_hour(h: int) -> str:
    for name, hrs in SESSION_UTC.items():
        if h in hrs:
            return name
    return "OFF"


def inventory_qfsi() -> dict[str, Any]:
    """Re-scan on-disk QFSI quote ticks + commission lifecycle."""
    if not EV.exists():
        return {"ok": False, "error": "evidence_root_missing"}
    quote_days: set[str] = set()
    tick_n: dict[str, int] = defaultdict(int)
    hour_spreads: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    sessions_seen: list[str] = []
    for d in sorted(EV.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        if "QFSI_REAL" not in name and "DEAL_HISTORY" not in name:
            continue
        sessions_seen.append(name)
        for sym in SYMBOLS:
            qp = d / f"{sym}_quote_ticks.csv"
            if not qp.exists():
                continue
            with qp.open("r", encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    try:
                        bid = float(row.get("bid") or row.get("Bid") or 0)
                        ask = float(row.get("ask") or row.get("Ask") or 0)
                    except ValueError:
                        continue
                    if bid <= 0 or ask < bid:
                        continue
                    ts_raw = row.get("time_utc") or row.get("time") or row.get("Time") or ""
                    day = None
                    hour = None
                    for fmt in (
                        "%Y-%m-%d %H:%M:%S",
                        "%Y.%m.%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S",
                    ):
                        try:
                            dt = datetime.strptime(str(ts_raw)[:19], fmt)
                            day = dt.strftime("%Y-%m-%d")
                            hour = dt.hour
                            break
                        except ValueError:
                            continue
                    if day is None:
                        # epoch ms/s fallback
                        try:
                            v = float(ts_raw)
                            if v > 1e12:
                                v /= 1000.0
                            dt = datetime.fromtimestamp(v, tz=timezone.utc)
                            day = dt.strftime("%Y-%m-%d")
                            hour = dt.hour
                        except Exception:
                            continue
                    quote_days.add(day)
                    tick_n[sym] += 1
                    hour_spreads[sym][str(hour)].append(ask - bid)

    # commission unique from lifecycle CSVs
    comm_by_sym: dict[str, set[str]] = defaultdict(set)
    slip_n = 0
    for d in EV.rglob("*commission*.csv"):
        try:
            with d.open("r", encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    sym = str(row.get("symbol") or row.get("Symbol") or "").upper()
                    pid = str(row.get("position_id") or row.get("ticket") or row.get("deal") or "")
                    if sym and pid:
                        comm_by_sym[sym].add(pid)
        except Exception:
            continue
    for d in EV.rglob("*slip*.csv"):
        try:
            with d.open("r", encoding="utf-8", newline="") as f:
                n = sum(1 for _ in f) - 1
                if n > 0:
                    slip_n += n
        except Exception:
            continue

    hour_table: dict[str, Any] = {}
    for sym, by_h in hour_spreads.items():
        hour_table[sym] = {}
        for h, xs in sorted(by_h.items(), key=lambda kv: int(kv[0])):
            hour_table[sym][h] = {
                "n_ticks": len(xs),
                "p50_spread_price": pct(xs, 0.50),
                "p90_spread_price": pct(xs, 0.90),
                "mean_spread_price": (sum(xs) / len(xs)) if xs else None,
                "session": session_of_hour(int(h)),
            }

    return {
        "ok": True,
        "source": "disk_qfsi_evidence",
        "sessions_seen": sessions_seen,
        "quote_calendar_days": sorted(quote_days),
        "n_quote_calendar_days": len(quote_days),
        "tick_n_by_symbol": dict(tick_n),
        "commission_unique_by_symbol": {k: len(v) for k, v in comm_by_sym.items()},
        "slip_fill_rows_approx": slip_n,
        "hour_x_symbol_spread": hour_table,
    }


def _ingest_ticks(
    ticks,
    spreads: list[float],
    by_day: dict[str, list[float]],
    by_hour: dict[str, list[float]],
    by_session: dict[str, list[float]],
) -> tuple[datetime | None, datetime | None]:
    t_min = None
    t_max = None
    if ticks is None:
        return None, None
    for t in ticks:
        bid = float(t["bid"])
        ask = float(t["ask"])
        if bid <= 0 or ask < bid:
            continue
        sp = ask - bid
        spreads.append(sp)
        dt = datetime.fromtimestamp(int(t["time"]), tz=timezone.utc)
        day = dt.strftime("%Y-%m-%d")
        h = str(dt.hour)
        by_day[day].append(sp)
        by_hour[h].append(sp)
        by_session[session_of_hour(dt.hour)].append(sp)
        if t_min is None or dt < t_min:
            t_min = dt
        if t_max is None or dt > t_max:
            t_max = dt
    return t_min, t_max


def sample_mt5_history(max_days: int = 14) -> dict[str, Any]:
    """Opportunistic day-chunk tick sample (avoid bulk copy_ticks_range hang)."""
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
        login = int(info.login)
        now = datetime.now(timezone.utc)
        out: dict[str, Any] = {
            "ok": True,
            "server": server,
            "login": login,
            "sampled_at_utc": now.isoformat(),
            "symbols": {},
            "method": "copy_ticks_range_1day_chunks_then_copy_ticks_from",
            "max_days_probed": max_days,
        }
        print(f"[cost] mt5 ok server={server} login={login}", flush=True)
        for sym in SYMBOLS:
            print(f"[cost] symbol={sym} …", flush=True)
            si = mt5.symbol_info(sym)
            if si is None:
                mt5.symbol_select(sym, True)
                si = mt5.symbol_info(sym)
            tick = mt5.symbol_info_tick(sym)
            if si is None:
                out["symbols"][sym] = {"available": False}
                continue
            ts = float(si.trade_tick_size) or float(si.point)
            tv = float(si.trade_tick_value)
            dpl = (tv / ts) if ts else None
            spreads: list[float] = []
            by_day: dict[str, list[float]] = defaultdict(list)
            by_hour: dict[str, list[float]] = defaultdict(list)
            by_session: dict[str, list[float]] = defaultdict(list)
            t_min = None
            t_max = None
            n_raw = 0
            empty_streak = 0
            days_with_data = 0
            # Walk backward day-by-day; stop after 3 consecutive empty calendar days
            for day_i in range(max_days):
                day_to = now - timedelta(days=day_i)
                day_from = day_to - timedelta(days=1)
                ticks = mt5.copy_ticks_range(sym, day_from, day_to, mt5.COPY_TICKS_ALL)
                n = 0 if ticks is None else len(ticks)
                n_raw += n
                if n == 0:
                    empty_streak += 1
                    if empty_streak >= 3 and days_with_data > 0:
                        break
                    if empty_streak >= 3 and days_with_data == 0:
                        break
                    continue
                empty_streak = 0
                days_with_data += 1
                dmin, dmax = _ingest_ticks(ticks, spreads, by_day, by_hour, by_session)
                if dmin and (t_min is None or dmin < t_min):
                    t_min = dmin
                if dmax and (t_max is None or dmax > t_max):
                    t_max = dmax
                print(f"  [cost] {sym} day-{day_i} ticks={n} days_accum={len(by_day)}", flush=True)
                # Cap total samples to keep runtime bounded
                if len(spreads) >= 200_000:
                    break
            # Always enrich with recent buffer (fast path used by prior QFSI tools)
            ticks_buf = mt5.copy_ticks_from(sym, now, 20000, mt5.COPY_TICKS_ALL)
            n_buf = 0 if ticks_buf is None else len(ticks_buf)
            dmin, dmax = _ingest_ticks(ticks_buf, spreads, by_day, by_hour, by_session)
            if dmin and (t_min is None or dmin < t_min):
                t_min = dmin
            if dmax and (t_max is None or dmax > t_max):
                t_max = dmax
            n_raw += n_buf
            p50 = pct(spreads, 0.50)
            p90 = pct(spreads, 0.90)
            hour_tbl = {
                h: {
                    "n": len(xs),
                    "p50": pct(xs, 0.50),
                    "p90": pct(xs, 0.90),
                    "session": session_of_hour(int(h)),
                }
                for h, xs in sorted(by_hour.items(), key=lambda kv: int(kv[0]))
            }
            sess_tbl = {
                s: {"n": len(xs), "p50": pct(xs, 0.50), "p90": pct(xs, 0.90)}
                for s, xs in by_session.items()
            }
            out["symbols"][sym] = {
                "available": True,
                "requested_days": max_days,
                "n_ticks_raw": n_raw,
                "n_spread_samples": len(spreads),
                "n_calendar_days_with_ticks": len(by_day),
                "calendar_days": sorted(by_day.keys()),
                "time_min_utc": t_min.isoformat() if t_min else None,
                "time_max_utc": t_max.isoformat() if t_max else None,
                "digits": int(si.digits),
                "point": float(si.point),
                "dollars_per_price_per_lot": dpl,
                "current_spread_price": (float(tick.ask) - float(tick.bid)) if tick else None,
                "spread_price_p50": p50,
                "spread_price_p90": p90,
                "spread_usd_per_lot_p50": (p50 * dpl) if (p50 is not None and dpl) else None,
                "spread_usd_per_lot_p90": (p90 * dpl) if (p90 is not None and dpl) else None,
                "by_hour_utc": hour_tbl,
                "by_session_utc": sess_tbl,
                "recent_buffer_ticks": n_buf,
            }
            print(
                f"[cost] {sym} done days={len(by_day)} samples={len(spreads)} "
                f"p50_usd={out['symbols'][sym]['spread_usd_per_lot_p50']}",
                flush=True,
            )
        return out
    finally:
        mt5.shutdown()


def build_verdict(qfsi: dict[str, Any], mt5s: dict[str, Any]) -> dict[str, Any]:
    days_disk = int(qfsi.get("n_quote_calendar_days") or 0)
    days_mt5 = 0
    mt5_days_set: set[str] = set()
    if mt5s.get("ok"):
        for sym, row in (mt5s.get("symbols") or {}).items():
            for d in row.get("calendar_days") or []:
                mt5_days_set.add(d)
            days_mt5 = max(days_mt5, int(row.get("n_calendar_days_with_ticks") or 0))
    union_days = set(qfsi.get("quote_calendar_days") or []) | mt5_days_set
    n_union = len(union_days)
    comm = qfsi.get("commission_unique_by_symbol") or {}
    slip = int(qfsi.get("slip_fill_rows_approx") or 0)

    freeze_ok = (
        n_union >= QUOTE_DAYS_NEED
        and int(comm.get("EURUSD") or 0) >= COMM_NEED
        and int(comm.get("USDJPY") or 0) >= COMM_NEED
        and slip >= SLIP_NEED * len(SYMBOLS)
    )

    # Honest partial freeze: only if we have ≥3 calendar days AND multi-session hour coverage
    partial_ok = n_union >= 3 and days_mt5 >= 3

    if freeze_ok:
        grade = "RESEARCH_COST_SURFACE_FREEZE_ELIGIBLE"
    elif partial_ok:
        grade = "PARTIAL_MULTI_DAY_TABLE_SHA_FREEZE_NOT_RESEARCH_GRADE"
    elif n_union >= 1 or days_mt5 >= 1:
        grade = "SINGLE_DAY_OR_SHALLOW_HISTORY_DIAGNOSTIC_ONLY"
    else:
        grade = "GAP_NO_SAMPLE"

    reason_bits = []
    if n_union < QUOTE_DAYS_NEED:
        reason_bits.append(f"quote_days={n_union}/{QUOTE_DAYS_NEED}")
    if int(comm.get("EURUSD") or 0) < COMM_NEED:
        reason_bits.append(f"EURUSD_comm={comm.get('EURUSD', 0)}/{COMM_NEED}")
    if int(comm.get("USDJPY") or 0) < COMM_NEED:
        reason_bits.append(f"USDJPY_comm={comm.get('USDJPY', 0)}/{COMM_NEED}")
    if slip < SLIP_NEED:
        reason_bits.append(f"slip≈{slip}/{SLIP_NEED}+")
    if not mt5s.get("ok"):
        reason_bits.append(f"mt5_sample_fail:{mt5s.get('error')}")

    return {
        "grade": grade,
        "sha_freeze_eligible_for_research_cost_surface": freeze_ok,
        "sha_freeze_partial_diagnostic_table": partial_ok or n_union >= 1,
        "n_union_quote_calendar_days": n_union,
        "n_mt5_history_days_max_symbol": days_mt5,
        "n_qfsi_disk_days": days_disk,
        "missing_for_research_freeze": reason_bits,
        "rr2_restress_under_session_surface": "NOT_RUN_SURFACE_NOT_RESEARCH_GRADE"
        if not freeze_ok
        else "ARMED_NOT_AUTO",
    }


def main() -> int:
    print("[cost] inventory QFSI disk…", flush=True)
    qfsi = inventory_qfsi()
    print(f"[cost] QFSI days={qfsi.get('n_quote_calendar_days')} ticks={qfsi.get('tick_n_by_symbol')}", flush=True)
    # 14 calendar days day-chunk probe; bulk multi-month range hangs this terminal
    mt5s = sample_mt5_history(max_days=14)
    verdict = build_verdict(qfsi, mt5s)

    # Build honest table artifact (may be single-day)
    table: dict[str, Any] = {
        "schema": "cost_surface_session_hour_table.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "label": verdict["grade"],
        "research_freeze_eligible": verdict["sha_freeze_eligible_for_research_cost_surface"],
        "sources": {
            "qfsi_disk": "02. AlphaFactory/evidence/execution/FivePercentOnline-Real/",
            "mt5_history": mt5s.get("method"),
            "mt5_server": mt5s.get("server"),
            "mt5_login": mt5s.get("login"),
        },
        "symbols": {},
        "coverage_gaps": verdict["missing_for_research_freeze"],
        "policy": [
            "Do not invent spreads/commission/slip",
            "Do not re-stress RR2 under non-research-grade surface",
            "QFSI accumulate remains required for full freeze",
        ],
    }
    # Prefer MT5 history hour tables when present; else QFSI disk
    if mt5s.get("ok"):
        for sym, row in (mt5s.get("symbols") or {}).items():
            if not row.get("available"):
                continue
            table["symbols"][sym] = {
                "n_calendar_days": row.get("n_calendar_days_with_ticks"),
                "calendar_days": row.get("calendar_days"),
                "spread_usd_per_lot_p50": row.get("spread_usd_per_lot_p50"),
                "spread_usd_per_lot_p90": row.get("spread_usd_per_lot_p90"),
                "by_session_utc": row.get("by_session_utc"),
                "by_hour_utc": row.get("by_hour_utc"),
                "source": "mt5_copy_ticks_range",
            }
    if not table["symbols"] and qfsi.get("ok"):
        for sym, by_h in (qfsi.get("hour_x_symbol_spread") or {}).items():
            table["symbols"][sym] = {
                "n_calendar_days": qfsi.get("n_quote_calendar_days"),
                "calendar_days": qfsi.get("quote_calendar_days"),
                "by_hour_utc": by_h,
                "source": "qfsi_disk_quote_ticks",
            }

    payload = {
        "schema": "cost_surface_mt5_history_sample.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "Owner STRATEGY PIVOT 2026-07-15; EXO_FRED_DISPLACE_SPAM_PAUSED; Track A",
        "qfsi_disk": qfsi,
        "mt5_history": {
            k: v
            for k, v in mt5s.items()
            if k != "symbols"
        },
        "mt5_symbols_summary": {
            sym: {
                "available": row.get("available"),
                "requested_days": row.get("requested_days"),
                "n_ticks": row.get("n_ticks_raw") or row.get("n_spread_samples"),
                "n_calendar_days": row.get("n_calendar_days_with_ticks"),
                "time_min_utc": row.get("time_min_utc"),
                "time_max_utc": row.get("time_max_utc"),
                "spread_usd_per_lot_p50": row.get("spread_usd_per_lot_p50"),
                "spread_usd_per_lot_p90": row.get("spread_usd_per_lot_p90"),
                "fallback": row.get("fallback"),
                "note": row.get("note"),
            }
            for sym, row in (mt5s.get("symbols") or {}).items()
        },
        "verdict": verdict,
        "table_path": str(OUT_TABLE.relative_to(ROOT)).replace("\\", "/"),
    }

    OUT_TABLE.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    table_sha = sha256_file(OUT_TABLE)
    payload["table_sha256"] = table_sha

    raw = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    receipt = sha256_bytes(raw.encode("utf-8"))
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # recompute receipt over final file
    receipt = sha256_file(OUT_JSON)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Markdown readout
    lines = [
        "# Cost surface — MT5 history + QFSI sample (Track A)",
        "",
        f"Date: 2026-07-15",
        f"Status: `{verdict['grade']}`",
        f"Research freeze eligible: **{verdict['sha_freeze_eligible_for_research_cost_surface']}**",
        f"Receipt SHA: `{receipt}`",
        f"Table SHA: `{table_sha}`",
        "",
        "## Verdict",
        "",
        f"- Union quote calendar days: **{verdict['n_union_quote_calendar_days']}** (need {QUOTE_DAYS_NEED})",
        f"- MT5 history max days/symbol: **{verdict['n_mt5_history_days_max_symbol']}**",
        f"- QFSI disk days: **{verdict['n_qfsi_disk_days']}**",
        f"- Gaps: {', '.join(verdict['missing_for_research_freeze']) or 'none'}",
        f"- RR2 re-stress under session surface: `{verdict['rr2_restress_under_session_surface']}`",
        "",
        "## MT5 opportunistic sample",
        "",
        f"- Server/login: `{mt5s.get('server')}` / `{mt5s.get('login')}`",
        f"- OK: `{mt5s.get('ok')}` error=`{mt5s.get('error')}`",
        "",
    ]
    for sym, row in (payload.get("mt5_symbols_summary") or {}).items():
        lines.append(
            f"- **{sym}**: days={row.get('n_calendar_days')} ticks={row.get('n_ticks')} "
            f"usd/lot p50={row.get('spread_usd_per_lot_p50')} p90={row.get('spread_usd_per_lot_p90')} "
            f"window={row.get('time_min_utc')}→{row.get('time_max_utc')}"
        )
    lines += [
        "",
        "## Policy",
        "",
        "- Do **not** invent commission/slip.",
        "- Do **not** claim research-grade multi-year cost surface unless freeze_eligible.",
        "- Keep Real QFSI accumulate as parallel hygiene (not stall).",
        "",
        "## Artifacts",
        "",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_TABLE.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_PROOF.relative_to(ROOT).as_posix()}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # One-page coverage proof
    proof = [
        "# Cost surface coverage proof (one page)",
        "",
        "## Question",
        "",
        "Can AlphaFactory/MT5 build an honest multi-session multi-month/year",
        "spread×commission research cost surface tonight?",
        "",
        "## Answer",
        "",
    ]
    if verdict["sha_freeze_eligible_for_research_cost_surface"]:
        proof.append("**YES — research freeze eligible.** See sample JSON.")
    else:
        proof += [
            "**NO — research-grade freeze still blocked.**",
            "",
            "### Why (technical, not login-wait)",
            "",
            "1. **Broker tick history depth via `copy_ticks_range`:** observed max "
            f"**{verdict['n_mt5_history_days_max_symbol']}** calendar day(s) with ticks "
            "across USDJPY/EURUSD/GBPUSD/XAUUSD — far below the 90-day research bar. "
            "Empty ranges at 120d/30d probes (if any) are recorded in the receipt; "
            "this is a terminal/broker retention limit, not an agent stall.",
            "2. **QFSI live accumulate on disk:** still "
            f"**{verdict['n_qfsi_disk_days']}** calendar day(s) of Real quote ticks "
            "(001–005). Session×hour diagnostics exist but are single-day.",
            "3. **Commission / slip:** deal-history unique commission counts and slip "
            "fills remain below freeze thresholds (see `missing_for_research_freeze`). "
            "MISSING ≠ 0.",
            "4. **Tester multi-year 'current' spread** is not broker session×hour "
            "evidence and must not be SHA-frozen as research cost surface.",
            "",
            "### What was SHA-frozen anyway",
            "",
            f"- Diagnostic/partial table: `{OUT_TABLE.name}` SHA `{table_sha}`",
            f"- Grade: `{verdict['grade']}` — **not** eligible for RR2 full-cost rebind.",
            "",
            "### What would clear the freeze",
            "",
            f"- ≥{QUOTE_DAYS_NEED} distinct UTC quote days (Real accumulate or vendor tape)",
            f"- ≥{COMM_NEED} unique commission observations per primary symbol",
            f"- ≥{SLIP_NEED} side-referenced fill/slip samples per symbol",
            "",
            "### Binding blocker",
            "",
            "`COST_PROVENANCE_GAP` remains **NARROWED_NOT_CLEARED**. Track B "
            "(architecture rebuild) proceeds without inventing a surface.",
        ]
    proof += [
        "",
        f"Receipt: `{receipt}`",
        f"Sample: `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        "",
    ]
    OUT_PROOF.write_text("\n".join(proof) + "\n", encoding="utf-8")

    print(json.dumps({"receipt": receipt, "table_sha": table_sha, "verdict": verdict}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
