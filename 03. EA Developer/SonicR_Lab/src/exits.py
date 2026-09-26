"""exits.py - ROUND 2D managed-exit layer for F2_NH_b (Lead 21:25Z).

One exit-resolution path shared by BOTH evaluation modes:
  - fixed list: re-simulate the exit of each X0 trade from its fill bar
    (runs/design_2d.py) - every selection statistic uses this.
  - free running: sim.run_trades(..., exit_rule=...) calls the same
    function, so the one-position rule reshuffles later signals.

Rules (trigger = first CLEAN M1 bar i, fill bar included, whose
favourable extreme reaches fill + dir * 1.0 * R0, R0 = |fill - SL|):
  X0   baseline (F2_NH_b as in 2C) - no management.
  X1   BE1: from bar i+1 SL -> BE = fill + dir*cost_x1 (reason "be").
  X2   PART: two half positions at fill; leg A TP = +1R, leg B original
       TP; both carry original SL; when leg A fills on bar i, leg B SL
       -> BE from i+1. One round-trip cost for the whole size.
  X3   DRAGON: X1 + exit at the open of the first clean M1 bar of the
       next M15 bar after an M15 close through EMA34(Low) (long; High
       for short) - priority over that M1 bar's SL/TP (reason "dragon").
  X4   RUN: X3 with NO take-profit (exits: SL/BE/dragon/flats).

EA semantics (copied exactly): the EA acts at the OPEN of bar i+1, so a
new stop level is live from bar i+1; on bar i the original SL/TP hold;
inside a bar the order is SL first, then TP. pessimistic=True implements
the reported "pessimistic same-bar" column: if the trigger bar's range
also contains the BE level, exit at BE on that bar (unless SL first).
E1 (skip suspect), E1b (roll stress), Friday/daily flat: identical to
SL/TP handling today.
"""
from __future__ import annotations

import numpy as np

from . import data as data_mod
from . import sim as sim_mod              # _in_roll, round_trip_cost

BE = "be"


def _be_level(sym, fill, dr):
    return fill + dr * sim_mod.round_trip_cost(sym)


def _sl_fill(dr, level, mo_i):
    """Stop fill: gap -> bar open (long: worse = lower)."""
    return (min(level, mo_i) if mo_i < level else level) if dr == 1 else \
        (max(level, mo_i) if mo_i > level else level)


def _tp_fill(dr, level, mo_i, prev_sus):
    """TP fill: gap bonus allowed, except right after a suspect run."""
    if dr == 1:
        return level if (prev_sus and mo_i >= level) else \
            (max(level, mo_i) if mo_i > level else level)
    return level if (prev_sus and mo_i <= level) else \
        (min(level, mo_i) if mo_i < level else level)


def _dragon_exit_i(m1, tfx, trig_i, dr, skip_suspect):
    """First dragon exit M1 index after the trigger bar's time, or -1.

    For each M15 bar j whose CLOSE time (tf.t[j]+900) is after the
    trigger bar's time: long exits when tf.c[j] < EMA34(low)[j]; the
    exit is the open of the first clean M1 bar of the next M15 bar.
    Under H1, skip j when its LAST M1 bar is suspect."""
    mt = m1["t"]; msus = m1.get("suspect")
    t_c, e34h, e34l = tfx["c"], tfx["e34h"], tfx["e34l"]
    hi_idx = tfx["m1_hi"]
    t0 = mt[trig_i]
    j0 = int(np.searchsorted(tfx["t"] + 900, t0, side="right"))
    for j in range(j0, len(t_c)):
        last_m1 = int(hi_idx[j]) - 1
        if last_m1 < 0:
            continue
        if skip_suspect and msus is not None and msus[last_m1]:
            continue                                  # E1: skip check
        cond = (dr == 1 and t_c[j] < e34l[j]) or \
               (dr == -1 and t_c[j] > e34h[j])
        if not cond:
            continue
        k = int(np.searchsorted(mt, tfx["t"][j] + 900))
        if skip_suspect and msus is not None:
            while k < len(mt) and msus[k]:
                k += 1
        return k if k < len(mt) else -1
    return -1


def resolve_exit(m1, tfx, sym, dr, fill_i, fill, sl, tp, flat_ctm,
                 rule, skip_suspect=False, daily_flat_ctm=None,
                 pessimistic=False):
    """Re-simulate ONE trade's exit from its fill bar.

    tfx: dict with tf arrays needed for dragon {"t","c","e34h","e34l",
    "m1_hi"} (None-safe for non-dragon rules). rule: "X0".."X4".
    Returns dict(exit_i, exit_px, reason, part_i, part_px, mfe_seg)."""
    mt, mo, mh, ml = m1["t"], m1["o"], m1["h"], m1["l"]
    msus = m1.get("suspect", np.zeros(len(mt), bool))
    R0 = abs(fill - sl)
    trig = fill + dr * 1.0 * R0
    be = _be_level(sym, fill, dr)
    has_tp = rule != "X4"
    two_leg = rule == "X2"
    dragon = rule in ("X3", "X4")

    fctm = min(flat_ctm, daily_flat_ctm) \
        if daily_flat_ctm is not None else flat_ctm
    last_i = int(np.searchsorted(mt, fctm))
    if last_i <= fill_i:
        last_i = fill_i + 1 if fill_i + 1 < len(mt) else fill_i
    scan_end = min(last_i, len(mt))

    sl_cur = sl                       # live stop (may move to BE)
    trig_i = -1
    dragon_i = -1
    part_i = -1; part_px = np.nan     # X2 leg A
    prev_sus = False
    exit_i = -1; exit_px = np.nan; reason = ""

    i = fill_i
    while i < scan_end:
        if skip_suspect and msus[i]:
            prev_sus = True
            i += 1
            continue
        sgn = sim_mod._roll_px(sym) if sim_mod._in_roll(sym, int(mt[i])) \
            else 0.0
        # ---- dragon exit has priority on its bar ---------------------
        if dragon_i >= 0 and i == dragon_i:
            exit_i = i; exit_px = mo[i]; reason = "dragon"
            break
        # ---- stops (SL first) ----------------------------------------
        tp_hit = has_tp and ((mh[i] >= tp) if dr == 1 else (ml[i] <= tp))
        if dr == 1:
            if ml[i] <= sl_cur:
                exit_i = i
                exit_px = _sl_fill(1, sl_cur, mo[i]) - sgn
                reason = "be" if sl_cur != sl else \
                    ("sl_same" if (i == fill_i and tp_hit) else "sl")
                break
        else:
            if mh[i] >= sl_cur:
                exit_i = i
                exit_px = _sl_fill(-1, sl_cur, mo[i]) + sgn
                reason = "be" if sl_cur != sl else \
                    ("sl_same" if (i == fill_i and tp_hit) else "sl")
                break
        # ---- pessimistic same-bar: trigger + BE in one bar -> BE ------
        hit_t = (mh[i] >= trig) if dr == 1 else (ml[i] <= trig)
        if trig_i < 0 and hit_t and pessimistic and not two_leg:
            be_hit = (ml[i] <= be) if dr == 1 else (mh[i] >= be)
            if be_hit:
                exit_i = i
                exit_px = _sl_fill(dr, be, mo[i])
                exit_px += -sgn if dr == 1 else sgn
                reason = "be"
                break
        # ---- X2 leg A (+1R TP, no gap bonus) --------------------------
        if two_leg and part_i < 0:
            hit_a = (mh[i] >= trig) if dr == 1 else (ml[i] <= trig)
            if hit_a:
                part_i = i
                part_px = trig + (-sgn if dr == 1 else sgn)
                # leg B SL -> BE from bar i+1 (deferred below)
                if pessimistic:
                    be_hit = (ml[i] <= be) if dr == 1 else (mh[i] >= be)
                    if be_hit:
                        exit_i = i
                        exit_px = _sl_fill(dr, be, mo[i])
                        exit_px += -sgn if dr == 1 else sgn
                        reason = "be"
                        break
        # ---- TP (leg B / single leg) -----------------------------------
        if has_tp:
            if tp_hit:
                exit_i = i
                exit_px = _tp_fill(dr, tp, mo[i], prev_sus)
                exit_px += -sgn if dr == 1 else sgn
                reason = "tp"
                break
        # ---- trigger bookkeeping (levels live from bar i+1) -----------
        if trig_i < 0 and hit_t:
            trig_i = i
            if rule in ("X1", "X3", "X4"):
                sl_cur = be                   # live from i+1
            if dragon:
                dragon_i = _dragon_exit_i(m1, tfx, trig_i, dr,
                                          skip_suspect)
                if 0 <= dragon_i <= i:        # decided for a past bar
                    dragon_i = i + 1          # cannot act retroactively
        if two_leg and part_i == i and sl_cur == sl:
            sl_cur = be                       # leg B BE live from i+1
        prev_sus = False
        i += 1

    if exit_i < 0:                            # friday/daily flatten
        j = min(last_i, len(mt) - 1)
        while j < len(mt) - 1 and skip_suspect and msus[j]:
            j += 1
        exit_i = j; exit_px = mo[j]
        reason = "flat" if last_i < len(mt) else "window_end"
    seg = np.arange(fill_i, exit_i + 1)
    if skip_suspect:
        seg = seg[~msus[seg]]
        if len(seg) == 0:
            seg = np.array([fill_i])
    return {"exit_i": int(exit_i), "exit_px": float(exit_px),
            "reason": reason, "part_i": int(part_i),
            "part_px": float(part_px), "seg": seg}
