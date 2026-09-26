"""pipes.py — FamilyPipe shells (ARCH MIGRATION_PLAN A3).

Thin per-family delegates: BoxPipe/LinePipe/LevelPipe/AnnotPipe wrap
``e.boxes``/``e.lines``/``e.levels``/``e.patterns`` and forward every
attribute read to the wrapped book.  Pure indirection — same call
order, same methods; the pipes are the future carrier for per-family
state (Phase B) and for the event bus (B2+).
"""

from kernel import Candidate  # noqa: E402  (B5: EventBox birth)


class FamilyPipe:
    """Delegate shell: ``pipe.X`` == ``book.X`` for every attribute."""

    KIND = ""

    def __init__(self, book):
        self.book = book

    def pool_view(self):
        """B1 shadow view: this family's read-time slice of the
        shared salience pool (see Salience.pool_view).  Returns []
        under ``arch_v2`` OFF — no v2 state is ever constructed on
        the OFF path."""
        return self.e.salience.pool_view(self.KIND)

    def __getattr__(self, k):
        # self.__dict__ first: during unpickle the instance exists
        # before ``book`` is restored, and an unconditional
        # ``self.book`` read here re-enters __getattr__ forever
        # (pickle probes __setstate__/__getstate__ on the shell).
        book = self.__dict__.get("book")
        if book is None:
            raise AttributeError(k)
        return getattr(book, k)


class BoxPipe(FamilyPipe):
    KIND = "box"

    def __init__(self, book):
        super().__init__(book)
        # B5 (R75 s.75.5, MIGRATION_PLAN): UIP event state relocated
        # here with event_step().  engine._ev_box_birth (ev_route_box
        # arm) shares the cooldown counter via pipes.box._last_ev_birth.
        self._ev_uip_born = False
        self._last_ev_birth = -999

    def event_step(self, i, piv):
        """R62 s.62.4 T1/UIP-rd (BOX-LAB spec, REQUESTS.md s.19): the
        throttled event birth.  The event family holds exactly ONE
        live object: the first non-shadowed route cand births it
        directly (v0 birth path); every later non-shadowed
        range_double_* cand rewrites its (lo, hi, t0) in place —
        geometry mutation, no new object, no extra ink.  pullback_end
        cands never write.  Constants stated by the spec: WIN 600,
        MIN_SEP 8, PB_SEP 8, DTOL 2.0p, envelope 6-34p, dedup tol
        max(1p, .25*ABR), cooldown 10b (at first birth only; rewrites
        are free).  v1 lifecycle still kills/governs the object; the
        rank-1 grant lives in salience under this flag.

        B5: verbatim relocation of engine._ev_uip_step — same calls,
        same order, same writes; engine state reached via ``e``."""
        e = self.e
        DTOL, SEP, PBSEP, COOL = 2.0, 8, 8, 10
        HMIN, HMAX, WIN = 6.0, 34.0, 600
        idx, price, side = piv.t_ext, piv.price, piv.dir
        abr = e.abr[i] if i < len(e.abr) else 5.0
        dtol = max(1.0, 0.25 * abr)
        seq = [p for p in e.book.seq
               if p is not piv and p.t_ext <= idx]
        same = [p for p in seq if p.dir == side and idx - p.t_ext <= WIN]
        opp = [p for p in seq if p.dir == -side and idx - p.t_ext <= WIN]
        cands = []
        for prev in reversed(same):
            if idx - prev.t_ext < SEP:
                continue
            if abs(prev.price - price) <= DTOL:
                lo_i = min(prev.t_ext, idx)
                seg = e.bars[max(0, lo_i - 2):idx + 1]
                if side > 0:
                    top = max(prev.price, price)
                    bot = min(x["l"] for x in seg)
                else:
                    bot = min(prev.price, price)
                    top = max(x["h"] for x in seg)
                cands.append((bot, top, max(prev.t_ext, 0),
                              "ev_range_double_" +
                              ("top" if side > 0 else "bottom")))
                break
        if opp:
            last_opp = opp[-1]
            if side < 0:
                L, H = price, last_opp.price
            else:
                L, H = last_opp.price, price
            t0a = min(idx, last_opp.t_ext)
            # R68 s.68.3 V3 (flag ev_uip_pb_birth): while the panel has
            # no UIP object yet, the pullback_end cand forms at v0's
            # route gate (idx - t0a >= 3, engine_v0._box_birth) so it
            # may BIRTH the object as a BOX birth.  Once born, the gate
            # stays at PBSEP and rewrites remain rd-only (V1 semantics).
            pb_gate = 3 if (e.p["salience"].get("ev_uip_pb_birth")
                            and not self._ev_uip_born) else PBSEP
            if idx - t0a >= pb_gate:
                cands.append((L, H, t0a, "ev_pullback_end"))
        for c in cands[1:]:
            e._cand("BOX", i, c[3], "route_shadow",
                    {"top": c[1], "bottom": c[0], "t0": c[2]})
        if not cands:
            return
        lo, hi, t_left, why = cands[0]
        evs = [o for o in e.active("BOX")
               if o.geometry.get("meta_ev_route")]
        if evs:
            o = evs[-1]
            # R66 s.66.3 V2 (flag ev_uip_pb_write): UIP-all - the
            # pullback_end route rewrites the object too (DR-BOX
            # measured +2 edge-exact over rd-only on the reachable
            # set).  Default stays rd-only per the T1 spec.
            if why.startswith("ev_range_double") or (
                    why == "ev_pullback_end" and
                    e.p["salience"].get("ev_uip_pb_write")):
                o.geometry["top"] = round(hi, 2)
                o.geometry["bottom"] = round(lo, 2)
                o.geometry["t0"] = int(t_left)
                if e.p["salience"].get("ev_uip_buildstart"):
                    o.geometry["meta_build_start"] = \
                        e._uip_build_start(lo, hi, t_left)
                o.event(i, "uip_rewrite",
                        "%s -> [%.1f,%.1f] t0=%d" % (why, lo, hi,
                                                     t_left))
                e._cand("BOX", i, why, "uip_rewrite",
                        {"top": round(hi, 2), "bottom": round(lo, 2),
                         "t0": int(t_left)})
            else:
                e._cand("BOX", i, why, "uip_skip_pb",
                        {"top": round(hi, 2), "bottom": round(lo, 2),
                         "t0": int(t_left)})
            return
        if self._ev_uip_born:
            # spec: exactly ONE object per panel - the family does not
            # re-birth after the object's (v1-lifecycle) death.
            e._cand("BOX", i, why, "uip_spent",
                    {"top": hi, "bottom": lo, "t0": t_left})
            return
        if not (HMIN - 0.01 <= hi - lo <= HMAX + 0.01):
            e._cand("BOX", i, why, "vetoed_height",
                    {"top": hi, "bottom": lo, "t0": t_left})
            return
        if idx - self._last_ev_birth < COOL:
            e._cand("BOX", i, why, "vetoed_cooldown",
                    {"top": hi, "bottom": lo, "t0": t_left})
            return
        for o in e.active("BOX"):
            g = o.geometry
            if abs(g["top"] - hi) <= dtol and \
                    abs(g["bottom"] - lo) <= dtol:
                e._cand("BOX", i, why, "dedup_existing",
                        {"top": hi, "bottom": lo, "t0": t_left})
                return
        cand = Candidate(
            "BOX", why, {"top": round(hi, 2), "bottom": round(lo, 2),
                         "t0": int(t_left), "t1": int(idx)}, i,
            meta={"ev_route": True,
                  "uip_persist": bool(
                      e.p["salience"].get("ev_uip_persist"))})
        sc, _c = e.salience.score(cand, i, is_cand=True)
        o = e._birth(cand, i, sc)
        if o is not None:
            if e.p["salience"].get("ev_uip_buildstart"):
                o.geometry["meta_build_start"] = \
                    e._uip_build_start(lo, hi, t_left)
            self._last_ev_birth = idx
            self._ev_uip_born = True
            e._cand("BOX", i, why, "uip_birth",
                    {"top": round(hi, 2), "bottom": round(lo, 2),
                     "t0": int(t_left)})


class LinePipe(FamilyPipe):
    KIND = "line"


class LevelPipe(FamilyPipe):
    KIND = "level"


class AnnotPipe(FamilyPipe):
    KIND = "annot"


class Pipes:
    """The engine's four family pipes, in fixed family order."""

    def __init__(self, eng):
        self.box = BoxPipe(eng.boxes)
        self.line = LinePipe(eng.lines)
        self.level = LevelPipe(eng.levels)
        self.annot = AnnotPipe(eng.patterns)
