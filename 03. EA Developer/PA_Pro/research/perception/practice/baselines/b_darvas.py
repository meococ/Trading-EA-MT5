"""b_darvas.py — Darvas 4-state range machine (PA-ATLAS baseline C3).

Clean-room implementation from public descriptions (TradingView
"Auto Darvas Boxes" state machine + "Advanced Intraday Darvas Box"
ATR filter).  Fully causal, O(1) per bar:

  STATE 0 define:   over the last N bars, top = max(h)+tol,
                    bot = min(l)-tol; remember the window start.
  STATE 1 validate: the NEXT N bars must stay inside; the first
                    violating bar restarts STATE 0 AT that bar
                    (no overlap, no half boxes).
  STATE 2 active:   box drawn from the STATE-0 window start; dies on
                    the first CLOSE beyond an edge.  A newly confirmed
                    box retires any still-open older box (fresh ink).
  Quality gate:     box height >= q*ABR at confirm.

Params: N=7, tol = max(1.0, 0.25*ABR) (spec tolerance), q=0.4.
"""
import numpy as np


def emit(t, m, o, h, l, c, abr, N=7, q=0.4, tol_pips=1.0,
         tol_abr=0.25):
    n = len(h)
    out = []
    state, s0 = 0, 0          # s0 = bar where STATE0 window started
    top = bot = 0.0
    v0 = 0                    # STATE1 started at bar v0
    active = None             # open box dict or None
    i = 0
    while i < n:
        tol = max(tol_pips, tol_abr * abr[i])
        if state == 0:
            if i - s0 + 1 >= N:
                top = float(np.max(h[s0:i + 1])) + tol
                bot = float(np.min(l[s0:i + 1])) - tol
                state, v0 = 1, i + 1
            i += 1
            continue
        if state == 1:
            if h[i] > top or l[i] < bot:
                state, s0 = 0, i      # restart at the violating bar
            elif i - v0 + 1 >= N:
                if top - bot >= q * abr[i]:
                    if active is not None and active["die"] is None:
                        active["die"] = int(m[i])
                    active = {"type": "BOX", "why": "darvas",
                              "birth": int(m[i]),
                              "birth_drawn": int(m[s0]),
                              "die": None, "score": float(m[i]),
                              "lo": bot, "hi": top,
                              "bs": int(m[s0]), "be": int(m[i])}
                    out.append(active)
                state = 2
            i += 1
            continue
        # STATE 2 — active box: extends until a close beyond an edge
        if c[i] > active["hi"] or c[i] < active["lo"]:
            active["die"] = int(m[i])
            active["be"] = int(m[i])
            active = None
            state, s0 = 0, i
        else:
            active["be"] = int(m[i])
            i += 1
    return out
