"""lines.py — PATTERN_LINE / CONTEXT_LINE (DN_LINE §5).

Anchor universe = convex-hull vertices of the confirmed pivot stream
(theta2 structural for normal lines; theta1 allowed on steep legs).
Each new confirmed pivot triggers one evaluation round: candidate
lines through hull-vertex pairs are scored by touches-in-tol minus
overshoot; the max-touch fit freezes on confirm.  Slope direction is a
hard constraint (a rising line through highs is never a break-defining
top line).  Pierce policy: a close through by >tol marks the line
PIERCED; kept as dashed extension for a bounded window, then converts
to a broken-barrier level reference.
"""

import gates
from salience import Candidate
from swings import Pivot


class LineBook:
    def __init__(self, eng):
        self.e = eng
        # L7 anchor extensions (MANDATE_LINE_LAB_2):
        # _term[side] = (bar j, price) of the freshest unconfirmed
        #   leg extreme — the "theta1 terminal anchor that needs no
        #   confirmation" (L2: the last touch is wick-only 48% of the
        #   time; draw lag ~1 bar).  Usable as anchor once it has stood
        #   for >=1 bar (t_conf = j + 1).
        # _sess[side] = (bar j, price) running extreme since the last
        #   session boundary (gates ASIA/EU/US) — the book's named-bar
        #   class ("the Asia high", "the pre-ECB low").
        self._term = {-1: None, 1: None}
        self._term_fired = {-1: None, 1: None}
        self._sess = {-1: None, 1: None}
        self._sess_edge = None        # cet_min boundary last crossed

    # ---------------- candidates ---------------------------------- #

    def on_pivot(self, i, piv):
        e = self.e
        if gates.hard_block(e.bars[i]["cet_min"]):
            return
        self._eval(i, piv, context=False)
        self._eval(i, piv, context=True)

    def _pool(self, i, side, context=False):
        """Anchor pool: same-side confirmed pivots within lookback.

        PATTERN_LINE anchors on the alive stream (theta1-passed): golden
        anchors include sub-structural pivots (L3 diagnostic — only 7/16
        golden lines carry >=2 structural on-line pivots).  CONTEXT_LINE
        keeps the structural stream (session-extreme anchors).
        """
        e = self.e
        lp = e.p["line"]
        lookback = lp["context_max_bars"] if context else \
            lp["span_max_bars"]
        src = e.book.structural() if context else e.book.alive()
        pool = [p for p in src if p.dir == side and p.t_conf <= i
                and not p.lone_spike and p.t_ext >= i - lookback]
        if context:
            return pool
        # named-bar anchors (DN_LINE §2 "drawn from a named bar"): a
        # causal local extreme — bar j's wick is the window extremum
        # over +-loc_ext_bars; usable only once the right side is
        # known (t_conf = j + k).  Covers golden anchors that never
        # confirm as DC pivots (e.g. 9.1b 15:55 bar low).
        k = lp["loc_ext_bars"]
        ext = "l" if side < 0 else "h"
        seen = {p.t_ext for p in pool}
        out = list(pool)
        for j in range(max(0, i - lookback),
                       min(i - k + 1, len(e.bars) - k)):
            if j in seen:
                continue
            if self._is_loc_ext(j, side):
                p = Pivot(t_ext=j, t_conf=j + k,
                          price=e.bars[j][ext], dir=side, theta=0.0)
                p.bar_ext = True
                out.append(p)
        # terminal-leg + session-extreme anchors (L7): pseudo-pivots
        # already deduped against pool t_ext via `seen`.  term_ext
        # marks them second-class: _eval prefers a confirmed-anchor
        # pair when one passes (L7-R1: unmarked term anchors crowded
        # out right geometry, oracle 0.36 -> 0.34).
        for ref in (self._term.get(side), self._sess.get(side)):
            if ref is None:
                continue
            j, px = ref
            if j in seen or j >= i or i - j > lookback:
                continue
            p = Pivot(t_ext=j, t_conf=j + 1, price=px, dir=side,
                      theta=0.0)
            p.bar_ext = True
            p.term_ext = True
            out.append(p)
            seen.add(j)
        out.sort(key=lambda p: p.t_ext)
        return out

    def _is_loc_ext(self, j, side):
        """Bar j is a defended-side named-bar anchor: its extreme is
        the extremum over +-loc_ext_bars (confirmed at j+k) OR over
        the trailing loc_sess_bars window ending at j — the leg/
        session extreme class (LINE-LAB L2: ~9% of golden anchors are
        named leg extremes like 'the ~14:45 low' that no +-k test or
        DC pivot catches; R12 L5 port item 2)."""
        e = self.e
        lp = e.p["line"]
        n = len(e.bars)
        k = lp["loc_ext_bars"]
        if j < 0 or j + k >= n:
            return False
        ext = "l" if side < 0 else "h"
        px = e.bars[j][ext]
        win = [e.bars[q][ext]
               for q in range(max(0, j - k), min(j + k + 1, n))]
        if (px <= min(win)) if side < 0 else (px >= max(win)):
            return True
        w = lp.get("loc_sess_bars", 0)
        if w:
            win = [e.bars[q][ext]
                   for q in range(max(0, j - w), j + 1)]
            return (px <= min(win)) if side < 0 else px >= max(win)
        return False

    def _scan(self, i, piv, pool, stream, tol, lp, span_lo, span_hi,
              context, allow_term):
        """One pass over anchor pairs; returns (key, pa, pb, slope, nt,
        n_pt) of the best candidate or None.  allow_term=False skips
        pairs containing a terminal/session pseudo-anchor."""
        e = self.e
        side = piv.dir
        flat = lp["slope_flat_max"]
        drift = lp["flat_drift_pips"]
        best = None
        for a in range(len(pool)):
            for b in range(a + 1, len(pool)):
                pa, pb = pool[a], pool[b]
                if pb.t_ext <= pa.t_ext:
                    continue
                if not allow_term and \
                        (getattr(pa, "term_ext", False) or
                         getattr(pb, "term_ext", False)):
                    continue
                span = pb.t_ext - pa.t_ext
                if not (span_lo <= span <= span_hi):
                    continue
                if i - pb.t_ext > span_hi:
                    continue
                slope = (pb.price - pa.price) / span
                # DN_LINE §5: candidates are hull edges through the new
                # pivot, or pairs the new pivot is tolerance-feasible on
                is_ep = pa.t_ext == piv.t_ext or pb.t_ext == piv.t_ext
                if not is_ep and \
                        abs(piv.price - (pa.price + slope *
                                         (piv.t_ext - pa.t_ext))) > tol:
                    continue
                # slope rule (hard): a top line never rises, a bottom
                # line never falls — flat drift allowance is bounded
                # per-bar AND per-span (Q1: +-10 pips per span);
                # L3 kill-audit: golden tolerates ~2x drift on gently
                # rising necklines -> slope_drift_mult (R12 L5 item 4)
                dmul = lp.get("slope_drift_mult", 1.0)
                if side > 0 and slope > 0 and \
                        (slope > flat or slope * span > drift * dmul):
                    continue
                if side < 0 and slope < 0 and \
                        (-slope > flat or -slope * span > drift * dmul):
                    continue
                # defended-edge test (per-pair hull semantics): no
                # in-span pivot may lie beyond touch tolerance on the
                # defended side — a pierced-at-birth chord is not a
                # defended line
                over = 0.0
                n_pt = 0
                omul = lp.get("over_veto_tol_mult", 1.0)
                for q in stream:
                    if not (pa.t_ext <= q.t_ext <= i):
                        continue
                    d = (q.price - (pa.price + slope *
                                    (q.t_ext - pa.t_ext))) * side
                    if d > over:
                        over = d
                        if over > tol * omul:
                            break
                    if abs(q.price - (pa.price + slope *
                                      (q.t_ext - pa.t_ext))) <= tol:
                        n_pt += 1
                # >=2-touch confirm counts the anchors themselves;
                # a named-bar (bar_ext) anchor is a touch by
                # construction
                n_anch = int(getattr(pa, "bar_ext", False)) + \
                    int(getattr(pb, "bar_ext", False))
                if over > tol * omul or \
                        n_pt + n_anch < lp["min_touches"]:
                    continue
                # touch evidence = bar wicks within tol over the span
                # (golden §4 measure: median 6, p75 10 wick touches);
                # n_ev dedupes consecutive in-tol bars into touch
                # events — birth floor >=3 events = 2 anchors + a
                # defended mid touch (Volman 3-point rule; L3: nt>=3
                # keeps recall, nt>=4 loses it)
                ext = "l" if side < 0 else "h"
                nt = 0
                n_ev = 0
                cur = False
                for j in range(pa.t_ext, i + 1):
                    if j >= len(e.bars):
                        break
                    pj = pa.price + slope * (j - pa.t_ext)
                    wv = abs(e.bars[j][ext] - pj) <= tol
                    if wv:
                        nt += 1
                        if not cur:
                            n_ev += 1
                    cur = wv
                if not context and n_ev < lp.get("min_touch_events", 2):
                    continue
                age = max(0, (i - pa.t_ext) * 5 - lp["span_max_min"])
                score_key = nt - lp["span_age_w"] * age / 60.0
                key = (round(score_key, 6), span, -pa.t_ext)
                if best is None or key > best[0]:
                    best = (key, pa, pb, slope, nt, n_pt)
        return best

    def _eval(self, i, piv, context):
        e = self.e
        lp = e.p["line"]
        abr = max(e.abr[i], 1e-9)
        tol = max(lp["touch_tol_pips"], lp["touch_tol_abr_frac"] * abr)
        side = piv.dir
        pool = self._pool(i, side, context=context)
        # membership by (t_ext, dir): local-extreme triggers arrive as
        # fresh pseudo-pivots, not pool identities (L5 item 1)
        in_pool = any(q is piv or (q.t_ext == piv.t_ext and
                                   q.dir == piv.dir) for q in pool)
        if len(pool) < 2 or not in_pool:
            return
        if context:
            span_lo, span_hi = lp["context_min_bars"], \
                lp["context_max_bars"]
        else:
            span_lo, span_hi = lp.get("span_min_bars", 2), \
                lp["span_max_bars"]
        flat = lp["slope_flat_max"]
        drift = lp["flat_drift_pips"]
        stream = [q for q in e.book.alive() if q.dir == side
                  and q.t_conf <= i]
        # two-pass scan: confirmed anchors first; terminal/session
        # (term_ext) anchors only when no confirmed pair survives —
        # they add coverage, never crowd out structure (L7-R1)
        best = self._scan(i, piv, pool, stream, tol, lp,
                          span_lo, span_hi, context, allow_term=False)
        if best is None:
            best = self._scan(i, piv, pool, stream, tol, lp,
                              span_lo, span_hi, context,
                              allow_term=True)
        if best is None:
            return
        _, pa, pb, slope, nt, n_pt = best
        geom = {"t0": pa.t_ext, "p0": round(pa.price, 2),
                "slope": round(slope, 4),
                "side": "top" if side > 0 else "bottom", "t1": i}
        kind = "CONTEXT_LINE" if context else "PATTERN_LINE"
        feats = {"touches": nt, "piv_touches": n_pt,
                 "prom_abr": round(sum(q.prom for q in pool) /
                                   len(pool) / abr, 2),
                 # L3 measured the only fold-stable discriminator
                 # (AUC 0.73-0.85, all 5 day-folds): age of the first
                 # anchor past the span_max_min knee (L8 selection)
                 "age_min": int(max(0, (i - pa.t_ext) * 5
                                    - lp["span_max_min"]))}
        # incumbent re-anchor: a challenger must beat the frozen line's
        # score by margin m (RT4 §10 hysteresis)
        for o in e.active("PATTERN_LINE") + e.active("CONTEXT_LINE"):
            g = o.geometry
            if g["side"] != geom["side"] or \
                    (o.type == "CONTEXT_LINE") != context:
                continue
            same = abs(g["p0"] + g["slope"] * (i - g["t0"]) -
                       (geom["p0"] + slope * (i - g["t0"]))) <= 2 * tol \
                and abs(g["slope"] - slope) * max(1, i - g["t0"]) \
                <= 2 * tol
            if same:
                if piv.t_ext > g.get("last_touch", 0):
                    g["last_touch"] = piv.t_ext
                    g["n_touches"] = max(g.get("n_touches", 0), nt)
                return
            chal = nt
            inc = g.get("n_touches", 0)
            if chal > inc + lp["reanchor_margin"]:
                g["p0"], g["slope"], g["t0"] = geom["p0"], \
                    geom["slope"], geom["t0"]
                g["n_touches"] = nt
                g["last_touch"] = piv.t_ext
                o.event(i, "re_anchor", "better fit %.1f>%1.f" %
                        (chal, inc))
            return
        # revive a recently closed same-side line instead of new ink:
        # same geometry re-triggering is the same structure resuming
        # (L3 anti-churn; salience's grave band would refuse the
        # re-proposal anyway, which would lose the golden re-draw)
        rmax = lp.get("revive_max_age_bars", 48)
        for o in reversed(e.objects):
            if o.type != kind or o.state != "CLOSED":
                continue
            g = o.geometry
            if g["side"] != geom["side"]:
                continue
            if i - (o.t_right or 0) > rmax:
                continue            # stale history stays dead
            if abs(g["slope"] - slope) * max(1, i - g["t0"]) <= 2 * tol \
                    and abs(g["p0"] + g["slope"] * (i - g["t0"]) -
                            (geom["p0"] + slope * (i - g["t0"]))) \
                    <= 2 * tol:
                o.state = "ACTIVE"
                o.t_right = None
                g["pierced"] = False
                g["dead"] = False
                g["n_touches"] = max(g.get("n_touches", 0), nt)
                g["last_touch"] = piv.t_ext
                o.event(i, "revive", "same geometry re-triggered")
                return
        e.salience.propose(Candidate(
            kind, "hull_max_touch", geom, i, feats=feats,
            meta={"anchors": [pa.t_ext, pb.t_ext]},
            ttl=e.p["salience"]["cand_ttl_bars"]))

    # ---------------- maintenance --------------------------------- #

    def maintain(self, i):
        e = self.e
        lp = e.p["line"]
        b = e.bars[i]
        tol = e._tol()
        # L5 item 1: named-bar anchors also trigger evaluations — bar
        # j = i - loc_ext_bars has just completed its +-k confirm
        # window; run the pair eval with it as the trigger pivot.
        j = i - lp["loc_ext_bars"]
        if j >= 0:
            for sd in (-1, 1):
                if self._is_loc_ext(j, sd):
                    trig = Pivot(t_ext=j, t_conf=i,
                                 price=e.bars[j]["l" if sd < 0
                                                else "h"],
                                 dir=sd, theta=0.0)
                    trig.bar_ext = True
                    self._eval(i, trig, context=False)
        # L7: theta1 terminal anchor — the DC stream's unconfirmed leg
        # extreme (e.dc.ext_idx/ext_price).  Needs no confirmation by
        # design: L2 measured the last touch is a wick-only unconfirmed
        # extreme ~48% of the time and draw lag ~1 bar.  Fires only
        # when the extreme moves to a new bar and is fresh (printed
        # within term_lookback_bars).
        w = lp.get("term_lookback_bars", 0)
        dc = getattr(e, "dc", None)
        if w and dc is not None and 0 <= dc.ext_idx < i \
                and i - dc.ext_idx <= w:
            sd = dc.dir
            self._term[sd] = (dc.ext_idx, dc.ext_price)
            if self._term_fired[sd] != dc.ext_idx:
                self._term_fired[sd] = dc.ext_idx
                trig = Pivot(t_ext=dc.ext_idx, t_conf=i,
                             price=dc.ext_price, dir=sd, theta=0.0)
                trig.bar_ext = True
                trig.term_ext = True
                self._eval(i, trig, context=False)
        # L7: session-extreme anchors — running extreme since the last
        # session boundary (480=EU open, 840=US open, gates.py).  The
        # book names these ("the Asia high", "the EU-open low"); they
        # persist in the pool via _pool, refreshed here.
        cm = b["cet_min"]
        for edge in (480, 840):
            prev = self._sess_edge
            if prev is not None and prev < edge <= cm:
                self._sess = {-1: (i, b["l"]), 1: (i, b["h"])}
        self._sess_edge = cm
        for sd in (-1, 1):
            ext = "l" if sd < 0 else "h"
            ref = self._sess[sd]
            if ref is None:
                self._sess[sd] = (i, b[ext])
            else:
                j0, p0 = ref
                better = b[ext] < p0 if sd < 0 else b[ext] > p0
                if better:
                    self._sess[sd] = (i, b[ext])
        for o in list(e.active("PATTERN_LINE")) + \
                list(e.active("CONTEXT_LINE")):
            g = o.geometry
            price_at = g["p0"] + g["slope"] * (i - g["t0"])
            if abs(b["h"] - price_at) <= tol or \
                    abs(b["l"] - price_at) <= tol:
                g["last_touch"] = i
            elif not g.get("pierced") and \
                    i - g.get("last_touch", o.t_birth) > \
                    lp.get("stale_retire_bars", 10 ** 9):
                # R11 §2 / DR-MARKET v2: level premium ~0 after ~5h
                # without a touch -> retire the line (its ink ends).
                o.close(i, "stale_no_touch")
                continue
            through = (g["side"] == "top" and b["c"] > price_at + tol) \
                or (g["side"] == "bottom" and b["c"] < price_at - tol)
            poke = (g["side"] == "top" and b["h"] > price_at + tol
                    and b["c"] <= price_at) or \
                   (g["side"] == "bottom" and b["l"] < price_at - tol
                    and b["c"] >= price_at)
            if poke and not g.get("pierced"):
                e.patterns.label(i, o,
                                 side="above" if g["side"] == "top"
                                 else "below", letter="T",
                                 price=b["h"] if g["side"] == "top"
                                 else b["l"])
            if through and not g.get("pierced"):
                if gates.hard_block(b["cet_min"]):
                    continue          # window suppresses initiation
                g["pierced"] = True
                g["pierce_bar"] = i
                o.event(i, "pierced", "close through line")
            if g.get("pierced"):
                nb = i - g["pierce_bar"]
                if (g["side"] == "top" and b["c"] <= price_at) or \
                        (g["side"] == "bottom" and
                         b["c"] >= price_at):
                    # re-entered: tease, not a break
                    g["pierced"] = False
                    o.event(i, "tease_pierce", "re-entered")
                    continue
                if nb >= lp.get("pierce_dead_bars", 1) and \
                        not g.get("dead"):
                    # decisive traverse (>=pierce_dead_bars closes
                    # through; a 1-bar poke is a tease — golden
                    # tolerates them, L1) -> broken barrier carry; the
                    # solid line's drawn span ends at the traverse bar
                    # (golden t1 convention), residual stays dashed
                    e.levels.spawn(i, price_at, "broken_line_edge",
                                   side="below" if g["side"] == "top"
                                   else "above", src=o.id,
                                   t0=g["t0"])
                    g["dead"] = True
                    g["t1_drawn"] = g["pierce_bar"]
                if not g.get("dead"):
                    continue        # grace window: pierced, not dead
                if nb >= lp["extend_max_bars"] or (
                        nb >= lp["extend_min_bars"] and
                        i - g.get("last_touch", g["pierce_bar"]) > 8):
                    o.close(i, "extension_done")
