"""VPA-DR1 trace tool — full gate evaluation per candidate, no short-circuit.

Shares the single gate code path with `Dr1Detector` (`_dr1_gates`,
`verdict_from_gates`, `full_fail_set`); this module re-implements NO gate.

Used for:
  - the recall trace on the Lead-labelled cases (`PLAN/diag_dr1/`);
  - later, as the reference for the MQL5 forensic indicator (draw what the EA
    sees and why it skipped).
"""

import csv
import os

from vpa_dr1 import Dr1Detector, full_fail_set  # noqa: F401  (shared gate path)

TRACE_FIELDS = [
    "case_id", "lead_grade", "group", "setup_v1", "bar_idx", "side", "case_barrier",
    "dr1_barrier", "dr1_lock_idx", "touches", "category", "reason", "n_evals",
    "first_fail", "fail_set", "session", "trend_slope", "trend_frac",
    "buildup_n", "band_closes", "buildup_touches", "overlap", "contraction",
    "chop_value", "room_r", "obstacle_price", "obstacle_type",
    "adverse_price", "adverse_type", "entry_b_atr", "range_atr", "ema_dist_atr",
]


def run_trace(bars, cfg=None, max_bars=None):
    """Run the detector once with gate collection and compact event logs."""
    c = {"collect_gates": True, "trace_barriers": True}
    if cfg:
        c.update(cfg)
    d = Dr1Detector(bars, cfg=c)
    recs, counters = d.run(max_bars=max_bars)
    return d, recs, counters


def row_from_record(rec):
    g = rec.get("gates") or {}
    bu = (g.get("buildup", {}).get("value") or {})
    room = (g.get("room", {}).get("value") or {})
    obs = room.get("obstacle") or {}
    adv = (g.get("adverse", {}).get("value") or {})
    anti = (g.get("anti_chase", {}).get("value") or {})
    chop = (g.get("chop", {}).get("value") or {})
    return {
        "bar_idx": rec.get("bar_idx"), "side": rec.get("side"), "barrier": rec.get("level"),
        "touches": len(rec.get("touches") or []), "session": rec.get("session"),
        "trend_slope": g.get("trend", {}).get("value", {}).get("slope"),
        "trend_frac": g.get("trend", {}).get("value", {}).get("frac"),
        "buildup_n": bu.get("n"), "band_closes": bu.get("band_closes"),
        "buildup_touches": bu.get("touches"), "overlap": bu.get("overlap"),
        "contraction": bu.get("contraction"),
        "chop_value": chop.get("chop"), "room_r": room.get("room_r"),
        "obstacle_price": obs.get("price"), "obstacle_type": obs.get("type"),
        "adverse_price": adv.get("price"), "adverse_type": adv.get("type"),
        "entry_b_atr": anti.get("entry_b_atr"), "range_atr": anti.get("range_atr"),
        "ema_dist_atr": anti.get("ema_dist_atr"),
        "first_fail": rec.get("skip_reason"), "fail_set": ";".join(full_fail_set(g)),
        "executable": rec.get("executable"), "setup": rec.get("setup"),
    }


def active_barriers(d, lo, hi):
    """Barriers whose [lock_idx, exp_idx] overlaps [lo, hi], with the bar they
    were first consumed (if any) from the compact event log."""
    consumed = {}
    for (t, kind, side, level, lock_idx) in d.event_log:
        consumed.setdefault((side, level, lock_idx), (t, kind))
    out = []
    for (lock_idx, side, level, exp_idx, touches) in d.lock_log:
        if lock_idx > hi or exp_idx < lo:
            continue
        end = min(exp_idx, consumed.get((side, level, lock_idx), (exp_idx, None))[0])
        out.append({"side": side, "level": level, "lock_idx": lock_idx, "exp_idx": exp_idx,
                    "touches": len(touches), "consumed_at": consumed.get((side, level, lock_idx), (None, None))[0],
                    "consumed_kind": consumed.get((side, level, lock_idx), (None, None))[1],
                    "active_end": end})
    return out


def classify_cases(bars, cases, half=12, cfg=None):
    """One detector run over the full series; classify every labelled case."""
    d, recs, counters = run_trace(bars, cfg=cfg)
    by_bar = {}
    for r in recs:
        by_bar.setdefault(r["bar_idx"], []).append(r)
    out = []
    for case in cases:
        row = dict(case)
        cb = case.get("bar_idx")
        side = case.get("side")
        lvl = case.get("barrier_level")
        tol = max(0.25 * (case.get("atr") or 0.0004), 2 * bars["pip"])
        lo, hi = (cb - half, cb + half) if cb is not None else (None, None)
        row.update({"dr1_barrier": None, "dr1_lock_idx": None, "touches": None,
                    "category": None, "reason": None, "n_evals": 0,
                    "first_fail": None, "fail_set": None})
        if cb is None or lvl is None:
            row["category"] = "(i) no barrier locked nearby"
            row["reason"] = "no case barrier level (PR case or missing key)"
            out.append(row)
            continue
        barriers = [b for b in active_barriers(d, lo, hi)
                    if b["side"] == side and abs(b["level"] - lvl) <= tol]
        if not barriers:
            row["category"] = "(i) no barrier locked nearby"
            out.append(row)
            continue
        b0 = barriers[0]
        row["dr1_barrier"] = round(b0["level"], 6)
        row["dr1_lock_idx"] = b0["lock_idx"]
        row["touches"] = b0["touches"]
        row["_barriers"] = barriers
        row["_consumed_at"] = b0["consumed_at"]
        row["_consumed_kind"] = b0["consumed_kind"]
        evals = []
        for t in range(lo, hi + 1):
            for r in by_bar.get(t, []):
                if r["side"] == side and abs(r["level"] - b0["level"]) <= tol:
                    evals.append(r)
        row["n_evals"] = len(evals)
        if not evals:
            row["category"] = "(ii) no signal eval"
            if b0["consumed_kind"] == "missed" and lo <= (b0["consumed_at"] or 0) <= hi:
                row["reason"] = "barrier consumed as missed break at t=%s" % b0["consumed_at"]
            elif b0["consumed_kind"] == "exec":
                row["reason"] = "barrier consumed by an earlier executable at t=%s" % b0["consumed_at"]
            elif b0["consumed_at"] is None and b0["exp_idx"] < cb:
                row["reason"] = "barrier expired before the case bar"
            else:
                row["reason"] = ("no close inside [B-0.05A, B+0.25A] within +/-%d bars "
                                 "(signal-bar definition/window/session)" % half)
            out.append(row)
            continue
        last = evals[-1]
        row["_last_rec"] = last
        if any(r.get("executable") for r in evals):
            row["category"] = "(iv) executable"
            row["fail_set"] = ""
        else:
            row["category"] = "(iii) evaluated but failed"
            row["first_fail"] = last.get("skip_reason")
            row["fail_set"] = ";".join(full_fail_set(last.get("gates") or {}))
        # measured values from the last evaluation
        m = row_from_record(last)
        for k in ("session", "trend_slope", "trend_frac", "buildup_n", "band_closes",
                  "buildup_touches", "overlap", "contraction", "chop_value", "room_r",
                  "obstacle_price", "obstacle_type", "adverse_price", "adverse_type",
                  "entry_b_atr", "range_atr", "ema_dist_atr"):
            row[k] = m.get(k)
        out.append(row)
    return d, out, counters


def write_csv(path, rows, fields=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = fields or TRACE_FIELDS
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
