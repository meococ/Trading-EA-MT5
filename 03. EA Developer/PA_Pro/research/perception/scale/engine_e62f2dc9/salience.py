"""salience.py — score -> NMS -> hysteresis -> budget (DN_SALIENCE §5).

The candidate pool holds every structure the routes propose; ranking
decides ink.  No cooldowns, no ad-hoc vetoes: a candidate that loses
stays in the pool while its structure remains valid and may win later.

Budget classes (RT1 §4.4, ~3 objects / ~9 max per panel):
  signal    — BOX, PATTERN_LINE, LEVEL_CARRIED, MINI_LEVEL, BRACKET,
              SQUEEZE          (sub-budget ~3)
  context   — RANGE_OPEN, CONTEXT_RANGE, CONTEXT_LINE  (dotted, ~2)
  annot     — LABEL_TF, BAR_MARKER                     (small ink, ~4)

Score terms (all causal, bars <= t; every weight carries provenance in
params_v1_1.json):
  w_touches * touches_in_tol
  + w_span * span_min/60
  + w_prom * mean(anchor prominence)/ABR
  + w_recency * 0.5**(age/halflife)
  + w_prox * triangular peak at prox_peak_abr
  + w_session * session_prior
  - w_consumed * depth_consumed
  - mdl_penalty
"""

SIGNAL = {"BOX", "PATTERN_LINE", "LEVEL_CARRIED", "MINI_LEVEL",
          "BRACKET"}
CONTEXT = {"RANGE_OPEN", "CONTEXT_RANGE", "CONTEXT_LINE"}
# SQUEEZE is annotation ink (a marked compression between walls), not
# a barrier — it annotates the story of the walls, like LABEL_TF.
ANNOT = {"LABEL_TF", "BAR_MARKER", "SQUEEZE"}

FAMILY = {
    "BOX": "box", "RANGE_OPEN": "box", "CONTEXT_RANGE": "box",
    "PATTERN_LINE": "line", "CONTEXT_LINE": "line",
    "LEVEL_CARRIED": "level", "MINI_LEVEL": "level",
    "BRACKET": "bracket", "SQUEEZE": "squeeze",
    "LABEL_TF": "annot", "BAR_MARKER": "annot",
}


def budget_class(otype):
    if otype in SIGNAL:
        return "signal"
    if otype in CONTEXT:
        return "context"
    return "annot"


class Candidate:
    """A structure under evaluation — geometry frozen at proposal."""

    __slots__ = ("kind", "route", "geom", "born_i", "t0", "t1",
                 "feats", "meta", "score", "comps", "expires", "side",
                 "_logged")

    def __init__(self, kind, route, geom, born_i, feats=None,
                 meta=None, ttl=24):
        self.kind = kind
        self.route = route
        self.geom = dict(geom)          # pips / bar idx, frozen
        self.born_i = born_i
        self.t0 = geom.get("t0", born_i)
        self.t1 = geom.get("t1", born_i)
        self.feats = dict(feats or {})  # generation-time features
        self.meta = dict(meta or {})    # route payload for birth
        self.score = None
        self.comps = {}
        self.expires = born_i + ttl
        self.side = geom.get("side")
        self._logged = set()     # outcomes already written to cand_log

    def band(self, i):
        """(lo, hi) price band of the candidate at bar i."""
        g = self.geom
        if "bottom" in g and "top" in g:
            return g["bottom"], g["top"]
        for k in ("price", "level", "mid"):
            if g.get(k) is not None:
                return g[k], g[k]
        if g.get("p0") is not None:
            p = g["p0"] + g.get("slope", 0.0) * (i - g["t0"])
            return p, p
        return None, None


def footprint_overlap(a_band, a_span, b_band, b_span, iou_thresh):
    """Type-family-agnostic overlap: price-band overlap AND span IoU."""
    if a_band is None or b_band is None:
        return False
    if a_band[1] < b_band[0] or b_band[1] < a_band[0]:
        return False
    a0, a1 = a_span
    b0, b1 = b_span
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return union > 0 and inter / union >= iou_thresh


class Salience:
    """The ranking layer.  Holds the candidate pool; applies score ->
    NMS -> hysteresis -> budget each bar."""

    def __init__(self, eng):
        self.e = eng
        self.pool = []
        # signature -> bar until which a just-evaluated candidate is
        # still "the same evaluation".  Re-proposal of identical
        # geometry inside its own TTL window is the same candidate
        # dying again, not a new one (candidate lifecycle = ttl).
        self._grave = {}
        # (family, price-band) -> bar-until for recently dead objects —
        # footprint-level grave so a killed congestion can't re-birth
        # as a 1-pip-shifted twin.
        self._grave_band = {}
        self._graved = set()   # object ids already shadowed
        # close reasons that must NOT be revived: the structure was
        # retired by rule (§11.4a) — resurrecting it re-draws ink the
        # author chose to drop.  Natural deaths (outranked, traverse,
        # session end) are the REQ-1(b) revival population.
        self._no_revive = ("retire_far", "retire_stale", "wall_exit",
                           "wall_gone")
        # rolling birth ledger — the budget is a RATE per family, not
        # just a concurrency cap: golden births/72 bars are ~1 box,
        # ~2 lines, ~1 level, ~1 bracket (p90, MEASURE-TUNE), so each
        # family's births per rolling window are capped at that count
        # (DN_SALIENCE §5 stage 5: "emit top-k where k follows the
        # golden count distribution").
        self._births = []

    def _sig(self, c):
        ptol = self.e._tol()
        out = [c.kind, c.route]
        for k in ("top", "bottom", "price", "p0", "level"):
            v = c.geom.get(k)
            out.append(None if v is None else round(float(v) / ptol))
        v = c.geom.get("slope")
        out.append(None if v is None else round(float(v) / 0.05))
        return tuple(out)

    def _sig_obj(self, o):
        """Same signature space for a live/dead object — lets a killed
        structure keep its evaluation window (no instant re-birth)."""
        ptol = self.e._tol()
        g = o.geometry
        out = [o.type, o.why]
        for k in ("top", "bottom", "price", "p0", "level"):
            v = g.get(k)
            out.append(None if v is None else round(float(v) / ptol))
        v = g.get("slope")
        out.append(None if v is None else round(float(v) / 0.05))
        return tuple(out)

    # ---------------- pool ------------------------------------- #

    def propose(self, cand):
        """Add a candidate; same-structure duplicates collapse to the
        existing live proposal (a re-proposed structure is still live,
        not a new candidate).  Price-like geometry compares within the
        structure tolerance; slope within a small absolute eps."""
        ptol = self.e._tol()
        for c in self.pool:
            if c.kind == cand.kind and c.route == cand.route:
                same = True
                for k in ("top", "bottom", "price", "p0", "level"):
                    a = c.geom.get(k)
                    b = cand.geom.get(k)
                    if a is None and b is None:
                        continue
                    if a is None or b is None \
                            or abs(float(a) - float(b)) > ptol:
                        same = False
                        break
                if same and "slope" in c.geom or "slope" in cand.geom:
                    a = c.geom.get("slope")
                    b = cand.geom.get("slope")
                    if a is None or b is None \
                            or abs(float(a) - float(b)) > 0.05:
                        same = False
                if same:
                    c.expires = max(c.expires, cand.expires)
                    return c
        sig = self._sig(cand)
        if self._grave.get(sig, -1) >= cand.born_i:
            return cand            # same evaluation still in window
        # near-identical re-birth of a just-dead structure: the grave
        # holds recent kills' bands — a same-family candidate whose
        # band center sits within ~1 ABR of a dead band with similar
        # height is that congestion resuming, not new evidence
        # (DN_SALIENCE §5 hysteresis on the dead).
        if self._grave_hit(cand, cand.born_i):
            return cand
        self.pool.append(cand)
        return cand

    def _grave_hit(self, cand, i):
        """True when cand's band overlaps a recently-dead same-family
        footprint.  Wide bands match by shared mass (overlap >= half
        of the thinner band) or by near-coincident edges; thin/point
        bands (levels, line-at-bar) match by center proximity."""
        cb = cand.band(i)
        if cb is None:
            return False
        abr = max(self.e.abr[i] if i < len(self.e.abr)
                  else self.e.abr[-1], 1e-9)
        c_ctr = 0.5 * (cb[0] + cb[1])
        c_h = cb[1] - cb[0]
        for (gfam, _n, _id), gval in self._grave_band.items():
            gband, guntil = gval[0], gval[1]
            if guntil < i or gband is None:
                continue
            if gfam != FAMILY.get(cand.kind):
                continue
            g_ctr = 0.5 * (gband[0] + gband[1])
            g_h = gband[1] - gband[0]
            if min(c_h, g_h) <= abr:
                hit = abs(c_ctr - g_ctr) <= abr
            else:
                ov = min(cb[1], gband[1]) - max(cb[0], gband[0])
                hit = ov >= 0.5 * min(c_h, g_h) or (
                    abs(cb[0] - gband[0]) <= abr and
                    abs(cb[1] - gband[1]) <= abr)
                # same-episode test (DN_BOX): a wide-band candidate
                # whose structure window reuses bars from inside the
                # dead object's drawn span is the same congestion
                # episode, not a new one.  A genuinely new congestion
                # builds after the old drawing ended.
                g_tr = gval[3]
                if hit and g_tr is not None:
                    c_t0 = cand.geom.get("t0")
                    if c_t0 is not None and c_t0 >= g_tr:
                        hit = False
            if hit:
                return True
        return False

    def _expire(self, i):
        self.pool = [c for c in self.pool if c.expires >= i]

    # ---------------- scoring ---------------------------------- #

    def score(self, item, i, is_cand=True):
        """Score a Candidate or a live Obj.  Returns (score, comps)."""
        e = self.e
        sp = e.p["salience"]
        abr = max(e.abr[i] if i < len(e.abr) else e.abr[-1], 1e-9)
        c = e.bars[i]["c"]
        if is_cand:
            kind, geom, feats = item.kind, item.geom, item.feats
            t0, t1 = item.t0, item.t1
            consumed = 0
        else:
            kind, geom = item.type, item.geometry
            sali = geom.get("sali", {})
            # birth feats frozen: post-birth touches are consumption
            # (already penalized via "consumed"), not added strength.
            feats = dict(sali.get("feats", {}))
            t0 = item.t_left
            t1 = item.t_right if item.t_right is not None else i
            consumed = sali.get("consumed", 0)
        if e.p["line"].get("lab_score") and \
                kind in ("PATTERN_LINE", "CONTEXT_LINE"):
            s, comps = self._lab_line_score(geom, i)
            if not is_cand and (geom.get("broke") or geom.get("dead")):
                s = round(s * sp["post_break_demote"], 4)
            return s, comps
        band = self._band_of(kind, geom, i)
        # distance from current close to the nearest band edge, in ABR
        if band is None:
            d_abr = 3.0
        else:
            lo, hi = band
            d = 0.0 if lo <= c <= hi else min(abs(c - lo), abs(c - hi))
            d_abr = d / abr
        peak, width = sp["prox_peak_abr"], sp["prox_width_abr"]
        prox = max(0.0, 1.0 - abs(d_abr - peak) / width)
        span_min = max(0, (t1 - t0)) * 5
        # DN_SALIENCE §5: recency(t0 vs now) — the structure's start,
        # identical for candidate and incumbent (a re-proposed twin
        # must not win on freshness alone).
        recency = 0.5 ** (max(0, i - t0) / sp["recency_halflife_bars"])
        import gates
        sess = gates.session_prior(e.bars[i]["cet_min"],
                                   sp["asia_demote"])
        comps = {
            "touches": feats.get("touches", 0),
            "span_min": span_min,
            "prom_abr": feats.get("prom_abr", 0.0),
            "recency": round(recency, 3),
            "prox": round(prox, 3),
            "d_abr": round(d_abr, 2),
            "session": round(sess, 2),
            "consumed": consumed,
        }
        # kind-scoped prom weight: on the production FUNNEL labels
        # prom_abr is the only BOX separator clearing the 0.60/fold
        # gate (0.70-0.79) — let it dominate BOX ranking.  Other kinds
        # fall back to the shared w_prom.
        wp = sp.get("w_prom_" + kind.lower(), sp["w_prom"])
        if sp.get("box_prom_rank") and FAMILY.get(kind) == "box":
            # R34 C1 queue 5: prom_abr as the box ranker (AUC .743,
            # only feature at >=.60 on every fold) — strong weight so
            # it dominates ordering inside the box family while the
            # shared terms keep scale for min_score/hyst gates.
            wp = sp["box_prom_w"]
        # R34 C1 queue 5 / §34.8.2.4: BOX-LAB's rank score arrives on
        # the candidate as feats["box_rank"] (box.rank_score flag,
        # output-only in boxes.py).  Under box.lab_score_use the lab
        # score IS the box-family score — the kept selection ranker.
        if sp.get("box_lab_score_use") and FAMILY.get(kind) == "box" \
                and feats.get("box_rank") is not None:
            s = feats["box_rank"]
            if not is_cand and (geom.get("broke") or geom.get("dead")):
                s = round(s * sp["post_break_demote"], 4)
            return round(s, 4), dict(comps, lab_rank=feats["box_rank"])
        s = (sp["w_touches"] * comps["touches"]
             + sp["w_span"] * (span_min / 60.0)
             + wp * comps["prom_abr"]
             + sp["w_recency"] * comps["recency"]
             + sp["w_prox"] * comps["prox"]
             + sp["w_session"] * comps["session"]
             - sp["w_consumed"] * consumed
             - sp["mdl_penalty"])
        # post-break demotion (DN_BOX §5 carry grammar): once a box is
        # broken or a line dead its live reference is the carried
        # level; the parent's remaining ink is residual, not a
        # competing structure.
        if not is_cand and (geom.get("broke") or geom.get("dead")):
            s *= sp["post_break_demote"]
        return round(s, 4), comps

    def _lab_line_score(self, g, i):
        """R34 C1 queue 3: linelab's ranker ported behind
        `line.lab_score` (lab stream line@2 .124 vs engine .083).
        score = n_touch_events - overshoot_w*over_all/tol
                - span_age_w*age/60
        where over_all = max(pivot overshoot, worst close violation
        beyond the defended side).  Causal: scans bars <= i only."""
        e = self.e
        lp = e.p["line"]
        abr = max(e.abr[i] if i < len(e.abr) else e.abr[-1], 1e-9)
        tol = max(lp["touch_tol_pips"], lp["touch_tol_abr_frac"] * abr)
        side = 1 if g.get("side") == "top" else -1
        t0 = g.get("t0") or 0
        p0 = g.get("p0") or 0.0
        slope = g.get("slope") or 0.0
        ext = "l" if side < 0 else "h"
        nt = 0
        cur = False
        worst_c = 0.0
        j_end = min(i, len(e.bars) - 1)
        for j in range(max(0, t0), j_end + 1):
            pj = p0 + slope * (j - t0)
            wv = abs(e.bars[j][ext] - pj) <= tol
            if wv:
                if not cur:
                    nt += 1
                cur = True
            else:
                cur = False
            cv = (pj - e.bars[j]["c"]) * (1 if side < 0 else -1)
            if cv > worst_c:
                worst_c = cv
        over = 0.0
        for q in e.book.alive():
            if q.dir != side or q.t_conf > i or not (t0 <= q.t_ext <= i):
                continue
            d = (q.price - (p0 + slope * (q.t_ext - t0))) * side
            if d > over:
                over = d
        over_all = max(over, worst_c)
        age = max(0, (i - t0) * 5 - lp["span_max_min"])
        s = nt - lp["overshoot_w"] * over_all / tol \
            - lp["span_age_w"] * age / 60.0
        return round(s, 4), {"lab_nt": nt, "lab_over": round(over_all, 2),
                             "lab_age": age}

    def _revive_target(self, cand, i):
        """REQ-1(b): a re-proposal of a closed same-geometry structure
        is the same ink resuming, not a new birth.  Returns the most
        recent CLOSED same-kind object whose band overlaps the
        candidate's (grave-band overlap semantics), if it died within
        revive_max_bars and did not die by a retirement rule."""
        sp = self.e.p["salience"]
        cb = cand.band(i)
        if cb is None:
            return None
        tol = self.e._tol()
        ch = cb[1] - cb[0]
        c_ctr = 0.5 * (cb[0] + cb[1])
        best = None
        for o in reversed(self.e.objects):
            if o.type != cand.kind or o.state != "CLOSED" \
                    or o.t_right is None:
                continue
            if i - o.t_right > sp.get("revive_max_bars", 144):
                continue         # too old to be the same ink
            why = next((w for _i, ev, w in o.events if ev == "close"),
                       None)
            if why in self._no_revive:
                continue
            ob = self._band_of(o.type, o.geometry, i)
            if ob is None:
                continue
            oh = ob[1] - ob[0]
            ov = min(cb[1], ob[1]) - max(cb[0], ob[0])
            if min(ch, oh) <= 2 * tol:
                ok = abs(c_ctr - 0.5 * (ob[0] + ob[1])) <= tol
            else:
                ok = ov >= 0.5 * min(ch, oh)
            if ok:
                best = o
                break
        return best

    def _band_of(self, kind, g, i):
        if "bottom" in g and "top" in g:
            return g["bottom"], g["top"]
        for k in ("price", "level", "mid"):
            if g.get(k) is not None:
                return g[k], g[k]
        if g.get("p0") is not None:
            p = g["p0"] + g.get("slope", 0.0) * (i - g["t0"])
            return p, p
        return None, None

    # ---------------- NMS --------------------------------------- #

    def _suppressed(self, cand, i):
        """Candidate suppressed if its footprint overlaps a live
        higher-ranked object — with the nested-box exception.  A live
        object only shadows a candidate it actually outranks (DN_
        SALIENCE §5.3): a weak context range must not veto a strong
        congestion box forming inside it."""
        e = self.e
        sp = e.p["salience"]
        cb = cand.band(i)
        cspan = (cand.t0, max(cand.t1, i))
        for o in e.active():
            if o.type == "LABEL_TF" or o.type == "BAR_MARKER":
                continue
            if sp.get("fam_budget"):
                # R34 C1: NMS within each kind only — a context range
                # must not shadow a box on the same footprint.
                if o.type != cand.kind:
                    continue
            else:
                fam = FAMILY.get(o.type)
                if fam != FAMILY.get(cand.kind):
                    continue
            ob = self._band_of(o.type, o.geometry, i)
            # nested-allowed: inner box inside a parent box (9.6a)
            if (o.type == "BOX" and cand.kind == "BOX" and cb and ob
                    and ob[0] <= cb[0] <= cb[1] <= ob[1]
                    and (cb[1] - cb[0]) <= sp["nested_frac"]
                    * (ob[1] - ob[0])):
                continue
            ospan = (o.t_left, i)
            if footprint_overlap(cb, cspan, ob, ospan, sp["nms_iou"]):
                o_score, _ = self.score(o, i, is_cand=False)
                if o_score >= cand.score:
                    return o.id
        return None

    # ---------------- the round --------------------------------- #

    def round(self, i):
        """One ranking round at bar i: expire, score, NMS, budget."""
        e = self.e
        sp = e.p["salience"]
        # band-level grave FIRST: an object closed earlier this same
        # bar (maintain ran before this round) must already shadow its
        # footprint — otherwise the death bar itself re-births the same
        # congestion.  Thin bands (levels, line-at-bar) shadow ttl
        # bars; a wide congestion footprint shadows the rest of the
        # session — golden draws a box once per episode (the broken
        # edge lives on as LEVEL_CARRIED), so a same-episode re-box is
        # never new evidence.  The t0>=dead.t_right clause in
        # _grave_hit still admits a genuinely new buildup in the band.
        abr = max(e.abr[i] if i < len(e.abr) else e.abr[-1], 1e-9)
        n = 0
        for o in e.objects:
            if o.t_right == i and o.id not in self._graved:
                band = self._band_of(o.type, o.geometry, i)
                key = (FAMILY.get(o.type), n, o.id)
                ttl = 1 << 30 if band is not None \
                    and band[1] - band[0] > abr \
                    else sp["cand_ttl_bars"]
                self._grave_band[key] = (band, i + ttl,
                                         o.t_left, o.t_right)
                self._graved.add(o.id)
                n += 1
        self._grave_band = {k: v for k, v in self._grave_band.items()
                            if v[1] > i}
        self._expire(i)
        # score pool + actives
        for c in self.pool:
            c.score, c.comps = self.score(c, i, is_cand=True)
        act_scores = {}
        for o in e.active():
            s, _c = self.score(o, i, is_cand=False)
            act_scores[o.id] = s
            o.geometry["sali"]["score"] = s
            o.score = s            # output-only exposure (R20 §20.4)
        born = []
        # iterate candidates by score desc; deterministic tie-break:
        # kind, route, t0, then geometry key order
        order = sorted(
            self.pool,
            key=lambda c: (-c.score, c.kind, c.route, c.t0,
                           repr(sorted(c.geom.items()))))
        for c in order:
            cls = budget_class(c.kind)
            cap = {"signal": sp["budget_signal"],
                   "context": sp["budget_context"],
                   "annot": sp["budget_annot"]}[cls]
            # dead/broke objects are residual ink (dashed extension /
            # broken parent) — they occupy context, not signal, so a
            # converted line's carry can take the freed signal slot.
            live = [o for o in e.active()
                    if (("context" if (o.geometry.get("dead") or
                                       o.geometry.get("broke"))
                         else budget_class(o.type)) == cls)]
            slot_free = len(live) < cap and \
                len(e.active()) < sp["budget_hard"]
            if slot_free and sp.get("fam_budget"):
                # R34 C1: per-family live budget — the author's
                # per-family live count at tau on TUNE is med 0-1,
                # p90 1 (box 0/1/3, line 1/1/2, level 0/1/2,
                # bracket 0/1/2) -> budget 1 per family.  Count all
                # active objects in the family incl. dead/broke
                # residual ink — it is still drawn on the chart,
                # as in the golden live count.
                lf = FAMILY.get(c.kind)
                if lf in ("box", "line", "level", "bracket"):
                    fam_n = sum(1 for o in e.active()
                                if FAMILY.get(o.type) == lf)
                    slot_free = fam_n < sp.get("famlive_" + lf, 1)
            if slot_free and sp.get("fam_budget") \
                    and sp.get("fam_caps"):
                # R36 §36.3 variant: hold each returning kind to the
                # author's own TUNE count — golden per-panel max is
                # CR 1 / CL 1 / MINI 2 / SQZ 1 over 198 panels, so a
                # kind may not birth past famcap_<kind> objects in a
                # panel.  Counts born objects (covers annot kinds like
                # SQUEEZE that bypass the signal/context ledger).
                fc = sp.get("famcap_" + c.kind.lower())
                if fc is not None and sum(
                        1 for o in e.objects
                        if o.type == c.kind) >= fc:
                    if "fam_capped" not in c._logged:
                        e._cand(c.kind, i, c.route, "fam_capped",
                                self._geom_log(c), score=c.score)
                        c._logged.add("fam_capped")
                    continue
            sup = self._suppressed(c, i)
            if sup is not None:
                e._cand(c.kind, i, c.route, "nms_suppressed",
                        self._geom_log(c), score=c.score, by=sup)
                c.expires = i  # lose once — the structure is covered
                continue
            if c.score < sp["min_score_birth"]:
                if "below_min_score" not in c._logged:
                    e._cand(c.kind, i, c.route, "below_min_score",
                            self._geom_log(c), score=c.score)
                    c._logged.add("below_min_score")
                continue
            # grave check BEFORE any displacement: a blocked candidate
            # must not kill an incumbent on its way out.
            if self._grave_hit(c, i):
                c.expires = i
                continue
            # per-family birth rate (DN_SALIENCE stage 5): at most
            # rate_<family> births of this family per rolling
            # rate_window_bars — golden count distribution measured on
            # TUNE (BOX p90=1, LINE p90=2, LEVEL p90=1, BRACKET p90=1).
            # The candidate stays in the pool — it can win when the
            # window rolls or an incumbent dies of natural causes.
            # RANGE_OPEN is session-tracker ink that converts in place
            # to BOX at the asia boundary — a lifecycle transition,
            # not a selected birth; it doesn't spend a rate slot.
            # Rate keys are per-KIND (golden births are measured per
            # spec_type): a weak MINI_LEVEL must not starve a strong
            # LEVEL_CARRIED sharing its family.
            fam = None if c.kind == "RANGE_OPEN" else c.kind.lower()
            if cls in ("signal", "context") and fam is not None:
                win = sp["rate_window_bars"]
                cap_r = sp["rate_" + fam] \
                    if "rate_" + fam in sp else sp["rate_default"]
                # per-kind ceiling AND joint count: golden's ~2.3
                # objects/panel is a joint distribution — the engine
                # may not birth every kind at its p90 at once
                # (DN_SALIENCE stage 5: k follows the count dist).
                # Broken-edge/congestion carries are the parent's edge
                # continuing (DN_LEVEL routes 1-2): the structure was
                # already paid for at the parent's birth — exempt from
                # the joint cap, still bound by rate_level_carried.
                cont = c.route.startswith("broken_") or \
                    c.route == "congestion_edge"
                recent = sum(1 for f_, b in self._births
                             if f_ == fam and b > i - win)
                total = sum(1 for _, b in self._births
                            if b > i - win)
                # shared context cap on a day-length window: the
                # author marks at most ~2 context objects/day (TUNE:
                # 15 over 9 days, 183/198 panels zero) while per-kind
                # 1/72 caps let context ride at ~10/day and spend
                # ~18% of joint rate_total on rarely-drawn ink.
                ctx_full = cls == "context" and sp["rate_context"] \
                    and sum(1 for f_, b in self._births
                            if f_ in ("context_line", "context_range")
                            and b > i - sp["context_window_bars"]) \
                    >= sp["rate_context"]
                # same long-window cap for MINI_LEVEL: golden draws
                # ~0.7/day (31 objects/198 panels) while the 1/72
                # per-kind cap lets ~0.45/panel ride the joint ledger.
                mini_full = fam == "mini_level" and \
                    sp.get("rate_mini_day") and sum(
                        1 for f_, b in self._births
                        if f_ == "mini_level"
                        and b > i - sp["context_window_bars"]) \
                    >= sp["rate_mini_day"]
                # R25 §25.5 per-family ledger (flag fam_ledger): the
                # joint rate_total pool is replaced by per-kind shares
                # summing to rate_total, taken from the 584c7743
                # default birth mix (PL 878 BOX 470 LC 461 BRA 350
                # CL 200 CR 159 MINI 90 of 2608 -> largest-remainder
                # shares 2/1/1/1/0/0/0).  A defended LC birth draws on
                # level_carried's share (same kind key); continuation
                # births stay joint-exempt but still count toward
                # their kind's share, exactly as they count toward
                # the joint pool today.
                # R34 C-round 1 (flag fam_budget, v2): a floor share
                # for EVERY kind (default fam_floor) so no kind is
                # silenced, and the cont bypass is closed — a
                # continuation birth also needs its kind's share.
                if sp.get("fam_budget"):
                    joint_full = recent >= sp.get(
                        "fam_rate_" + fam, sp["fam_floor"])
                else:
                    joint_full = not cont and (
                        (sp.get("fam_ledger") and
                         recent >= sp.get("fam_rate_" + fam, 0)) or
                        (not sp.get("fam_ledger") and
                         total >= sp["rate_total"]))
                if recent >= cap_r or ctx_full or mini_full or \
                        joint_full:
                    # REQ-1(b): a re-proposal that revives a closed
                    # same-geometry structure is not new ink — it
                    # must not spend a birth slot.  Resurrect the
                    # object in place; it still needs a live budget
                    # slot this bar, and rule-dead structures
                    # (retire_*/wall_*) stay dead.  Measured: extending
                    # the same exemption to UNBLOCKED proposals
                    # (c188ae66) changed nothing but a LEVEL_CARRIED
                    # loss — the ledger is only relieved when the
                    # relief matters (rate-bound), so the check stays
                    # inside the rate-limited branch.
                    if sp.get("revive_exempt"):
                        ro = self._revive_target(c, i)
                        if ro is not None and slot_free:
                            ro.state = "ACTIVE"
                            ro.t_right = None
                            ro.geometry["_last_int"] = i
                            ro.geometry["dead"] = False
                            ro.geometry["broke"] = False
                            ro.geometry["pierced"] = False
                            ro.event(i, "revive",
                                     "same geometry re-proposed")
                            act_scores[ro.id] = c.score
                            born.append(ro)
                            e._cand(c.kind, i, c.route, "revived",
                                    self._geom_log(c), score=c.score)
                            c.expires = i
                            continue
                    # R34 C1 queue 4: LC selection inside the family —
                    # the first proposal in a window spends
                    # rate_level_carried=1 and blocks later, better
                    # ones (19/33 covered-but-unhit LC goldens).
                    # Under lc_score_pick the score decides: a higher-
                    # scored LC candidate supersedes the in-window
                    # incumbent, which keeps the ledger conserved
                    # (its slot moves to this birth — no extra ink
                    # rate) and the incumbent closes "superseded".
                    if sp.get("lc_score_pick") and \
                            fam == "level_carried":
                        win_bars = {b for f_, b in self._births
                                    if f_ == fam and b > i - win}
                        # the slot holder is the in-window LC birth —
                        # live or dead (the ledger does not refund a
                        # death; measured: most LC incumbents close
                        # "traversed" 1-4 bars after birth, so a
                        # live-only check leaves the flag inert).
                        holders = [o for o in e.objects
                                   if o.type == "LEVEL_CARRIED"
                                   and o.t_birth in win_bars]
                        live_h = [o for o in holders
                                  if o.state == "ACTIVE"
                                  and not o.geometry.get("_pend_break")]
                        pool_h = live_h or holders
                        if pool_h:
                            weakest = min(
                                pool_h,
                                key=lambda o: act_scores.get(
                                    o.id, getattr(o, "score", None)
                                    or 0.0))
                            wsc = act_scores.get(
                                weakest.id,
                                getattr(weakest, "score", None) or 0.0)
                            if c.score > wsc + sp["hyst_margin"]:
                                if weakest.state == "ACTIVE":
                                    weakest.event(
                                        i, "superseded",
                                        "LC %.2f>%.2f" % (c.score, wsc))
                                    weakest.close(i, "superseded")
                                    self._grave[
                                        self._sig_obj(weakest)] = \
                                        i + sp["cand_ttl_bars"]
                                # the slot moves to this birth: ledger
                                # conserved, no extra ink rate.
                                for k_, (f_, b_) in enumerate(
                                        self._births):
                                    if f_ == fam and \
                                            b_ == weakest.t_birth:
                                        del self._births[k_]
                                        break
                                o = e._birth(c, i, c.score)
                                act_scores[o.id] = c.score
                                born.append(o)
                                c.expires = i
                                self._births.append((fam, i))
                                e._cand(c.kind, i, c.route, "born",
                                        self._geom_log(c),
                                        score=c.score)
                                continue
                    # the ledger counts real births — a killed object
                    # does not refund its slot (golden's count
                    # distribution is births per window, not live
                    # structures).  Measured on TUNE: refunding the
                    # slot on death recycled every post-break close
                    # into a re-birth and doubled ink for +0 recall;
                    # re-tested with live-count + persistent grave —
                    # same result (births 302->734, clutter 4.33->6.67,
                    # hit-rate flat).  Score-gated ledger TRANSFER
                    # (displace weakest in-window incumbent, move its
                    # entry) tested under R12 §12.4: births/window is
                    # conserved but birth EVENTS chain per bar —
                    # BOX e=962, clutter 7.0, hit/birth flat ~0.017.
                    # Same volume-churn signature -> rejected.
                    if "rate_limited" not in c._logged:
                        e._cand(c.kind, i, c.route, "rate_limited",
                                self._geom_log(c), score=c.score)
                        c._logged.add("rate_limited")
                    # REQ-2 (candidate TTL) is deferred (R13 section
                    # 13.3): the wait-out-the-window extension below
                    # stays gated behind salience.rate_blocked_extend
                    # until its paired A/B is ruled on (R14 §14.2).
                    if sp.get("rate_blocked_extend"):
                        # A cap-blocked candidate has already passed
                        # the score floor — let it wait out the
                        # blocking window instead of dying on the
                        # generic TTL (ttl 24 << window 72: FUNNEL
                        # shows ~40% of right proposals expire while
                        # their window is still full).  Bounded at
                        # born_i + win: at most one window of
                        # patience, never immortal.
                        if recent >= cap_r:
                            roll = min(b for f_, b in self._births
                                       if f_ == fam and b > i - win)
                        else:
                            roll = min(b for _, b in self._births
                                       if b > i - win)
                        c.expires = min(max(c.expires, roll + 1),
                                        c.born_i + win)
                    continue
            if not slot_free:
                # displacement: beat the weakest same-class incumbent
                # by margin, respecting min dwell.  An object with a
                # traverse in flight (pierced line / pending box break)
                # is evidence mid-resolution — it cannot be displaced
                # until its own lifecycle settles the event (DN_TF §6:
                # evidence first, budget second).
                displaceable = [o for o in live
                                if not o.geometry.get("_pend_break")
                                and not (o.geometry.get("pierced")
                                         and not o.geometry.get("dead"))]
                weakest = min(displaceable,
                              key=lambda o: act_scores[o.id]) \
                    if displaceable else None
                # dwell protects a live structure from flicker; a
                # finished one (broke/dead — residual ink per D9) no
                # longer needs it: its carry is the live reference.
                dwell_ok = weakest is not None and (
                    weakest.geometry.get("dead") or
                    weakest.geometry.get("broke") or
                    i - weakest.t_birth >= sp["dwell_bars"])
                if weakest is not None and \
                        c.score > act_scores[weakest.id] + \
                        sp["hyst_margin"] and dwell_ok:
                    weakest.event(i, "outranked",
                                  "%s %.2f>%.2f" % (c.kind, c.score,
                                                    act_scores[weakest.id]))
                    weakest.close(i, "outranked")
                    # the displaced structure keeps its evaluation
                    # window: identical geometry can't re-birth until
                    # TTL passes or new evidence changes the signature
                    self._grave[self._sig_obj(weakest)] = \
                        i + sp["cand_ttl_bars"]
                    slot_free = True
            if not slot_free:
                if "outranked" not in c._logged:
                    e._cand(c.kind, i, c.route, "outranked",
                            self._geom_log(c), score=c.score)
                    c._logged.add("outranked")
                continue
            o = e._birth(c, i, c.score)
            act_scores[o.id] = c.score
            born.append(o)
            c.expires = i
            bk = None if c.kind == "RANGE_OPEN" else c.kind.lower()
            if cls in ("signal", "context") and bk is not None:
                self._births.append((bk, i))
            e._cand(c.kind, i, c.route, "born",
                    self._geom_log(c), score=c.score)
        for c in self.pool:
            if c.expires <= i:
                if "expired" not in c._logged:
                    e._cand(c.kind, i, c.route, "expired",
                            self._geom_log(c), score=c.score)
                self._grave[self._sig(c)] = c.born_i + \
                    self.e.p["salience"]["cand_ttl_bars"]
        self.pool = [c for c in self.pool if c.expires > i]
        self._grave = {s: u for s, u in self._grave.items() if u > i}
        return born

    def _geom_log(self, c):
        g = dict(c.geom)
        g["t_left"] = c.t0
        for fk, fv in c.feats.items():
            g.setdefault(fk, fv)
        return g
