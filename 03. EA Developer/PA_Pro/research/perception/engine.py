"""engine.py — PerceptionEngine v1 (design-note build).

Incremental, causal, deterministic.  Feed closed M5 bars via update();
objects at bar t depend on bars <= t only.  No outcomes, no future.

v1 architecture (the eight design notes):
  swings.py   — theta1 DC stream + prominence floor (theta2 = subset)
  boxes.py    — bucket-merge clustered edges, company rule, D9 windows
  lines.py    — hull anchors, max-touch select, freeze/pierce policy
  levels.py   — multi-route level book (broken/congestion/continuation/
                session/formation/marker)
  patterns.py — M/W/Mm/Ww/SHS brackets, squeeze, BAR_MARKER, LABEL_TF
  gates.py    — CET calendar gates, abnormal-vol + chop stand-asides
  salience.py — score -> NMS -> hysteresis -> budget (the ONLY
                selection mechanism; routes propose, ranking disposes)

Bar input: update(t, o, h, l, c, cet_min=None).  Prices absolute; the
engine works in pips internally (price * 1e4).  cet_min is supplied by
the caller's feed-aware clock; when omitted it is derived from the
feed: BOOK = Berlin wall (identity, D3); DESIGN = EET (CET = server-1h).
"""

import json
import os

import numpy as np

import gates
from swings import DCStream, SwingBook
from boxes import BoxBook
from lines import LineBook
from levels import LevelBook
from patterns import PatternBook
from salience import Salience, budget_class, Candidate
from objects import Obj, ObjectStore
from pipes import Pipes
import trade_tags as TT            # R78 s.78.4(3): pure predicates only

PIP = 1e4          # default pip multiplier (price * PIP = pips)

# A6 (MIGRATION_PLAN): declared retire-sweep family order — the
# ARCH_V2 target.  ARCH_REVIEW (c) A6: a family-major iteration is a
# behaviour change (wall_gone reads close order), so the sweep below
# keeps the parent append order (active()'s _oi sort) and this
# constant only documents the intended Phase-B order.
RETIRE_FAM_ORDER = ["box", "line", "level", "bracket", "squeeze",
                    "annot", "context"]

_DEFAULT_PARAMS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "params_v1_1.json")


def _pip_mult(symbol):
    """F3: pip multiplier from the symbol — price * mult = pips.  FX
    convention: a pip is the 4th decimal (EURUSD -> 1e4), JPY crosses
    the 2nd (USDJPY -> 1e2).  Other instruments keep the 5-digit FX
    default until the EA port supplies an explicit mult."""
    return 1e2 if symbol and "JPY" in symbol.upper() else PIP


def load_params(path=None):
    with open(path or _DEFAULT_PARAMS, encoding="utf8") as f:
        data = json.load(f)
    if "params" in data:
        _check_provenance(data["params"], data.get("provenance", {}))
        return data["params"]
    return data          # bare dict (tests may pass v0-style params)


def _check_provenance(params, prov, prefix=""):
    """Every leaf parameter must carry a provenance entry (DN_SALIENCE
    test i)."""
    missing = []
    for k, v in params.items():
        path = "%s.%s" % (prefix, k) if prefix else k
        if isinstance(v, dict):
            _check_provenance(v, prov, path)
        elif path not in prov:
            missing.append(path)
    if missing:
        raise ValueError("params without provenance: %s" % missing)


# ------------------------------------------------------------------ #
# objects
# ------------------------------------------------------------------ #
# A2 (R67 s.67.3 MIGRATION_PLAN): Obj + the object store moved to
# objects.py verbatim; imported above so `engine.Obj` (old pickles,
# lab scripts) still resolves.


# ------------------------------------------------------------------ #
# engine
# ------------------------------------------------------------------ #

class PerceptionEngine:
    """Causal M5 perception engine (Volman chart grammar), v1."""

    def __init__(self, params=None, feed=None, symbol=None, pip=None):
        self.p = params or load_params()
        self.feed = (feed or self.p.get("feed_clock") or "BOOK").upper()
        self.pip = float(pip) if pip else _pip_mult(symbol)
        self.bars = []                  # dicts: t,cet_min,o,h,l,c (pips)
        self.ema = []                   # EMA25 on close (pips)
        self.abr = []                   # ABR in pips
        # A2: the object registry lives in ObjectStore; `objects` and
        # `_act` below are property shims onto it (no call site moves).
        self.store = ObjectStore(self)
        self.domes = []                 # (idx, height_pips, side)
        self.bar_facts = []             # per-bar fact list
        self.pressure = {"state": "NEUTRAL", "since": 0, "conf": 0.0}
        self._ema_k = 2.0 / (self.p["ema_len"] + 1)
        sp = self.p["swing"]
        # R73 §73.2 L-4 V2 (swing.prom_snap): prominence computed on
        # prices snapped to the line family's 0.5*touch-tol grid —
        # anchor-zone stability upstream of lines AND boxes.
        _snap_fn = self._snap_tol if sp.get("prom_snap") else None
        self.book = SwingBook(sp["pmin_abr"], sp["pstruct_abr"],
                              abr_fn=self._abr, snap_fn=_snap_fn)
        self.dc = DCStream(self._theta, self._spike)
        self.boxes = BoxBook(self)
        self.lines = LineBook(self)
        self.levels = LevelBook(self)
        self.patterns = PatternBook(self)
        # A3: thin FamilyPipe shells — engine call sites go through
        # pipes.* while the books stay put (pure indirection).
        self.pipes = Pipes(self)
        self.salience = Salience(self)
        dp = self.p["derived"]
        self.todvol = gates.TodVol(dp["tod_window_days"],
                                   dp["abnormal_vol_q"],
                                   dp["abnormal_vol_mult"])
        self._cur_day = None
        self._day_hi = None
        self._day_lo = None
        self._day_ranges = []
        self._last_birth_i = None
        self._prev_birth_i = None
        # B5: _last_ev_birth/_ev_uip_born live on pipes.box (event_step).
        self.w0_min = None              # R66 s.66.4: panel left edge (cet)
        # R63 s.63.4 option-B port (prep only, default OFF): when
        # salience.box_v0_family is on, a verbatim engine_v0 instance
        # runs alongside on the same bar stream; its box-family objects
        # (BOX, RANGE_OPEN) are mirrored into self.objects while v1's
        # own box-family cands are suppressed in salience.round.
        # Mirrors never enter _act, so v1 budgets/scoring/eviction are
        # untouched; v0's own lifecycle is authoritative (state synced
        # each bar).  This reproduces the R60 hybrid in one engine.
        self._v0e = None
        self._v0m = {}
        if self.p["salience"].get("box_v0_family"):
            import engine_v0 as _E0
            self._v0e = _E0.PerceptionEngine()
            self._v0e.cand_log = []
        # candidate-universe audit channel (Ruling 2 §2.2.3): assign a
        # list to receive every evaluated candidate's score + outcome
        self.cand_log = None

    # ---------------- helpers ------------------------------------ #

    def _theta(self, i):
        """DC retrace threshold: theta1 = k1 * ABR (wick mode)."""
        return self.p["swing"]["k1_abr"] * \
            (self.abr[i] if i < len(self.abr) else 5.0)

    def _spike(self, i):
        """Lone-spike flag: bar range >> ABR (DN_SWING spike class)."""
        if i >= len(self.bars):
            return False
        rng = self.bars[i]["h"] - self.bars[i]["l"]
        return rng > self.p["swing"]["spike_abr_mult"] * \
            (self.abr[i] if i < len(self.abr) else 5.0)

    def _cand(self, kind, idx, route, outcome, geom=None, **feats):
        if self.cand_log is None:
            return
        b = self.bars[idx]
        row = {"kind": kind, "idx": int(idx), "cet_min": b.get("cet_min"),
               "route": route, "outcome": outcome, "close": b["c"],
               "abr": round(self.abr[idx], 2) if idx < len(self.abr)
               else None,
               "ema": round(self.ema[idx], 2) if idx < len(self.ema)
               else None}
        row["n_active"] = len(self.active())
        if geom:
            row.update(geom)
        row.update(feats)
        self.cand_log.append(row)

    def _tol(self):
        """Generic edge tolerance: max(1 pip, 0.25*ABR)."""
        bp = self.p["box"]
        abr = self.abr[-1] if self.abr else 5.0
        return max(bp["break_tol_pips"], bp["break_tol_abr_frac"] * abr)

    def _abr(self, i):
        return self.abr[i] if i < len(self.abr) else 5.0

    def _snap_tol(self, j):
        # L-4 V2 grid: half the line touch tolerance. Bound method (not
        # lambda) so SwingBook.snap_fn survives pickling.
        lp = self.p["line"]
        return 0.5 * max(lp["touch_tol_pips"],
                         lp["touch_tol_abr_frac"] * self._abr(j))

    # ---- object store shims (A2: real impl in objects.py) --------- #

    def __setstate__(self, d):
        # legacy pickles (pre-A2) carry objects/_act in the engine
        # __dict__; route them into the ObjectStore they now live in.
        objs = d.pop("objects", None)
        act = d.pop("_act", None)
        # pre-B5 pickles carry _ev_uip_born/_last_ev_birth on the
        # engine; they now live on pipes.box (B5 relocation).
        uip_born = d.pop("_ev_uip_born", None)
        ev_birth = d.pop("_last_ev_birth", None)
        self.__dict__.update(d)
        if objs is not None or act is not None:
            st = ObjectStore(self)
            if objs is not None:
                st.all = objs
            if act is not None:
                st._act = act
            self.store = st
        if "pipes" not in self.__dict__:
            # pre-A3 pickles have no pipes record; rebuild the shells.
            self.pipes = Pipes(self)
        if uip_born is not None:
            self.pipes.box._ev_uip_born = uip_born
        if ev_birth is not None:
            self.pipes.box._last_ev_birth = ev_birth

    @property
    def objects(self):
        return self.store.all

    @property
    def _act(self):
        return self.store._act

    def active(self, otype=None):
        return self.store.active(otype)

    def _mk(self, otype, style, t_birth, geometry, why, role=""):
        return self.store.mk(otype, style, t_birth, geometry, why, role)

    def _birth(self, cand, i, score):
        return self.store.birth(cand, i, score)

    def _ev_box_birth(self, i, piv):
        """R61 s.61.4 event-route port (BOX-LAB spec, REQUESTS.md):
        v0's box birth criterion on v1's confirmed-pivot stream
        (book.seq).  At a confirmed pivot, evaluate v0's two routes —
        range_double_* (preferred) then pullback_end — and on a pass
        PROPOSE the BOX into the salience pool: v1's budget/lifecycle
        admits and governs it (spec: no one-governing-box veto, no v0
        lifecycle ports).  The incumbent CONTEXT_RANGE is never vetoed
        or deleted — the event box's rank-1 grant lives in salience.
        Birth conditions kept from v0: height 6-34p, edge dedup,
        10-bar cooldown between event proposals.  Constants are v0's
        params_v1.json values, stated in the log before the A/B."""
        DTOL, SEP, COOL = 2.0, 4, 10
        HMIN, HMAX = 6.0, 34.0
        WIN = self.p["window_bars"]
        idx, price, side = piv.t_ext, piv.price, piv.dir
        tol = self._tol()
        seq = [p for p in self.book.seq
               if p is not piv and p.t_ext <= idx]
        same = [p for p in seq if p.dir == side and idx - p.t_ext <= WIN]
        opp = [p for p in seq if p.dir == -side and idx - p.t_ext <= WIN]
        cands = []
        for prev in reversed(same):
            if idx - prev.t_ext < SEP:
                continue
            if abs(prev.price - price) <= DTOL:
                lo_i = min(prev.t_ext, idx)
                seg = self.bars[max(0, lo_i - 2):idx + 1]
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
        if opp and self.p["salience"].get("ev_route_pullback", True):
            last_opp = opp[-1]
            if side < 0:
                L, H = price, last_opp.price
            else:
                L, H = last_opp.price, price
            t0a = min(idx, last_opp.t_ext)
            if idx - t0a >= 3:
                cands.append((L, H, t0a, "ev_pullback_end"))
        for c in cands[1:]:
            self._cand("BOX", i, c[3], "route_shadow",
                       {"top": c[1], "bottom": c[0], "t0": c[2]})
        if idx - self.pipes.box._last_ev_birth < COOL:
            if cands:
                c = cands[0]
                self._cand("BOX", i, c[3], "vetoed_cooldown",
                           {"top": c[1], "bottom": c[0], "t0": c[2]})
            return
        if not cands:
            return
        lo, hi, t_left, why = cands[0]
        if not (HMIN - 0.01 <= hi - lo <= HMAX + 0.01):
            self._cand("BOX", i, why, "vetoed_height",
                       {"top": hi, "bottom": lo, "t0": t_left})
            return
        for o in self.active("BOX"):
            g = o.geometry
            if abs(g["top"] - hi) <= tol and \
                    abs(g["bottom"] - lo) <= tol:
                self._cand("BOX", i, why, "dedup_existing",
                           {"top": hi, "bottom": lo, "t0": t_left})
                return
        cand = Candidate(
            "BOX", why, {"top": round(hi, 2), "bottom": round(lo, 2),
                         "t0": int(t_left), "t1": int(idx)}, i,
            meta={"ev_route": True})
        self.salience.propose(cand)
        self.pipes.box._last_ev_birth = idx
        self._cand("BOX", i, why, "proposed",
                   {"top": round(hi, 2), "bottom": round(lo, 2),
                    "t0": int(t_left)})

    def _uip_build_start(self, lo, hi, t0):
        """R66 s.66.4 (BOX-LAB spec, REQUESTS.md s.20): episode-anchored
        recorded start for the event object.  From the cand's earlier
        pivot bar t0, walk back while the previous bar still overlaps
        [lo, hi]; cap at the panel's w0 bar (bar 0 when w0 unknown).
        Pure function of (lo, hi, t0, bars) - recomputed at every
        rewrite.  Returns a bar index; eval converts to minutes."""
        cap = 0
        if self.w0_min is not None:
            for j, b in enumerate(self.bars):
                if b.get("cet_min") is not None and \
                        b["cet_min"] >= self.w0_min:
                    cap = j
                    break
        bs = int(t0)
        while bs > cap and self.bars[bs - 1]["h"] >= lo and \
                self.bars[bs - 1]["l"] <= hi:
            bs -= 1
        return bs

    # B5 (R75 s.75.5): _ev_uip_step relocated verbatim to
    # BoxPipe.event_step in pipes.py - same calls, same order,
    # same writes; _ev_uip_born/_last_ev_birth moved with it.

    # ---------------- main update -------------------------------- #

    def update(self, t, o, h, l, c, cet_min=None):
        """Feed one closed M5 bar.  Prices in absolute terms."""
        i = len(self.bars)
        if cet_min is None:
            off = 0 if self.feed == "BOOK" else 3600   # DESIGN: EET->CET
            cet_min = int(((int(t) - off) % 86400) // 60)
        bar = {"i": i, "t": int(t), "cet_min": cet_min,
               "o": o * self.pip, "h": h * self.pip,
               "l": l * self.pip, "c": c * self.pip}
        self.bars.append(bar)

        # daily range (20-grid regime switch, spec §2)
        day = int(t) // 86400
        if self._cur_day is None:
            self._cur_day = day
        elif day != self._cur_day:
            if self._day_hi is not None:
                self._day_ranges.append(self._day_hi - self._day_lo)
                gw = self.p["derived"].get("grid_window_days", 10)
                self._day_ranges = self._day_ranges[-gw:]
            self._cur_day = day
            self._day_hi = self._day_lo = None
        self._day_hi = bar["h"] if self._day_hi is None \
            else max(self._day_hi, bar["h"])
        self._day_lo = bar["l"] if self._day_lo is None \
            else min(self._day_lo, bar["l"])

        # EMA25 + ABR + time-of-day vol stats
        self.ema.append(c * self.pip if i == 0 else
                        self.ema[-1] + self._ema_k *
                        (c * self.pip - self.ema[-1]))
        rng = bar["h"] - bar["l"]
        n = self.p["abr_len"]
        if i < n:
            self.abr.append(sum(x["h"] - x["l"] for x in self.bars)
                            / (i + 1))
        else:
            self.abr.append(self.abr[-1] +
                            (rng - (self.bars[i - n]["h"] -
                                    self.bars[i - n]["l"])) / n)
        self.todvol.update(cet_min, rng)

        self._bar_facts(i)

        # ---- swing stream ----
        self.book.update_running(self.dc.dir, self.dc.ext_price)
        for p in self.dc.update(i, bar["h"], bar["l"]):
            piv = self.book.add(p)
            self._dome_update(piv)
            self.pipes.annot.on_pivot(i, piv)
            self.pipes.level.on_pivot(i, piv)
            # the box *touch* may be a micro pivot — tight buildups
            # (9.44a) never confirm a theta2 pivot inside; the windows
            # and the alternation prior still anchor on the theta2
            # stream inside on_pivot (DN_BOX §5).  CONTEXT_RANGE keeps
            # the structural trigger (session-scale object).
            self.pipes.box.on_pivot(i, piv)
            if self.book.is_structural(piv):
                self.pipes.box.reanchor_check(i, piv)
                self.pipes.box.propose_context_range(i)
            if self.p["salience"].get("ev_route_box"):
                self._ev_box_birth(i, piv)
            if self.p["salience"].get("ev_uip"):
                self.pipes.box.event_step(i, piv)
            self.pipes.line.on_pivot(i, piv)

        # ---- trackers + lifecycle ----
        # A3 (ARCH_REVIEW c): this call order is the birth-order
        # contract — asia_update -> congestion_scan -> session_update
        # -> maintain x3 -> squeeze_scan -> _retire -> salience.round.
        # Do not reorder without a measured arm.
        self.pipes.box.asia_update(i)
        # bar-driven buildup route: tight congestions that never
        # confirm a pivot inside (9.44a, DN_BOX §6 false negatives)
        self.pipes.box.congestion_scan(i)
        self.pipes.level.session_update(i)
        self.pipes.box.maintain(i)
        self.pipes.line.maintain(i)
        self.pipes.level.maintain(i)
        self.pipes.annot.squeeze_scan(i)
        # Ruling 11 section 11.4a zombie retirement, after the books'
        # own maintain passes and before selection
        self._retire(i)
        # R83 s.83.4 arm Y: the incumbent yields to its own break
        self._box_yield_step(i)

        # ---- selection ----
        self.salience.round(i)
        self._pressure_update(i)
        self._trade_tag_step(i)

        # ---- option-B: v0 box-family mirror (R63 s.63.4) ----
        if self._v0e is not None:
            self._v0e.update(t, o, h, l, c, cet_min=cet_min)
            self._v0_sync(i)

    def _v0_sync(self, i):
        """Mirror engine_v0's box-family objects (BOX, RANGE_OPEN)
        into self.objects.  Mirrors are appended without _act
        registration: v1's active()-driven logic (budgets, eviction,
        scoring, retire) never sees them, so v1 internals reproduce
        the parent's exactly, while eval paths that read e.objects
        (eng_objects) or state!=DELETED (live_records) see the v0
        boxes.  Ranking falls to recency (score=None) — v0's
        newest-governs ordering.  Invariant (ARCH_REVIEW A2 fix): the
        Obj.state setter auto-registers in _act on an ACTIVE write —
        mirrors must therefore never RECEIVE an ACTIVE transition,
        which holds because engine_v0 never revives a closed object.
        If that ever changes, set mirror state via _state directly."""
        for v0o in self._v0e.objects:
            if v0o.type not in ("BOX", "RANGE_OPEN"):
                continue
            m = self._v0m.get(id(v0o))
            if m is None:
                g = dict(v0o.geometry)
                g["meta_v0_port"] = True
                m = Obj(v0o.type, v0o.style, v0o.t_birth, g,
                        why="v0:" + (v0o.why or ""),
                        oid="v0_" + v0o.id)
                m._oi = len(self.objects)
                m._eng = self
                m.t_left = v0o.t_left
                m.priority = v0o.priority
                m.score = None
                self.objects.append(m)
                self._v0m[id(v0o)] = m
                self._cand(v0o.type, i, "v0_port", "born",
                           {"top": g.get("top"),
                            "bottom": g.get("bottom"),
                            "t0": v0o.t_left})
            if m.state != v0o.state:
                m.state = v0o.state
            m.t_right = v0o.t_right
            m.t_left = v0o.t_left
            g2 = dict(v0o.geometry)
            g2["meta_v0_port"] = True
            m.geometry = g2
            m.events = list(v0o.events)

    # ---------------- zombie retirement (Ruling 11 §11.4a) -------- #

    def _retire(self, i):
        """An object price has left behind stops being drawn.
        retire_far:  close held > far_abr*ABR from the object's band
        for far_bars straight; retire_stale: no band interaction for
        stale_bars; a SQUEEZE ends when a close leaves its walls.
        Instant annotations (LABEL_TF, BAR_MARKER) are exempt."""
        lc = self.p.get("lifecycle")
        if lc is None:
            return
        b = self.bars[i]
        tol = self._tol()
        far = lc["far_abr"] * self.abr[i]
        # A6 (MIGRATION_PLAN): the sweep order is pinned to object
        # append order — the parent's emergent order (active() sorts
        # _act keys = _oi).  ARCH_REVIEW (c) A6 verdict BLOCK on
        # family-major: _squeeze_exit's wall_gone reads make close
        # order observable, so the family order lives in
        # RETIRE_FAM_ORDER as a declaration only (measured arm later).
        for o in self.active():
            if o.type in ("LABEL_TF", "BAR_MARKER"):
                continue
            g = o.geometry
            lo, hi = self.salience._band_of(o.type, g, i)
            if lo is None:
                continue
            dist = max(lo - b["c"], b["c"] - hi, 0.0)
            g["_far_n"] = (g.get("_far_n", 0) + 1) if dist > far else 0
            if b["l"] <= hi + tol and b["h"] >= lo - tol:
                g["_last_int"] = i
            if o.type == "SQUEEZE" and lc.get("wall_exit_enabled", True) \
                    and self._squeeze_exit(i, o, b):
                continue
            if lc.get("far_enabled", True) and \
                    g["_far_n"] >= lc["far_bars"]:
                o.close(i, "retire_far")
            elif lc.get("stale_enabled", True) and \
                    i - g.get("_last_int", o.t_birth) >= \
                    lc["stale_bars"]:
                o.close(i, "retire_stale")

    def _squeeze_exit(self, i, o, b):
        """A SQUEEZE ends when a close leaves its walls (§11.4a).
        Wall prices are re-evaluated from the wall object ids stored
        at birth (meta_walls); a dead wall voids the squeeze."""
        g = o.geometry
        wl_id, wu_id = g.get("meta_walls") or (None, None)
        lo = hi = None
        for wid, upper in ((wl_id, False), (wu_id, True)):
            if wid is None:
                continue
            if wid == "EMA25":
                pw = self.ema[i]
            else:
                wo = next((x for x in self.objects if x.id == wid),
                          None)
                if wo is None or wo.state != "ACTIVE":
                    o.close(i, "wall_gone")
                    return True
                band = self.salience._band_of(wo.type, wo.geometry, i)
                if band[0] is None:
                    o.close(i, "wall_gone")
                    return True
                # the wall edge facing the squeeze
                pw = band[0] if upper else band[1]
            if upper:
                hi = pw if hi is None else min(hi, pw)
            else:
                lo = pw if lo is None else max(lo, pw)
        if (hi is not None and b["c"] > hi) or \
                (lo is not None and b["c"] < lo):
            o.close(i, "wall_exit")
            return True
        return False

    # ---------------- bar facts ----------------------------------- #

    def _bar_facts(self, i):
        f = []
        b = self.bars[i]
        bf = {"strong_bar_vs_neighbours": 1.8,
              "inside_protrusion_pips": 1.0, "doji_body_frac": 0.15}
        if i >= 1:
            p = self.bars[i - 1]
            if b["h"] > p["h"]:
                f.append("breakout_up")
            if b["l"] < p["l"]:
                f.append("breakout_down")
            if b["h"] <= p["h"] + bf["inside_protrusion_pips"] and \
                    b["l"] >= p["l"] - bf["inside_protrusion_pips"]:
                f.append("inside")
            lo = max(0, i - 5)
            neigh = [self.bars[k]["h"] - self.bars[k]["l"]
                     for k in range(lo, i)]
            avg = sum(neigh) / len(neigh) if neigh else \
                max(0.01, b["h"] - b["l"])
            rng = b["h"] - b["l"]
            if rng >= bf["strong_bar_vs_neighbours"] * avg:
                body = b["c"] - b["o"]
                if rng > 0 and abs(body) > 0.6 * rng:
                    f.append("strong_up" if body > 0 else "strong_down")
            if i >= 2:
                b0, b1 = self.bars[i - 2], self.bars[i - 1]
                if b1["h"] > b0["h"] and b1["c"] < b1["o"] and \
                        b["l"] < b1["l"]:
                    f.append("false_high")
                if b1["l"] < b0["l"] and b1["c"] > b1["o"] and \
                        b["h"] > b1["h"]:
                    f.append("false_low")
        rng = b["h"] - b["l"]
        if rng > 0 and abs(b["c"] - b["o"]) <= bf["doji_body_frac"] * rng:
            f.append("doji")
        self.bar_facts.append(f)

    # ---------------- domes ---------------------------------------- #

    def _dome_update(self, piv):
        """Swing height vs the level it rose from; shrinking sequences
        are facts, never ink (spec §3.8)."""
        opp = [p for p in self.book.alive() if p.dir == -piv.dir
               and p.t_conf <= piv.t_conf]
        if not opp:
            return
        height = (piv.price - opp[-1].price) * piv.dir
        if height <= 0:
            return
        self.domes.append((piv.t_ext, round(height, 2), piv.dir))

    # ---------------- pressure / facts ----------------------------- #

    def _pressure_update(self, i):
        dp = self.p["derived"]
        hyst = dp["ema_slope_hysteresis_bars"]
        if i < self.p["ema_len"] + 5:
            return
        slope = self.ema[i] - self.ema[i - 5]
        flat = abs(slope) < 0.15 * self.abr[i]
        curv = (self.ema[i] - self.ema[i - 3]) - \
            (self.ema[i - 3] - self.ema[i - 6]) if i >= 6 else 0.0
        raw = self.pressure["state"]
        if not flat:
            want = "UP" if slope > 0 else "DOWN"
            if want != raw:
                if self.pressure.get("want") == want:
                    self.pressure["persist"] = \
                        self.pressure.get("persist", 0) + 1
                else:
                    self.pressure["want"] = want
                    self.pressure["persist"] = 1
                if self.pressure["persist"] >= hyst:
                    raw = want
            else:
                self.pressure["persist"] = 0
                self.pressure["want"] = None
        conf = min(1.0, abs(slope) / max(1.0, self.abr[i]))
        if curv * (1 if raw == "UP" else -1) < 0:
            conf *= 0.7
        self.pressure = {"state": raw, "since": i, "conf": round(conf, 2)}

    # ---------------- R78 s.78.4(3) TT: trade tags (facts only) ------ #

    def _box_yield_step(self, i):
        """R83 s.83.4 arm Y (flag box_yield: 0 off, 1 = box_broken
        only, 2 = box_broken OR stale_far).  A live box-family object
        whose yield predicate has set is closed as a natural death,
        reason 'yield_broken' - including the event/UIP incumbent
        despite ev_uip_persist (the veto is bypassed for THIS reason
        only; close() is not used).  Runs before salience.round so the
        freed slot is handled by the existing pool rules.  v0-port
        mirrors are not in _act, so active() never yields them.
        Nothing else changes: no score, rank, budget or generation
        change.  OFF == parent (early return)."""
        mode = int(self.p.get("box_yield", 0) or 0)
        if not mode:
            return
        c = np.asarray([b["c"] for b in self.bars])
        abr = np.asarray(self.abr)
        h = l = None
        for ob in list(self.active()):
            if TT._TYPE_FAM.get(ob.type) != "box":
                continue
            g = ob.geometry
            if "top" not in g:
                continue
            j1 = min(int(g.get("t1_drawn") or
                         (ob.t_right if ob.t_right is not None else i)),
                     i)
            j0 = min(int(ob.t_left), j1)
            dead = TT.s_box_broken(g["bottom"], g["top"], j0, j1,
                                   c, abr).get("bbroken")
            if not dead and mode >= 2:
                if h is None:
                    h = np.asarray([b["h"] for b in self.bars])
                    l = np.asarray([b["l"] for b in self.bars])
                jb = int(ob.t_birth) if ob.t_birth is not None \
                    else None
                dead = TT.s_stale_far("box", g, jb, j1, h, l, c,
                                      abr).get("stale")
            if dead:
                # natural death incl. UIP incumbents (s.83.4)
                ob.t_right = i
                ob.state = "CLOSED"
                ob.events.append((i, "close", "yield_broken"))

    def _trade_tag_step(self, i):
        """Observability-only Owner-rule facts on every live object.

        Delegates to trade_tags.tags_for — the same predicates
        DR_RULES_measure imports back (single source).  Writes
        object.facts["trade_tags"] = {bar, tags, tradeable}; nothing
        in the engine reads it back, it is excluded from canonical(),
        and it never alters geometry/state/ranking/selection.
        Causal: uses bars <= i only."""
        if not self.p.get("trade_tags"):
            return
        arr = {"m": np.asarray([b["cet_min"] for b in self.bars]),
               "o": np.asarray([b["o"] for b in self.bars]),
               "h": np.asarray([b["h"] for b in self.bars]),
               "l": np.asarray([b["l"] for b in self.bars]),
               "c": np.asarray([b["c"] for b in self.bars])}
        ema = np.asarray(self.ema)
        abr = np.asarray(self.abr)
        for ob in self.active():
            tags, st = TT.tags_for(ob, i, arr,
                                   ema, abr, self.book.seq)
            rec = {"bar": i, "tags": sorted(tags),
                   "tradeable": TT.tradeable(tags)}
            if "box_broken" in tags:               # R83 s.83.2 facts
                rec["exit_bar"] = st.get("exit_bar")
                rec["break_clause"] = st.get("break_clause")
            ob.facts["trade_tags"] = rec

    def _grid_step(self):
        dp = self.p["derived"]
        if len(self._day_ranges) < 3:
            return 50
        r = sorted(self._day_ranges)
        med = r[len(r) // 2] if len(r) % 2 else \
            (r[len(r) // 2 - 1] + r[len(r) // 2]) / 2
        return 20 if med < dp["low_vol_daily_range_pips"] else 50

    def _chop(self, i):
        """Efficiency-ratio chop measure (DN_TF §5, RT4 §12.9)."""
        n = self.p["derived"]["chop_er_bars"]
        if i < n:
            return False
        seg = self.bars[i - n:i + 1]
        net = abs(seg[-1]["c"] - seg[0]["c"])
        path = sum(abs(seg[k + 1]["c"] - seg[k]["c"])
                   for k in range(len(seg) - 1))
        er = net / path if path > 0 else 0.0
        return er < self.p["derived"]["chop_er_min"]

    def stand_aside(self, i):
        """First-class engine output: reasons to stand aside at bar i."""
        out = []
        b = self.bars[i]
        cm = b["cet_min"]
        win = gates.windows_at(cm)
        if "us_data" in win or "ecb_fix" in win:
            out.append("news_window")
        if "wmr_fix" in win:
            out.append("wmr_fix")
        if "option_cut" in win:
            out.append("option_cut")
        rng = b["h"] - b["l"]
        if self.todvol.alarm(cm, rng, self.abr[i]):
            out.append("abnormal_vol")
        if self._chop(i):
            out.append("chop")
        c = b["c"]
        rn = round(c / 50.0) * 50.0
        for o in self.active("BOX"):
            if o.geometry["bottom"] < rn < o.geometry["top"]:
                out.append("round_number_battle")
        sig = [o for o in self.active()
               if budget_class(o.type) == "signal"
               and not o.geometry.get("dead")]
        if not sig:
            out.append("no_structure")
        return out

    def facts(self, i):
        """Derived facts for the setup layer (spec §4)."""
        b = self.bars[i]
        tol = self._tol()
        c = b["c"]
        rn_lo = (int(c) // 50) * 50.0
        rn_hi = rn_lo + 50.0
        obs_up, obs_dn = [], []
        for o in self.active():
            g = o.geometry
            if o.type in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE"):
                obs_up.append((g["top"] - c, "box_edge", o.id))
                obs_dn.append((c - g["bottom"], "box_edge", o.id))
            elif o.type in ("LEVEL_CARRIED", "MINI_LEVEL"):
                d = g["price"] - c
                (obs_up if d > 0 else obs_dn).append(
                    (abs(d), o.type.lower(), o.id))
            elif o.type in ("PATTERN_LINE", "CONTEXT_LINE"):
                p = g["p0"] + g["slope"] * (i - g["t0"])
                d = p - c
                (obs_up if d > 0 else obs_dn).append(
                    (abs(d), "line_ext", o.id))
        obs_up = sorted(d for d in obs_up if d[0] > -tol)
        obs_dn = sorted(d for d in obs_dn if d[0] > -tol)
        room = self.p["derived"]["room_rule_pips"]
        return {
            "bar": i, "cet_min": b["cet_min"],
            "pressure": self.pressure,
            "ema25": round(self.ema[i], 2), "abr": round(self.abr[i], 2),
            "rn_above": rn_hi, "rn_below": rn_lo,
            "grid_step": self._grid_step(),
            "magnet_up": round(rn_hi - c, 1),
            "magnet_dn": round(c - rn_lo, 1),
            "obstacles_up": obs_up[:3],
            "obstacles_dn": obs_dn[:3],
            "room_up": (obs_up[0][0] >= room) if obs_up else True,
            "room_dn": (obs_dn[0][0] >= room) if obs_dn else True,
            "domes": self.domes[-4:],
            "stand_aside": self.stand_aside(i),
        }

    # ---------------- snapshot -------------------------------------- #

    @property
    def swings(self):
        """Confirmed pivots as plain tuples (serialization-safe)."""
        return [(p.t_ext, p.t_conf, round(p.price, 4), p.dir,
                 round(p.prom_birth, 4), round(p.prom, 4),
                 p.lone_spike) for p in self.book.seq]

    def snapshot(self, i=None):
        """JSON-able view at bar i (default: latest)."""
        i = len(self.bars) - 1 if i is None else i
        return {
            "bar": i,
            "objects": [o.to_dict() for o in self.objects
                        if o.state == "ACTIVE"
                        and (o.t_right is None or o.t_right >= i)],
            "stand_aside": self.stand_aside(i) if self.bars else [],
            "facts": self.facts(i) if self.bars else {},
        }


def rng_local(b):
    return max(0.01, b["h"] - b["l"])


# ------------------------------------------------------------------ #
# convenience: feed a loader dict
# ------------------------------------------------------------------ #

def run(bars, params=None, feed=None):
    """Feed a book_loader.load_m5() dict; return the engine."""
    eng = PerceptionEngine(params, feed=feed)
    for k in range(len(bars["t"])):
        eng.update(bars["t"][k], bars["o"][k], bars["h"][k],
                   bars["l"][k], bars["c"][k],
                   cet_min=int(bars["cet_min"][k]))
    return eng
