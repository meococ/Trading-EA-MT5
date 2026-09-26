"""levels.py — LEVEL_CARRIED / MINI_LEVEL multi-route book (DN_LEVEL §5).

A level is a *memory*: price frozen at birth, never re-priced; only the
span extends (continuation route).  The stored price is the defended
extreme; the rendered zone is asymmetric — near side where TPs cluster,
far side where stops sit (RT3 P1).

Consumption: each touch inside the zone decrements `depth`; at 0 the
level demotes — it stops generating context (weight, not death).
Death: a close back through the zone, or panel end.

Routes: broken_edge, congestion_edge, continuation, session_extreme,
formation_extreme (MINI_LEVEL), marker-adjacent single-bar level.
"""

import gates
from salience import Candidate


class LevelBook:
    def __init__(self, eng):
        self.e = eng
        self._sess = {}            # window idx -> {"hi","lo","done"}
        # defended_origin route (flag level.defended_origin, R19 §19.3):
        # origin registry of defended prices — confirmed theta pivots
        # plus running session/Asia extremes with a grace period.
        self.origins = []          # {bar,price,dir,cls,n_def,last_t,...}
        self._run_hi = -1e18
        self._run_lo = 1e18

    # ---------------- generic spawn ------------------------------- #

    def spawn(self, i, price, route, side, src="", t0=None, mini=False):
        """Propose a carried-level candidate.  If a live same-side
        level already covers the price, this is a continuation event —
        extend, don't birth (DN_LEVEL route 3)."""
        e = self.e
        dd = e.p["level"]["dedupe_within_pips"]
        for o in e.active("LEVEL_CARRIED") + e.active("MINI_LEVEL"):
            g = o.geometry
            if g.get("side") == side and \
                    abs(g["price"] - price) <= dd:
                o.event(i, "continuation", "extends %s" % route)
                o.geometry["t1"] = i
                e._cand("LEVEL_CARRIED", i, route, "dedup_existing",
                        {"price": round(price, 2), "side": side})
                return o
        abr = e.abr[i]
        zn = max(e.p["level"]["z_near_pips"],
                 e.p["level"]["z_near_abr"] * abr)
        zf = min(e.p["level"]["z_far_abr_cap"] * abr,
                 zn + e.p["level"]["z_far_extra_pips"])
        geom = {"price": round(price, 2), "side": side,
                "z_near": round(zn, 2), "z_far": round(zf, 2),
                "depth": e.p["level"]["depth_init"],
                "t0": t0 if t0 is not None else i, "t1": i}
        # a broken/congestion-edge carry IS the parent edge continuing
        # (DN_LEVEL route 1-2): it inherits the source's defendedness
        feats = {"touches": 1, "prom_abr": 0.0}
        if src:
            src_o = next((o for o in e.objects if o.id == src), None)
            if src_o is not None:
                bf = src_o.geometry.get("sali", {}).get("feats", {})
                feats = {"touches": max(1, bf.get("touches", 0)),
                         "prom_abr": bf.get("prom_abr", 0.0)}
        kind = "MINI_LEVEL" if mini else "LEVEL_CARRIED"
        c = Candidate(kind, route, geom, i,
                      feats=feats,
                      meta={"src": src},
                      ttl=e.p["salience"]["cand_ttl_bars"])
        e.salience.propose(c)
        return c

    # ---------------- session extremes ---------------------------- #

    def session_update(self, i):
        """Track session hi/lo over the configured CET windows; at each
        window end propose session_extreme levels at the extremes."""
        e = self.e
        b = e.bars[i]
        if e.p["level"].get("defended_origin"):
            # flag ON replaces this route: running session/Asia extremes
            # feed the origin registry instead of window-end proposals.
            cm = b["cet_min"]
            if b["h"] > self._run_hi:
                self._run_hi = b["h"]
                self._mark_superseded(i, 1)
                self._add_origin(i, b["h"], 1,
                                 "asia" if cm < e.p["level"]
                                 ["def_asia_end_min"] else "session",
                                 sess=True)
            if b["l"] < self._run_lo:
                self._run_lo = b["l"]
                self._mark_superseded(i, -1)
                self._add_origin(i, b["l"], -1,
                                 "asia" if cm < e.p["level"]
                                 ["def_asia_end_min"] else "session",
                                 sess=True)
            return
        cm = b["cet_min"]
        day = b["t"] // 86400
        wins = e.p["level"]["session_windows_cet"]
        for k, (lo_m, hi_m) in enumerate(wins):
            key = (day, k)
            if lo_m <= cm < hi_m:
                s = self._sess.get(key)
                if s is None:
                    s = self._sess[key] = {"hi": b["h"], "lo": b["l"],
                                           "start": i, "done": False}
                s["hi"] = max(s["hi"], b["h"])
                s["lo"] = min(s["lo"], b["l"])
            elif key in self._sess and not self._sess[key]["done"]:
                s = self._sess[key]
                s["done"] = True
                if gates.hard_block(cm):
                    continue
                for price, side in ((s["hi"], "above"),
                                    (s["lo"], "below")):
                    self.spawn(i, price, "session_extreme", side,
                               t0=s["start"])
                self._sess[key] = s

    # ---------------- formation extremes (MINI_LEVEL) -------------- #

    def on_pivot(self, i, piv):
        """formation_extreme: a tight cluster of >=mini_min_pivots theta1
        pivots inside a <=mini_band_abr*ABR band over a short span is a
        named micro formation -> MINI_LEVEL candidates at its defended
        extremes (extreme-with-company via the cluster)."""
        e = self.e
        if e.p["level"].get("defended_origin"):
            # flag ON replaces this route: every confirmed pivot is a
            # defended-price origin (theta2 structural, theta1 micro).
            self._add_origin(piv.t_ext, piv.price, piv.dir,
                             "theta2" if e.book.is_structural(piv)
                             else "theta1")
            return
        lp = e.p["level"]
        al = [p for p in e.book.alive() if p.t_conf <= i]
        if len(al) < lp["mini_min_pivots"]:
            return
        abr = e.abr[i]
        # trailing micro pivots within the span cap
        tail = [p for p in al if i - p.t_ext <= lp["mini_span_max_bars"]]
        if len(tail) < lp["mini_min_pivots"]:
            return
        tail = tail[-(2 * lp["mini_min_pivots"]):]
        hi = max(p.price for p in tail if p.dir > 0) \
            if any(p.dir > 0 for p in tail) else None
        lo = min(p.price for p in tail if p.dir < 0) \
            if any(p.dir < 0 for p in tail) else None
        if hi is None or lo is None or hi - lo > lp["mini_band_abr"] * abr \
                or hi - lo <= 0:
            return
        t0 = min(p.t_ext for p in tail)
        # ceiling = the high cluster (extreme with company), floor =
        # the low cluster; both compete, salience picks
        for price, side in ((hi, "above"), (lo, "below")):
            geom = {"price": round(price, 2), "side": side,
                    "z_near": round(max(lp["z_near_pips"],
                                        lp["z_near_abr"] * abr), 2),
                    "z_far": round(min(lp["z_far_abr_cap"] * abr,
                                       lp["z_near_pips"] +
                                       lp["z_far_extra_pips"]), 2),
                    "depth": lp["depth_init"], "t0": t0, "t1": i}
            e.salience.propose(Candidate(
                "MINI_LEVEL", "formation_extreme", geom, i,
                feats={"touches": len(tail), "prom_abr": 0.0},
                ttl=min(e.p["salience"]["cand_ttl_bars"], 12)))

    # ---------------- maintenance --------------------------------- #

    def maintain(self, i):
        """Consumption + traverse-death for carried/mini levels."""
        e = self.e
        b = e.bars[i]
        if e.p["level"].get("defended_origin"):
            self._expire_sweep(i)
            self._touch_sweep(i, b)
            self._trigger(i, b)
        for o in list(e.active("LEVEL_CARRIED")) + \
                list(e.active("MINI_LEVEL")):
            g = o.geometry
            if o.why == "defended_origin":
                self._maintain_defended(o, i, b)
                continue
            p = g["price"]
            zn, zf = g.get("z_near", 1.0), g.get("z_far", 2.0)
            # zone: for support (side below) near = above, far = below
            if g["side"] == "below":
                lo_z, hi_z = p - zf, p + zn
            else:
                lo_z, hi_z = p - zn, p + zf
            inside = b["l"] <= hi_z and b["h"] >= lo_z
            traversed = (b["c"] < lo_z) if g["side"] == "below" \
                else (b["c"] > hi_z)
            if traversed and i > o.t_birth:
                o.event(i, "traversed", "close through zone")
                o.close(i, "traversed")
                continue
            if inside and i > o.t_birth:
                g["depth"] = g.get("depth", 3) - 1
                o.touches.append((i, round(p, 2)))
                if g["depth"] <= 0 and not g.get("consumed"):
                    g["consumed"] = True
                    g["sali"]["consumed"] = \
                        g["sali"].get("consumed", 0) + 3
                    o.event(i, "consumed",
                            "depth exhausted -> weight demote")

    # ---------------- defended_origin route (R19 §19.3, flag) ------ #
    # Ported from levellab/levels_lab.py (measured config, ROUND_L7/L8).
    # Golden levels are old defended pivots/session extremes; a level
    # births when price APPROACHES a defended origin, not at formation.
    # The route enforces its own live budget so salience never sees
    # more than def_level_max_live LC + def_mini_max_live MINI.

    def _def_tol(self, i):
        e = self.e
        abr = e.abr[i] if i < len(e.abr) else 5.0
        return max(e.p["level"]["def_touch_tol_pips"],
                   e.p["level"]["def_touch_tol_abr_frac"] * abr)

    def _add_origin(self, j, price, side, cls, sess=False):
        """Register a defended-price origin; merge into an existing
        same-side origin within touch tol, keeping the defended EDGE
        price (min for lows, max for highs) — never the mean."""
        tol = self._def_tol(j)
        for og in self.origins:
            if og["dir"] != side:
                continue
            if abs(og["price"] - price) <= tol:
                og["price"] = min(og["price"], price) if side < 0 \
                    else max(og["price"], price)
                og["n_piv"] = og.get("n_piv", 1) + 1
                prov = og["cls"] in ("theta1", "leg", "session",
                                     "asia")
                og["cls"] = cls if (prov and cls in ("theta1", "theta2")
                                    or og["cls"] == "theta1") \
                    else og["cls"]
                if "expire" in og and cls in ("theta1", "theta2"):
                    del og["expire"]   # confirmed pivot: no expiry
                return
        self.origins.append({"bar": j, "price": price, "dir": side,
                             "cls": cls, "n_def": 0, "n_piv": 1,
                             "last_t": j, "_run": False,
                             "sess": sess})

    def _mark_superseded(self, i, side):
        """A superseded session extreme gets sess_grace_bars to earn
        defences before the registry drops it."""
        for og in self.origins:
            if og.get("sess") and og["dir"] == side \
                    and "expire" not in og:
                og["expire"] = i + self.e.p["level"]["def_sess_grace_bars"]

    def _expire_sweep(self, i):
        lp = self.e.p["level"]
        self.origins = [og for og in self.origins
                        if not (og.get("expire") is not None
                                and i >= og["expire"]
                                and og["n_def"] < lp["def_min_defences"])]

    def _touch_sweep(self, i, b):
        """A bar extreme within tol of an origin = a defence event;
        consecutive in-tol bars count once."""
        tol = self._def_tol(i)
        for og in self.origins:
            ext = b["l"] if og["dir"] < 0 else b["h"]
            hit = abs(ext - og["price"]) <= tol
            if hit and not og["_run"]:
                og["n_def"] += 1
                og["last_t"] = i
                og.setdefault("tch", []).append(round(ext, 1))
            og["_run"] = hit

    def _live_score(self, i, n_def, price, last_t):
        """Budget ranker (ROUND_L7, CV-chosen): defences minus distance
        plus ret24 — a defence touch within def_ret24_bars."""
        e = self.e
        abr = max(e.abr[i] if i < len(e.abr) else 5.0, 1e-9)
        ret24 = 1.0 if i - last_t <= e.p["level"]["def_ret24_bars"] \
            else 0.0
        return n_def - abs(e.bars[i]["c"] - price) / abr + ret24

    def _budget_ok(self, i, og, eprice, kind):
        """Live budget inside the proposer (R19 §19.3 item 2): the route
        proposes only while live+pending < cap, or when the challenger
        beats the weakest live member (closed 'superseded', revivable).
        Salience never sees more than the cap from this route."""
        e = self.e
        lp = e.p["level"]
        cap = lp["def_level_max_live"] if kind == "LEVEL_CARRIED" \
            else lp["def_mini_max_live"]
        if not cap:
            return True
        live = [o for o in e.active(kind)
                if o.why == "defended_origin"]
        pending = [c for c in e.salience.pool
                   if c.kind == kind and c.route == "defended_origin"]
        if len(live) + len(pending) < cap:
            return True
        chal = self._live_score(i, og["n_def"], eprice, og["last_t"])
        if live:
            weakest = min(live, key=lambda o: self._live_score(
                i, o.geometry.get("n_def", 0), o.geometry["price"],
                o.geometry.get("last_touch", o.t_birth)))
            wscore = self._live_score(
                i, weakest.geometry.get("n_def", 0),
                weakest.geometry["price"],
                weakest.geometry.get("last_touch", weakest.t_birth))
            # eviction hysteresis (post-L11): under all-LC typing a
            # marginal challenger evicted a matched incumbent then
            # died within 2 bars — require a margin to evict.
            if chal > wscore + lp.get("def_evict_margin", 0.0):
                weakest.event(i, "superseded",
                              "budget evict by def=%d" % og["n_def"])
                weakest.close(i, "superseded")
                return True
        e._cand(kind, i, "defended_origin", "suppressed_budget",
                {"price": round(eprice, 2)},
                n_def=og["n_def"], score=round(chal, 3))
        return False

    def _trigger(self, i, b):
        """Birth when price approaches a defended origin."""
        e = self.e
        lp = e.p["level"]
        abr = max(e.abr[i] if i < len(e.abr) else 5.0, 1e-9)
        for og in self.origins:
            if og["n_def"] < lp["def_min_defences"]:
                continue
            eprice = og["price"]
            dist = abs(b["c"] - eprice) / abr
            if dist > lp["def_approach_abr"]:
                continue
            # def_price_mode="modal" (post-L11): residual trusted misses
            # are sub-2p off the defended EDGE — propose at the modal
            # defence touch instead (the author's anchor price).
            if lp.get("def_price_mode") == "modal" and og.get("tch"):
                from collections import Counter as _Ct
                eprice = _Ct(og["tch"]).most_common(1)[0][0]
            age = (i - og["bar"]) * 5
            score = og["n_def"] - dist
            feats = {"touches": og["n_def"], "prom_abr": 0.0,
                     "n_def": og["n_def"], "n_piv": og.get("n_piv", 1),
                     "age_min": age, "dist_abr": round(dist, 2),
                     "cls": og["cls"], "ret24": int(
                         i - og["last_t"] <= lp["def_ret24_bars"])}
            e._cand("LEVEL_CARRIED", i, "defended_origin", "proposed",
                    {"price": round(eprice, 2)}, score=round(score, 3),
                    **feats)
            if score < lp["def_min_score"]:
                continue
            kind = "MINI_LEVEL" if age <= lp["def_mini_max_age_min"] \
                else "LEVEL_CARRIED"
            # v2 sub-flag (R24 §24.2): defended MINIs are ~43% of
            # births with 0/31 golden hits and spend the shared
            # rate_total ledger — LC-only arm skips them.
            if kind == "MINI_LEVEL" and lp.get("def_mini_off"):
                continue
            # v2b (measured after v2): the family match is
            # type-agnostic — young defended origins typed LC keep the
            # MINI-carried LC hits while consolidating on the 2-live
            # LC budget instead of the separate MINI slot.
            if lp.get("def_all_lc"):
                kind = "LEVEL_CARRIED"
            self._def_birth(i, og, eprice, score, kind)

    def _def_birth(self, i, og, eprice, score, kind):
        e = self.e
        lp = e.p["level"]
        band = lp["def_nms_band_pips"]
        # reprice: a challenger in-band at least as defended as the
        # incumbent's ORIGIN moves the level to the better edge and
        # keeps the early birth (side-free: defended zones flip roles).
        for o in e.active("LEVEL_CARRIED") + e.active("MINI_LEVEL"):
            g = o.geometry
            if o.why == "defended_origin" and \
                    abs(g["price"] - eprice) <= band:
                if og["n_def"] >= g.get("n_def0", 0):
                    g["price"] = round(eprice, 2)
                    g["n_def0"] = og["n_def"]
                    g["n_def"] = max(g.get("n_def", 0), og["n_def"])
                    o.event(i, "reprice", "edge def=%d" % og["n_def"])
                return
        if not self._budget_ok(i, og, eprice, kind):
            return
        # revive a closed same-price defended level instead of new ink
        for o in reversed(e.objects):
            if o.state != "CLOSED" or o.why != "defended_origin":
                continue
            g = o.geometry
            if abs(g["price"] - eprice) <= band and \
                    i - (o.t_right or 0) <= lp["def_revive_bars"]:
                o.state = "ACTIVE"
                o.t_right = None
                g["n_def"] = max(g.get("n_def", 0), og["n_def"])
                o.event(i, "revive", "same price re-approach")
                return
        abr = max(e.abr[i] if i < len(e.abr) else 5.0, 1e-9)
        zn = max(lp["z_near_pips"], lp["z_near_abr"] * abr)
        zf = min(lp["z_far_abr_cap"] * abr, zn + lp["z_far_extra_pips"])
        geom = {"price": round(eprice, 2),
                "side": "above" if og["dir"] > 0 else "below",
                "z_near": round(zn, 2), "z_far": round(zf, 2),
                "depth": lp["depth_init"], "t0": i, "t1": i,
                "n_def": og["n_def"], "n_def0": og["n_def"],
                "cls": og["cls"], "last_touch": i,
                "origin_i": og["bar"]}
        feats = {"touches": og["n_def"], "prom_abr": 0.0,
                 "n_def": og["n_def"], "n_piv": og.get("n_piv", 1),
                 "age_min": (i - og["bar"]) * 5,
                 "dist_abr": round(abs(e.bars[i]["c"] - eprice)
                                 / abr, 2),
                 "cls": og["cls"],
                 "ret24": int(i - og["last_t"] <= lp["def_ret24_bars"])}
        e.salience.propose(Candidate(
            kind, "defended_origin", geom, i, feats=feats,
            ttl=e.p["salience"]["cand_ttl_bars"]))

    def _maintain_defended(self, o, i, b):
        """Lab lifecycle for defended_origin objects: die on price
        departure, 2 consecutive closes through, or staleness; count
        post-birth touches for the budget ranker."""
        e = self.e
        lp = e.p["level"]
        g = o.geometry
        abr = max(e.abr[i] if i < len(e.abr) else 5.0, 1e-9)
        tol = self._def_tol(i)
        hit = abs(b["h"] - g["price"]) <= tol or \
            abs(b["l"] - g["price"]) <= tol
        if hit:
            g["last_touch"] = i
            if not g.get("_run"):
                g["n_def"] = g.get("n_def", 0) + 1
        g["_run"] = hit
        dist = abs(b["c"] - g["price"])
        if dist > lp["def_live_abr"] * abr:
            o.event(i, "close", "price_left")
            o.close(i, "price_left")
            return
        sgn = (b["c"] > g["price"]) - (b["c"] < g["price"])
        if dist > tol and sgn and sgn != g.get("_last_sign", sgn):
            g["pierce_n"] = g.get("pierce_n", 0) + 1
            if g["pierce_n"] >= lp["def_traverse_bars"]:
                o.event(i, "close", "traversed")
                o.close(i, "traversed")
                return
        else:
            g["pierce_n"] = 0
        if sgn:
            g["_last_sign"] = sgn
        if i - g.get("last_touch", o.t_birth) > lp["def_stale_bars"]:
            o.event(i, "close", "stale")
            o.close(i, "stale")
