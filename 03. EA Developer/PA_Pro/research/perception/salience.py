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

# R67 s.67.3 MIGRATION_PLAN A1: the candidate/geometry kernel moved to
# kernel.py verbatim.  Re-exported here so `from salience import X`
# call sites (boxes/levels/lines/patterns/engine, lab scripts) stay
# unchanged.
from kernel import (SIGNAL, CONTEXT, ANNOT, FAMILY, budget_class,
                    Candidate, footprint_overlap, band_of, sig, sig_obj)


class _AdmitCtx:
    """Per-round shared state handed to _admit_one/_displace/
    _joint_pass (A4 stage split — carries what used to be locals
    of the monolith round())."""

    __slots__ = ("i", "sp", "prio_live", "act_scores", "born")

    def __init__(self, i, sp, prio_live, act_scores, born):
        self.i = i
        self.sp = sp
        self.prio_live = prio_live
        self.act_scores = act_scores
        self.born = born


class Salience:
    """The ranking layer.  Holds the candidate pool; applies score ->
    NMS -> hysteresis -> budget each bar."""

    def __init__(self, eng):
        self.e = eng
        self.pool = []
        # R-1 probe (R75 s.75.3.4): in-run peak pool occupancy —
        # "*" = max len(pool), per-family keys = max fam count at
        # grant time.  Observability only; canonical() never reads
        # it.  Feeds the MQL5 port cap decision.
        self.pool_peak = {"*": 0}
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
        # ctx_yield (R49 §49.4.2): context objects hidden while a
        # priority-1 box is live — tracked here so they can be shown
        # again (never evicted, never re-born).
        self._hidden_ctx = []

    def __setstate__(self, d):
        self.__dict__.update(d)
        # R-1 probe: pre-probe pickles carry no pool_peak
        self.__dict__.setdefault("pool_peak", {"*": 0})

    def _sig(self, c):
        return sig(self.e, c)      # A1: body moved to kernel.py

    def _sig_obj(self, o):
        """Same signature space for a live/dead object — lets a killed
        structure keep its evaluation window (no instant re-birth)."""
        return sig_obj(self.e, o)  # A1: body moved to kernel.py

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
        npk = len(self.pool)
        if npk > self.pool_peak.get("*", 0):
            self.pool_peak["*"] = npk
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

    def pool_view(self, fam):
        """B1 shadow view (MIGRATION_PLAN, master flag ``arch_v2``):
        the family's read-only slice of the shared pool, derived by
        filtering ``c.fam`` at read time.  Never stored alongside
        ``self.pool``, never re-sorted, never written back — the
        single source of truth stays the shared pool.  OFF returns
        ``[]`` so the OFF path constructs no v2 state at all."""
        if not self.e.p.get("arch_v2"):
            return []
        return [c for c in self.pool
                if getattr(c, "fam", None) == fam]

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
        if sp.get("level_touch_rec") and FAMILY.get(kind) == "level" \
                and geom.get("price") is not None:
            # R38 §38.5: score levels by touches (ABR-scaled
            # tolerance) x recency decay, counted causally through
            # bar i — a level the tape keeps defending is the one the
            # author draws.
            pr = geom["price"]
            tol_l = e._tol()
            nt = 0
            in_t = False
            j0 = max(0, geom.get("t0", t0))
            for j in range(j0, min(i, len(e.bars))):
                b = e.bars[j]
                tch = b["l"] - tol_l <= pr <= b["h"] + tol_l
                if tch and not in_t:
                    nt += 1
                in_t = tch
            rec_l = 0.5 ** (max(0, i - j0) / sp["recency_halflife_bars"])
            s = nt * rec_l
            if not is_cand and (geom.get("dead") or geom.get("broke")):
                s = round(s * sp["post_break_demote"], 4)
            return round(s, 4), dict(comps, lab_nt=nt,
                                     lab_rec=round(rec_l, 3))
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
        return band_of(kind, g, i)  # A1: body moved to kernel.py

    def _fam(self, kind):
        """R44 §44.2 (flag fam_context): under fam_budget the spec's
        CONTEXT items (CONTEXT_RANGE, CONTEXT_LINE) are their own
        family with a live budget of 1 — spec §5 lists CONTEXT as a
        separate priority-4 item that never competes with the
        priority-1 box.  Flag off: the parent's family map."""
        if self.e.p["salience"].get("fam_context") and \
                kind in ("CONTEXT_RANGE", "CONTEXT_LINE"):
            return "context"
        return FAMILY.get(kind)

    def _box_prio(self, kind, band, i):
        """R42 §42.4: the spec's box priority.  Class 1 = a BOX or
        RANGE_OPEN whose band contains the current price, or that
        price left within the last 12 bars (R21 §21.3: the author
        keeps a broken box drawn ~60 min).  Class 0 = CONTEXT_RANGE
        and every box price is neither in nor just left.  A class-1
        box outranks every class-0 box-family member regardless of
        score; among equals the score decides."""
        if kind not in ("BOX", "RANGE_OPEN") or band is None or \
                band[0] is None:
            return 0
        e = self.e
        lo, hi = band
        if lo <= e.bars[i]["c"] <= hi:
            return 1
        for j in range(max(0, i - 12), i):
            if lo <= e.bars[j]["c"] <= hi:
                return 1
        return 0

    def _joint_drop(self, struct, i):
        """R43 §43.4.2 (flag joint_struct): over the structure cap,
        drop in reverse spec §5 priority — CONTEXT objects first,
        then levels that are not the nearest ahead in either
        direction, then lines not tied to the live box's breakout
        side, then the oldest.  A §5 priority-1 box (contains price
        or just left within 12 bars) is never dropped.  Returns the
        victim object or None."""
        e = self.e
        px = e.bars[i]["c"]

        def mid(o):
            b = self._band_of(o.type, o.geometry, i)
            return None if b is None or b[0] is None else \
                (b[0] + b[1]) / 2.0

        lvs = [(o, mid(o)) for o in struct
               if FAMILY.get(o.type) == "level"]
        lvs = [(o, m) for o, m in lvs if m is not None]
        keep_lv = set()
        above = [(m, o) for o, m in lvs if m > px]
        below = [(m, o) for o, m in lvs if m < px]
        if above:
            keep_lv.add(min(above)[1].id)
        if below:
            keep_lv.add(max(below)[1].id)

        # the live box's breakout side: any active box-family member
        # with a resolved or pending break
        bside = None
        for o in struct:
            if FAMILY.get(o.type) == "box":
                b = o.geometry.get("broke") or o.geometry.get(
                    "_pend_break")
                if b in ("up", "down"):
                    bside = b
        keep_ln = set()
        if bside:
            want = "top" if bside == "up" else "bottom"
            for o in struct:
                if FAMILY.get(o.type) == "line" and \
                        o.geometry.get("side") == want:
                    keep_ln.add(o.id)

        def tier(o):
            if o.geometry.get("_pend_break"):
                return 9          # evidence mid-resolution
            if FAMILY.get(o.type) == "box" and self._box_prio(
                    o.type, self._band_of(o.type, o.geometry, i), i):
                return 9          # never drop the priority-1 box
            if budget_class(o.type) == "context":
                return 0
            f = FAMILY.get(o.type)
            if f == "level" and o.id not in keep_lv:
                return 1
            if f == "line" and o.id not in keep_ln:
                return 2
            return 3

        victim = min(struct, key=lambda o: (tier(o), o.t_birth))
        return None if tier(victim) == 9 else victim

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
                continue
            if sp.get("line_dedup_merge") and \
                    FAMILY.get(cand.kind) == "line" and \
                    o.geometry.get("side") == cand.geom.get("side") \
                    and ob is not None and cb is not None:
                # R38 §38.5: merge duplicate lines before the 2-line
                # budget — two same-side lines tracking within
                # dedup_abr of each other are ONE structure; the
                # score picks the survivor instead of both living.
                p_c = cand.geom.get("p0", 0) + \
                    cand.geom.get("slope", 0) * (i - cand.geom.get("t0", 0))
                p_o = o.geometry.get("p0", 0) + \
                    o.geometry.get("slope", 0) * (i - o.geometry.get("t0", 0))
                if abs(p_c - p_o) <= sp.get("line_dedup_abr", 1.0) * \
                        e._tol():
                    o_score, _ = self.score(o, i, is_cand=False)
                    if o_score >= cand.score:
                        return o.id
        return None

    # ---------------- the round --------------------------------- #

    def round(self, i):
        """One ranking round at bar i: expire, score, NMS, budget."""
        # A4 (MIGRATION_PLAN): the monolith is split into named stages,
        # called in the identical order — no condition changes.
        sp = self.e.p["salience"]
        # R-1 probe: per-family pool occupancy at grant time (the
        # decision-relevant peak).  Read-only counting.
        cnt = {}
        for c in self.pool:
            f = getattr(c, "fam", None) or "?"
            cnt[f] = cnt.get(f, 0) + 1
        for f, v in cnt.items():
            if v > self.pool_peak.get(f, 0):
                self.pool_peak[f] = v
        self._grave_sweep(i, sp)
        prio_live = self._yield_sweep(i, sp)
        act_scores = self._score_pass(i, sp)
        born = self._grant_pass(i, sp, prio_live, act_scores)
        self._pool_sweep(i)
        return born

    def _grave_sweep(self, i, sp):
        e = self.e
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

    def _yield_sweep(self, i, sp):
        e = self.e
        # R49 §49.4.2 (flag ctx_yield): "yield, not evict".  While a
        # spec-§5 priority-1 box is live, context objects are hidden —
        # not evicted, not re-born, counting neither as ink nor
        # against any budget.  Hidden objects go DELETED (the
        # evaluator's live book counts state != DELETED) and return
        # ACTIVE unchanged when no box is live.  Without fam_context
        # the context stays in the box family (shared live slot, no
        # parallel birth lane): restore requires the box-family slot
        # free, i.e. no box-family object live at all.  Runs before
        # the score pass so a restored object re-enters act_scores
        # like any other active.
        ctx_yield = sp.get("ctx_yield")
        prio_live = False
        if ctx_yield:
            prio_live = any(
                self._box_prio(o.type, self._band_of(
                    o.type, o.geometry, i), i)
                for o in e.active()
                if o.type in ("BOX", "RANGE_OPEN"))
            if prio_live:
                for o in e.active():
                    if o.type in ("CONTEXT_RANGE", "CONTEXT_LINE"):
                        o._yielded = True
                        o.state = "DELETED"
                        o.event(i, "yield", "prio-1 box live")
                        self._hidden_ctx.append(o)
            elif self._hidden_ctx:
                if sp.get("fam_context"):
                    slot_free_ctx = not any(
                        self._fam(o.type) == "context"
                        for o in e.active())
                else:
                    slot_free_ctx = sum(
                        1 for o in e.active()
                        if FAMILY.get(o.type) == "box") < \
                        sp.get("famlive_box", 1)
                keep = []
                for o in self._hidden_ctx:
                    if o.state == "DELETED" and \
                            getattr(o, "_yielded", False) and \
                            slot_free_ctx:
                        o._yielded = False
                        o.state = "ACTIVE"
                        o.event(i, "unhide", "")
                        slot_free_ctx = False
                    elif o.state == "DELETED":
                        keep.append(o)
                self._hidden_ctx = keep
        return prio_live

    def _score_pass(self, i, sp):
        e = self.e
        # score pool + actives
        for c in self.pool:
            c.score, c.comps = self.score(c, i, is_cand=True)
        act_scores = {}
        evs = []
        if sp.get("ev_route_box") or sp.get("ev_uip"):
            evs = [o for o in e.active()
                   if o.type == "BOX" and
                   o.geometry.get("meta_ev_route")]
        ev_top = None
        ev_best = -1e18
        for o in e.active():
            s, _c = self.score(o, i, is_cand=False)
            act_scores[o.id] = s
            o.geometry["sali"]["score"] = s
            o.score = s            # output-only exposure (R20 §20.4)
            if o in evs and s > ev_best:
                ev_best, ev_top = s, o.id
            elif (sp.get("box_prio") or sp.get("box_tau_prio")) and \
                    FAMILY.get(o.type) == "box" and \
                    self._box_prio(o.type, self._band_of(
                        o.type, o.geometry, i), i):
                # R42 §42.4: the exposed ranking at tau must carry the
                # spec's box priority — a box containing/just-left by
                # price sorts above every CONTEXT_RANGE and stale box
                # (BOX-LAB: 3 rank-2 misses where a stale structural
                # envelope's raw score beats the fresh right box).
                # The bonus is output-layer only; act_scores stays raw
                # so same-class score margins still decide internals.
                o.geometry["sali"]["score"] = s + 100.0
                o.score = s + 100.0
        if ev_top is not None:
            # R61 s.61.4 spec default: the best-SCORING live
            # event-route BOX takes box-family rank-1 at tau (the
            # rank-1 grant is its floor vs CONTEXT_RANGE); event
            # boxes rank among themselves by raw score.  Output-layer
            # only, like box_prio: act_scores stays raw.
            for o in e.active():
                if o.id == ev_top:
                    o.geometry["sali"]["score"] += 100.0
                    o.score += 100.0
                    break
        return act_scores

    def _grant_pass(self, i, sp, prio_live, act_scores):
        e = self.e
        born = []
        # iterate candidates by score desc; deterministic tie-break:
        # kind, route, t0, then geometry key order
        order = sorted(
            self.pool,
            key=lambda c: (-c.score, c.kind, c.route, c.t0,
                           repr(sorted(c.geom.items()))))
        if sp.get("box_young_first"):
            # A1v2 (R56, dataset evidence): the box family's
            # representative at a birth decision is the most recently
            # formed candidate — the author draws the current
            # congestion (H5-causal: right box = freshly touched,
            # close[tau] inside).  Reorders WITHIN the family's own
            # positions only: cross-family competition is unchanged.
            bx = [k for k, c in enumerate(order) if c.kind == "BOX"]
            yng = sorted((order[k] for k in bx),
                         key=lambda c: (
                             -c.t0,
                             -((c.feats or {}).get("touches")
                               or c.geom.get("touches") or 0),
                             c.route, repr(sorted(c.geom.items()))))
            for k, c in zip(bx, yng):
                order[k] = c
        if e.p["line"].get("rank") == "young_a":
            # R73 §73.2 L-1: the same freshest-structure ordering at
            # the grant stage — line cands occupy their score-earned
            # slots, but among themselves the freshest first anchor
            # (geom t0) wins, ties by touch count.  Reorders WITHIN
            # the family's own positions only, like box_young_first.
            ln = [k for k, c in enumerate(order)
                  if c.kind in ("PATTERN_LINE", "CONTEXT_LINE")]
            yng = sorted((order[k] for k in ln),
                         key=lambda c: (
                             -c.t0,
                             -((c.feats or {}).get("touches")
                               or c.geom.get("touches") or 0),
                             c.route, repr(sorted(c.geom.items()))))
            for k, c in zip(ln, yng):
                order[k] = c
        ctx = _AdmitCtx(i=i, sp=sp, prio_live=prio_live,
                        act_scores=act_scores, born=born)
        for c in order:
            self._admit_one(c, ctx)
        return born

    def _admit_one(self, c, ctx):
        """One candidate through the admit pipeline: suppression,
        budgets, rate ledger, yield/convert, displacement, joint cap,
        birth.  `continue` in the old monolith == `return` here."""
        i, sp = ctx.i, ctx.sp
        e = self.e
        act_scores = ctx.act_scores
        born = ctx.born
        prio_live = ctx.prio_live
        ctx_yield = sp.get("ctx_yield")
        ctx_convert = sp.get("ctx_convert")
        if True:
            if sp.get("box_v0_family") and FAMILY.get(c.kind) == "box":
                # R63 s.63.4 option-B: the box family is supplied by
                # the v0 mirror (engine._v0_sync); v1's own box-kind
                # cands (BOX, RANGE_OPEN, CONTEXT_RANGE) never birth.
                if "fam_v0" not in c._logged:
                    e._cand(c.kind, i, c.route, "fam_v0",
                            self._geom_log(c), score=c.score)
                    c._logged.add("fam_v0")
                return
            cls = budget_class(c.kind)
            if prio_live and c.kind in ("CONTEXT_RANGE",
                                        "CONTEXT_LINE"):
                # yield, not evict: the context waits in the pool until
                # no priority-1 box is live.
                if "ctx_yield" not in c._logged:
                    e._cand(c.kind, i, c.route, "ctx_yield",
                            self._geom_log(c), score=c.score)
                    c._logged.add("ctx_yield")
                return
            cap = {"signal": sp["budget_signal"],
                   "context": sp["budget_context"],
                   "annot": sp["budget_annot"]}[cls]
            # dead/broke objects are residual ink (dashed extension /
            # broken parent) — they occupy context, not signal, so a
            # converted line's carry can take the freed signal slot.
            # R66 s.66.3(b) (flag ev_uip_lvfree): the persistent UIP
            # object is box ink only - it never occupies a shared or
            # joint slot and can never be a displacement victim.
            lvfree = sp.get("ev_uip_lvfree")
            live = [o for o in e.active()
                    if not (lvfree and
                            o.geometry.get("meta_uip_persist"))
                    and (("context" if (o.geometry.get("dead") or
                                        o.geometry.get("broke"))
                          else budget_class(o.type)) == cls)]
            n_act = sum(1 for o in e.active()
                        if not (lvfree and
                                o.geometry.get("meta_uip_persist")))
            slot_free = len(live) < cap and n_act < sp["budget_hard"]
            if slot_free and sp.get("fam_budget"):
                # R34 C1: per-family live budget — the author's
                # per-family live count at tau on TUNE is med 0-1,
                # p90 1 (box 0/1/3, line 1/1/2, level 0/1/2,
                # bracket 0/1/2) -> budget 1 per family.  Count all
                # active objects in the family incl. dead/broke
                # residual ink — it is still drawn on the chart,
                # as in the golden live count.
                lf = self._fam(c.kind)
                if lf in ("box", "line", "level", "bracket") or \
                        (lf == "context" and sp.get("fam_context")):
                    # R42 §42.4 / R44 §44.2: a RANGE_OPEN is the
                    # session tracker's in-place precursor of the box
                    # (asia_convert / asia_absorbed in boxes.py handle
                    # the coexistence) — under the priority flags it
                    # does not hold the family's structural slot.
                    ro_skip = lf == "box" and (
                        sp.get("fam_context") or
                        ((sp.get("box_prio") or ctx_yield) and
                         self._box_prio(c.kind, c.band(i), i)))
                    fam_n = sum(1 for o in e.active()
                                if self._fam(o.type) == lf
                                and not (ro_skip and
                                         o.type == "RANGE_OPEN"))
                    slot_free = fam_n < sp.get("famlive_" + lf, 1)
                if slot_free and sp.get("fam_total_live"):
                    # R39 §39.6: joint panel budget — the author's
                    # joint live distribution on TUNE is median 1,
                    # p90 2 (SCALE reference); the per-kind caps
                    # admit every quota at once, which the author
                    # never does.  Cap total live objects.
                    if n_act >= sp["fam_total_live"]:
                        slot_free = False
            if slot_free and sp.get("fam_budget") \
                    and sp.get("fam_caps"):
                # R36 §36.3 variant: hold each returning kind to the
                # author's own TUNE count — golden per-panel max is
                # CR 1 / CL 1 / MINI 2 / SQZ 1 over 198 panels, so a
                # kind may not birth past famcap_<kind> objects in a
                # panel.  Counts born objects (covers annot kinds like
                # SQUEEZE that bypass the signal/context ledger).
                fc = sp.get("famcap_" + c.kind.lower())
                if fc and sum(
                        1 for o in e.objects
                        if o.type == c.kind) >= fc:
                    if "fam_capped" not in c._logged:
                        e._cand(c.kind, i, c.route, "fam_capped",
                                self._geom_log(c), score=c.score)
                        c._logged.add("fam_capped")
                    return
            if c.kind == "LABEL_TF" and sp.get("rate_label_tf"):
                # B3(i) playbook: with BAR_MARKER off the annot lane is
                # empty and poke labels flood (189 -> 616 on TUNE).
                # Golden marks run p90 = 1/day — cap births per
                # context_window_bars like rate_context/rate_mini_day.
                # Counts objects (not the ledger): annot kinds never
                # enter _births.
                if sum(1 for o in e.objects
                       if o.type == "LABEL_TF"
                       and o.t_birth > i - sp["context_window_bars"]) \
                        >= sp["rate_label_tf"]:
                    if "rate_limited" not in c._logged:
                        e._cand(c.kind, i, c.route, "rate_limited",
                                self._geom_log(c), score=c.score)
                        c._logged.add("rate_limited")
                    return
            sup = self._suppressed(c, i)
            if sup is not None:
                e._cand(c.kind, i, c.route, "nms_suppressed",
                        self._geom_log(c), score=c.score, by=sup)
                c.expires = i  # lose once — the structure is covered
                return
            if sp.get("box_live_at_birth") and c.kind == "BOX":
                # A3-rule (R56, H5-causal KEEP vs density nulls): a
                # box births only while price interacts with it —
                # close inside the band or within 0.5*ABR of an edge
                # (0.5 pre-stated in BOX-LAB r57_causal).  Pending
                # cands keep their seat; the gate is continuous.
                px = e.bars[i]["c"]
                abr = e.abr[i] if i < len(e.abr) and e.abr[i] else 5.0
                bnd = c.band(i)
                if bnd is None or not (
                        bnd[0] <= px <= bnd[1] or
                        min(abs(px - bnd[0]), abs(px - bnd[1]))
                        <= 0.5 * abr):
                    if "not_live" not in c._logged:
                        e._cand(c.kind, i, c.route, "not_live",
                                self._geom_log(c), score=c.score)
                        c._logged.add("not_live")
                    return
            lvs = sp.get("box_live_scope")
            if lvs and c.kind == "BOX" and c.t1 is not None \
                    and c.t1 < i - lvs:
                # A1 (R56 s.56.4): the box must be current — its span
                # end within K bars of now (a span containing now
                # trivially qualifies).  Stale cands keep their pool
                # seat — not evicted — but cannot take the slot.
                if "not_current" not in c._logged:
                    e._cand(c.kind, i, c.route, "not_current",
                            self._geom_log(c), score=c.score)
                    c._logged.add("not_current")
                return
            if c.score < sp["min_score_birth"]:
                if "below_min_score" not in c._logged:
                    e._cand(c.kind, i, c.route, "below_min_score",
                            self._geom_log(c), score=c.score)
                    c._logged.add("below_min_score")
                return
            # grave check BEFORE any displacement: a blocked candidate
            # must not kill an incumbent on its way out.
            if self._grave_hit(c, i):
                c.expires = i
                return
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
                            return
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
                                return
                    # R39 §39.4 / R40 §40.3: box supersede — the same
                    # ledger-transfer mechanism as lc_score_pick,
                    # generalized to fam == "box".  BOX-LAB's kill
                    # trace: 26 of 40 proposed-but-dead box goldens
                    # die rate-limited behind a weaker earlier box
                    # whose birth still holds the 72-bar slot.
                    # Arm A (box_score_pick): score decides inside the
                    # family — a rate-blocked box outscoring the slot
                    # holder's current act_scores by hyst_margin takes
                    # the slot; the holder closes "superseded" and its
                    # ledger entry moves (no extra ink rate).
                    # Arm B (box_score_pick_prio): adds the spec's
                    # priority-1 gate (§5) — supersede only when the
                    # new box CONTAINS the current close and the
                    # holder's band no longer does (price has left).
                    if sp.get("box_score_pick") and fam == "box":
                        win_bars = {b for f_, b in self._births
                                    if f_ == fam and b > i - win}
                        # under box_prio the ledger slot can be held
                        # by any box-family member (a CONTEXT_RANGE
                        # is a legal holder) — flag-off keeps the
                        # arm-A BOX-only holder set identical.
                        hk = ("BOX", "RANGE_OPEN", "CONTEXT_RANGE") \
                            if sp.get("box_prio") else ("BOX",)
                        holders = [o for o in e.objects
                                   if o.type in hk
                                   and o.t_birth in win_bars]
                        live_h = [o for o in holders
                                  if o.state == "ACTIVE"
                                  and not o.geometry.get("_pend_break")]
                        pool_h = live_h or holders
                        if pool_h:
                            if sp.get("box_prio"):
                                # R42 §42.4: the spec's box priority —
                                # a box containing/just-left by price
                                # outranks every CONTEXT_RANGE and
                                # stale box regardless of score; the
                                # ledger slot goes to the class-1
                                # candidate without a score margin.
                                cprio = self._box_prio(
                                    c.kind, c.band(i), i)
                                weakest = min(
                                    pool_h,
                                    key=lambda o: (
                                        self._box_prio(
                                            o.type,
                                            self._band_of(
                                                o.type, o.geometry, i),
                                            i),
                                        act_scores.get(
                                            o.id,
                                            getattr(o, "score", None)
                                            or 0.0)))
                                wprio = self._box_prio(
                                    weakest.type,
                                    self._band_of(weakest.type,
                                                  weakest.geometry, i),
                                    i)
                                wsc = act_scores.get(
                                    weakest.id,
                                    getattr(weakest, "score", None)
                                    or 0.0)
                                wins = cprio > wprio or (
                                    cprio == wprio and
                                    c.score > wsc + sp["hyst_margin"])
                            else:
                                weakest = min(
                                    pool_h,
                                    key=lambda o: act_scores.get(
                                        o.id,
                                        getattr(o, "score", None)
                                        or 0.0))
                                wsc = act_scores.get(
                                    weakest.id,
                                    getattr(weakest, "score", None)
                                    or 0.0)
                                wins = c.score > wsc + sp["hyst_margin"]
                            if wins:
                                gate_ok = True
                                if sp.get("box_score_pick_prio"):
                                    px = e.bars[i]["c"]
                                    cb2 = c.band(i)
                                    hb = self._band_of(
                                        weakest.type,
                                        weakest.geometry, i)
                                    gate_ok = (
                                        cb2 is not None and
                                        hb is not None and
                                        cb2[0] <= px <= cb2[1] and
                                        not (hb[0] <= px <= hb[1]))
                                if gate_ok:
                                    if weakest.state == "ACTIVE":
                                        weakest.event(
                                            i, "superseded",
                                            "BOX %.2f>%.2f" % (
                                                c.score, wsc))
                                        weakest.close(i, "superseded")
                                        self._grave[
                                            self._sig_obj(weakest)] = \
                                            i + sp["cand_ttl_bars"]
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
                                    e._cand(c.kind, i, c.route,
                                            "born",
                                            self._geom_log(c),
                                            score=c.score)
                                    return
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
                    return
            if not slot_free and ctx_yield and \
                    FAMILY.get(c.kind) == "box" and \
                    self._box_prio(c.kind, c.band(i), i):
                slot_free = self._yield_birth(c, ctx)
            if not slot_free and ctx_convert and \
                    FAMILY.get(c.kind) == "box" and \
                    self._box_prio(c.kind, c.band(i), i):
                if self._ctx_convert(c, ctx):
                    return
            if not slot_free:
                slot_free = self._displace(c, ctx, live)
            if not slot_free:
                if "outranked" not in c._logged:
                    e._cand(c.kind, i, c.route, "outranked",
                            self._geom_log(c), score=c.score)
                    c._logged.add("outranked")
                return
            if not self._joint_pass(c, ctx):
                return
            o = e._birth(c, i, c.score)
            act_scores[o.id] = c.score
            born.append(o)
            c.expires = i
            bk = None if c.kind == "RANGE_OPEN" else c.kind.lower()
            if cls in ("signal", "context") and bk is not None:
                self._births.append((bk, i))
            e._cand(c.kind, i, c.route, "born",
                    self._geom_log(c), score=c.score)

    def _yield_birth(self, c, ctx):
        """R49 §49.4.2 yield-on-propose: a priority-1 box does
        not evict the context incumbent — the context yields
        (hides) and returns unchanged once no box is live.
        Only when context alone holds the family slot; a
        real box incumbent still gates through the normal
        displacement path.  RANGE_OPEN doesn't block — it is
        the box's own precursor (asia_convert absorbs it).
        The yield is a re-label, not a takeover: it fires
        only when the incumbent's band overlaps the
        candidate's — the context that IS this price region."""
        i = ctx.i
        e = self.e
        cb = c.band(i)
        blockers = [o for o in e.active()
                    if FAMILY.get(o.type) == "box"
                    and o.type != "RANGE_OPEN"
                    and not o.geometry.get("_pend_break")]

        def _ovl(o):
            ob = self._band_of(o.type, o.geometry, i)
            return ob is not None and ob[0] is not None and \
                cb is not None and cb[0] is not None and \
                ob[1] >= cb[0] and ob[0] <= cb[1]

        if blockers and all(
                o.type in ("CONTEXT_RANGE", "CONTEXT_LINE")
                and _ovl(o)
                for o in blockers):
            for o in blockers:
                o._yielded = True
                o.state = "DELETED"
                o.event(i, "yield", "prio-1 box birth")
                self._hidden_ctx.append(o)
            return True
        return False

    def _ctx_convert(self, c, ctx):
        """R51 §51.4.2 conversion-in-place: a CONTEXT_RANGE
        that meets a priority-1 box candidate becomes that
        box (the asia_convert precedent) — same object
        relabelled and re-edged, zero net births, zero new
        ink footprint (t_left kept).  Only when every
        blocker is context; a real BOX incumbent still goes
        through displacement.  Returns True when the
        conversion consumed the candidate."""
        i = ctx.i
        e = self.e
        act_scores = ctx.act_scores
        cb = c.band(i)
        blockers = [o for o in e.active()
                    if FAMILY.get(o.type) == "box"
                    and o.type != "RANGE_OPEN"
                    and not o.geometry.get("_pend_break")]

        def _ovl_c(o):
            ob = self._band_of(o.type, o.geometry, i)
            return ob is not None and ob[0] is not None and \
                cb is not None and cb[0] is not None and \
                ob[1] >= cb[0] and ob[0] <= cb[1]

        conv = [o for o in blockers
                if o.type == "CONTEXT_RANGE" and _ovl_c(o)]
        # the context must BE this region, not merely touch
        # it: the band contains the box and is at most ~2x
        # its width.  A wide structural envelope converted
        # to a tight box loses the coverage levels/lines
        # scored against (loose-overlap variant: 186
        # conversions, level -4 line -3); edge-equality
        # rejects the fixtures (fixture context is ~1.5x).
        def _wraps(o):
            ob = self._band_of(o.type, o.geometry, i)
            if ob is None or ob[0] is None:
                return False
            ow, cw = ob[1] - ob[0], cb[1] - cb[0]
            return ob[0] <= cb[0] and ob[1] >= cb[1] and \
                ow <= 2.0 * cw
        conv = [o for o in conv if _wraps(o)]
        if conv and all(o.type in ("CONTEXT_RANGE",
                                   "CONTEXT_LINE")
                        for o in blockers):
            o = conv[0]
            g = o.geometry
            o.type = "BOX"
            o.style = "solid"
            o.why = c.route
            for k, v in c.geom.items():
                g[k] = v
            g["sali"]["score"] = c.score
            g["sali"]["feats"].update(c.feats)
            o.priority = 1
            o.score = c.score
            act_scores[o.id] = c.score
            o.event(i, "ctx_convert",
                    "context_range -> box %s" % c.route)
            e._cand(c.kind, i, c.route, "ctx_convert",
                    self._geom_log(c), score=c.score)
            c.expires = i
            return True
        return False

    def _displace(self, c, ctx, live):
        """Displacement: beat the weakest same-class incumbent
        by margin, respecting min dwell.  Returns slot_free."""
        i, sp = ctx.i, ctx.sp
        e = self.e
        act_scores = ctx.act_scores
        slot_free = False
        if True:
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
            if sp.get("fam_budget"):
                # R38 §38.4 scoping: under per-family budgeting a
                # family at cap may only displace its OWN weakest
                # member — a box on a lab-rank scale must not
                # evict a live level sharing the class pool.
                cf = self._fam(c.kind)
                displaceable = [o for o in displaceable
                                if self._fam(o.type) == cf]
                if sp.get("box_prio"):
                    # R42 §42.4: draw from the whole FAMILY, not
                    # the budget class — a CONTEXT_RANGE is
                    # context-class but box-family, and it is
                    # exactly the incumbent the spec's priority
                    # exists to displace.
                    displaceable = [o for o in e.active()
                                    if FAMILY.get(o.type) == cf
                                    and not o.geometry.get(
                                        "_pend_break")
                                    and not (o.geometry.get(
                                        "pierced")
                                             and not o.geometry.get(
                                                 "dead"))]
            if sp.get("box_prio") and \
                    FAMILY.get(c.kind) == "box":
                # R42 §42.4: the family's live slot sorts by
                # (prio class, score) — a box containing price or
                # just left by it outranks every CONTEXT_RANGE
                # and stale box whatever the score; among equals
                # the score decides.
                cprio = self._box_prio(c.kind, c.band(i), i)
                weakest = min(
                    displaceable,
                    key=lambda o: (
                        self._box_prio(
                            o.type,
                            self._band_of(o.type, o.geometry, i),
                            i),
                        act_scores[o.id])) \
                    if displaceable else None
                wprio = self._box_prio(
                    weakest.type,
                    self._band_of(weakest.type,
                                  weakest.geometry, i), i) \
                    if weakest is not None else 0
            else:
                cprio = wprio = 0
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
            lvb_win = False
            if (sp.get("box_live_birth") or sp.get("box_edge_birth")) \
                    and weakest is not None \
                    and FAMILY.get(c.kind) == "box":
                # A4 (R58 s.58.3): the box slot admits by
                # liveness order.  A CURRENT (t1 >= now-30) cand
                # evicts an incumbent the contest says is dead-
                # handed, without score margin or dwell.
                # box_live_birth: cand band contains/near-contains
                #   price, incumbent band does not (measured INERT
                #   @b1d94617 - envelopes always contain price).
                # box_edge_birth (v2): cand qualifies when price
                #   interacts with it (close_at_box = inside the
                #   band or within 0.5*ABR of an edge); the
                #   incumbent defends its slot only while price is
                #   actually AT one of its edges (<=0.5*ABR) - a
                #   wide envelope merely containing price is not
                #   interaction.  Params: K=30 bars, X=0.5 ABR.
                _k = sp.get("box_live_scope") or 30
                _abr = e.abr[i] if i < len(e.abr) and e.abr[i] \
                    else 5.0
                _px = e.bars[i]["c"]
                _cb = c.band(i)
                _wb = self._band_of(weakest.type,
                                    weakest.geometry, i)
                if sp.get("box_edge_birth"):
                    _clive = _cb[0] is not None and (
                        _cb[0] <= _px <= _cb[1] or
                        min(abs(_px - _cb[0]), abs(_px - _cb[1]))
                        <= 0.5 * _abr)
                    _wlive = _wb[0] is not None and min(
                        abs(_px - _wb[0]), abs(_px - _wb[1])) \
                        <= 0.5 * _abr
                else:
                    _clive = _cb[0] is not None and (
                        _cb[0] <= _px <= _cb[1] or
                        min(abs(_px - _cb[0]), abs(_px - _cb[1]))
                        <= 0.5 * _abr)
                    _wlive = _wb[0] is not None and (
                        _wb[0] <= _px <= _wb[1] or
                        min(abs(_px - _wb[0]), abs(_px - _wb[1]))
                        <= 0.5 * _abr)
                lvb_win = (c.t1 is not None and c.t1 >= i - _k
                           and _clive and not _wlive)
            # R42 §42.4: a class-1 candidate takes the slot from a
            # class-0 incumbent without waiting out the dwell —
            # dwell is an anti-flicker guard among equals, not a
            # veto over the spec's ranking.
            if weakest is not None and \
                    (lvb_win or
                     (dwell_ok or cprio > wprio) and (
                     cprio > wprio or
                     (cprio == wprio and
                      c.score > act_scores[weakest.id] +
                      sp["hyst_margin"]))):
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
        return slot_free

    def _joint_pass(self, c, ctx):
        """R43 §43.4.2: joint cap on live STRUCTURE (annot
        transients not counted).  Over the cap the birth
        still proceeds — the lowest-priority droppable
        member yields, in reverse spec §5 order.
        Returns False when the cap vetoes the birth."""
        i, sp = ctx.i, ctx.sp
        e = self.e
        if sp.get("joint_struct"):
            struct = [o for o in e.active()
                      if budget_class(o.type) != "annot"
                      and not (sp.get("ev_uip_lvfree") and
                               o.geometry.get(
                                   "meta_uip_persist"))]
            if len(struct) >= sp["joint_struct"]:
                victim = self._joint_drop(struct, i)
                if victim is None:
                    if "joint_capped" not in c._logged:
                        e._cand(c.kind, i, c.route,
                                "joint_capped",
                                self._geom_log(c), score=c.score)
                        c._logged.add("joint_capped")
                    return False
                victim.event(i, "joint_cap",
                             "dropped for %s" % c.kind)
                victim.close(i, "joint_cap")
                self._grave[self._sig_obj(victim)] = \
                    i + sp["cand_ttl_bars"]
        return True

    def _pool_sweep(self, i):
        e = self.e
        for c in self.pool:
            if c.expires <= i:
                if "expired" not in c._logged:
                    e._cand(c.kind, i, c.route, "expired",
                            self._geom_log(c), score=c.score)
                self._grave[self._sig(c)] = c.born_i + \
                    self.e.p["salience"]["cand_ttl_bars"]
        self.pool = [c for c in self.pool if c.expires > i]
        self._grave = {s: u for s, u in self._grave.items() if u > i}

    def _geom_log(self, c):
        g = dict(c.geom)
        g["t_left"] = c.t0
        for fk, fv in c.feats.items():
            g.setdefault(fk, fv)
        return g
