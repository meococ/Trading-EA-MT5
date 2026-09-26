"""pa_fill — order / fill / exit engine on the M1 path (the referee's heart).

Frozen semantics reproduced here (source of truth, READ-ONLY):
``03. EA Developer/EA_VolmanPA/research/lab/vpa_econ1_sim.py:53-160`` — the
ECON-1 order model — and ``vpa_random_baseline.py:125-266``.

Order model
-----------
- ``stop``: order price = signal-bar extreme +/- ``buf_pips`` (or an explicit
  ``order_px`` on the entry); valid ``v_bars`` TF bars (legacy V=3 M5 bars);
  optionally cancelled at the session end (``session_cancel``).
- ``limit``: entry must carry ``order_px``; fill when price trades through.
- ``market_next_open``: fill at the open of the first M1 bar after the signal
  bar close (no invalidation, no expiry).
- Gap-aware fills: long ``max(open, order)`` / short ``min(open, order)``.
- Pre-fill invalidation cancel, adverse-first inside an M1 bar (a cancel wins
  over a same-bar fill).
- All-in cost applied ONCE as an adverse fill shift: ``fill = fill_raw +
  side * cost``.
- ``SL = fill - side * S``, ``TP = fill + side * tp_mult * S`` (configurable).
- Resolution on M1 from the fill bar, SL checked FIRST when both levels are
  inside one M1 bar.
- Exits: fixed SL/TP, daily time-flat at server 22:00 (close of that bar),
  weekend flat, server-midnight fallback (close of the previous bar),
  ``DATA_END`` (last close).  Positions never hold over the weekend.

Flats policies
--------------
- ``legacy_flats=True`` reproduces the frozen quirk: ``dow == 4`` of the
  formula ``((t//86400)+4)%7`` (Sunday=0) fires on THURSDAY 20:00 server, and
  there is no weekend veto.
- ``legacy_flats=False`` (default) uses the corrected calendar: real FRIDAY
  20:00 server (Monday=0 weekday), plus a Saturday/Sunday veto/flat.
"""

import numpy as np

__all__ = [
    "BUF_PIPS", "V_BARS", "S_PIPS", "TP_MULT", "DEFAULT_SPEC", "TIER_MULT",
    "resolve_spec", "build_ctx", "compute_next_end", "simulate",
]

BUF_PIPS = 1.0
V_BARS = 3
S_PIPS = 8.0
TP_MULT = 2.0

TIER_MULT = {"gross": 0.0, "x1": 1.0, "x1.5": 1.5, "x2": 2.0}

DEFAULT_SPEC = {
    "order_type": "stop",       # stop | limit | market_next_open
    "S_pips": S_PIPS,
    "tp_mult": TP_MULT,
    "buf_pips": BUF_PIPS,
    "v_bars": V_BARS,
    "invalidation": True,
    "flats": True,
    "legacy_flats": False,      # corrected (real Friday 20:00 server) default
    "session_cancel": True,
    "daily_flat_hour": 22,
    "friday_flat_hour": 20,
    "weekend_veto": True,
}

_STATUSES = ("FILLED", "CANCELLED", "EXPIRED", "VETO_FRIDAY", "VETO_WEEKEND")


def resolve_spec(spec=None):
    """Merge a fill spec over :data:`DEFAULT_SPEC` (extra keys ignored, so a
    family spec with ``family``/``params``/... can be passed straight in)."""
    src = dict(spec or {})
    if "V" in src:
        src.setdefault("v_bars", src["V"])
    out = dict(DEFAULT_SPEC)
    for k in DEFAULT_SPEC:
        if k in src:
            out[k] = src[k]
    if out["order_type"] not in ("stop", "limit", "market_next_open"):
        raise ValueError(f"order_type {out['order_type']!r} not supported")
    return out


def build_ctx(m1, m5, m5_t, starts, pip, next_end=None, first_live_idx=0,
              symbol=None, c_rt_pips=None):
    """Pre-extract the hot-loop lists (one pass), mirroring the frozen
    ``vpa_econ1_sim.build_ctx`` and adding the corrected weekday/session data,
    the warm-up boundary and the symbol's x1 cost."""
    mt = np.asarray(m1["t"], dtype=np.int64)
    day = mt // 86400
    return {
        "n_m1": int(len(mt)),
        "mt": mt.tolist(),
        "mo": np.asarray(m1["o"], dtype=np.float64).tolist(),
        "mh": np.asarray(m1["h"], dtype=np.float64).tolist(),
        "ml": np.asarray(m1["l"], dtype=np.float64).tolist(),
        "mc": np.asarray(m1["c"], dtype=np.float64).tolist(),
        "mday": day.tolist(),
        "mdow": ((day + 4) % 7).tolist(),          # legacy Sunday=0 convention
        "mdow_correct": ((day + 3) % 7).tolist(),  # Monday=0, real weekday
        "msrv": ((mt % 86400) // 3600).tolist(),
        "starts": np.asarray(starts, dtype=np.int64).tolist(),
        "m5h": np.asarray(m5["h"], dtype=np.float64).tolist(),
        "m5l": np.asarray(m5["l"], dtype=np.float64).tolist(),
        "m5_t": np.asarray(m5_t, dtype=np.int64).tolist(),
        "n_m5": int(len(m5_t)),
        "next_end": (np.asarray(next_end, dtype=np.int64).tolist()
                     if next_end is not None else None),
        "pip": float(pip),
        "first_live_idx": int(first_live_idx),
        "symbol": symbol,
        "c_rt_pips": (None if c_rt_pips is None else float(c_rt_pips)),
    }


def compute_next_end(starts, mask, n_m1):
    """M1 index where the session containing each TF bar ends (frozen
    ``vpa_econ1_run.compute_next_end``): for an in-session bar j, the M1 start
    index of the first subsequent out-of-session bar (or ``n_m1``)."""
    n = len(mask)
    next_end = np.full(n, n_m1, dtype=np.int64)
    cur = n_m1
    for j in range(n - 1, -1, -1):
        if mask[j]:
            next_end[j] = cur
        else:
            cur = starts[j]
    return next_end


def _tier_mult(cost_tier):
    if isinstance(cost_tier, str):
        if cost_tier not in TIER_MULT:
            raise ValueError(f"unknown cost tier {cost_tier!r}; known: {sorted(TIER_MULT)}")
        return TIER_MULT[cost_tier]
    return float(cost_tier)


def simulate(spec, ctx, entries, cost_tier):
    """Run every entry through the order/fill/exit engine.

    Returns one dict per entry, ``status`` in {FILLED, CANCELLED, EXPIRED,
    VETO_FRIDAY, VETO_WEEKEND}; FILLED dicts carry ``r`` in R units plus the
    full fill/exit audit trail.
    """
    sp = resolve_spec(spec)
    mult = _tier_mult(cost_tier)
    pip = ctx["pip"]
    c_rt_pips = ctx.get("c_rt_pips")
    if c_rt_pips is None:
        import pa_costs

        sym = ctx.get("symbol")
        if sym not in pa_costs.C_RT_P90:
            raise KeyError(
                f"no c_rt for symbol {sym!r}; set ctx['c_rt_pips'] explicitly")
        c_rt_pips = pa_costs.C_RT_P90[sym]
    c = c_rt_pips * mult * pip
    sl_d = sp["S_pips"] * pip
    tp_d = sp["tp_mult"] * sp["S_pips"] * pip
    order_type = sp["order_type"]
    buf = sp["buf_pips"] * pip
    v_bars = int(sp["v_bars"])
    use_inv = bool(sp["invalidation"])
    flats = bool(sp["flats"])
    legacy = bool(sp["legacy_flats"])
    daily_h = sp["daily_flat_hour"]
    fri_h = sp["friday_flat_hour"]
    weekend_veto = bool(sp["weekend_veto"])

    starts = ctx["starts"]
    n_m5 = ctx["n_m5"]
    n_m1 = ctx["n_m1"]
    mt, mo, mh, ml, mc = ctx["mt"], ctx["mo"], ctx["mh"], ctx["ml"], ctx["mc"]
    mday, msrv = ctx["mday"], ctx["msrv"]
    mdow, mdow_c = ctx["mdow"], ctx["mdow_correct"]
    m5h, m5l, m5_t = ctx["m5h"], ctx["m5l"], ctx["m5_t"]
    next_end = ctx.get("next_end")
    first_live = int(ctx.get("first_live_idx") or 0)
    symbol = ctx.get("symbol")

    out = []
    for e in entries:
        sig = int(e["sig"])
        d = int(e["side"])
        if d not in (-1, 1):
            raise ValueError(f"entry side must be +1/-1, got {d!r}")
        tag = e.get("tag")
        if sig < first_live:
            raise ValueError(
                f"entry {tag!r} signal bar {sig} is in the warm-up zone "
                f"(first live bar = {first_live}); warm-up bars must never "
                "produce signals or outcomes")
        if sig + 1 >= n_m5:
            continue

        # --- weekend / Friday close veto (no new order) -------------------
        if flats:
            sig_t = m5_t[sig]
            srv_h = (sig_t % 86400) // 3600
            legacy_dow_sig = ((sig_t // 86400) + 4) % 7
            correct_dow_sig = ((sig_t // 86400) + 3) % 7
            if legacy:
                if legacy_dow_sig == 4 and srv_h >= fri_h:
                    out.append({"sig": sig, "side": d, "tag": tag, "symbol": symbol,
                                "status": "VETO_FRIDAY"})
                    continue
            else:
                if correct_dow_sig >= 5 and weekend_veto:
                    out.append({"sig": sig, "side": d, "tag": tag, "symbol": symbol,
                                "status": "VETO_WEEKEND"})
                    continue
                if correct_dow_sig == 4 and srv_h >= fri_h:
                    out.append({"sig": sig, "side": d, "tag": tag, "symbol": symbol,
                                "status": "VETO_FRIDAY"})
                    continue

        # --- order price --------------------------------------------------
        if order_type == "market_next_open":
            i0 = starts[sig + 1]
            fi = i0
            fill_raw = mo[i0]
            stop = fill_raw
        else:
            if "order_px" in e and e["order_px"] is not None:
                stop = float(e["order_px"])
            elif order_type == "stop":
                stop = (m5h[sig] + buf) if d > 0 else (m5l[sig] - buf)
            else:  # limit
                if e.get("order_px") is None:
                    raise ValueError("limit orders need an explicit 'order_px'")
                stop = float(e["order_px"])
            inv = e.get("inv") if use_inv else None
            i0 = starts[sig + 1]
            j = sig + 1 + v_bars
            i1 = starts[j] if j < n_m5 else n_m1
            if next_end is not None and sp["session_cancel"] and next_end[sig] < i1:
                i1 = next_end[sig]
            fi = -1
            fill_raw = 0.0
            cancelled = False
            for i in range(i0, i1):
                if inv is not None:
                    if (d > 0 and ml[i] <= inv) or (d < 0 and mh[i] >= inv):
                        cancelled = True
                        break
                if order_type == "stop":
                    if d > 0 and mh[i] >= stop:
                        fill_raw = mo[i] if mo[i] > stop else stop
                        fi = i
                        break
                    if d < 0 and ml[i] <= stop:
                        fill_raw = mo[i] if mo[i] < stop else stop
                        fi = i
                        break
                else:  # limit
                    if d > 0 and ml[i] <= stop:
                        fill_raw = mo[i] if mo[i] < stop else stop
                        fi = i
                        break
                    if d < 0 and mh[i] >= stop:
                        fill_raw = mo[i] if mo[i] > stop else stop
                        fi = i
                        break
            if cancelled:
                out.append({"sig": sig, "side": d, "tag": tag, "symbol": symbol,
                            "status": "CANCELLED"})
                continue
            if fi < 0:
                out.append({"sig": sig, "side": d, "tag": tag, "symbol": symbol,
                            "status": "EXPIRED"})
                continue

        # --- fill + bracket ----------------------------------------------
        gap = d * (fill_raw - stop)
        fill = fill_raw + d * c
        SL = fill - d * sl_d
        TP = fill + d * tp_d
        fday = mday[fi]
        exit_i = -1
        exit_px = fill
        reason = ""
        for i in range(fi, n_m1):
            if d > 0:
                if ml[i] <= SL:
                    exit_i, exit_px, reason = i, SL, "SL"
                    break
                if mh[i] >= TP:
                    exit_i, exit_px, reason = i, TP, "TP"
                    break
            else:
                if mh[i] >= SL:
                    exit_i, exit_px, reason = i, SL, "SL"
                    break
                if ml[i] <= TP:
                    exit_i, exit_px, reason = i, TP, "TP"
                    break
            if flats:
                if daily_h is not None and msrv[i] >= daily_h:
                    exit_i, exit_px, reason = i, mc[i], "DAILY"
                    break
                if legacy:
                    if mdow[i] == 4 and msrv[i] >= fri_h:
                        exit_i, exit_px, reason = i, mc[i], "FRIDAY"
                        break
                else:
                    if mdow_c[i] == 4 and msrv[i] >= fri_h:
                        exit_i, exit_px, reason = i, mc[i], "FRIDAY"
                        break
                    if weekend_veto and mdow_c[i] >= 5:
                        exit_i, exit_px, reason = i, mc[i], "WEEKEND"
                        break
            if mday[i] != fday:
                exit_i, exit_px, reason = i - 1, mc[i - 1], "MIDNIGHT"
                break
        if exit_i < 0:
            exit_i, exit_px, reason = n_m1 - 1, mc[n_m1 - 1], "DATA_END"
        if reason == "SL":
            r = -1.0
        elif reason == "TP":
            r = 2.0
        else:
            r = d * (exit_px - fill) / sl_d
        atr = e.get("atr")
        rec = {
            "sig": sig, "side": d, "tag": tag, "symbol": symbol,
            "status": "FILLED", "order_type": order_type,
            "fill_idx": fi, "fill": fill, "fill_raw": fill_raw, "stop": stop,
            "sl": SL, "tp": TP, "exit_idx": exit_i, "exit_px": exit_px,
            "reason": reason, "r": r, "bars_m1": exit_i - fi + 1,
            "gap_atr": (gap / atr) if (atr and atr > 0) else None,
            "cost_pips": (c / pip) if pip else None,
            "cost_tier": cost_tier,
            "exit_t": mt[exit_i], "fill_t": mt[fi],
            "sig_t": m5_t[sig],
        }
        out.append(rec)
    return out
