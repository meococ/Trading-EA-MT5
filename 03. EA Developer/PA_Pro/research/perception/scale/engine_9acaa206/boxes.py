"""boxes.py — congestion boxes (DN_BOX §5): clustered edges, company
rule, D9 build window, freeze/re-anchor, close-out + follow-through.

Birth: on each confirmed pivot, anchored window scans (last k pivot
legs) propose candidates whose edges are bucket-merge clusters of the
member *bar* extremes — the most extreme cluster still having
minPts support.  A lone wick is a poke, not an edge.

Lifecycle: edges freeze at birth; re-anchor only on a new aligned
cluster (>=min_company members) within reanchor_max — logged.  Death =
decisive close beyond an edge followed by a bar that does not re-enter
(follow-through); a re-entered break demotes to a tease label.
"""

import numpy as np

import gates
from salience import Candidate


def bucket_merge(values, eps, min_pts):
    """Single-linkage clustering on sorted values: consecutive members
    within eps merge.  Returns clusters as (extreme, members) lists,
    extreme = the most extreme member (max for a top edge)."""
    vals = sorted(values)
    clusters = []
    cur = []
    for v in vals:
        if cur and v - cur[-1] > eps:
            clusters.append(cur)
            cur = []
        cur.append(v)
    if cur:
        clusters.append(cur)
    return [c for c in clusters if len(c) >= min_pts]


def cluster_edge(highs, lows, eps, min_pts):
    """(top_edge, bot_edge, n_top, n_bot) from member extremes, or
    None when a side lacks a defended cluster (company rule)."""
    tops = bucket_merge(highs, eps, min_pts)
    bots = bucket_merge(lows, eps, min_pts)
    if not tops or not bots:
        return None
    top_c = max(tops, key=lambda c: max(c))     # most extreme top cluster
    bot_c = min(bots, key=lambda c: min(c))     # most extreme bottom
    return max(top_c), min(bot_c), len(top_c), len(bot_c)


def longest_contained_run(closes, lo, hi, i0):
    """Longest run of closes inside [lo, hi] within the window list;
    returns (start_bar, end_bar) in absolute bar index, or None."""
    best = cur = None
    for k, cl in enumerate(closes):
        if lo <= cl <= hi:
            cur = (cur[0], i0 + k) if cur else (i0 + k, i0 + k)
            if best is None or cur[1] - cur[0] > best[1] - best[0]:
                best = cur
        else:
            cur = None
    return best


class BoxBook:
    # C-round-1 flagged extensions (BOX-LAB X4 port, R34 §34.7): every
    # change sits behind its own box.* flag, all defaults OFF — with
    # all flags at default the object stream must equal the parent's.
    # Constants stay in code; kept values move to params_v1_1.json via
    # the build lane.
    _WATCH_MATURE = 24      # bars: a persisting watch emits w/o break
    _WATCH_MAXAGE = 144     # bars: a watch that never resolves dies
    _NEST_IOU = 0.5         # same-episode dedup window IoU (lab r37)
    _ANCHOR_CAP = 8         # dense pivot-anchor variants (lab r42)
    _REEMIT = 6             # bars between repeat "proposed" log rows

    def __init__(self, eng):
        self.e = eng
        self._asia = None          # {"hi","lo","start","ro"} tracker
        self._asia_day = None
        self._watch = {}           # watch_birth registry (flag OFF: empty)
        self._wseq = 0
        self._emit_log = {}        # proposed-row reemit throttle

    # ---------------- birth candidates --------------------------- #

    def on_pivot(self, i, piv):
        """Anchored window scan: windows ending at the new pivot,
        starting at each of the last max_legs_back pivot extremes."""
        e = self.e
        if gates.hard_block(e.bars[i]["cet_min"]):
            return
        book = e.book
        # windows anchor on structural (theta2) extremes only — micro
        # anchors make windows that are just noise (DN_BOX: the buildup
        # is measured on the structural stream).
        al = [p for p in book.recent(i) if book.is_structural(p)]
        if len(al) < 3:
            return
        # one buildup per touch (DN_BOX): the contained run through the
        # touch is determined by the band, not by where the scan window
        # starts — s only bounds the run's left extent, so take the
        # farthest leg-back start once instead of proposing one
        # candidate per window start (multi-start flooded the pool with
        # near-duplicate bands of the same congestion).
        k = min(len(al), e.p["box"]["max_legs_back"])
        self._propose_window(i, al[-k].t_ext, piv=piv)

    def _propose_window(self, i, s, route="cluster_range", piv=None):
        """D9 buildup construction: seed the last min_build_bars bars
        ending at the confirming touch (piv.t_ext), grow the contained
        run left while closes stay inside the seed band (bounded by s),
        then rebuild clustered edges on the buildup only.

        The earlier scheme clustered extremes over a whole pivot-leg
        window: older congestion episodes and post-buildup excursions
        leaked in, so edges landed on outer poke clusters (44-pip
        boxes vs golden ~13).  Golden buildups are compact (TUNE:
        median 7 bars, p90 28, max 45)."""
        e = self.e
        bp = e.p["box"]
        abr = e.abr[i]
        eps = max(bp["eps_pips"], bp["eps_abr_frac"] * abr)
        tease = max(bp["tease_tol_pips"], bp["tease_tol_abr_frac"] * abr)
        k = bp["min_build_bars"]
        be = piv.t_ext if piv is not None else i
        if be - s + 1 < k or be > i:
            return None
        W = e.bars[s:i + 1]
        tops = bucket_merge([b["h"] for b in W], eps,
                            bp["min_company"]) or []
        bots = bucket_merge([b["l"] for b in W], eps,
                            bp["min_company"]) or []
        lev = bp.get("level_edges")
        # 1) anchor edge = the defended cluster the confirming pivot
        #    touched: most extreme cluster on its side still within
        #    tease_tol of the touch (the touch may poke past it).
        #    This is what keeps excursion clusters from defining the
        #    edge — a touch 20 pips inside a 44-pip band is not a
        #    touch of that band's edge.
        anch, opps = None, []
        if tops and bots:
            if piv is not None:
                if piv.dir > 0:
                    cand = [max(c) for c in tops
                            if piv.price - tease <= max(c) <=
                            piv.price + eps]
                    if not cand:
                        if not lev:
                            return None
                    else:
                        anch = max(cand)
                        opps = sorted(
                            (min(c) for c in bots if min(c) < anch),
                            reverse=True)
                else:
                    cand = [min(c) for c in bots
                            if piv.price - eps <= min(c) <=
                            piv.price + tease]
                    if not cand:
                        if not lev:
                            return None
                    else:
                        anch = min(cand)
                        opps = sorted(
                            max(c) for c in tops if max(c) > anch)
        elif not lev:
            return None
        # 2) opposite edge: scan clusters from tightest (nearest the
        #    anchor) outward; the first band yielding a contained run
        #    of >=k closes through the touch bar wins.  Golden prefers
        #    the tight core of the congestion, not its widest
        #    self-consistent envelope.
        picked = None
        lv_used = False
        for opp in opps:
            top, bot = (anch, opp) if piv is None or piv.dir > 0 \
                else (opp, anch)
            band = self._buildup_run(s, i, be, bot, top, k)
            if band is not None:
                picked = band
                break
        if picked is None and piv is not None and lev:
            # level_edges (R42 probe): the author's box edge is often an
            # OLD confirmed level — measured median edge-pivot t_ext is
            # ~7h before build_start — which window clustering can never
            # emit.  When no clustered band qualifies, retry with pivot
            # levels formed before the proposal window.
            ups = sorted(p.price for p in e.book.seq
                         if p.dir > 0 and p.t_conf <= i and
                         p.t_ext < s)
            dns = sorted(p.price for p in e.book.seq
                         if p.dir < 0 and p.t_conf <= i and
                         p.t_ext < s)
            if piv.dir > 0:
                lv = [x for x in ups
                      if piv.price - tease <= x <= piv.price + eps]
                anch = min(lv, key=lambda x: abs(x - piv.price)) \
                    if lv else None
                opps = sorted((x for x in dns
                               if anch is not None and x < anch),
                              reverse=True)[:6]
            else:
                lv = [x for x in dns
                      if piv.price - eps <= x <= piv.price + tease]
                anch = min(lv, key=lambda x: abs(x - piv.price)) \
                    if lv else None
                opps = sorted(x for x in ups
                              if anch is not None and x > anch)[:6]
            if anch is not None:
                for opp in opps:
                    top, bot = (anch, opp) if piv.dir > 0 \
                        else (opp, anch)
                    band = self._buildup_run(s, i, be, bot, top, k,
                                             fix_edges=True)
                    if band is not None:
                        picked = band
                        lv_used = True
                        break
        if picked is None:
            return None
        bs, be2, top, bot, nt, nb = picked
        rbars = e.bars[bs:be2 + 1]
        h = top - bot
        if not (bp["height_min_abr"] * abr <= h <=
                bp["height_max_abr"] * abr) or \
                not (bp["height_min_pips"] <= h <=
                     bp["height_max_pips"]):
            return None
        # containment: >=contain_min_frac of buildup closes inside
        inside = sum(bot <= x["c"] <= top for x in rbars)
        if inside / len(rbars) < bp["contain_min_frac"]:
            return None
        # prior state: >=1 structural pivot pair alternating sides
        # within the candidate span (the sideways sequence that built
        # the box — wider than the tight contained run).  lv bands carry
        # their own structure evidence (two old confirmed levels), so
        # the pivot-starved buildup is allowed through under the flag.
        if not lv_used:
            st = [p for p in e.book.structural()
                  if s <= p.t_ext <= i and p.t_conf <= i]
            if not (any(p.dir > 0 for p in st) and
                    any(p.dir < 0 for p in st)):
                return None
        # the touch must still sit on the rebuilt edge (it may drift
        # inward as the run tightens)
        if piv is not None and \
                abs(piv.price - (top if piv.dir > 0 else bot)) > tease:
            return None
        # don't re-propose an existing box's own edges
        tol = e._tol()
        for o in e.active("BOX"):
            g = o.geometry
            if abs(g["top"] - top) <= tol and \
                    abs(g["bottom"] - bot) <= tol:
                if bp.get("dedup_iou"):
                    # X4 #3 (r36/r37): same edges alone do not make the
                    # same episode — a wrong-window incumbent must not
                    # preempt a right-window band.  Only a high window
                    # overlap still dedups.
                    a0, a1 = self._obj_window(o, i)
                    if self._win_iou(bs, be2, a0, a1) < self._NEST_IOU:
                        continue
                return o
        geom = {"top": round(top, 2), "bottom": round(bot, 2),
                "t0": bs, "t1": be2}
        anch = [p for p in e.book.alive() if bs <= p.t_ext <= be2]
        prom = sum(p.prom for p in anch) / len(anch) / abr if anch \
            else 0.0
        feats = {"touches": nt + nb, "prom_abr": round(prom, 2),
                 "contain": round(inside / len(rbars), 2)}
        if lv_used:
            feats["lv_edge"] = 1
        feats.update(self._barrier_feats(
            i, top, bot, bs, be2, piv.dir if piv is not None else 0))
        meta = {"build_start": bs, "build_end": be2}
        if bp.get("rank_score"):
            rs, deep = self._rank_score(i, top, bot, bs, be2, feats)
            feats["box_rank"] = rs
            feats["deeper_lv"] = deep
            meta["box_rank"] = rs
        c = Candidate("BOX", route, geom, i, feats=feats,
                      meta=meta,
                      ttl=self._ttl())
        if bp.get("watch_birth"):
            # X4 #1: deferred birth — log the proposal (oracle stream)
            # and register the watch; the birth fires at the break /
            # maturity via _watch_update in maintain().
            self._log_proposed(c, i)
            self._watch_add(c, i)
        else:
            e.salience.propose(c)
        self._variants(i, s, bs, be2, top, bot, feats)
        return c

    def _buildup_run(self, s, i, be, bot, top, k, fix_edges=False):
        """The D9 buildup for a candidate band: the contiguous run of
        closes inside [bot, top] containing the touch bar `be`,
        extended through the confirm bar `i` (post-touch rejection
        bars are part of the congestion evidence).  Edges are rebuilt
        on the run and the run re-taken until the band stabilises;
        returns (bs, be2, top, bot, nt, nb) or None.

        fix_edges (level_edges path): the seeded edges ARE the levels —
        skip the rebuild, keep (top, bot) as passed; nt/nb count the
        cluster nearest each seeded edge."""
        e = self.e
        bp = e.p["box"]
        eps = max(bp["eps_pips"], bp["eps_abr_frac"] * e.abr[i])
        for _ in range(1 if fix_edges else 3):
            bs = be
            while bs - 1 >= s and bot <= e.bars[bs - 1]["c"] <= top:
                bs -= 1
            be2 = be
            while be2 + 1 <= i and bot <= e.bars[be2 + 1]["c"] <= top:
                be2 += 1
            if be2 - bs + 1 < k:
                return None
            rbars = e.bars[bs:be2 + 1]
            tops = bucket_merge([x["h"] for x in rbars], eps,
                                bp["min_company"])
            bots = bucket_merge([x["l"] for x in rbars], eps,
                                bp["min_company"])
            if not tops or not bots:
                if fix_edges:
                    tops, bots = tops or [], bots or []
                    break
                return None
            if fix_edges:
                break
            t2 = max(max(c) for c in tops)
            b2 = min(min(c) for c in bots)
            if t2 == top and b2 == bot:
                break
            top, bot = t2, b2
        if not fix_edges:
            # final run under the stabilised band
            bs = be
            while bs - 1 >= s and bot <= e.bars[bs - 1]["c"] <= top:
                bs -= 1
            be2 = be
            while be2 + 1 <= i and bot <= e.bars[be2 + 1]["c"] <= top:
                be2 += 1
            if be2 - bs + 1 < k:
                return None
            rbars = e.bars[bs:be2 + 1]
            tops = bucket_merge([x["h"] for x in rbars], eps,
                                bp["min_company"])
            bots = bucket_merge([x["l"] for x in rbars], eps,
                                bp["min_company"])
            if not tops or not bots:
                return None
        nt = len(max(tops, key=lambda c: max(c))) if tops else 0
        nb = len(min(bots, key=lambda c: min(c))) if bots else 0
        if fix_edges:
            nt = max((len(c) for c in tops
                      if abs(max(c) - top) <= eps), default=0)
            nb = max((len(c) for c in bots
                      if abs(min(c) - bot) <= eps), default=0)
        return bs, be2, top, bot, nt, nb

    def _barrier_feats(self, i, top, bot, bs, be2, anchor_dir):
        """Barrier/buildup evidence for the score (Ruling 9a.2; RT1
        Box/Barrier/Buildup: Volman draws the box that is a buildup
        pressed against a barrier).  All causal at bar i.

        anchor_dir: +1 top edge is the defended barrier, -1 bottom,
        0 unknown (scan route — both edges tested).
        """
        e = self.e
        abr = max(e.abr[i], 1e-9)
        tease = max(e.p["box"]["tease_tol_pips"],
                    e.p["box"]["tease_tol_abr_frac"] * abr)

        def _near_structure(edge):
            # an earlier pivot extreme predating the buildup
            for p in e.book.seq:
                if p.t_ext < bs and abs(p.price - edge) <= tease:
                    return True
            # a live level's price
            for o in e.active():
                pr = o.geometry.get("price")
                if pr is not None and abs(pr - edge) <= tease:
                    return True
            # the day's high/low printed before the buildup
            if bs > 0:
                pre_hi = max(x["h"] for x in e.bars[:bs])
                pre_lo = min(x["l"] for x in e.bars[:bs])
                if abs(edge - pre_hi) <= tease or \
                        abs(edge - pre_lo) <= tease:
                    return True
            return False

        edges = [top] if anchor_dir > 0 else \
            ([bot] if anchor_dir < 0 else [top, bot])
        barrier = 1.0 if any(_near_structure(ed) for ed in edges) \
            else 0.0

        rbars = e.bars[bs:be2 + 1]
        pressure = 0.0
        if len(rbars) >= 3 and anchor_dir:
            xs = np.arange(len(rbars), dtype=float)
            if anchor_dir > 0:
                # defended ceiling: lows rising toward it
                sl = np.polyfit(xs,
                                [x["l"] for x in rbars], 1)[0]
                pressure = sl / abr
            else:
                # defended floor: highs falling toward it
                sl = np.polyfit(xs,
                                [x["h"] for x in rbars], 1)[0]
                pressure = -sl / abr

        compression = float(np.median(
            [x["h"] - x["l"] for x in rbars]) / abr)

        ema_guide = 0.0
        if len(rbars) >= 3:
            d0 = abs(rbars[0]["c"] - e.ema[rbars[0]["i"]])
            d1 = abs(rbars[-1]["c"] - e.ema[rbars[-1]["i"]])
            ema_guide = (d0 - d1) / abr    # + = closing toward the EMA
        return {"barrier": barrier,
                "pressure": round(pressure, 3),
                "compression": round(compression, 3),
                "ema_guide": round(ema_guide, 3)}

    # ------------- C-round-1 flagged helpers (boxlab X4) ---------- #

    @staticmethod
    def _win_iou(a0, a1, b0, b1):
        """Interval IoU on bar indices (the same-episode window test,
        lab r37)."""
        inter = max(0.0, min(a1, b1) - max(a0, b0))
        union = max(a1 - a0, 0.0) + max(b1 - b0, 0.0) - inter
        return inter / union if union > 0 else 0.0

    def _obj_window(self, o, i):
        """A live object's containment window for dedup tests:
        recorded meta_build_start..meta_build_end, else drawn span."""
        g = o.geometry
        a = g.get("meta_build_start", g.get("t0", o.t_left))
        b = g.get("meta_build_end", g.get("t1",
                     o.t_right if o.t_right is not None else i))
        return a, b

    def _rank_score(self, i, top, bot, bs, be2, feats):
        """box.rank_score — the lab r33 ranker ported to production
        features.  OUTPUT FIELD ONLY: it never gates, orders or blocks
        anything in this file; the build lane wires it into selection
        (§34.8 item 2).  Surviving lab terms (X4): edge prominence
        (prom_min/abr), containment, touches, deeper_lv (a defended
        pivot deeper than an edge within ~1 ABR — window-independent
        envelope test), and anti-barrier (identity barrier is
        anti-predictive, r33, fold-stable).  hgt / edge_gap /
        deep_piv / positive barrier were falsified in-lab and are
        deliberately absent (R20 §20.2).  Returns (score, deeper)."""
        e = self.e
        abr = max(e.abr[i] if i < len(e.abr) else 5.0, 1e-9)
        tol = e._tol()

        def _edge_prom(edge):
            best = 0.0
            for p in e.book.seq:
                if p.t_conf <= i and bs <= p.t_ext <= be2 and \
                        abs(p.price - edge) <= tol:
                    best = max(best, p.prom)
            return best / abr

        rng = max(abr, 6.0)
        deeper = 0
        for p in e.book.structural():
            if p.t_conf > i:
                continue
            if p.dir > 0 and top < p.price <= top + rng:
                deeper += 1
            elif p.dir < 0 and bot - rng <= p.price < bot:
                deeper += 1
        score = (min(_edge_prom(top), _edge_prom(bot))
                 + feats.get("contain", 0.0)
                 + 0.25 * feats.get("touches", 0.0)
                 - 0.75 * feats.get("barrier", 0.0)
                 - 1.5 * deeper)
        return round(score, 3), deeper

    def _log_proposed(self, cand, i):
        """Watch-mode proposal stream: the band qualified now, so the
        proposal is real even though the birth is deferred — same
        semantics as the lab cand stream (the oracle needs it)."""
        e = self.e
        tol = e._tol()
        g = cand.geom
        key = (cand.route, round(g["top"] / tol),
               round(g["bottom"] / tol), g.get("t0"))
        if i - self._emit_log.get(key, -10 ** 9) < self._REEMIT:
            return
        self._emit_log[key] = i
        e._cand(cand.kind, i, cand.route, "proposed",
                {"t0": g.get("t0"), "t1": g.get("t1"),
                 "top": g.get("top"), "bottom": g.get("bottom")},
                **cand.feats)

    def _watch_add(self, cand, i):
        """One watch per congestion episode (X4 #1 + #3).  Same edges
        (within tol) AND window IoU >= _NEST_IOU = same episode: the
        watch keeps its best-scoring geometry and accumulates distinct
        build_start anchors; a genuinely different band gets its own
        watch instead of being preempted (lab r36/r37)."""
        e = self.e
        tol = e._tol()
        t, b = cand.geom["top"], cand.geom["bottom"]
        t0 = cand.geom.get("t0", cand.t0)
        for w in self._watch.values():
            g = w["geom"]
            if abs(g["top"] - t) <= tol and abs(g["bottom"] - b) <= tol \
                    and self._win_iou(t0, cand.geom.get("t1", i),
                                      g["t0"], g.get("t1", i)) \
                    >= self._NEST_IOU:
                w["t0s"].add(t0)
                if cand.feats.get("box_rank", 0.0) > \
                        w["feats"].get("box_rank", 0.0):
                    w["geom"] = dict(cand.geom)
                    w["feats"] = dict(cand.feats)
                    w["meta"] = dict(cand.meta)
                    w["route"] = cand.route
                w["lastq"] = i
                return w
        self._wseq += 1
        key = (round(t / tol), round(b / tol), t0, self._wseq)
        self._watch[key] = {"geom": dict(cand.geom),
                            "feats": dict(cand.feats),
                            "meta": dict(cand.meta),
                            "route": cand.route, "firstq": i,
                            "lastq": i, "t0s": {t0}}
        return self._watch[key]

    def _watch_update(self, i):
        """Deferred birth (X4 #1): a watch emits its candidate into
        salience when the band resolves — first close beyond an edge,
        the author's draw moment (X2 anatomy: golden build_end ~ the
        first decisive close) — or after _WATCH_MATURE bars of
        unbroken qualification.  One cand per recorded anchor start:
        the funnel's +-20-min build_start rule needs the t0 shots;
        equal-score same-band cands suppress in salience, so only one
        inks.  Emitted geometry is frozen from the watch's best
        qualification (r35: edges freeze at the draw moment)."""
        e = self.e
        b = e.bars[i]
        tol = e._tol()
        for k in list(self._watch):
            w = self._watch[k]
            g = w["geom"]
            top, bot = g["top"], g["bottom"]
            broke = b["c"] > top + tol or b["c"] < bot - tol
            aged = i - w["firstq"] >= self._WATCH_MATURE
            if not (broke or aged):
                if i - w["lastq"] > self._WATCH_MAXAGE:
                    del self._watch[k]
                continue
            for n, t0 in enumerate(sorted(w["t0s"])[-self._ANCHOR_CAP:]):
                geom = {"top": top, "bottom": bot,
                        "t0": t0, "t1": i}
                meta = dict(w["meta"])
                meta["build_start"] = t0
                meta["build_end"] = i    # resolution bar ~= golden
                                         # build_end (X1 audit)
                e.salience.propose(Candidate(
                    "BOX", "%s_w%d" % (w["route"], n), geom, i,
                    feats=w["feats"], meta=meta,
                    ttl=self._ttl()))
            del self._watch[k]

    def _ttl(self):
        """Candidate TTL under box.wait_ttl (R38 anatomy: 26/42 right
        proposals die rate_limited because ttl 24 < rate_window 72 —
        a blocked cand expires before its first retry, and
        salience.rate_blocked_extend only extends to the blocking
        birth + 1, not to the window roll).  box.wait_ttl gives a box
        proposal enough patience to survive one full rate window.
        Flag OFF: the stock cand_ttl_bars."""
        e = self.e
        sp = e.p["salience"]
        if e.p["box"].get("wait_ttl"):
            return sp["rate_window_bars"] + sp["cand_ttl_bars"]
        return sp["cand_ttl_bars"]

    def _variants(self, i, s, bs, be2, top, bot, feats):
        """Oracle-candidate variants of one qualifying band
        (X4 #5-#7).  dense_anchors: extra build_start anchors at
        recent in-run pivot bars (r42).  leg_edges: the running DC-leg
        extreme as a provisional edge (r43, levellab 'leg' origin).
        wick_edges: p99/p01 wick extremes (r47) — proposal stream
        ONLY, never a born object until defence evidence exists
        (X4 honest limit)."""
        e = self.e
        bp = e.p["box"]
        tol = e._tol()
        watch = bp.get("watch_birth")
        ttl = self._ttl()
        meta_r = {"box_rank": feats["box_rank"]} \
            if "box_rank" in feats else {}
        if bp.get("dense_anchors"):
            anch = sorted({p.t_ext for p in e.book.seq
                           if p.t_conf <= i and
                           bs < p.t_ext <= be2})[-self._ANCHOR_CAP:]
            for n, a in enumerate(anch):
                c2 = Candidate(
                    "BOX", "cluster_range_a%d" % n,
                    {"top": top, "bottom": bot, "t0": a, "t1": be2}, i,
                    feats=feats,
                    meta=dict({"build_start": a, "build_end": be2},
                              **meta_r), ttl=ttl)
                if watch:
                    self._watch_add(c2, i)
                else:
                    e.salience.propose(c2)
        if bp.get("leg_edges") and e.dc.ext_price is not None:
            ext = e.dc.ext_price
            t2, b2 = top, bot
            if e.dc.dir > 0 and ext > top + tol:
                t2 = ext
            elif e.dc.dir < 0 and ext < bot - tol:
                b2 = ext
            if (t2, b2) != (top, bot) and \
                    bp["height_min_pips"] <= t2 - b2 <= \
                    bp["height_max_pips"]:
                c2 = Candidate(
                    "BOX", "cluster_range_leg",
                    {"top": t2, "bottom": b2, "t0": bs, "t1": be2}, i,
                    feats=feats,
                    meta=dict({"build_start": bs, "build_end": be2},
                              **meta_r), ttl=ttl)
                if watch:
                    self._watch_add(c2, i)
                else:
                    e.salience.propose(c2)
        if bp.get("wick_edges"):
            seg = e.bars[bs:i + 1]
            if len(seg) >= 3:
                whi = float(np.percentile([x["h"] for x in seg], 99))
                wlo = float(np.percentile([x["l"] for x in seg], 1))
                if wlo < bot - 0.5 or whi > top + 0.5:
                    if bp.get("wick_birth") and \
                            bp["height_min_pips"] <= whi - wlo <= \
                            bp["height_max_pips"]:
                        # R38 §38.3.2 born-side arm: the wick-edge cand
                        # joins the pool — it may birth only by
                        # out-scoring the box field (top-in-family).
                        c2 = Candidate(
                            "BOX", "cluster_range_wick",
                            {"top": whi, "bottom": wlo,
                             "t0": bs, "t1": be2}, i,
                            feats=feats,
                            meta=dict({"build_start": bs,
                                       "build_end": be2}, **meta_r),
                            ttl=ttl)
                        if watch:
                            self._watch_add(c2, i)
                        else:
                            e.salience.propose(c2)
                    else:
                        e._cand("BOX", i, "cluster_range_wick",
                                "proposed",
                                {"t0": bs, "t1": be2, "top": whi,
                                 "bottom": wlo}, **feats)
        if bp.get("kde_edges"):
            seg = e.bars[bs:i + 1]
            if len(seg) >= 5:
                hi = np.array([x["h"] for x in seg])
                lo = np.array([x["l"] for x in seg])
                khi = self._kde_peak(
                    hi[hi >= np.percentile(hi, 90)], tol)
                klo = self._kde_peak(
                    lo[lo <= np.percentile(lo, 10)], tol)
                if khi is not None and klo is not None and \
                        (klo < bot - 0.5 or khi > top + 0.5) and \
                        bp["height_min_pips"] <= khi - klo <= \
                        bp["height_max_pips"]:
                    geom = {"t0": bs, "t1": be2, "top": khi,
                            "bottom": klo}
                    if bp.get("wick_birth"):
                        # same born rule as wick_edges: births only by
                        # ranking top in the box family at the slot.
                        c2 = Candidate(
                            "BOX", "cluster_range_kde", geom, i,
                            feats=feats,
                            meta=dict({"build_start": bs,
                                       "build_end": be2}, **meta_r),
                            ttl=ttl)
                        if watch:
                            self._watch_add(c2, i)
                        else:
                            e.salience.propose(c2)
                    else:
                        e._cand("BOX", i, "cluster_range_kde",
                                "proposed", geom, **feats)

    @staticmethod
    def _kde_peak(vals, bw):
        """Wick-tip density edge (R38 §38.3.3, WEB_RESEARCH_C1 #2):
        the price where tail wicks concentrate — a Gaussian-KDE argmax
        over the tail tips, so a lone spike cannot pull the edge out
        to its own extreme the way a percentile does."""
        if vals is None or not len(vals):
            return None
        vals = np.asarray(vals, dtype=float)
        d = np.exp(-0.5 * ((vals[:, None] - vals[None, :]) / bw) ** 2)
        return float(vals[int(np.argmax(d.sum(1)))])

    # ---------------- congestion scan ----------------------------- #

    def congestion_scan(self, i):
        """Bar-driven birth route for tight buildups that never confirm
        a pivot inside (9.44a-class false negative, DN_BOX §6): the
        last min_build_bars closes are already inside a defended band.
        The second-touch trigger is implicit — both edge clusters need
        minPts company within the seed window.  Same geometry path as
        the pivot route: seed band -> contained run -> rebuilt edges."""
        e = self.e
        bp = e.p["box"]
        b = e.bars[i]
        if gates.hard_block(b["cet_min"]) or \
                b["cet_min"] < bp["asia_end_cet"]:
            return
        abr = e.abr[i]
        eps = max(bp["eps_pips"], bp["eps_abr_frac"] * abr)
        k = bp["min_build_bars"]
        if i + 1 < 2 * k:
            return
        # don't rescan while a live box already covers this band
        for o in e.active("BOX"):
            g = o.geometry
            if g["bottom"] <= b["c"] <= g["top"]:
                if bp.get("dedup_iou"):
                    a0, a1 = self._obj_window(o, i)
                    if self._win_iou(
                            max(0, i - bp.get("scan_lookback_bars", 45)),
                            i, a0, a1) < self._NEST_IOU:
                        continue   # different episode — don't preempt
                return
        s = max(0, i - bp.get("scan_lookback_bars", 45))
        seed = e.bars[i - k + 1:i + 1]
        tops = bucket_merge([x["h"] for x in seed], eps,
                            bp["min_company"]) or []
        bots = bucket_merge([x["l"] for x in seed], eps,
                            bp["min_company"]) or []
        band = None
        lv_band = False
        cong_band = False
        if tops and bots:
            band = self._buildup_run(s, i, i,
                                     min(min(c) for c in bots),
                                     max(max(c) for c in tops), k)
        if band is None and bp.get("level_edges"):
            # level_edges on the scan route (R42): the author's edges
            # sit INSIDE the wick envelope on old confirmed levels —
            # the extreme seed is too tall / its run never contains.
            # Seed bands from pivot levels bracketing the seed closes.
            clo = min(x["c"] for x in seed)
            chi = max(x["c"] for x in seed)
            ups = sorted({p.price for p in e.book.seq
                          if p.dir > 0 and p.t_conf <= i and
                          p.t_ext < s})
            dns = sorted({p.price for p in e.book.seq
                          if p.dir < 0 and p.t_conf <= i and
                          p.t_ext < s})
            for t2 in [x for x in ups if x >= chi - 0.5][:4]:
                for b2 in sorted((x for x in dns
                                  if x <= clo + 0.5), reverse=True)[:4]:
                    if t2 - b2 < bp["height_min_pips"]:
                        continue
                    band = self._buildup_run(s, i, i, b2, t2, k,
                                             fix_edges=True)
                    if band is not None:
                        lv_band = True
                        break
                if band is not None:
                    break
        if band is None and bp.get("cong_trigger"):
            band = self._cong_run(i, s, k)
            cong_band = band is not None
        if band is None:
            return
        bs, be2, top, bot, nt, nb = band
        rbars = e.bars[bs:be2 + 1]
        h = top - bot
        if not (bp["height_min_abr"] * abr <= h <=
                bp["height_max_abr"] * abr) or \
                not (bp["height_min_pips"] <= h <=
                     bp["height_max_pips"]):
            return
        inside = sum(bot <= x["c"] <= top for x in rbars)
        if inside / len(rbars) < bp["contain_min_frac"]:
            return
        if not (lv_band or cong_band):
            st = [p for p in e.book.structural()
                  if s <= p.t_ext <= i and p.t_conf <= i]
            if not (any(p.dir > 0 for p in st) and
                    any(p.dir < 0 for p in st)):
                return
        tol = e._tol()
        for o in e.active("BOX"):
            g = o.geometry
            if abs(g["top"] - top) <= tol and \
                    abs(g["bottom"] - bot) <= tol:
                if bp.get("dedup_iou"):
                    a0, a1 = self._obj_window(o, i)
                    if self._win_iou(bs, be2, a0, a1) < self._NEST_IOU:
                        continue
                return
        geom = {"top": round(top, 2), "bottom": round(bot, 2),
                "t0": bs, "t1": be2}
        anch = [p for p in e.book.alive() if bs <= p.t_ext <= be2]
        prom = sum(p.prom for p in anch) / len(anch) / abr if anch \
            else 0.0
        feats = {"touches": nt + nb, "prom_abr": round(prom, 2),
                 "contain": round(inside / len(rbars), 2)}
        if lv_band:
            feats["lv_edge"] = 1
        if cong_band:
            feats["cong"] = 1
        feats.update(self._barrier_feats(i, top, bot, bs, be2, 0))
        meta = {"build_start": bs, "build_end": be2}
        if bp.get("rank_score"):
            rs, deep = self._rank_score(i, top, bot, bs, be2, feats)
            feats["box_rank"] = rs
            feats["deeper_lv"] = deep
            meta["box_rank"] = rs
        c = Candidate("BOX", "congestion_scan", geom, i,
                      feats=feats, meta=meta,
                      ttl=self._ttl())
        if bp.get("watch_birth"):
            self._log_proposed(c, i)
            self._watch_add(c, i)
        else:
            e.salience.propose(c)
        self._variants(i, s, bs, be2, top, bot, feats)

    def _cong_run(self, i, s, k):
        """R44 §44.3 pivot-free congestion trigger.  51/51 no-edge
        goldens have zero structural pivots during buildup, so
        on_pivot never fires while the author's box forms.  Every
        bar, take the longest run ending at i whose h-l envelope
        stays within cong_h_abr * ABR; when it reaches cong_min_bars
        the band qualifies on overlap alone — no pivot requirement.
        Edges are the run's own extremes, snapped to an old confirmed
        level within tolerance under box.level_edges (the author's
        edges sit on prior-session structure ~7h back).

        N/k provenance (TUNE goldens with both build times, n=37):
        buildup len p10=4 p25=5 med=10 p75=20 p90=31 bars (5m);
        envelope/ABR24 p25=2.3 med=2.9 p75=4.0 p90=4.7.
        Defaults cong_min_bars=6 (~p25), cong_h_abr=4.0 (~p75)."""
        e = self.e
        bp = e.p["box"]
        abr = e.abr[i]
        cap = bp.get("cong_h_abr", 4.0) * abr
        hi, lo, j = -1e18, 1e18, i
        while j > s:
            x = e.bars[j]
            h2 = hi if hi > x["h"] else x["h"]
            l2 = lo if lo < x["l"] else x["l"]
            if h2 - l2 > cap:
                break
            hi, lo = h2, l2
            j -= 1
        bs = j + 1
        if i - bs + 1 < bp.get("cong_min_bars", 6):
            return None
        top, bot = hi, lo
        if bp.get("level_edges"):
            tol = e._tol()
            ups = [p.price for p in e.book.seq
                   if p.dir > 0 and p.t_conf <= i and p.t_ext < bs]
            dns = [p.price for p in e.book.seq
                   if p.dir < 0 and p.t_conf <= i and p.t_ext < bs]
            ut = [x for x in ups if abs(x - top) <= tol]
            bt = [x for x in dns if abs(x - bot) <= tol]
            if ut:
                top = min(ut, key=lambda x: abs(x - top))
            if bt:
                bot = min(bt, key=lambda x: abs(x - bot))
        return self._buildup_run(s, i, i, bot, top, k, fix_edges=True)

    def propose_context_range(self, i):
        """CONTEXT_RANGE: coarse envelope of structural pivots over the
        trailing window, when no box already covers it (dedupe by
        containment).  Context class, dotted budget."""
        e = self.e
        win = e.p["window_bars"]
        st = e.book.structural()
        st = [p for p in st if p.t_conf <= i]
        if len(st) < 2:
            return
        lows = [p.price for p in st if p.dir < 0]
        highs = [p.price for p in st if p.dir > 0]
        if not lows or not highs:
            return
        lo, hi = min(lows), max(highs)
        h = hi - lo
        abr = e.abr[i]
        if h < 2.5 * abr or h > 7.0 * abr:
            return
        for o in e.active("BOX") + e.active("CONTEXT_RANGE"):
            g = o.geometry
            if g["bottom"] <= lo <= hi <= g["top"] or \
                    (lo <= g["bottom"] and hi >= g["top"]):
                return
        t0 = min(p.t_ext for p in st)
        geom = {"top": round(hi, 2), "bottom": round(lo, 2),
                "t0": t0, "t1": i}
        c = Candidate("CONTEXT_RANGE", "structural_envelope", geom, i,
                      feats={"touches": len(st),
                             "prom_abr": sum(p.prom for p in st)
                             / len(st) / abr},
                      ttl=e.p["salience"]["cand_ttl_bars"])
        e.salience.propose(c)

    # ---------------- Asia / RANGE_OPEN --------------------------- #

    def asia_update(self, i):
        """00:00-08:00 CET running range tracker.  RANGE_OPEN itself is
        a context candidate (never auto-drawn); conversion proposes a
        signal-class box."""
        e = self.e
        b = e.bars[i]
        bp = e.p["box"]
        day = b["t"] // 86400
        if self._asia is None and self._asia_day != day and \
                b["cet_min"] <= bp["asia_end_cet"]:
            self._asia = {"hi": b["h"], "lo": b["l"], "start": i,
                          "ro": None, "proposed": False}
        a = self._asia
        if a is None:
            return
        if b["cet_min"] <= bp["asia_end_cet"]:
            a["hi"] = max(a["hi"], b["h"])
            a["lo"] = min(a["lo"], b["l"])
            ro = a["ro"]
            if ro is not None and ro.state == "ACTIVE":
                ro.geometry["top"] = round(a["hi"], 2)
                ro.geometry["bottom"] = round(a["lo"], 2)
                ro.geometry["t1"] = i
            elif i - a["start"] >= 2 and not a["proposed"]:
                geom = {"top": round(a["hi"], 2),
                        "bottom": round(a["lo"], 2),
                        "t0": a["start"], "t1": i}
                c = Candidate("RANGE_OPEN", "asia_range", geom, i,
                              feats={"touches": 0, "prom_abr": 0.0},
                              meta={"live_tracker": True}, ttl=96)
                e.salience.propose(c)
                a["proposed"] = True
        else:
            # post-window (>=08:00): the Asian range converts to the
            # day's box — a lifecycle transition of existing ink, not a
            # new claim.  If a covering cluster box already exists it
            # absorbs the role; a drawn RANGE_OPEN converts in place;
            # only an undrawn range goes through salience.
            a = self._asia
            ro = a["ro"]
            thin = (a["hi"] - a["lo"]) <= bp["asia_thin_pips"]
            tol = 2 * e._tol()
            covering = None
            for o in e.active("BOX"):
                g = o.geometry
                if abs(g["top"] - a["hi"]) <= tol and \
                        abs(g["bottom"] - a["lo"]) <= tol:
                    covering = o
                    break
            if covering is not None:
                covering.geometry["asia_convert"] = True
                covering.event(i, "asia_convert",
                               "absorbs asia range %.1f-%.1f" %
                               (a["lo"], a["hi"]))
                if thin:
                    covering.event(i, "thin_range",
                                   "false-break prone (9.40a)")
                if ro is not None and ro.state == "ACTIVE":
                    ro.close(i, "asia_absorbed")
            elif ro is not None and ro.state == "ACTIVE":
                g = ro.geometry
                ro.type = "BOX"
                ro.style = "solid"
                ro.why = "asia_session"
                g["top"] = round(a["hi"], 2)
                g["bottom"] = round(a["lo"], 2)
                g["meta_build_start"] = a["start"]
                g["meta_build_end"] = i
                g["meta_thin"] = thin
                if bp.get("rank_score"):
                    rs, _dp = self._rank_score(
                        i, g["top"], g["bottom"], a["start"], i, {})
                    g["meta_box_rank"] = rs
                ro.priority = 1
                ro.event(i, "asia_convert", "range -> box")
                if thin:
                    ro.event(i, "thin_range", "false-break prone (9.40a)")
            else:
                geom = {"top": round(a["hi"], 2),
                        "bottom": round(a["lo"], 2),
                        "t0": a["start"], "t1": i}
                # the session range's defendedness = confirmed pivot
                # extremes contained inside it during the session
                n_t = sum(1 for p in e.book.alive()
                          if a["start"] <= p.t_ext <= i
                          and a["lo"] <= p.price <= a["hi"])
                _a_meta = {"build_start": a["start"],
                           "build_end": i, "thin": thin}
                _a_feats = {"touches": max(2, n_t),
                            "prom_abr": 0.0, "thin": thin}
                if bp.get("rank_score"):
                    rs, _dp = self._rank_score(
                        i, round(a["hi"], 2), round(a["lo"], 2),
                        a["start"], i, _a_feats)
                    _a_feats["box_rank"] = rs
                    _a_meta["box_rank"] = rs
                c = Candidate("BOX", "asia_session", geom, i,
                              feats=_a_feats, meta=_a_meta,
                              ttl=self._ttl())
                e.salience.propose(c)
            self._asia = None
            self._asia_day = day

    # ---------------- maintenance --------------------------------- #

    def maintain(self, i):
        e = self.e
        b = e.bars[i]
        tol = e._tol()
        bp = e.p["box"]
        if bp.get("watch_birth"):
            self._watch_update(i)
        for o in list(e.active("BOX")) + list(e.active("RANGE_OPEN")):
            g = o.geometry
            top, bot = g["top"], g["bottom"]
            hgt = top - bot
            dead = g.get("broke") is not None
            # touches (wick contact at the defended price)
            if abs(b["h"] - top) <= tol:
                g["touches_top"] = g.get("touches_top", 0) + 1
            if abs(b["l"] - bot) <= tol:
                g["touches_bot"] = g.get("touches_bot", 0) + 1
            if o.type == "RANGE_OPEN":
                continue
            # ---- pending break resolution (follow-through) ----
            pend = g.get("_pend_break")
            if pend is not None:
                side = pend["side"]
                edge = top if side == "up" else bot
                inside = bot <= b["c"] <= top     # strict re-entry
                if inside:
                    g["_pend_break"] = None
                    g["broke"] = None
                    o.event(i, "tease_break", side)
                    e.patterns.label(i, o, side="above" if side == "up"
                                     else "below", letter="F",
                                     price=edge)
                else:
                    # decisive: convert — the broken edge births a level
                    g["_pend_break"] = None
                    g["broke"] = side
                    g["break_bar"] = i
                    g["dead"] = True
                    o.event(i, "break_confirm", side)
                    lvl = top if side == "up" else bot
                    e.levels.spawn(i, lvl,
                                   "broken_box_edge_%s" % side,
                                   side="below" if side == "up"
                                   else "above",
                                   src=o.id, t0=o.t_left)
                    # the opposite edge is the congestion's other
                    # defended side -> congestion_edge route
                    other = bot if side == "up" else top
                    e.levels.spawn(i, other, "congestion_edge",
                                   side="above" if side == "up"
                                   else "below", src=o.id,
                                   t0=g.get("build_start", o.t_left))
                    # R21 §21.3 drawn tail: the author keeps a broken
                    # box drawn ~60min past the break (golden t1 minus
                    # build_end: med 6.2 bars, p75 17; tail measured
                    # from the break bar).  Close the object now — it
                    # leaves the live book, stops being a barrier and
                    # frees its budget slot — while t1_drawn extends
                    # the inked span through the tail, so the snapshot
                    # lens sees it at tau.
                    tb = bp.get("tail_bars", 0)
                    if tb:
                        g["t1_drawn"] = pend["bar"] + tb
                        # X4 #2: the ruler reads meta_build_end as the
                        # window end — extend it to the decisive close
                        # (golden build_end ~ first decisive close, X1),
                        # not the proposal-time run end.
                        g["meta_build_end"] = pend["bar"]
                        o.close(i, "break_tail")
                continue
            if dead:
                # already broken: no second initiation — only the
                # post-break right-edge window still runs
                if g.get("break_bar") is not None:
                    nb = i - g["break_bar"]
                    if nb >= bp["right_edge_min_bars"]:
                        near = not (b["l"] > top + 2 * tol or
                                    b["h"] < bot - 2 * tol)
                        if not near or nb >= bp["right_edge_max_bars"]:
                            o.close(i, "post_break_window")
                continue
            # ---- break initiation: close beyond edge by > tol ----
            broke_up = b["c"] > top + tol
            broke_dn = b["c"] < bot - tol
            in_hard = gates.hard_block(b["cet_min"])
            if (broke_up or broke_dn) and not in_hard:
                side = "up" if broke_up else "down"
                edge_t = g.get("touches_top" if broke_up else
                               "touches_bot", 0)
                g["_pend_break"] = {"side": side, "bar": i}
                g["broke"] = side          # provisional until confirmed
                g["break_class"] = self._break_class(
                    i, o, top if broke_up else bot, broke_up)
                if edge_t < 2:
                    g["break_class"] += "_weak"
                o.event(i, "break", "%s %s" % (side, g["break_class"]))
                continue
            # ---- tease poke: wick beyond, close back inside ----
            poke_up = b["h"] > top + tol and b["c"] <= top
            poke_dn = b["l"] < bot - tol and b["c"] >= bot
            if poke_up or poke_dn:
                depth = (b["h"] - top) if poke_up else (bot - b["l"])
                if depth <= max(bp["tease_max_abr"] * e.abr[i],
                                bp["tease_tol_pips"]):
                    side = "above" if poke_up else "below"
                    if g.get("_poke_exc") != side:
                        g["_poke_exc"] = side
                        e.patterns.label(i, o, side=side, letter="T",
                                         price=b["h"] if poke_up
                                         else b["l"])
                        o.touches.append(
                            (i, round(top if poke_up else bot, 2)))
                        o.event(i, "poke", "%s %.1f" % (side, depth))
            else:
                g["_poke_exc"] = None
            # ---- T -> F relabel (spec §3.2 relabel window) ----
            e.patterns.relabel(i, o, top, bot, hgt)

    def _break_class(self, i, o, edge, broke_up):
        """Buildup location at break (spec §3.3): resting on the edge
        -> proper; mid-range -> tease; nothing -> false."""
        recent = self.e.bars[max(0, i - 6):i]
        near = 1.2 * self.e.abr[i]
        if not recent:
            return "false"
        if broke_up:
            rest = sum(abs(x["l"] - edge) <= near for x in recent)
        else:
            rest = sum(abs(x["h"] - edge) <= near for x in recent)
        g = o.geometry
        if rest >= max(2, len(recent) // 2):
            return "proper"
        if any(abs(x["l"] - g["top"]) <= near or
               abs(x["h"] - g["bottom"]) <= near for x in recent):
            return "tease"
        return "false"

    # ---------------- re-anchor ------------------------------------ #

    def reanchor_check(self, i, piv):
        """Pre-break edge move only on a NEW aligned cluster: >=min_
        company same-side extremes within eps at a level beyond the
        frozen edge by > tol and <= reanchor_max (RT1 §6.3, Fig 3.9)."""
        e = self.e
        bp = e.p["box"]
        tol = e._tol()
        eps = max(bp["eps_pips"], bp["eps_abr_frac"] * e.abr[i])
        for o in e.active("BOX"):
            g = o.geometry
            if g.get("broke") is not None:
                continue
            if i - g.get("last_reanchor", -999) < \
                    bp["reanchor_cooldown_bars"]:
                continue
            key = "top" if piv.dir > 0 else "bottom"
            edge = g[key]
            move = (piv.price - edge) * piv.dir
            if not (tol < move <= bp["reanchor_max_pips"]):
                continue
            look = e.bars[max(0, i - 8):i + 1]
            vals = [x["h"] for x in look] if piv.dir > 0 else \
                [x["l"] for x in look]
            cl = bucket_merge(vals, eps, bp["min_company"])
            if not cl:
                continue
            best = max((max(c) for c in cl) if piv.dir > 0 else
                       (min(c) for c in cl))
            if (best - edge) * piv.dir <= tol:
                continue
            new_top = max(g["top"], best) if piv.dir > 0 else g["top"]
            new_bot = min(g["bottom"], best) if piv.dir < 0 else \
                g["bottom"]
            h = new_top - new_bot
            if not (bp["height_min_abr"] * e.abr[i] <= h <=
                    bp["height_max_abr"] * e.abr[i]):
                continue
            old = edge
            g[key] = round(best, 2)
            g["last_reanchor"] = i
            o.event(i, "re_anchor",
                    "%s %.1f->%.1f" % (key, old, g[key]))
            o.touches = [tc for tc in o.touches
                         if abs(tc[1] - old) > tol]
            if piv.dir > 0:
                g["touches_top"] = 0
            else:
                g["touches_bot"] = 0
