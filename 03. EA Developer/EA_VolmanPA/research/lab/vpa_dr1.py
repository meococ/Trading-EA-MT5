"""VPA-DR1 detector — signal-bar stop-entry revision.

Implements `research/VPA-DR1_FROZEN_PREREG.md` (D1-D6) on top of the vpa_core
barrier/indicator engine:

  - decision at the close of the SIGNAL bar (first bar closing at/through the
    barrier in the trade direction, within the anti-chase margin);
  - entry = stop order 1 pip beyond the signal bar's extreme, valid V=3 bars,
    cancelled on invalidation;
  - gates in the prereg order: warmup, session, direction, trend, buildup,
    chop (exempt if buildup passes), room, adverse magnet, anti-chase, cost;
  - Combi is only an entry-timing classification inside a valid PB context.

SINGLE GATE CODE PATH: `_dr1_gates()` computes every gate without
short-circuiting and `verdict_from_gates()` derives (executable, first_fail).
Both the detector (`_dr1_candidate`) and the trace tool (`vpa_trace.py`) call
these, so there is exactly one implementation of each gate.

Causal: only bars <= t are read; no wall clock; deterministic.
"""

import math

from vpa_core import Detector, _median

# DR3: only these are hard gates (F2); the rest are logged features (F3)
DR3_HARD_GATES = ("warmup", "session", "direction", "trend", "integrity", "cost")

DR1_DEFAULTS = {
    # engine (DR1 overrides)
    "barrier_expiry": 20,
    # sessions (UTC minutes)
    "eu": (420, 660),
    "us": (810, 990),
    # trend gate
    "theta_slope": 0.10,
    "frac_side_min": 0.6,
    "frac_lookback": 10,
    "slope_lookback": 6,
    # signal bar
    "signal_atr": 0.05,
    "signal_max_atr": 0.25,
    "doji_body_frac": 0.10,
    # buildup (4-condition AND)
    "buildup_max": 10,
    "buildup_min": 3,
    "band_lo_atr": -0.10,
    "band_hi_atr": 0.50,
    "min_band_closes": 2,
    "buildup_touch_atr": 0.10,
    "min_touches": 1,
    "overlap_min": 0.45,
    "contraction_max": 0.85,
    # chop (narrowed)
    "chop_lookback": 4,
    "chop_overlap_min": 0.65,
    "chop_prog_max": 1.0 / 3.0,
    "chop_body_max": 0.35,
    "chop_long_atr": 1.5,
    # room / magnets
    "room_r_min": 2.0,
    "adverse_pivot_r": 0.5,
    "adverse_skip_frac": 0.10,   # ignore magnets within 0.10*S of the entry
    "round_grid_pips": 50.0,     # book tr.43: 00/50 on M5
    # anti-chase
    "anti_entry_b_atr": 0.35,
    "anti_signal_range_atr": 1.5,
    "anti_ema_atr": 1.5,
    # squeeze feature
    "squeeze_ema_atr": 0.6,
    "squeeze_min_bars": 2,
    # combi
    "combi_body_atr": 0.35,
    "combi_clv": 0.50,
    "combi_inside_ratio": 0.75,
    "warmup_bars": 50,
    # trace / diagnostics
    "collect_gates": False,
    "trace_barriers": False,
    # DR2 experiment knobs (defaults = DR1 behavior)
    "room_significant_only": False,
    "room_include_pdh": False,
    "buildup_min_conditions": 4,
    "pivot_sig_lag": 5,
    "signal_prev_bar": False,
    # DR3 (F2/F3): hard-gate subset + integrity + feature options
    "hard_gates": None,          # None = DR1 (all gates hard)
    "integrity_eps_atr": 0.10,
    "room_zone_touch": False,    # ignore obstacles inside the barrier's own zone
    "room_zone_r": 0.0,          # ... and within this many R beyond the entry
    "chop_in_buildup": False,    # measure chop over the buildup window
    "buildup_variants": False,   # also log the 2-of-4 and tight variants
}

DR3_CFG = {
    "signal_atr": 0.50,
    "eu": (300, 660), "us": (690, 1050),
    "signal_prev_bar": True,
    "hard_gates": DR3_HARD_GATES,
    "integrity_eps_atr": 0.10,
    "room_significant_only": True,
    "room_include_pdh": True,
    "room_zone_touch": True,
    "room_zone_r": 0.5,
    "chop_in_buildup": True,
    "buildup_variants": True,
}

# ordered first-fail evaluation; chop precedes buildup so that a failed buildup
# inside a chop still reports skip_chop (same as the original implementation)
GATE_ORDER = [
    ("warmup", "skip_warmup"),
    ("session", "skip_session"),
    ("direction", "skip_direction"),
    ("trend", "skip_trend"),
    ("integrity", "skip_integrity"),
    ("chop", "skip_chop"),
    ("buildup", "skip_no_buildup"),
    ("room", "skip_room"),
    ("adverse", "skip_adverse_magnet"),
    ("anti_chase", "skip_anti_chase"),
    ("cost", "skip_cost"),
]


def verdict_from_gates(gates, hard=None):
    """(executable, first_fail_reason) from a full gate dict. Single source of
    truth for the detector verdict and the trace. `hard` = the hard-gate subset
    (None = all gates, the DR1 behavior). NB: gate values may be numpy bools,
    so compare by truthiness, never by identity."""
    for key, reason in GATE_ORDER:
        if hard is not None and key not in hard:
            continue
        gp = gates.get(key, {}).get("pass")
        if gp is None:
            continue
        if not bool(gp):
            return False, reason
    return True, None


def full_fail_set(gates):
    """All gates whose pass is False (None = not evaluable is ignored)."""
    out = []
    for k, _ in GATE_ORDER:
        gp = gates.get(k, {}).get("pass")
        if gp is not None and not bool(gp):
            out.append(k)
    return out


class Dr1Detector(Detector):
    def __init__(self, bars, cfg=None):
        merged = dict(DR1_DEFAULTS)
        if cfg:
            merged.update(cfg)
        super().__init__(bars, cfg=merged)
        self.pivots = []          # (idx, price, kind) confirmed pivots
        self.pivots_sig = []      # significant pivots (extremum over +-lag bars)
        self.cur_day = None
        self.cur_day_high = None
        self.cur_day_low = None
        self.pdh = None
        self.pdl = None
        self.barriers_locked = 0
        self.lock_log = []        # (lock_idx, side, level, exp_idx, touches) trace mode
        self.event_log = []       # (t, "missed"|"exec", side, level, lock_idx) trace mode
        if self.cfg.get("round_grid_price"):
            self.round_grid = float(self.cfg["round_grid_price"])
        else:
            self.round_grid = self.cfg["round_grid_pips"] * bars["pip"]

    # ---------------- engine hooks ----------------
    def _try_lock(self, i, side):
        n0 = len(self.active)
        super()._try_lock(i, side)
        if len(self.active) > n0:
            self.barriers_locked += 1
            self._cnt("barrier_locked")
            if self.cfg.get("trace_barriers"):
                b = self.active[-1]
                self.lock_log.append((i, b["side"], b["level"], b["exp_idx"], tuple(b["touches"])))

    def _confirm_pivots(self, t):
        cfg = self.cfg
        L = cfg["pivot_lag"]
        i = t - L
        if i >= L:
            h, l = self.b["h"], self.b["l"]
            if h[i] > max(h[i - L:i]) and h[i] >= max(h[i + 1:i + L + 1]):
                self.pivots.append((i, h[i], +1))
            if l[i] < min(l[i - L:i]) and l[i] <= min(l[i + 1:i + L + 1]):
                self.pivots.append((i, l[i], -1))
            if len(self.pivots) > 400:
                self.pivots = self.pivots[-400:]
            # significant pivots: extremum over a wider window (DR2 room option).
            # Tested at t = j + S so the full right window is known (causal);
            # each index j is tested exactly once, S bars after j.
            S = cfg["pivot_sig_lag"]
            j = t - S
            if j >= S and j + S <= t:
                if h[j] > max(h[j - S:j]) and h[j] >= max(h[j + 1:j + S + 1]):
                    self.pivots_sig.append((j, h[j], +1))
                if l[j] < min(l[j - S:j]) and l[j] <= min(l[j + 1:j + S + 1]):
                    self.pivots_sig.append((j, l[j], -1))
                if len(self.pivots_sig) > 400:
                    self.pivots_sig = self.pivots_sig[-400:]
        super()._confirm_pivots(t)

    def _update_bar(self, t):
        super()._update_bar(t)
        h, l = self.b["h"][t], self.b["l"][t]
        day = int(self.b["t"][t]) // 86400
        if self.cur_day is None or day != self.cur_day:
            if self.cur_day_high is not None:
                self.pdh = self.cur_day_high
                self.pdl = self.cur_day_low
            self.cur_day = day
            self.cur_day_high = h
            self.cur_day_low = l
        else:
            if h > self.cur_day_high:
                self.cur_day_high = h
            if l < self.cur_day_low:
                self.cur_day_low = l

    def _barrier_update(self, t):
        # expiry only; consumption is handled by _dr1_eval
        cfg = self.cfg
        if self.atr[t] != self.atr[t] or self.atr[t] <= 0:
            return
        keep = []
        for bar in self.active:
            if t > bar["exp_idx"]:
                self.tombstones.append((bar["side"], bar["level"], bar["lock_idx"], bar["exp_idx"], None))
                self._cnt("barrier_expired")
                continue
            keep.append(bar)
        self.active = keep
        self.tombstones = [x for x in self.tombstones if t - (x[3] or x[2]) <= cfg["tombstone_keep"]]

    def run(self, max_bars=None):
        n = self.n if max_bars is None else min(self.n, max_bars)
        for t in range(n):
            self._update_bar(t)
            if t > 14:
                self._confirm_pivots(t)
                self._barrier_update(t)
            self._dr1_eval(t)
        return self.records, self.counters

    # ---------------- signal-bar evaluation ----------------
    def _session_dr1(self, t):
        m = self.b["utc_min"][t]
        lo, hi = self.cfg["eu"]
        if lo <= m < hi:
            return "eu"
        lo, hi = self.cfg["us"]
        if lo <= m < hi:
            return "us"
        return None

    def _lunch_feature(self, t):
        """F4: book dead zones (tr. 227/273) as a logged feature only.
        EU lunch 12:00-14:00 CET = 11:00-13:00 UTC; NY 18:00-20:00 CET =
        17:00-19:00 UTC (CET = UTC+1)."""
        m = int(self.b["utc_min"][t])
        return (660 <= m < 780) or (1020 <= m < 1140)

    def _dr1_eval(self, t):
        cfg = self.cfg
        if t < 1:
            return
        A = self.atr[t]
        if A != A or A <= 0:
            return
        c = self.b["c"]
        missed = []
        consumed_exec = []
        consumed = []
        for bar in list(self.active):
            d = bar["side"]
            B = bar["level"]
            dist = d * (c[t] - B)
            if dist < -cfg["signal_atr"] * A:
                continue
            if dist > cfg["signal_max_atr"] * A:
                # breakout bar. DR2 option: the signal bar is the last bar
                # that touched the barrier before this bar (book tr. 88/95:
                # stop order 1 pip beyond the signal bar's extreme; the
                # breakout bar takes it out).
                if cfg.get("signal_prev_bar") and t >= 1:
                    tch = [i for i in bar["touches"] if bar["lock_idx"] <= i < t]
                    if tch:
                        self._cnt("signal_eval")
                        if self._dr1_candidate(t, bar, sig=tch[-1]) is not None:
                            consumed.append(bar)
                            consumed_exec.append((bar["side"], bar["level"], bar["lock_idx"]))
                            continue
                # the barrier was taken out by a long bar before any valid
                # signal bar: missed break (anti-chase), consume it.
                consumed.append(bar)
                missed.append((bar["side"], bar["level"], bar["lock_idx"]))
                self._cnt("skip_missed_break")
                continue
            self._cnt("signal_eval")
            if self._dr1_candidate(t, bar) is not None:
                consumed.append(bar)   # executable consumes the barrier
                consumed_exec.append((bar["side"], bar["level"], bar["lock_idx"]))
        if consumed:
            ids = {id(b) for b in consumed}
            self.active = [b for b in self.active if id(b) not in ids]
            for b in consumed:
                self.tombstones.append((b["side"], b["level"], b["lock_idx"], b["exp_idx"], t))
        if cfg.get("trace_barriers"):
            for (side, level, lock_idx) in missed:
                self.event_log.append((t, "missed", side, level, lock_idx))
            for (side, level, lock_idx) in consumed_exec:
                self.event_log.append((t, "exec", side, level, lock_idx))

    # ---------------- gates (single code path) ----------------
    def _dr1_gates(self, t, bar, trig=None):
        """Evaluate ALL gates for the signal-bar candidate at t. No short-circuit.
        `trig` = the trigger/entry bar (defaults to t); the session gate is
        measured there (prereg DR3 §2)."""
        cfg = self.cfg
        d = bar["side"]
        B = bar["level"]
        pip = self.b["pip"]
        A = self.atr[t]
        o, h, l, c = self.b["o"], self.b["h"], self.b["l"], self.b["c"]
        session = self._session_dr1(trig if trig is not None else t)
        g = {}
        g["warmup"] = {"pass": t >= cfg["warmup_bars"], "value": {"bar_idx": t}}
        g["session"] = {"pass": session is not None, "value": {"session": session}}
        rng = h[t] - l[t]
        body = c[t] - o[t]
        doji = rng > 0 and abs(body) <= cfg["doji_body_frac"] * rng
        dir_ok = (d > 0 and (body > 0 or doji)) or (d < 0 and (body < 0 or doji))
        g["direction"] = {"pass": bool(dir_ok),
                          "value": {"body_frac": (body / rng) if rng > 0 else 0.0, "doji": bool(doji)}}
        lb = cfg["slope_lookback"]
        slope = d * (self.ema[t] - self.ema[t - lb]) / A
        fb = cfg["frac_lookback"]
        frac = sum(1 for i in range(t - fb + 1, t + 1) if d * (c[i] - self.ema[i]) >= 0) / fb
        g["trend"] = {"pass": (slope >= cfg["theta_slope"] and frac >= cfg["frac_side_min"]),
                      "value": {"slope": round(slope, 4), "frac": round(frac, 3)}}
        # barrier integrity (F2c, tr.39-41): a level crossed by closes is not a
        # barrier. Between the first touch and the signal bar no close may go
        # beyond B by more than eps = integrity_eps_atr * ATR.
        eps = cfg["integrity_eps_atr"] * A
        tch = [i for i in (bar.get("touches") or []) if i <= t]
        first_touch = min(tch) if tch else None
        int_ok = True
        worst = None
        if first_touch is not None:
            for i in range(first_touch, t + 1):
                beyond = d * (c[i] - B)
                if beyond > eps:
                    int_ok = False
                    worst = {"bar": i, "beyond_atr": round(beyond / A, 3)}
                    break
        g["integrity"] = {"pass": bool(int_ok),
                          "value": {"first_touch": first_touch, "eps_atr": cfg["integrity_eps_atr"],
                                    "worst": worst, "n_checked": (t - first_touch + 1) if first_touch is not None else 0}}
        bu = self._buildup_dr1(t, d, B, A)
        g["buildup"] = {"pass": bu is not None, "value": bu}
        chop = self._chop_dr1(t)
        chop_win = None
        if cfg.get("chop_in_buildup") and bu is not None:
            chop_win = self._chop_window(bu["start"], t)
        chop_pass = (not chop) or (bu is not None)
        g["chop"] = {"pass": bool(chop_pass),
                     "value": {"chop": bool(chop), "exempt": bool(chop and bu is not None),
                               "chop_window": (bool(chop_win) if chop_win is not None else None),
                               "buildup_start": (bu["start"] if bu is not None else None)}}
        if bu is not None:
            entry = (h[t] + cfg["entry_buffer_pips"] * pip) if d > 0 else (l[t] - cfg["entry_buffer_pips"] * pip)
            inv = (min(l[bu["start"]:t]) - 0.10 * A) if d > 0 else (max(h[bu["start"]:t]) + 0.10 * A)
            S = cfg["stop_pips"] * pip
            room, obstacle = self._room_dr1_detail(t, d, entry, A, bar=bar)
            g["room"] = {"pass": room >= cfg["room_r_min"] * S,
                         "value": {"room_r": round(room / S, 3) if room != float("inf") else float("inf"),
                                   "obstacle": obstacle}}
            adv, adv_info = self._adverse_dr1_detail(t, d, entry, S, A, bu["start"])
            g["adverse"] = {"pass": not adv, "value": adv_info}
            entry_b = d * (entry - B)
            ema_dist = abs(entry - self.ema[t])
            g["anti_chase"] = {"pass": (entry_b <= cfg["entry_buffer_pips"] * pip + cfg["anti_entry_b_atr"] * A
                                        and rng <= cfg["anti_signal_range_atr"] * A
                                        and ema_dist <= cfg["anti_ema_atr"] * A),
                               "value": {"entry_b_atr": round(entry_b / A, 4),
                                         "range_atr": round(rng / A, 4),
                                         "ema_dist_atr": round(ema_dist / A, 4)}}
            rho = cfg["cost_pips"] / cfg["stop_pips"]
            g["cost"] = {"pass": rho <= cfg["rho_max"], "value": {"rho": rho}}
            g["_derived"] = {"entry": entry, "invalidation": inv, "atr": A}
        else:
            for k in ("room", "adverse", "anti_chase", "cost"):
                g[k] = {"pass": None, "value": None}
            g["_derived"] = {"entry": None, "invalidation": None, "atr": A}
        return g

    def _dr1_candidate(self, t, bar, sig=None):
        """t = evaluation/entry bar (session + trigger), sig = signal bar
        (entry stop / gate bar). sig=None -> DR1 behavior (sig == t)."""
        cfg = self.cfg
        sig = t if sig is None else sig
        d = bar["side"]
        B = bar["level"]
        c = self.b["c"]
        h, l = self.b["h"], self.b["l"]
        session = self._session_dr1(t)
        gates = self._dr1_gates(sig, bar, trig=t)
        derived = gates["_derived"]
        A = derived["atr"]
        rec = {
            "time": int(self.b["t"][t]), "bar_idx": sig, "trigger_idx": t, "side": d, "level": B,
            "lock_idx": bar["lock_idx"], "touches": list(bar["touches"]),
            "session": session, "atr": A, "ema": self.ema[sig], "bias": self.bias[sig],
            "setup": "pattern_break", "executable": False, "skip_reason": None,
            "n": (gates["buildup"]["value"] or {}).get("n", 0),
            "contraction": (gates["buildup"]["value"] or {}).get("contraction"),
            "overlap": (gates["buildup"]["value"] or {}).get("overlap"),
            "band_closes": (gates["buildup"]["value"] or {}).get("band_closes"),
            "touches_in_buildup": (gates["buildup"]["value"] or {}).get("touches"),
            "squeeze": (gates["buildup"]["value"] or {}).get("squeeze", False),
            "trend_slope": gates["trend"]["value"]["slope"],
            "frac_side": gates["trend"]["value"]["frac"],
            "signal_close": c[sig], "signal_body_frac": gates["direction"]["value"]["body_frac"],
            "entry_level": derived["entry"], "invalidation": derived["invalidation"],
            "room_pips": None, "room_r": None, "adverse_magnet": False,
            "buildup_start": (gates["buildup"]["value"] or {}).get("start"),
            "rho": (gates["cost"]["value"] or {}).get("rho"),
            "pressure": bool(self.pressure[sig]),
            "bars_since_pressure": int(sig - self.last_pressure_end),
            "lunch": bool(self._lunch_feature(t)),
            "hard_gates": (list(cfg["hard_gates"]) if cfg.get("hard_gates") else None),
            "active_others": [(b["side"], b["level"]) for b in self.active
                              if not (b["side"] == bar["side"] and b["lock_idx"] == bar["lock_idx"])],
        }
        if gates["room"]["value"] is not None:
            rr = gates["room"]["value"]["room_r"]
            rec["room_r"] = rr
            rec["room_pips"] = None if rr == float("inf") else round(rr * cfg["stop_pips"], 3)
        if gates["adverse"]["pass"] is not None and not bool(gates["adverse"]["pass"]):
            rec["adverse_magnet"] = True
        if cfg.get("collect_gates"):
            rec["gates"] = gates
        ok, reason = verdict_from_gates(gates, cfg.get("hard_gates"))
        pre_fail = reason in ("skip_warmup", "skip_session", "skip_direction", "skip_trend")
        if gates["chop"]["value"]["exempt"] and not pre_fail:
            self._cnt("chop_exempt_buildup")
        if not ok:
            return self._reject(rec, reason)
        combi = self._combi_dr1(sig, d, B)
        if combi:
            rec["setup"] = "combi"
            rec["combi"] = combi
        rec["executable"] = True
        self._cnt("executable_" + rec["setup"])
        self.records.append(rec)
        return rec

    # ---------------- gate helpers ----------------
    def _buildup_dr1(self, t, d, B, A):
        cfg = self.cfg
        min_conds = cfg.get("buildup_min_conditions", 4)
        variants = bool(cfg.get("buildup_variants"))
        h, l, c = self.b["h"], self.b["l"], self.b["c"]
        prim = v2 = vt = None
        for n in range(cfg["buildup_max"], cfg["buildup_min"] - 1, -1):
            s = t - n
            if s < 1:
                continue
            band_closes = sum(1 for i in range(s, t)
                              if cfg["band_lo_atr"] * A <= d * (B - c[i]) <= cfg["band_hi_atr"] * A)
            touches = sum(1 for i in range(s, t)
                          if abs((h[i] if d > 0 else l[i]) - B) <= cfg["buildup_touch_atr"] * A)
            tr_w = self.tr[s:t]
            tr_p = self.tr[max(0, s - 12):s]
            if not tr_w or not tr_p:
                continue
            contraction = _median(tr_w) / _median(tr_p) if _median(tr_p) > 0 else 9.9
            overlaps = []
            for i in range(s + 1, t):
                den = max(min(h[i] - l[i], h[i - 1] - l[i - 1]), 1e-12)
                overlaps.append(max(0.0, min(h[i], h[i - 1]) - max(l[i], l[i - 1])) / den)
            overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
            conds = [band_closes >= cfg["min_band_closes"],
                     touches >= cfg["min_touches"],
                     overlap >= cfg["overlap_min"],
                     contraction <= cfg["contraction_max"]]
            m = {"n": n, "start": s, "contraction": contraction, "overlap": overlap,
                 "band_closes": band_closes, "touches": touches,
                 "conditions_passed": int(sum(bool(x) for x in conds)),
                 "cond_flags": [bool(x) for x in conds]}
            if prim is None and m["conditions_passed"] >= min_conds:
                prim = m
            if v2 is None and m["conditions_passed"] >= 2:
                v2 = m
            if vt is None and band_closes >= 3 and touches >= 2 and contraction <= cfg["contraction_max"]:
                vt = m
            if prim is not None and (not variants or (v2 is not None and vt is not None)):
                break
        if prim is None:
            return None
        squeeze = (abs(self.ema[t] - B) <= cfg["squeeze_ema_atr"] * A
                   and sum(1 for i in range(prim["start"], t) if l[i] <= self.ema[i] <= h[i]) >= cfg["squeeze_min_bars"])
        out = dict(prim)
        out["squeeze"] = bool(squeeze)
        if variants:
            out["v2of4"] = v2
            out["vtight"] = vt
        return out

    def _chop_metrics(self, lo, hi):
        """Chop over bars [lo, hi): full-overlap / falling-lows / doji-or-long."""
        cfg = self.cfg
        o, h, l, c = self.b["o"], self.b["h"], self.b["l"], self.b["c"]
        if hi - lo < 2:
            return False
        overlaps = []
        doji = False
        long_bar = False
        for i in range(lo, hi):
            den = max(min(h[i] - l[i], h[i - 1] - l[i - 1]), 1e-12)
            overlaps.append(max(0.0, min(h[i], h[i - 1]) - max(l[i], l[i - 1])) / den)
            rng = h[i] - l[i]
            if rng > 0 and abs(c[i] - o[i]) / rng <= cfg["chop_body_max"]:
                doji = True
            if rng > cfg["chop_long_atr"] * self.atr[i]:
                long_bar = True
        overlap = sum(overlaps) / len(overlaps)
        seq = [l[i] for i in range(lo, hi)]
        prog = sum(1 for i in range(1, len(seq)) if (seq[i] - seq[i - 1]) >= 0) / (len(seq) - 1)
        return (overlap >= cfg["chop_overlap_min"] and prog <= cfg["chop_prog_max"]
                and (doji or long_bar))

    def _chop_dr1(self, t):
        k = self.cfg["chop_lookback"]
        if t < k + 1:
            return False
        return self._chop_metrics(t - k, t)   # k bars BEFORE the signal bar

    def _chop_window(self, lo, t):
        """F3: chop measured only inside the buildup window [lo, t)."""
        return self._chop_metrics(lo, t)

    def _room_zone(self, t, d, entry, A, bar):
        """F3: the barrier zone = [B, touch-extreme + eps] plus the entry +
        max(eps, room_zone_r * R) band. Obstacles inside it are the barrier
        itself. Returns the price beyond which obstacles count (None = no zone)."""
        cfg = self.cfg
        if not cfg.get("room_zone_touch") and not cfg.get("room_zone_r"):
            return None
        B = bar["level"]
        eps = cfg["integrity_eps_atr"] * A
        S = cfg["stop_pips"] * self.b["pip"]
        tch = [i for i in (bar.get("touches") or []) if i <= t]
        if d > 0:
            extreme = max(self.b["h"][i] for i in tch) if tch else B
            return max(extreme + eps, entry + max(eps, cfg["room_zone_r"] * S))
        extreme = min(self.b["l"][i] for i in tch) if tch else B
        return min(extreme - eps, entry - max(eps, cfg["room_zone_r"] * S))

    def _room_dr1_detail(self, t, d, entry, A, bar=None):
        """Nearest obstacle ahead of the entry: (distance, info). Info = dict
        {price, type} or None when room is infinite."""
        cfg = self.cfg
        best = float("inf")
        info = None
        zone = self._room_zone(t, d, entry, A, bar) if (bar is not None and
                                                        (cfg.get("room_zone_touch") or cfg.get("room_zone_r"))) else None
        pivots = self.pivots_sig if cfg.get("room_significant_only") else self.pivots
        for (i, px, kind) in pivots:
            if i >= t or kind != d:
                continue
            if (d > 0 and px > entry + 0.05 * A) or (d < 0 and px < entry - 0.05 * A):
                if zone is not None and ((d > 0 and px <= zone) or (d < 0 and px >= zone)):
                    continue
                dist = abs(px - entry)
                if dist < best:
                    best = dist
                    info = {"price": px, "type": "pivot_sig" if cfg.get("room_significant_only") else "pivot"}
        for b in self.active:
            if b["side"] != d:
                continue
            if (d > 0 and b["level"] > entry) or (d < 0 and b["level"] < entry):
                if zone is not None and ((d > 0 and b["level"] <= zone) or (d < 0 and b["level"] >= zone)):
                    continue
                dist = abs(b["level"] - entry)
                if dist < best:
                    best = dist
                    info = {"price": b["level"], "type": "barrier", "lock_idx": b["lock_idx"],
                            "touches": len(b["touches"])}
        if cfg.get("room_include_pdh"):
            lvl = self.pdh if d > 0 else self.pdl
            if lvl is not None and ((d > 0 and lvl > entry + 0.05 * A) or (d < 0 and lvl < entry - 0.05 * A)):
                if zone is None or (d > 0 and lvl > zone) or (d < 0 and lvl < zone):
                    dist = abs(lvl - entry)
                    if dist < best:
                        best = dist
                        info = {"price": lvl, "type": "pdh" if d > 0 else "pdl"}
        g = self.round_grid
        if g and g > 0:
            nxt = math.floor(entry / g + 1.0) * g if d > 0 else math.ceil(entry / g - 1.0) * g
            if (d > 0 and nxt > entry) or (d < 0 and nxt < entry):
                if zone is None or (d > 0 and nxt > zone) or (d < 0 and nxt < zone):
                    dist = abs(nxt - entry)
                    if dist < best:
                        best = dist
                        info = {"price": nxt, "type": "round_grid"}
        if info is not None:
            info["zone_price"] = zone
        return best, info

    def _room_dr1(self, t, d, entry, A):
        return self._room_dr1_detail(t, d, entry, A)[0]
    def _adverse_dr1_detail(self, t, d, entry, S, A, buildup_start):
        """(bool, info). Info = {price, type} of the first adverse magnet found."""
        cfg = self.cfg
        skip = cfg["adverse_skip_frac"] * S
        for (i, px, kind) in self.pivots:
            if i >= t or i >= buildup_start:
                continue
            if d > 0 and kind == -1 and (entry - cfg["adverse_pivot_r"] * S) < px < (entry - skip):
                return True, {"price": px, "type": "pivot_low"}
            if d < 0 and kind == +1 and (entry + skip) < px < (entry + cfg["adverse_pivot_r"] * S):
                return True, {"price": px, "type": "pivot_high"}
        g = self.round_grid
        if g and g > 0:
            if d > 0:
                lvl = math.floor(entry / g) * g
                if (entry - S) < lvl < (entry - skip):
                    return True, {"price": lvl, "type": "round_grid"}
            else:
                lvl = math.ceil(entry / g) * g
                if (entry + skip) < lvl < (entry + S):
                    return True, {"price": lvl, "type": "round_grid"}
        return False, None

    def _adverse_dr1(self, t, d, entry, S, A, buildup_start):
        return self._adverse_dr1_detail(t, d, entry, S, A, buildup_start)[0]

    def _combi_dr1(self, t, d, B):
        cfg = self.cfg
        if t < 2:
            return None
        p = t - 1                        # strong bar; t = inside bar = signal bar
        o, h, l, c = self.b["o"], self.b["h"], self.b["l"], self.b["c"]
        A = self.atr[p]
        if A != A or A <= 0 or (h[p] - l[p]) <= 0:
            return None
        if d * (c[p] - o[p]) < cfg["combi_body_atr"] * A:
            return None
        if d * self.clv[p] < cfg["combi_clv"]:
            return None
        if h[t] > h[p] + 0.5 * self.b["tick"] or l[t] < l[p] - 0.5 * self.b["tick"]:
            return None
        if (h[t] - l[t]) / (h[p] - l[p]) > cfg["combi_inside_ratio"]:
            return None
        return {"strong_idx": p, "inside_idx": t}


def run_dr1(bars, cfg=None, max_bars=None):
    return Dr1Detector(bars, cfg).run(max_bars=max_bars)
