"""lines_lab — L3 anchor-first causal PATTERN_LINE proposer.

Sandbox engine with the same interface eval expects:
    e = LineLabEngine(); e.cand_log = []
    e.update(t_epoch, o, h, l, c, cet_min=...)   # absolute prices
    e.objects -> engine-shaped objects (t_left/t_right/geometry/events)

Design (from L2 anatomy, LINE_ANATOMY.md):
- anchor universe: confirmed theta1 pivots (swings.py DCStream,
  k1*ABR wick-confirm) UNION named-bar local extremes (+/-3 bars),
  same defended side, within span lookback.
- trigger: on each newly confirmed pivot, candidate pairs =
  (older anchor, new pivot) and pairs where the new pivot lies within
  tol of the pair line (the "line through X" continuation check).
- selection score = touches_events - w_o*overshoot - w_age*age,
  with a freshness gate option; births when score >= min_score.
- lifecycle: pierce = close through by >tol; re-entry next bar
  cancels; t1_drawn set at pierce bar (golden convention); dashed
  residual lives extend_min..extend_max bars then close.
- one active line per side (v0-style merge/replace).

Every parameter carries provenance: 'meas' (L1/L2 golden
measurement), 'spec' (v1 params), 'yard' (validate.py), 'lab'
(this lane's tuning choice, to be measured).
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)

from swings import DCStream, SwingBook, Pivot  # noqa: E402

PIP = 1e4

PARAMS = {
    # swing stream (spec: params_v1_1 swing block)
    "k1_abr": 0.8, "pmin_abr": 0.5, "pstruct_abr": 2.5,
    "spike_abr_mult": 2.5, "abr_len": 50,
    # line proposal
    "touch_tol_pips": 1.5,        # yard: TOUCH_TOL
    "touch_tol_abr_frac": 0.25,   # spec: line.touch_tol_abr_frac
    "span_min_bars": 4,           # lab: golden p10 span 30min=6 bars
    "span_max_bars": 96,          # spec: line.span_max_bars (8h)
    "loc_ext_bars": 3,            # spec: line.loc_ext_bars
    "slope_flat_max": 0.5,        # spec: pips/bar
    "flat_drift_pips": 10.0,      # spec: Q1 +-10p per span
    "slope_max_abr_hr": 8.0,      # lab: golden p90 |slope| = 4.4 ABR/hr
    "overshoot_w": 1.0,           # lab: weight on pivot overshoot
    "over_veto_tol_mult": 2.0,    # lab: L3 kill audit — 22 misses vetoed
                                  # at 1*tol while golden tolerates ~2*tol
    "slope_drift_mult": 2.0,      # lab: L3 kill audit — 6 misses were
                                  # rising tops/falling bottoms just
                                  # beyond 1*flat_drift
    "span_age_w": 0.5,            # spec: line.span_age_w
    "span_max_min": 360,          # meas: L1 trusted max span ~350min
    "loc_sess_bars": 18,          # lab: leg/session extreme window ~90min
    "min_touches": 3,             # lab: matched births nt p25=5.5 vs
                                # drawn med 4; yard floor is 2
    "min_score": 2.5,             # lab: birth floor; nt4+over1tol=2.5
    "reanchor_margin": 1.5,       # lab: anti-churn, spec default 0.5
    "pierce_dead_bars": 2,        # lab: need 2 consecutive closes
                                  # through before the line is dead
                                  # (golden tolerates teases)
    "extend_min_bars": 3,         # spec
    "extend_max_bars": 17,        # spec
    "stale_retire_bars": 60,      # meas: DR-MARKET FINAL v2 (R11) —
                                  # level premium ~0 after ~5h without
                                  # a touch; bound 48-96, pick 60
    "fresh_only": False,          # lab: v0-style freshness gate
}

PROVENANCE = {
    "k1_abr": "spec", "pmin_abr": "spec", "pstruct_abr": "spec",
    "spike_abr_mult": "spec", "abr_len": "spec",
    "touch_tol_pips": "yard:validate.TOUCH_TOL",
    "touch_tol_abr_frac": "spec:line",
    "span_min_bars": "lab:L2 span p10=30min",
    "span_max_bars": "spec:line.span_max_bars",
    "loc_ext_bars": "spec:line.loc_ext_bars",
    "slope_flat_max": "spec:line", "flat_drift_pips": "spec:line",
    "slope_max_abr_hr": "meas:L2 |slope_abr_hr| p90=4.4, headroom",
    "overshoot_w": "lab", "span_age_w": "spec:line",
    "over_veto_tol_mult": "lab:L3 kill audit 22/86",
    "slope_drift_mult": "lab:L3 kill audit 6/86",
    "span_max_min": "meas:L1 trusted span max ~350min",
    "loc_sess_bars": "lab:L2 sess-extreme anchor share ~9%",
    "min_touches": "lab:L3 birth-nt audit (matched p25=5.5)",
    "min_score": "lab", "reanchor_margin": "lab:anti-churn",
    "pierce_dead_bars": "lab:golden tolerates teases (L1)",
    "extend_min_bars": "spec:line", "extend_max_bars": "spec:line",
    "stale_retire_bars": "meas:DR-MARKET v2 via R11 (~5h, 48-96 bound)",
    "fresh_only": "lab",
}


class LabObj:
    """Minimal engine-compatible object record."""

    def __init__(self, otype, t_birth, geometry, why, oid):
        self.id = oid
        self.type = otype
        self.style = "solid"
        self.t_birth = t_birth
        self.t_left = t_birth
        self.t_right = None
        self.geometry = geometry
        self.state = "ACTIVE"
        self.touches = []
        self.events = []
        self.role = ""
        self.why = why
        self.priority = 2

    def close(self, i, why):
        self.t_right = i
        self.state = "CLOSED"
        self.events.append((i, "close", why))

    def event(self, i, code, detail=""):
        self.events.append((i, code, detail))


class LineLabEngine:
    """Causal anchor-first line proposer (sandbox)."""

    def __init__(self, params=None, cand_hook=None):
        self.p = dict(PARAMS)
        if params:
            self.p.update(params)
        self.bars = []
        self.abr = []
        self.ema = []
        self.objects = []
        self.cand_log = None
        self.cand_hook = cand_hook       # fn(bar_i, feats_dict) audit
        sp = self.p
        self.book = SwingBook(sp["pmin_abr"], sp["pstruct_abr"],
                              abr_fn=self._abr)
        self.dc = DCStream(
            lambda i: sp["k1_abr"] * self._abr(i),
            lambda i: self._spike(i))

    # ---------------- plumbing ----------------------------------- #

    def _abr(self, i):
        return self.abr[i] if i < len(self.abr) else 5.0

    def _ema(self, i):
        return self.ema[i] if i < len(self.ema) else self.bars[i]["c"]

    def _spike(self, i):
        if i >= len(self.bars):
            return False
        rng = self.bars[i]["h"] - self.bars[i]["l"]
        return rng > self.p["spike_abr_mult"] * self._abr(i)

    def update(self, t, o, h, l, c, cet_min=None):
        i = len(self.bars)
        bar = {"i": i, "t": int(t),
               "cet_min": int(cet_min) if cet_min is not None
               else int((int(t) % 86400) // 60),
               "o": o * PIP, "h": h * PIP, "l": l * PIP, "c": c * PIP}
        self.bars.append(bar)
        rng = bar["h"] - bar["l"]
        n = self.p["abr_len"]
        if i < n:
            self.abr.append(sum(x["h"] - x["l"] for x in self.bars)
                            / (i + 1))
        else:
            self.abr.append(self.abr[-1] +
                            (rng - (self.bars[i - n]["h"] -
                                    self.bars[i - n]["l"])) / n)
        self.ema.append(bar["c"] if i == 0 else
                        self.ema[-1] + (2.0 / 26) *
                        (bar["c"] - self.ema[-1]))
        self.book.update_running(self.dc.dir, self.dc.ext_price)
        for p in self.dc.update(i, bar["h"], bar["l"]):
            piv = self.book.add(p)
            self._propose(i, piv.t_ext, piv.price, piv.dir)
        # local-extreme anchors also trigger proposals: bar j = i-k has
        # just completed its +-k confirm window.
        j = i - self.p["loc_ext_bars"]
        if j >= 0:
            for sd in (-1, 1):
                if self._is_loc_ext(j, sd):
                    self._propose(i, j,
                                  self.bars[j]["l" if sd < 0 else "h"],
                                  sd)
        self._maintain(i)

    # ---------------- anchors ------------------------------------- #

    def _is_loc_ext(self, j, side):
        """Bar j is a defended-side anchor: extreme over +-loc_ext_bars
        (confirmed once j+k bars are known) OR over the trailing
        loc_sess_bars window ending at j (leg/session extreme)."""
        lp = self.p
        ext = "l" if side < 0 else "h"
        n = len(self.bars)
        k = lp["loc_ext_bars"]
        if j < 0 or j + k >= n:
            return False                # not yet confirmable
        px = self.bars[j][ext]
        win = [self.bars[q][ext]
               for q in range(max(0, j - k), min(j + k + 1, n))]
        if (px <= min(win)) if side < 0 else (px >= max(win)):
            return True
        w = lp["loc_sess_bars"]
        win = [self.bars[q][ext]
               for q in range(max(0, j - w), j + 1)]
        return (px <= min(win)) if side < 0 else (px >= max(win))

    def _anchor_pool(self, i, side):
        """Same-side anchors: alive confirmed pivots + local extremes."""
        lp = self.p
        look = lp["span_max_bars"]
        want = side                     # piv.dir: +1 high, -1 low
        pool = [p for p in self.book.alive()
                if p.dir == want and p.t_conf <= i
                and not p.lone_spike and p.t_ext >= i - look]
        seen = {p.t_ext for p in pool}
        k = lp["loc_ext_bars"]
        ext = "l" if side < 0 else "h"
        for j in range(max(0, i - look),
                       min(i - k + 1, len(self.bars) - k)):
            if j in seen:
                continue
            if self._is_loc_ext(j, side):
                p = Pivot(t_ext=j, t_conf=j + k,
                          price=self.bars[j][ext], dir=side, theta=0.0)
                p.bar_ext = True
                pool.append(p)
        pool.sort(key=lambda p: p.t_ext)
        return pool

    # ---------------- proposal ------------------------------------ #

    def _touch_events(self, t0_bar, i, p0, slope, side, tol):
        """Deduped defended-side wick touches: groups of consecutive
        bars within tol count once.  Returns (n_events, worst_close_viol,
        last_touch_bar)."""
        ext = "l" if side < 0 else "h"
        n, cur = 0, False
        worst, last = 0.0, t0_bar
        worst_wick = 0.0
        n_recent = 0                     # touches in last 30% of span
        third = t0_bar + 0.7 * max(1, i - t0_bar)
        for j in range(t0_bar, i + 1):
            pj = p0 + slope * (j - t0_bar)
            wv = abs(self.bars[j][ext] - pj) <= tol
            # close violation of the defended side: under -> c below pj
            cv = (pj - self.bars[j]["c"]) * (1 if side < 0 else -1)
            wv_pen = (pj - self.bars[j][ext]) * (1 if side < 0 else -1)
            if wv:
                if not cur:
                    n += 1
                    if j >= third:
                        n_recent += 1
                cur = True
                last = j
            else:
                cur = False
            if cv > worst:
                worst = cv
            if wv_pen > worst_wick:
                worst_wick = wv_pen
        return n, worst, last, worst_wick, n_recent

    def _propose(self, i, trig_t, trig_p, side):
        """Evaluate anchor pairs triggered by the anchor at
        (trig_t, trig_p): pairs it participates in, plus older pairs
        whose line it lies on (continuation check)."""
        p = self.p
        pool = self._anchor_pool(i, side)
        if len(pool) < 2:
            return
        abr = max(self._abr(i), 1e-9)
        tol = max(p["touch_tol_pips"], p["touch_tol_abr_frac"] * abr)
        flat = p["slope_flat_max"]
        drift = p["flat_drift_pips"]
        best = None
        for a in range(len(pool)):
            for b in range(a + 1, len(pool)):
                pa, pb = pool[a], pool[b]
                if pb.t_ext <= pa.t_ext:
                    continue
                span = pb.t_ext - pa.t_ext
                if not (p["span_min_bars"] <= span <= p["span_max_bars"]):
                    continue
                slope = (pb.price - pa.price) / span
                # defended-side-consistent slope: a top (highs) line
                # must not rise fast; a bottom line must not fall fast
                if side > 0 and slope > 0 and \
                        (slope > flat or
                         slope * span > drift * p["slope_drift_mult"]):
                    continue
                if side < 0 and slope < 0 and \
                        (-slope > flat or
                         -slope * span > drift * p["slope_drift_mult"]):
                    continue
                if abs(slope) * 12 > p["slope_max_abr_hr"] * abr:
                    continue          # steeper than golden p90+headroom
                # trigger rule: the new anchor must be an endpoint or
                # lie on the pair's line within tol
                on = abs(trig_p - (pa.price + slope *
                                   (trig_t - pa.t_ext))) <= tol
                is_ep = pa.t_ext == trig_t or pb.t_ext == trig_t
                if not is_ep and not on:
                    continue
                # defended-edge check on pivots AND bars
                over = 0.0
                for q in pool:
                    if not (pa.t_ext <= q.t_ext <= i):
                        continue
                    d = (q.price - (pa.price + slope *
                                    (q.t_ext - pa.t_ext))) * side
                    if d > over:
                        over = d
                if over > tol * p["over_veto_tol_mult"]:
                    continue
                nt, worst_c, last_t, worst_w, n_rec = \
                    self._touch_events(pa.t_ext, i, pa.price, slope,
                                       side, tol)
                if nt < p["min_touches"]:
                    continue
                if p["fresh_only"] and last_t != trig_t:
                    continue
                age = max(0, (i - pa.t_ext) * 5 - p["span_max_min"])
                over_all = max(over, worst_c)
                score = nt - p["overshoot_w"] * over_all / tol \
                    - p["span_age_w"] * age / 60.0
                line_now = pa.price + slope * (i - pa.t_ext)
                prox = abs(self.bars[i]["c"] - line_now) / abr
                ema_ok = None
                if len(self.abr) > 30:
                    e_v = self._ema(i)
                    ema_ok = (e_v < line_now if side < 0
                              else e_v > line_now)
                feats = {"nt": nt, "over_p": round(over_all, 2),
                         "wick_over": round(worst_w, 2),
                         "span": span, "slope": round(slope, 4),
                         "slope_abr_hr": round(abs(slope) * 12 / abr, 2),
                         "fresh": last_t == trig_t,
                         "recent_touches": n_rec,
                         "nt_per_span": round(nt / max(span, 1), 3),
                         "struct_first": bool(
                             getattr(pa, "prom", 0) >=
                             self.p["pstruct_abr"] * abr),
                         "ema_side": ema_ok,
                         "dist_to_last_p": round(
                             abs(self.bars[i]["c"] - line_now), 2),
                         "anch_bar_ext": int(getattr(pa, "bar_ext", False))
                         + int(getattr(pb, "bar_ext", False)),
                         "prox_abr": round(prox, 2),
                         "age_min": age,
                         "score": round(score, 3),
                         "p0": round(pa.price, 2), "t0": pa.t_ext,
                         "p1": round(pb.price, 2), "t1": pb.t_ext,
                         "i": i, "side": side}
                if self.cand_hook:
                    self.cand_hook(i, dict(feats))
                key = (round(score, 6), span, -pa.t_ext)
                if best is None or key > best[0]:
                    best = (key, pa, pb, slope, nt, score, feats)
        if best is None:
            return
        _, pa, pb, slope, nt, score, feats = best
        self._birth_or_merge(i, pa, pb, slope, nt, score, side, tol)

    def _birth_or_merge(self, i, pa, pb, slope, nt, score, side, tol):
        p = self.p
        sname = "top" if side > 0 else "bottom"
        for o in self.active("PATTERN_LINE"):
            g = o.geometry
            if g["side"] != sname:
                continue
            same = abs(g["slope"] - slope) * max(1, i - g["t0"]) <= \
                2 * tol and abs(
                    g["p0"] + g["slope"] * (i - g["t0"]) -
                    (pa.price + slope * (i - pa.t_ext))) <= 2 * tol
            if same:
                if pb.t_ext > g.get("last_touch", 0):
                    g["last_touch"] = pb.t_ext
                    g["n_touches"] = max(g.get("n_touches", 0), nt)
                    o.event(i, "touch", "%d" % pb.t_ext)
                return
            if nt <= g.get("n_touches", 0) + p["reanchor_margin"]:
                return              # challenger must beat incumbent
            o.close(i, "replaced_by_newer_line")
        # revive a recently closed same-side line instead of inking a
        # new object when the geometry matches (anti-churn)
        for o in reversed(self.objects):
            if o.type != "PATTERN_LINE" or o.state != "CLOSED":
                continue
            g = o.geometry
            if g["side"] != sname:
                continue
            if i - (o.t_right or 0) > 48:
                continue            # stale history stays dead
            price_now = pa.price + slope * (i - pa.t_ext)
            same = abs(g["slope"] - slope) * max(1, i - g["t0"]) <= \
                2 * tol and abs(
                    g["p0"] + g["slope"] * (i - g["t0"]) -
                    price_now) <= 2 * tol
            if same:
                o.state = "ACTIVE"
                o.t_right = None
                g["pierced"] = False
                g["dead"] = False
                g["n_touches"] = max(g.get("n_touches", 0), nt)
                g["last_touch"] = pb.t_ext
                o.event(i, "revive", "same geometry re-triggered")
                return
        if score < p["min_score"]:
            return
        g = {"t0": pa.t_ext, "p0": round(pa.price, 2),
             "slope": round(slope, 4), "side": sname,
             "last_touch": pb.t_ext, "n_touches": nt,
             "pierced": False}
        o = LabObj("PATTERN_LINE", i, g, "anchor_pair",
                   "LIN%04d" % len(self.objects))
        o.t_left = pa.t_ext
        o.event(i, "born", "score=%.2f nt=%d" % (score, nt))
        self.objects.append(o)

    def active(self, otype=None):
        return [o for o in self.objects if o.state == "ACTIVE"
                and (otype is None or o.type == otype)]

    # ---------------- lifecycle ------------------------------------ #

    def _maintain(self, i):
        p = self.p
        b = self.bars[i]
        tol = max(p["touch_tol_pips"], p["touch_tol_abr_frac"]
                  * max(self._abr(i), 1e-9))
        for o in list(self.active("PATTERN_LINE")):
            g = o.geometry
            price_at = g["p0"] + g["slope"] * (i - g["t0"])
            if abs(b["h"] - price_at) <= tol or \
                    abs(b["l"] - price_at) <= tol:
                g["last_touch"] = i
            elif i - g.get("last_touch", g["t0"]) > \
                    p["stale_retire_bars"]:
                o.close(i, "stale_no_touch")
                continue
            through = (g["side"] == "top" and b["c"] > price_at + tol) \
                or (g["side"] == "bottom" and b["c"] < price_at - tol)
            if through and not g["pierced"]:
                g["pierced"] = True
                g["pierce_bar"] = i
                o.event(i, "pierced", "close through line")
            if g["pierced"]:
                nb = i - g["pierce_bar"]
                if (g["side"] == "top" and b["c"] <= price_at) or \
                        (g["side"] == "bottom" and b["c"] >= price_at):
                    g["pierced"] = False
                    o.event(i, "tease_pierce", "re-entered")
                    continue
                if nb >= p["pierce_dead_bars"] and not g.get("dead"):
                    g["dead"] = True
                    g["t1_drawn"] = g["pierce_bar"]
                if not g.get("dead"):
                    continue
                if abs(b["h"] - price_at) <= tol or \
                        abs(b["l"] - price_at) <= tol:
                    g["last_touch"] = i
                if nb >= p["extend_max_bars"] or \
                        (nb >= p["extend_min_bars"] and
                         i - g.get("last_touch", g["pierce_bar"]) > 8):
                    o.close(i, "extension_done")
