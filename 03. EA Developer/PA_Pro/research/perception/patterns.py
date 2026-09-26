"""patterns.py — BRACKET (M/W/Mm/Ww/SHS), SQUEEZE, BAR_MARKER,
LABEL_TF (DN_BRACKET, DN_SQUEEZE, DN_TF).

Brackets match deterministic templates on the persistence-pruned pivot
stream (theta2 for major legs; a theta1 minor inner turn flags the
Mm/Ww variants).  A bracket earns ink only when decision-relevant:
its completing pivot near current price, or its edge/mid is a live
barrier.

Squeeze: small-bar contraction + two named live walls bracketing price
+ narrowing gap + apex proximity.  No walls -> no squeeze (Asia fix).

BAR_MARKER: evening/morning-star ticks — a confirmed theta1 pivot whose
extreme bar exceeds both neighbours' same-side extremes by >=
star_min_abr*ABR.

LABEL_TF: attribute events on a live edge — T on a poke that closes
back inside, F when the excursion then traverses (within the relabel
window).  One label per edge per excursion.
"""

import gates
from salience import Candidate


class PatternBook:
    def __init__(self, eng):
        self.e = eng

    # ---------------- pivot-driven: brackets + markers ------------ #

    def on_pivot(self, i, piv):
        e = self.e
        self._marker_check(i, piv)
        if gates.hard_block(e.bars[i]["cet_min"]):
            return
        self._brackets(i, piv)

    def _marker_check(self, i, piv):
        e = self.e
        if e.p["marker"].get("off"):
            # R50 §50.2 ink-only arm: BAR_MARKER is 117 objects on the
            # 34 marginal panels (3.4/panel, the author's rate is
            # 4/179) with zero M1-family matches and no downstream
            # consumer (skipped in NMS and anchor checks) — suppress
            # the kind entirely to buy clutter headroom.
            return
        abr = e.abr[i]
        t = piv.t_ext
        if t < 1 or t + 1 >= len(e.bars):
            return
        need = e.p["marker"]["star_min_abr"] * abr
        # R22 lever (default OFF): golden draws a bar marker only on
        # the NAMED day extreme ("the 08:05 low", "~14:00 spike") — 4
        # objects over TUNE — while an ungated star test emits ~740
        # and crowds the annot budget against LABEL_TF marks (40 right
        # T/F proposals died outranked).  Causal: the running extreme
        # is known by t_ext < t_conf.
        day_ex = e.p["marker"].get("day_extreme_only")
        live_anchor = False
        if day_ex and e.p["marker"].get("day_extreme_live_anchor_ok"):
            # variant arm (R22 §22.2): a pivot sitting on a live
            # object's edge marks a structure the chart already
            # shows — allow it even when it is not the day extreme.
            ex0 = e.bars[t]["h"] if piv.dir > 0 else e.bars[t]["l"]
            tol = e._tol()
            for o in e.active():
                if o.type in ("LABEL_TF", "BAR_MARKER"):
                    continue
                g = o.geometry
                if g.get("p0") is not None:
                    pw = g["p0"] + g.get("slope", 0.0) * \
                        (t - g.get("t0", t))
                    if abs(ex0 - pw) <= tol:
                        live_anchor = True
                        break
                else:
                    band = e.salience._band_of(o.type, g, t)
                    if band and band[0] - tol <= ex0 <= \
                            band[1] + tol:
                        live_anchor = True
                        break
        if piv.dir > 0:
            ex = e.bars[t]["h"]
            nbr = max(e.bars[t - 1]["h"], e.bars[t + 1]["h"])
            if ex - nbr < need:
                return
            if day_ex and not live_anchor and \
                    ex < max(x["h"] for x in e.bars[:t + 1]):
                return
            name = "evening_star" if e.bars[t]["c"] < e.bars[t]["o"] \
                else "tick_top"
            side = "above"
        else:
            ex = e.bars[t]["l"]
            nbr = min(e.bars[t - 1]["l"], e.bars[t + 1]["l"])
            if nbr - ex < need:
                return
            if day_ex and not live_anchor and \
                    ex > min(x["l"] for x in e.bars[:t + 1]):
                return
            name = "morning_star" if e.bars[t]["c"] > e.bars[t]["o"] \
                else "tick_bottom"
            side = "below"
        geom = {"t0": t, "t1": t, "price": round(ex, 2), "side": side,
                "letter": name}
        e.salience.propose(Candidate(
            "BAR_MARKER", "star_extreme", geom, i,
            feats={"touches": 0, "prom_abr": round(piv.prom / abr, 2)},
            meta={"bar": t}, ttl=12))

    def _brackets(self, i, piv):
        e = self.e
        bp = e.p["bracket"]
        abr = e.abr[i]
        eq = max(bp["eq_tol_pips"], bp["eq_tol_abr"] * abr)
        st = [p for p in e.book.structural() if p.t_conf <= i]
        al = [p for p in e.book.alive() if p.t_conf <= i]
        if len(st) < 3 or piv not in al:
            return
        # M/W pair route on the mixed-scale stream (DN_BRACKET §5
        # licenses the variants on the mixed-scale stream; measured:
        # 5/25 golden M/W have a theta1 anchor, and restricting anchors
        # to theta2 cost matches without freeing the cap — wrong
        # structural pairs saturate it just the same).  Pair = the new
        # pivot + the nearest earlier equal same-side extreme, with a
        # real intervening opposite extreme as the "middle".
        # Measured alternative — emit once for the FURTHEST valid
        # anchor: on FUNNEL labels the right sibling is the longest-sep
        # one in 85/85 right pivots, but the paired A/B (9044ab77) was
        # a wash (BRACKET +1, snapshot -2) — births stay cap-bound, so
        # anchor choice inside a saturated stream changes geometry,
        # not counts.  Nearest-first kept.
        for q in reversed([p for p in al[:-1]
                           if p.dir == piv.dir]):
            sep = piv.t_ext - q.t_ext
            if sep > bp["sep_max_bars"]:
                break
            if sep < bp["sep_min_bars"] or \
                    abs(piv.price - q.price) > eq:
                continue
            mid = [p for p in al
                   if p.dir == -piv.dir
                   and q.t_ext < p.t_ext < piv.t_ext]
            if not mid:
                continue
            mid_p = min(mid, key=lambda p: p.price) if piv.dir > 0 \
                else max(mid, key=lambda p: p.price)
            # the middle must be a real interim extreme, not a blip:
            # golden M/W dip med 1.49*ABR, min 0.58 (MEASURE-TUNE).
            shallow = min(piv.price, q.price) if piv.dir > 0 \
                else max(piv.price, q.price)
            if (shallow - mid_p.price) * piv.dir < \
                    bp["mid_min_abr"] * abr:
                continue
            letter = "M" if piv.dir > 0 else "W"
            # minor inner turn -> Mm / Ww (theta1 middle leg)
            if mid_p.prom_birth < e.book.floor_struct(mid_p):
                letter += "m" if piv.dir > 0 else "w"
            self._emit_bracket(i, letter, q, piv, mid=mid_p)
            break
        # SHS: chain-search the structural stream s1 n1 h n2 s2 —
        # intervening structural noise between pattern pivots must not
        # break the sequence (the "last five exactly" test missed
        # 9.1a's 04:00-08:00 SHS); each step takes the most recent
        # opposite/same-side structural pivot before the previous one.
        if len(st) >= 5 and e.book.is_structural(piv):
            def _last(d, before):
                return next((p for p in reversed(st)
                             if p.dir == d and p.t_ext < before), None)
            s2, n2 = piv, _last(-piv.dir, piv.t_ext)
            h = _last(piv.dir, n2.t_ext) if n2 else None
            n1 = _last(-piv.dir, h.t_ext) if h else None
            s1 = _last(piv.dir, n1.t_ext) if n1 else None
            if s1 is not None:
                sh_tol = bp["shoulder_tol_abr"] * abr
                head = (h.price - max(s1.price, s2.price)) * s1.dir
                if abs(s1.price - s2.price) <= sh_tol and \
                        head >= bp["head_min_abr"] * abr:
                    letter = "SHS" if s1.dir > 0 else "SHSi"
                    self._emit_bracket(i, letter, s1, s2, mid=h)

    def _emit_bracket(self, i, letter, p_a, p_b, mid):
        e = self.e
        bp = e.p["bracket"]
        abr = e.abr[i]
        c = e.bars[i]["c"]
        # relevance gate: completing pivot near price, or the pattern
        # edge/mid coincides with a live barrier
        rel = abs(p_b.price - c) <= bp["relevance_abr"] * abr
        if not rel:
            for o in e.active():
                band = e.salience._band_of(o.type, o.geometry, i)
                if band and not (band[0] - abr > p_b.price or
                                 band[1] + abr < p_b.price):
                    rel = True
                    break
        if not rel:
            e._cand("BRACKET", i, "letter_" + letter,
                    "vetoed_irrelevant",
                    {"t0": p_a.t_ext, "t1": p_b.t_ext,
                     "level": round(p_b.price, 2)})
            return
        # dedupe by anchor footprint
        for o in e.active("BRACKET"):
            g = o.geometry
            if g.get("letter") == letter and \
                    abs(g["t0"] - p_a.t_ext) <= 2:
                return
        lvl = round((p_a.price + p_b.price) / 2, 2)
        midp = round(mid.price, 2)
        geom = {"t0": p_a.t_ext, "t1": p_b.t_ext, "letter": letter,
                "level": lvl, "mid": midp}
        e.salience.propose(Candidate(
            "BRACKET", "letter_" + letter, geom, i,
            feats={"touches": 2,
                   "prom_abr": round((p_a.prom + p_b.prom)
                                     / 2 / abr, 2)},
            meta={"anchors": (p_a.t_ext, p_b.t_ext)},
            ttl=e.p["salience"]["cand_ttl_bars"]))
        # the middle section becomes a MINI_LEVEL candidate (DN_LEVEL
        # formation_extreme / DN_BRACKET §5 output)
        side = "above" if p_a.dir > 0 else "below"
        e.levels.spawn(i, mid.price, "formation_mid", side,
                       t0=p_a.t_ext, mini=True)

    # ---------------- squeeze ------------------------------------- #

    def squeeze_scan(self, i):
        """DN_SQUEEZE predicate: small bars + two live named walls
        bracketing price + narrowing gap + apex proximity."""
        e = self.e
        sp = e.p["squeeze"]
        n = sp["min_bars"]
        if i < n + 1 or gates.hard_block(e.bars[i]["cet_min"]):
            return
        abr = e.abr[i]
        seg = e.bars[i - n + 1:i + 1]
        if not all(x["h"] - x["l"] <= sp["small_bar_abr"] * e.abr[x["i"]]
                   for x in seg):
            return
        mid_hi = max(x["h"] for x in seg)
        mid_lo = min(x["l"] for x in seg)
        mid = (mid_hi + mid_lo) / 2
        # walls = live objects' evaluated prices at bar i, each
        # carrying a slope (0 for flat edges/levels, the line slope for
        # PATTERN_LINE/CONTEXT_LINE)
        wd = sp["wall_dist_abr"] * abr
        ups, dns = [], []
        for o in e.active():
            if o.type in ("LABEL_TF", "BAR_MARKER", "BRACKET",
                          "SQUEEZE"):
                continue
            g = o.geometry
            if g.get("p0") is not None:
                pw = g["p0"] + g["slope"] * (i - g["t0"])
                cand = [(pw, g["slope"], o.id)]
            else:
                band = e.salience._band_of(o.type, g, i)
                if band is None:
                    continue
                cand = [(band[0], 0.0, o.id), (band[1], 0.0, o.id)] \
                    if band[0] != band[1] else [(band[0], 0.0, o.id)]
            for pw, sl, oid in cand:
                if mid_hi < pw <= mid_hi + wd:
                    ups.append((pw, sl, oid))
                elif mid_lo - wd <= pw < mid_lo:
                    dns.append((pw, sl, oid))
        # EMA25 is a named wall too (spec Fig 5.1: compression pressed
        # between a structure edge and the rising/falling EMA)
        ema_now = e.ema[i]
        ema_slope = (e.ema[i] - e.ema[max(0, i - sp["span_max_bars"])]) \
            / min(i, sp["span_max_bars"]) if i else 0.0
        if mid_hi < ema_now <= mid_hi + wd:
            ups.append((ema_now, ema_slope, "EMA25"))
        elif mid_lo - wd <= ema_now < mid_lo:
            dns.append((ema_now, ema_slope, "EMA25"))
        if not ups or not dns:
            return
        wu = min(ups, key=lambda w: w[0])   # nearest upper wall
        wl = max(dns, key=lambda w: w[0])   # nearest lower wall
        gap_now = wu[0] - wl[0]
        if gap_now <= 0:
            return
        # narrowing is measured over the squeeze span — the walls'
        # convergence window up to span_max_bars back (DN_SQUEEZE §5:
        # gap_t1 <= ~0.6 x gap_t0 over the span).
        t0 = max(0, i - sp["span_max_bars"])
        gap0 = (wu[0] + wu[1] * (t0 - i)) - \
               (wl[0] + wl[1] * (t0 - i))
        narrowing = gap0 > 0 and gap_now <= sp["gap_shrink"] * gap0
        # apex: the two walls' crossing time ahead within apex_bars
        apex = False
        if wu[1] != wl[1]:
            dt = gap_now / (wl[1] - wu[1])
            if 0 <= dt <= sp["apex_bars"]:
                apex = True
        if not (narrowing and apex):
            return
        geom = {"t0": t0, "t1": i, "top": round(mid_hi, 2),
                "bottom": round(mid_lo, 2), "mid": round(mid, 2)}
        e.salience.propose(Candidate(
            "SQUEEZE", "walls_converge", geom, i,
            feats={"touches": n, "prom_abr": 0.0},
            meta={"walls": (wl[2], wu[2])}, ttl=6))

    # ---------------- LABEL_TF ------------------------------------- #

    def label(self, i, obj, side, letter, price):
        """Attach a T/F label event to a live object (dedupe: one label
        per edge per excursion — caller resets _poke_exc)."""
        e = self.e
        for o2 in e.objects:
            if o2.type == "LABEL_TF" and o2.role == obj.id and \
                    o2.state == "ACTIVE" and \
                    o2.geometry["side"] == side and \
                    i - o2.t_birth <= e.p["box"]["tf_relabel_bars"]:
                if letter == "F" and o2.geometry["letter"] == "T":
                    o2.geometry["letter"] = "F"
                    o2.event(i, "relabel", "T->F")
                return o2
        geom = {"price": round(price, 2), "side": side,
                "letter": letter, "t0": i, "t1": i}
        c = Candidate("LABEL_TF", "edge_poke", geom, i,
                      feats={"touches": 0, "prom_abr": 0.0},
                      meta={"parent": obj.id}, ttl=6)
        o = e.salience.propose(c)
        return o

    def relabel(self, i, o, top, bot, hgt):
        """T -> F when, within the relabel window, price moves >= half
        the box height the other way and closes back inside (spec
        §3.2)."""
        e = self.e
        bp = e.p["box"]
        b = e.bars[i]
        for o2 in e.objects:
            if o2.type != "LABEL_TF" or o2.role != o.id or \
                    o2.geometry["letter"] != "T":
                continue
            if not (1 <= i - o2.t_birth <= bp["tf_relabel_bars"]):
                continue
            moved = (top - b["c"]) if o2.geometry["side"] == "above" \
                else (b["c"] - bot)
            if moved >= bp["tf_relabel_frac_height"] * hgt and \
                    bot < b["c"] < top:
                o2.geometry["letter"] = "F"
                o2.event(i, "relabel", "T->F")
