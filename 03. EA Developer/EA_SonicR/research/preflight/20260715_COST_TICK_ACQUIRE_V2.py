#!/usr/bin/env python3
"""Track A V2 — aggressive same-broker tick/cost surface acquire.

Authority: Owner post-greenfield 2026-07-15; monetization rebuild authorized;
EXO_FRED_DISPLACE_SPAM_PAUSED. Maximize honest bid/ask + commission/slip
coverage via QFSI disk + MT5 day-chunks + deal history. SHA-freeze only if
research-grade; else document exact GAP.

Never invent zeros. Never RR2 full rebind under non-research surface.
Bulk multi-month copy_ticks_range hangs this terminal — use day chunks.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
EV = ROOT / "02. AlphaFactory" / "evidence" / "execution" / "FivePercentOnline-Real"
OUT_DIR = EV / "20260715_COST_TICK_ACQUIRE_V2"

OUT_JSON = PRE / "20260715_COST_TICK_ACQUIRE_V2.json"
OUT_TABLE = PRE / "20260715_COST_SURFACE_SESSION_HOUR_TABLE_V2.json"
OUT_MD = READ / "20260715_COST_TICK_ACQUIRE_V2.md"
OUT_PROOF = READ / "20260715_COST_TICK_ACQUIRE_V2_COVERAGE_PROOF.md"
OUT_GAP = READ / "20260715_COST_TICK_ACQUIRE_V2_REMAINING_GAP.md"

# Expanded book for broader session coverage
SYMBOLS = [
    "USDJPY",
    "EURUSD",
    "GBPUSD",
    "XAUUSD",
    "AUDUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "EURJPY",
    "GBPJPY",
    "BTCUSD",
]
PRIMARY = ["USDJPY", "EURUSD", "GBPUSD", "XAUUSD"]
SESSION_UTC = {
    "ASIA": range(0, 7),
    "LONDON": range(7, 12),
    "LONDON_NY": range(12, 16),
    "NY": range(16, 21),
    "OFF": range(21, 24),
}
QUOTE_DAYS_NEED = 90
COMM_NEED = 30
SLIP_NEED = 100
MAX_DAYS = 60  # aggressive day-chunk probe
EMPTY_STREAK_STOP = 5
MAX_SPREADS_PER_SYM = 250_000


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


def parse_ts(ts_raw: Any) -> datetime | None:
    s = str(ts_raw or "")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        v = float(ts_raw)
        if v > 1e12:
            v /= 1000.0
        return datetime.fromtimestamp(v, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def inventory_qfsi() -> dict[str, Any]:
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
        if "QFSI_REAL" not in name and "DEAL_HISTORY" not in name and "COST_TICK" not in name:
            continue
        sessions_seen.append(name)
        for sym in SYMBOLS:
            qp = d / f"{sym}_quote_ticks.csv"
            if not qp.exists():
                # also accept nested
                hits = list(d.rglob(f"{sym}_quote_ticks.csv"))
                if not hits:
                    continue
                qp = hits[0]
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
                    dt = parse_ts(row.get("time_utc") or row.get("time") or row.get("Time"))
                    if dt is None:
                        continue
                    day = dt.strftime("%Y-%m-%d")
                    quote_days.add(day)
                    tick_n[sym] += 1
                    hour_spreads[sym][str(dt.hour)].append(ask - bid)

    comm_by_sym: dict[str, set[str]] = defaultdict(set)
    slip_n = 0
    for d in EV.rglob("*commission*.csv"):
        try:
            with d.open("r", encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    sym = str(row.get("symbol") or row.get("Symbol") or "").upper()
                    pid = str(
                        row.get("position_id") or row.get("ticket") or row.get("deal") or ""
                    )
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


def pull_deals(mt5) -> dict[str, Any]:
    """Opportunistic deal-history commission/slip sample if Real is live."""
    info = mt5.account_info()
    if info is None:
        return {"ok": False, "error": "account_info_none"}
    now = datetime.now(timezone.utc)
    frm = now - timedelta(days=3650)
    deals = mt5.history_deals_get(frm, now)
    if deals is None:
        return {"ok": False, "error": f"history_deals_get:{mt5.last_error()}", "n": 0}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    comm_by: dict[str, set[str]] = defaultdict(set)
    slip_rows = 0
    for d in deals:
        sym = str(d.symbol or "").upper()
        comm = float(d.commission)
        profit = float(d.profit)
        volume = float(d.volume)
        entry = int(d.entry)  # 0 in, 1 out
        deal_id = str(d.ticket)
        pos_id = str(d.position_id)
        t = datetime.fromtimestamp(int(d.time), tz=timezone.utc).isoformat()
        rows.append(
            {
                "deal": deal_id,
                "position_id": pos_id,
                "symbol": sym,
                "time_utc": t,
                "entry": entry,
                "type": int(d.type),
                "volume": volume,
                "price": float(d.price),
                "commission": comm,
                "swap": float(d.swap),
                "profit": profit,
                "magic": int(d.magic),
                "comment": str(d.comment or ""),
            }
        )
        if sym and abs(comm) > 1e-12:
            comm_by[sym].add(pos_id or deal_id)
        # Slippage side-ref not in deal alone — count MISSING, not 0
    deals_path = OUT_DIR / "deals_raw.csv"
    with deals_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["deal"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return {
        "ok": True,
        "login": int(info.login),
        "server": str(info.server),
        "n_deals": len(rows),
        "commission_unique_by_symbol": {k: len(v) for k, v in comm_by.items()},
        "slip_side_ref_fills": "MISSING_NE_0",
        "slip_fill_rows": slip_rows,
        "deals_csv": str(deals_path.relative_to(ROOT)).replace("\\", "/"),
        "trade_mode": int(info.trade_mode) if hasattr(info, "trade_mode") else None,
    }


def sample_mt5_history(mt5, max_days: int = MAX_DAYS) -> dict[str, Any]:
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
        "method": "copy_ticks_range_1day_chunks_plus_copy_ticks_from_anchors",
        "max_days_probed": max_days,
        "anchors_tried": [],
    }
    print(f"[cost-v2] mt5 ok server={server} login={login}", flush=True)

    # Extra: sparse month-ago anchors via copy_ticks_from (fast; avoids hang)
    anchors = [1, 7, 14, 30, 60, 90, 180]
    for days_ago in anchors:
        out["anchors_tried"].append(days_ago)

    for sym in SYMBOLS:
        t0 = time.time()
        print(f"[cost-v2] symbol={sym} …", flush=True)
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
        day_hits: list[dict[str, Any]] = []

        for day_i in range(max_days):
            day_to = now - timedelta(days=day_i)
            day_from = day_to - timedelta(days=1)
            ticks = mt5.copy_ticks_range(sym, day_from, day_to, mt5.COPY_TICKS_ALL)
            n = 0 if ticks is None else len(ticks)
            n_raw += n
            if n == 0:
                empty_streak += 1
                day_hits.append({"day_i": day_i, "n": 0})
                if empty_streak >= EMPTY_STREAK_STOP:
                    break
                continue
            empty_streak = 0
            days_with_data += 1
            day_hits.append({"day_i": day_i, "n": n})
            dmin, dmax = _ingest_ticks(ticks, spreads, by_day, by_hour, by_session)
            if dmin and (t_min is None or dmin < t_min):
                t_min = dmin
            if dmax and (t_max is None or dmax > t_max):
                t_max = dmax
            print(f"  [cost-v2] {sym} day-{day_i} ticks={n} days={len(by_day)}", flush=True)
            if len(spreads) >= MAX_SPREADS_PER_SYM:
                break

        # Sparse anchors: copy_ticks_from at past points (broker may retain buffer)
        anchor_hits = {}
        for days_ago in anchors:
            if len(spreads) >= MAX_SPREADS_PER_SYM:
                break
            from_dt = now - timedelta(days=days_ago)
            ticks_a = mt5.copy_ticks_from(sym, from_dt, 5000, mt5.COPY_TICKS_ALL)
            n_a = 0 if ticks_a is None else len(ticks_a)
            anchor_hits[str(days_ago)] = n_a
            if n_a:
                dmin, dmax = _ingest_ticks(ticks_a, spreads, by_day, by_hour, by_session)
                if dmin and (t_min is None or dmin < t_min):
                    t_min = dmin
                if dmax and (t_max is None or dmax > t_max):
                    t_max = dmax
                n_raw += n_a

        ticks_buf = mt5.copy_ticks_from(sym, now, 30000, mt5.COPY_TICKS_ALL)
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
        # Persist per-symbol day summary CSV for audit
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        day_csv = OUT_DIR / f"{sym}_day_chunk_hits.csv"
        with day_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["day_i", "n"])
            w.writeheader()
            for row in day_hits:
                w.writerow(row)

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
            "anchor_ticks_from": anchor_hits,
            "elapsed_sec": round(time.time() - t0, 2),
            "sessions_covered": sorted(sess_tbl.keys()),
        }
        print(
            f"[cost-v2] {sym} done days={len(by_day)} samples={len(spreads)} "
            f"sessions={sorted(sess_tbl.keys())} "
            f"p50_usd={out['symbols'][sym]['spread_usd_per_lot_p50']} "
            f"({out['symbols'][sym]['elapsed_sec']}s)",
            flush=True,
        )
    return out


def build_verdict(
    qfsi: dict[str, Any], mt5s: dict[str, Any], deals: dict[str, Any]
) -> dict[str, Any]:
    days_disk = int(qfsi.get("n_quote_calendar_days") or 0)
    days_mt5 = 0
    mt5_days_set: set[str] = set()
    sessions_union: set[str] = set()
    if mt5s.get("ok"):
        for _sym, row in (mt5s.get("symbols") or {}).items():
            for d in row.get("calendar_days") or []:
                mt5_days_set.add(d)
            days_mt5 = max(days_mt5, int(row.get("n_calendar_days_with_ticks") or 0))
            for s in row.get("sessions_covered") or []:
                sessions_union.add(s)
    union_days = set(qfsi.get("quote_calendar_days") or []) | mt5_days_set
    n_union = len(union_days)

    # Merge commission: disk + live deals
    comm: dict[str, int] = dict(qfsi.get("commission_unique_by_symbol") or {})
    if deals.get("ok"):
        for k, v in (deals.get("commission_unique_by_symbol") or {}).items():
            comm[k] = max(int(comm.get(k) or 0), int(v))
    slip = int(qfsi.get("slip_fill_rows_approx") or 0)
    if deals.get("ok") and isinstance(deals.get("slip_fill_rows"), int):
        slip = max(slip, int(deals["slip_fill_rows"]))

    freeze_ok = (
        n_union >= QUOTE_DAYS_NEED
        and int(comm.get("EURUSD") or 0) >= COMM_NEED
        and int(comm.get("USDJPY") or 0) >= COMM_NEED
        and slip >= SLIP_NEED * len(PRIMARY)
    )
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
        reason_bits.append(f"slip≈{slip}/{SLIP_NEED}+_MISSING_NE_0")
    if not mt5s.get("ok"):
        reason_bits.append(f"mt5_sample_fail:{mt5s.get('error')}")

    unlock = [
        f">={QUOTE_DAYS_NEED} distinct UTC quote days (Real QFSI accumulate multi-week OR broker/vendor multi-month tick tape)",
        f">={COMM_NEED} unique commission observations per primary (EURUSD, USDJPY) from Real deal history",
        f">={SLIP_NEED} side-referenced fill/slip samples per primary symbol (order→fill, not deal.profit alone)",
        "Do not use Strategy Tester 'current' spread as research cost surface",
        "Bulk copy_ticks_range multi-month hangs this terminal — need chunked offline dump or vendor tape",
    ]

    return {
        "grade": grade,
        "sha_freeze_eligible_for_research_cost_surface": freeze_ok,
        "sha_freeze_partial_diagnostic_table": partial_ok or n_union >= 1,
        "n_union_quote_calendar_days": n_union,
        "union_quote_calendar_days": sorted(union_days),
        "n_mt5_history_days_max_symbol": days_mt5,
        "n_qfsi_disk_days": days_disk,
        "sessions_covered_union": sorted(sessions_union),
        "commission_merged": comm,
        "slip_fill_rows_approx": slip,
        "missing_for_research_freeze": reason_bits,
        "what_unlocks_freeze": unlock,
        "rr2_restress_under_session_surface": "NOT_RUN_SURFACE_NOT_RESEARCH_GRADE"
        if not freeze_ok
        else "ARMED_NOT_AUTO",
    }


def main() -> int:
    print("[cost-v2] inventory QFSI disk…", flush=True)
    qfsi = inventory_qfsi()
    print(
        f"[cost-v2] QFSI days={qfsi.get('n_quote_calendar_days')} "
        f"ticks={qfsi.get('tick_n_by_symbol')}",
        flush=True,
    )

    try:
        import MetaTrader5 as mt5
    except Exception as exc:  # noqa: BLE001
        mt5s = {"ok": False, "error": f"import:{exc}"}
        deals = {"ok": False, "error": "no_mt5"}
    else:
        if not mt5.initialize():
            mt5s = {"ok": False, "error": f"initialize:{mt5.last_error()}"}
            deals = {"ok": False, "error": "mt5_init_fail"}
        else:
            try:
                deals = pull_deals(mt5)
                print(
                    f"[cost-v2] deals n={deals.get('n_deals')} "
                    f"comm={deals.get('commission_unique_by_symbol')}",
                    flush=True,
                )
                mt5s = sample_mt5_history(mt5, max_days=MAX_DAYS)
            finally:
                mt5.shutdown()

    verdict = build_verdict(qfsi, mt5s, deals)

    table: dict[str, Any] = {
        "schema": "cost_surface_session_hour_table.v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "label": verdict["grade"],
        "research_freeze_eligible": verdict["sha_freeze_eligible_for_research_cost_surface"],
        "sources": {
            "qfsi_disk": "02. AlphaFactory/evidence/execution/FivePercentOnline-Real/",
            "mt5_history": mt5s.get("method"),
            "mt5_server": mt5s.get("server"),
            "mt5_login": mt5s.get("login"),
            "deals": deals.get("deals_csv"),
        },
        "symbols": {},
        "coverage_gaps": verdict["missing_for_research_freeze"],
        "what_unlocks_freeze": verdict["what_unlocks_freeze"],
        "policy": [
            "Do not invent spreads/commission/slip",
            "Do not re-stress RR2 under non-research-grade surface",
            "MISSING slip ≠ 0",
            "QFSI accumulate remains required for full freeze",
        ],
    }
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
                "sessions_covered": row.get("sessions_covered"),
                "anchor_ticks_from": row.get("anchor_ticks_from"),
                "source": "mt5_copy_ticks_range_day_chunks_v2",
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
        "schema": "cost_tick_acquire_v2.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": (
            "Owner post-greenfield 2026-07-15; monetization rebuild authorized; "
            "EXO_FRED_DISPLACE_SPAM_PAUSED; Track A V2"
        ),
        "qfsi_disk": {
            k: v
            for k, v in qfsi.items()
            if k != "hour_x_symbol_spread"
        },
        "qfsi_hour_summary_n_symbols": len(qfsi.get("hour_x_symbol_spread") or {}),
        "deals_live": deals,
        "mt5_history": {k: v for k, v in mt5s.items() if k != "symbols"},
        "mt5_symbols_summary": {
            sym: {
                "available": row.get("available"),
                "requested_days": row.get("requested_days"),
                "n_ticks": row.get("n_ticks_raw") or row.get("n_spread_samples"),
                "n_calendar_days": row.get("n_calendar_days_with_ticks"),
                "calendar_days": row.get("calendar_days"),
                "time_min_utc": row.get("time_min_utc"),
                "time_max_utc": row.get("time_max_utc"),
                "spread_usd_per_lot_p50": row.get("spread_usd_per_lot_p50"),
                "spread_usd_per_lot_p90": row.get("spread_usd_per_lot_p90"),
                "sessions_covered": row.get("sessions_covered"),
                "anchor_ticks_from": row.get("anchor_ticks_from"),
                "elapsed_sec": row.get("elapsed_sec"),
            }
            for sym, row in (mt5s.get("symbols") or {}).items()
        },
        "verdict": verdict,
        "table_path": str(OUT_TABLE.relative_to(ROOT)).replace("\\", "/"),
    }

    OUT_TABLE.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    table_sha = sha256_file(OUT_TABLE)
    payload["table_sha256"] = table_sha
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    receipt = sha256_file(OUT_JSON)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Cost/tick acquire V2 — Track A",
        "",
        "Date: 2026-07-15",
        f"Status: `{verdict['grade']}`",
        f"Research freeze eligible: **{verdict['sha_freeze_eligible_for_research_cost_surface']}**",
        f"Receipt SHA: `{receipt}`",
        f"Table SHA: `{table_sha}`",
        "",
        "## Verdict",
        "",
        f"- Union quote calendar days: **{verdict['n_union_quote_calendar_days']}** "
        f"(need {QUOTE_DAYS_NEED}) → `{verdict['union_quote_calendar_days']}`",
        f"- MT5 history max days/symbol: **{verdict['n_mt5_history_days_max_symbol']}**",
        f"- QFSI disk days: **{verdict['n_qfsi_disk_days']}**",
        f"- Sessions covered (MT5): `{verdict['sessions_covered_union']}`",
        f"- Commission merged: `{verdict['commission_merged']}`",
        f"- Gaps: {', '.join(verdict['missing_for_research_freeze']) or 'none'}",
        f"- RR2 re-stress: `{verdict['rr2_restress_under_session_surface']}`",
        "",
        "## Live deals (opportunistic)",
        "",
        f"- OK: `{deals.get('ok')}` login=`{deals.get('login')}` server=`{deals.get('server')}`",
        f"- n_deals=`{deals.get('n_deals')}` comm=`{deals.get('commission_unique_by_symbol')}`",
        f"- slip: `{deals.get('slip_side_ref_fills')}` (MISSING ≠ 0)",
        "",
        "## MT5 day-chunk + anchor sample",
        "",
        f"- Server/login: `{mt5s.get('server')}` / `{mt5s.get('login')}`",
        f"- OK: `{mt5s.get('ok')}` error=`{mt5s.get('error')}` max_days=`{MAX_DAYS}`",
        "",
    ]
    for sym, row in (payload.get("mt5_symbols_summary") or {}).items():
        lines.append(
            f"- **{sym}**: days={row.get('n_calendar_days')} ticks={row.get('n_ticks')} "
            f"usd/lot p50={row.get('spread_usd_per_lot_p50')} "
            f"sessions={row.get('sessions_covered')} "
            f"anchors={row.get('anchor_ticks_from')} "
            f"window={row.get('time_min_utc')}→{row.get('time_max_utc')}"
        )
    lines += [
        "",
        "## Policy",
        "",
        "- Do **not** invent commission/slip.",
        "- Do **not** claim research-grade freeze unless freeze_eligible.",
        "- Keep Real QFSI accumulate as parallel hygiene (not stall).",
        "",
        "## Artifacts",
        "",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_TABLE.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_PROOF.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_GAP.relative_to(ROOT).as_posix()}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    proof = [
        "# Cost/tick acquire V2 — coverage proof",
        "",
        "## Question",
        "",
        "Did this board clear research-grade multi-month bid/ask×commission×slip freeze?",
        "",
        "## Answer",
        "",
    ]
    if verdict["sha_freeze_eligible_for_research_cost_surface"]:
        proof.append("**YES — research freeze eligible.**")
    else:
        proof += [
            "**NO — research-grade freeze still blocked.**",
            "",
            "### Observed (honest max tonight)",
            "",
            f"- Union quote days: **{verdict['n_union_quote_calendar_days']}** / {QUOTE_DAYS_NEED}",
            f"- MT5 day-chunk max: **{verdict['n_mt5_history_days_max_symbol']}** calendar day(s)",
            f"- Symbols probed: **{len(SYMBOLS)}** (primary+majors+BTC)",
            f"- Sessions seen: `{verdict['sessions_covered_union']}`",
            f"- Commission merged: `{verdict['commission_merged']}`",
            f"- Slip: **{verdict['slip_fill_rows_approx']}** (MISSING ≠ 0 if side-ref absent)",
            "",
            f"- Diagnostic table SHA: `{table_sha}` grade=`{verdict['grade']}`",
            "",
            "### Exact remaining GAP",
            "",
        ]
        for g in verdict["missing_for_research_freeze"]:
            proof.append(f"- `{g}`")
        proof += ["", "### What unlocks freeze", ""]
        for u in verdict["what_unlocks_freeze"]:
            proof.append(f"- {u}")
        proof += [
            "",
            "### Binding blocker",
            "",
            "`COST_PROVENANCE_GAP` remains **NARROWED_NOT_CLEARED**. "
            "Track B monetization rebuild proceeds without inventing a surface.",
        ]
    proof += ["", f"Receipt: `{receipt}`", f"Sample: `{OUT_JSON.relative_to(ROOT).as_posix()}`", ""]
    OUT_PROOF.write_text("\n".join(proof) + "\n", encoding="utf-8")

    gap_md = [
        "# Remaining GAP — cost/tick acquire V2",
        "",
        f"Grade: `{verdict['grade']}`",
        f"Freeze eligible: **{verdict['sha_freeze_eligible_for_research_cost_surface']}**",
        "",
        "## Gaps",
        "",
    ]
    for g in verdict["missing_for_research_freeze"]:
        gap_md.append(f"- `{g}`")
    gap_md += ["", "## Unlock checklist", ""]
    for u in verdict["what_unlocks_freeze"]:
        gap_md.append(f"- [ ] {u}")
    gap_md += [
        "",
        "## Not blockers (do not stall)",
        "",
        "- Real login already connected → used opportunistically for deals+ticks.",
        "- QFSI accumulate continues in parallel; do not kill Real to chase ceremony.",
        "- Monetization rebuild Track B is authorized offline without this freeze.",
        "",
        f"Receipt: `{receipt}`",
        "",
    ]
    OUT_GAP.write_text("\n".join(gap_md) + "\n", encoding="utf-8")

    print(json.dumps({"receipt": receipt, "table_sha": table_sha, "verdict": verdict}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
