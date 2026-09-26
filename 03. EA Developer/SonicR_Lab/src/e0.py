"""e0.py - E0 impossible-print flags (LEAD_NOTE_5, frozen thresholds).

An M1 bar i is an IMPOSSIBLE PRINT if both hold:
  (a) max(|high_i/ref_i - 1|, |low_i/ref_i - 1|) > thresh (3%), where
      ref_i = close of the last bar before i that is not itself an
      impossible print;
  (b) the close of the first bar at or after (t_i + revert_sec, 15min)
      is within revert_tol (0.5%) of ref_i - the price came back.

Voided exactly like E1 suspect bars, on BOTH harnesses (wired into
run_trades via void_extra). Flags are computed on the loaded M1 slice
only - never past VALIDATION_END (holdout stays sealed).
"""
from __future__ import annotations

import numpy as np


def e0_flags(m1: dict, thresh: float = 0.03, revert_sec: int = 900,
             revert_tol: float = 0.005):
    """Return (flag, info): flag[i] True = impossible print.
    info rows for every bar that passed (a) - incl. bars that failed
    (b) so the report can list near-misses (e.g. bogus prints right
    before a data gap, where the revert check lands on Monday)."""
    t = np.asarray(m1["t"]); h = np.asarray(m1["h"])
    l = np.asarray(m1["l"]); c = np.asarray(m1["c"])
    n = len(t)
    flag = np.zeros(n, bool)
    info = []
    if n < 3:
        return flag, info
    # vectorized candidate pass (ref ~ prev close; refined below)
    prev_c = np.concatenate([[np.nan], c[:-1]])
    dev0 = np.maximum(np.abs(h / prev_c - 1), np.abs(l / prev_c - 1))
    cand = list(np.nonzero(dev0 > thresh)[0])
    i = 0
    while i < len(cand):
        j = cand[i]
        # ref = close of last non-flagged bar before j
        k = j - 1
        while k >= 0 and flag[k]:
            k -= 1
        if k < 0:
            i += 1
            continue
        ref = c[k]
        dev = max(abs(h[j] / ref - 1), abs(l[j] / ref - 1))
        if dev > thresh:
            rj = int(np.searchsorted(t, t[j] + revert_sec))
            if rj < n:
                rc = c[rj]
                rev = abs(rc / ref - 1)
                ok = rev <= revert_tol
            else:
                rc = np.nan; rev = np.nan; ok = False
            info.append({"i": j, "t": int(t[j]), "ref": float(ref),
                         "dev": float(dev), "revert_close": float(rc),
                         "rev_dev": float(rev), "flagged": bool(ok),
                         "revert_lag_s": int(t[rj] - t[j]) if rj < n
                         else -1})
            if ok:
                flag[j] = True
                # re-scan the next bars against the same ref: a cluster
                # of bogus bars can hide behind the first bogus close
                extra = []
                for m in range(j + 1, min(j + 120, n)):
                    devm = max(abs(h[m] / ref - 1),
                               abs(l[m] / ref - 1))
                    if devm > thresh:
                        extra.append(m)
                for m in extra:
                    if m not in cand:
                        cand.insert(i + 1, m)
                        i += 1
        i += 1
    return flag, info


def second_stamp(m1: dict):
    """Bars whose timestamp is not minute-aligned (bogus-print marker
    seen in this data: 2020-05-07 12:33:04, the two Sunday bars)."""
    return (np.asarray(m1["t"]) % 60) != 0
