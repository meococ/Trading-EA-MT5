"""boxes_lab — causal box proposer built from the X2 anatomy.

Blueprint (BOX_ANATOMY.md):
  * anchors = confirmed swing pivots (swings.py DCStream + SwingBook,
    params_v1_1 values) — 97% of trusted build windows start at a pivot
    extreme; ~93% of edges coincide with a pivot extreme within 2 p.
  * an edge = the extreme *with company*: the deepest member of a
    same-side pivot cluster, unless the deepest is a lone spike/poke
    more than `lone_gap` p beyond the next member (R12: excursions do
    not widen edges).
  * draw moment = first bar where both edges have >=2 contacts AND the
    last K closes are contained — lands ~15-25 min before build_end.
  * containment ends at the first decisive close beyond an edge
    (tease tolerance ~2 p; pokes that close back inside are texture).
  * start anchor = the episode start: contained-run start (closes inside
    [lo,hi]+-1 p, walked back from now) — |t0 - build_start| <= 20 min
    for ~65% of trusted boxes; a second emission anchors at the first
    in-run pivot extreme (union coverage ~70%).

Causal contract: at bar i the proposer sees bars <= i and pivot
confirmations with t_conf <= i.  Candidates are logged to cand_log in
the funnel's format so `funnel.cand_right()` scores them.

Emission discipline: candidates are emitted only when the level book
changes (a pivot confirms, or a level's contact count grows) — not per
bar — and a band re-emits only when an edge moved > edge_reemit p or a
contact signature changed or `reemit_bars` passed.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
for _p in (_PERC, os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from swings import DCStream, SwingBook  # noqa: E402

PIP = 1e-4

# params_v1_1 swing block (read-only reference values)
K1_ABR, PMIN_ABR, PSTRUCT_ABR, SPIKE_MULT = 0.8, 0.5, 2.5, 2.5

P = {
    # --- level clustering ---
    "level_eps_pips": 1.5,      # same-side pivots within eps merge
    "level_eps_abr": 0.30,      # ... or this fraction of ABR
    "lone_gap": 1.5,            # edge = deepest member unless it sits
                              # >lone_gap beyond the next member
    # --- box formation ---
    "height_min_pips": 4.0,
    "height_min_abr": 0.8,
    "height_max_pips": 70.0,
    "height_max_abr": 12.0,
    "min_contacts_edge": 1,     # weakest edge may be a single pivot...
    "min_contacts_sum": 3,      # ...but the pair must show >=3 total
    "struct_edge_ok": 1,        # a structural pivot counts as its own edge
    "min_contained": 3,         # contained closes needed since start
    "recent_inside_k": 5,       # last-k closes: allow misses (pokes)
    "recent_inside_miss": 3,
    "contain_frac_min": 0.55,   # fraction of closes inside since start
    "touch_tol_pips": 1.5,
    "run_eps": 1.0,             # contained-run slack (pips)
    # --- emission discipline ---
    "edge_reemit": 0.75,        # re-emit if an edge moved this much
    "reemit_bars": 6,           # r41: 24 let a band miss the whole
                              # scored window (pre_window_only misses)
    "max_level_age_bars": 288,  # r44 probe: whole day (was 144/~12h)
    "emit_anchors": ("run", "first_edge", "last_piv",
                     "first_piv", "prev_piv",
                     "mn_touch", "tf_max"),
    "born_anchor": "first_edge",  # geometry build_start for born objs
    # --- break / lifecycle ---
    "break_tol_pips": 0.5,      # decisive close = >0.5 p beyond edge
    "tease_tol_pips": 2.0,
    # --- selection ---
    # X3 policy: a watched band is born when it BREAKS (maximum
    # evidence, causal) — proposal time lands ~build_end+5min, inside
    # the funnel's be+10min window — or when it has stayed qualified
    # for mature_bars (slow path for boxes whose break lies beyond w1).
    # r17: the budget is LIVE boxes (snapshot lens, R13.2/R17.3), not
    # cumulative day births — the day cap exhausted before the golden
    # break in r9-r16 (9.4b: cap gone by min ~475, golden break ~820).
    "birth_cap_day": 999,       # safety valve only; live budget binds
    "max_live": 2,              # concurrent live boxes (author budget)
    "displace_hyst": 1.0,       # score margin to evict weakest live
    "nms_edge_pips": 2.0,
    "nms_iou": 0.6,             # suppress if window IoU vs live box high
    "watch_bars": 96,           # band must have qualified within this
    # birth at the KNOWABLE moment (anatomy: ~15-25 min before
    # build_end) so the box is live at tau=build_end — break-triggered
    # births land after tau and can never earn snapshot credit.
    "mature_bars": 4,           # qualified-persistence -> birth
    # birth gate (heuristic — fold AUC protocol found no >=0.60
    # feature; flagged for Lead review like LINE-LAB's gate)
    "gate_hgt_pips": 45.0,
    "gate_prom_abr": 3.0,
    "gate_n_piv": 10,
    "birth_min_span": 5,        # born window >= this many bars (25 min)
    "birth_min_persist": 2,     # band qualified across >= this span
    "birth_score_min": 3.0,     # birth floor on _score (r18; r32: 4.0
                              # was blocking golden bands whose edge_gap
                              # is transiently high mid-window; r38
                              # showed 3.5 costs 2 matches for -13% ink)
    "nest_iou_min": 0.5,        # same-episode dedup: same edges AND
                              # window IoU >= this (r37; r40 .35 same)
    "max_deep_piv": 2,          # envelope gate: in-window pivots beyond
                              # edge+tease (r20; 0 rejects 26% of right)
    # drawn tail (r28): the author's box stays on the chart past the
    # break (golden drawn span ~135 min vs build ~72).  Snapshot tau =
    # build_end = the break bar itself, so closing AT the break can
    # never be live at tau.  A BROKEN box keeps drawing tail_bars, then
    # closes; it still occupies a live-budget slot until then.
    "tail_bars": 12,            # golden tail ~60 min / 5-min bars (§21.3)
    # r35: born edges come from the watch's best-ever qualified snapshot
    # (golden boxes are static once drawn); r21 live-edge tracking off.
    "edge_track": False,
}


class Obj:
    __slots__ = ("type", "style", "t_birth", "t_left", "t_right",
                 "geometry", "why", "role", "id", "events", "state")

    def __init__(self, otype, t_birth, geometry, why, t_left):
        self.type = otype
        self.style = "solid"
        self.t_birth = t_birth
        self.t_left = t_left
        self.t_right = None
        self.geometry = geometry
        self.why = why
        self.role = ""
        self.id = None
        self.events = []
        self.state = "ACTIVE"


class Level:
    """One defended level: same-side pivot cluster + hug-bar company."""
    __slots__ = ("dir", "price", "t_first", "t_last", "n_piv",
                 "n_hug", "prom", "struct", "exts", "prices",
                 "spike_flags", "uid")

    _uid = 0

    def __init__(self, piv):
        self.dir = piv["dir"]
        self.t_first = piv["t_ext"]
        self.t_last = piv["t_ext"]
        self.n_piv = 1
        self.n_hug = 0
        self.prom = piv["prom"]
        self.struct = piv["struct"]
        self.exts = [piv["t_ext"]]
        self.prices = [piv["price"]]
        self.spike_flags = [piv["spike"]]
        self.uid = Level._uid
        Level._uid += 1
        self._reprice()

    def _reprice(self):
        """Edge = extreme with company: deepest member unless it sits
        > lone_gap beyond the next member (R12: excursions do not
        widen edges — a lone deep poke is texture, not the edge)."""
        ps = sorted(self.prices, reverse=(self.dir == 1))
        if len(ps) >= 2 and abs(ps[0] - ps[1]) > self._lone_gap:
            self.price = ps[1]
        else:
            self.price = ps[0]

    _lone_gap = 1.5

    def absorb(self, piv):
        self.prices.append(piv["price"])
        self.spike_flags.append(piv["spike"])
        self.t_last = piv["t_ext"]
        self.n_piv += 1
        self.prom = max(self.prom, piv["prom"])
        self.struct = self.struct or piv["struct"]
        self.exts.append(piv["t_ext"])
        self._reprice()

    @property
    def contacts(self):
        return self.n_piv + self.n_hug


class BoxLabEngine:
    """Causal box proposer.  Feed bars in order via update()."""

    def __init__(self, params=None):
        self.p = dict(P)
        if params:
            self.p.update(params)
        Level._lone_gap = self.p["lone_gap"]
        self.bars = []
        self.abr = []
        self.objects = []
        self.cand_log = []
        self._dc = None
        self._book = None
        self._tops = []
        self._bots = []
        self._emitted = {}        # (top.uid, bot.uid) -> signature
        self._uid = 0
        self._dirty = False
        self._born_day = {}       # day -> count
        self._last_birth_min = {}  # day -> minute of last birth
        self._watch = {}          # band key -> watch record
        self._rej = {}            # birth-path rejection counters
        # R23 §23.3 negative control: when p["shuffle_feats"] lists
        # feature names, _score substitutes those values with a draw
        # from the panel's pool of previously-emitted feats (seeded).
        self._feat_pool = []
        import random as _r
        self._rng = _r.Random(self.p.get("shuffle_seed", 0))
        # r43: provisional level at the running DC-leg extreme
        # (levellab 'leg' origins).  The golden edge is often an
        # unconfirmed swing extreme — 12/16 sampled no-edge misses
        # sat within tol of one.
        self._prov = None
        self._leg_dir = 0
        self._leg_start = 0

    # ---------------- internals ---------------- #

    def _abr_now(self, i):
        return self.abr[i] if i < len(self.abr) else 5.0

    def _eps(self, i):
        return max(self.p["level_eps_pips"],
                   self.p["level_eps_abr"] * self._abr_now(i))

    def update(self, t, o, h, l, c, cet_min=None):
        i = len(self.bars)
        b = {"t": t, "o": o / PIP, "h": h / PIP, "l": l / PIP,
             "c": c / PIP, "cet_min": cet_min}
        self.bars.append(b)
        rng = b["h"] - b["l"]
        n = len(self.abr)
        if n == 0:
            self.abr.append(rng)
        else:
            acc = self.abr[-1] * min(n, 50) + rng
            if n >= 50:
                acc -= (self.bars[n - 50]["h"] - self.bars[n - 50]["l"])
            self.abr.append(acc / min(n + 1, 50))

        if self._dc is None:
            self._dc = DCStream(lambda j: K1_ABR * self.abr[j],
                                lambda j: (self.bars[j]["h"]
                                           - self.bars[j]["l"])
                                > SPIKE_MULT * self.abr[j])
            self._book = SwingBook(PMIN_ABR, PSTRUCT_ABR,
                                   abr_fn=lambda j: self.abr[j])

        self._book.update_running(self._dc.dir, self._dc.ext_price)
        # running leg extreme -> provisional level (side = leg dir)
        d, ext = self._dc.dir, self._dc.ext_price
        if d != self._leg_dir:
            self._leg_dir, self._leg_start = d, i
            self._prov = None
        if d and ext is not None:
            if self._prov is None:
                self._prov = Level({"dir": d, "t_ext": self._leg_start,
                                    "price": ext,
                                    "prom": self._abr_now(i),
                                    "struct": True, "spike": False})
            self._prov.price = ext
            self._prov.t_last = i
            self._dirty = True
        for pv in self._dc.update(i, b["h"], b["l"]):
            pv = self._book.add(pv)
            d = {"t_ext": int(pv.t_ext), "t_conf": int(pv.t_conf),
                 "price": float(pv.price), "dir": int(pv.dir),
                 "prom": float(pv.prom),
                 "struct": bool(self._book.is_structural(pv)),
                 "spike": bool(pv.lone_spike)}
            self._add_pivot(d, i)
            self._dirty = True

        tol = self.p["touch_tol_pips"]
        for lv in self._tops:
            if abs(b["h"] - lv.price) <= tol and i > lv.t_last:
                lv.n_hug += 1
                lv.t_last = i
                self._dirty = True
        for lv in self._bots:
            if abs(b["l"] - lv.price) <= tol and i > lv.t_last:
                lv.n_hug += 1
                lv.t_last = i
                self._dirty = True

        self._maintain(i, b)

        # r45: emit check every bar — quiet stretches produced no
        # pivots/hugs so _dirty stayed False and right bands never
        # re-emitted inside the scored window (no_intime_emit class).
        self._try_form(i)
        self._dirty = False
        self._check_breaks(i, b)
        self._check_mature(i)
        return i

    # ---------------- levels ---------------- #

    def _add_pivot(self, piv, i):
        book = self._tops if piv["dir"] == 1 else self._bots
        eps = self._eps(i)
        for lv in book:
            if abs(lv.price - piv["price"]) <= eps:
                lv.absorb(piv)
                return lv
        lv = Level(piv)
        book.append(lv)
        return lv

    def _prune(self, book, i):
        return [lv for lv in book
                if i - lv.t_last <= self.p["max_level_age_bars"]]

    # ---------------- formation ---------------- #

    def _run_start(self, lo, hi, i):
        """Bar index where the current contained run began: walk back
        from i while closes stay inside [lo,hi]+-run_eps."""
        eps = self.p["run_eps"]
        j = i
        while j > 0 and lo - eps <= self.bars[j - 1]["c"] <= hi + eps:
            j -= 1
        return j

    def _first_inrun_piv(self, j0):
        """First confirmed pivot with t_ext >= j0 (either dir)."""
        best = None
        for lv in self._tops + self._bots:
            for e in lv.exts:
                if e >= j0 and (best is None or e < best):
                    best = e
        return best

    def _prev_piv(self, j0):
        """Latest confirmed pivot extreme before bar j0."""
        best = None
        for lv in self._tops + self._bots:
            for e in lv.exts:
                if e < j0 and (best is None or e > best):
                    best = e
        return best

    def _edge_pivs_in_run(self, lo, hi, j0):
        """In-run pivot extremes within 2 p of an edge -> (first, last)."""
        first = last = None
        for lv in self._tops + self._bots:
            for e, px in zip(lv.exts, lv.prices):
                if e < j0:
                    continue
                if min(abs(px - lo), abs(px - hi)) <= 2.0:
                    if first is None or e < first:
                        first = e
                    if last is None or e > last:
                        last = e
        return first, last

    def _band_ok(self, top, bot, i):
        p = self.p
        hi, lo = top.price, bot.price
        hgt = hi - lo
        abr = self._abr_now(i)
        if not (p["height_min_pips"] <= hgt <= p["height_max_pips"]):
            return False, "height_pips"
        if not (p["height_min_abr"] * abr <= hgt <= p["height_max_abr"] * abr):
            return False, "height_abr"
        for lv, tag in ((top, "top"), (bot, "bot")):
            ok_edge = lv.contacts >= p["min_contacts_edge"] or \
                (p["struct_edge_ok"] and lv.struct and lv.contacts >= 1)
            if not ok_edge:
                return False, tag + "_contacts"
        if top.contacts + bot.contacts < p["min_contacts_sum"]:
            return False, "contacts_sum"
        t0 = self._run_start(lo, hi, i)
        if t0 >= i:
            return False, "degenerate"
        closes = np.array([x["c"] for x in self.bars[t0:i + 1]])
        inside = (closes >= lo) & (closes <= hi)
        if len(closes) < p["min_contained"]:
            return False, "short_window"
        if inside[-p["recent_inside_k"]:].sum() < \
                p["recent_inside_k"] - p["recent_inside_miss"]:
            return False, "recent_escape"
        if inside.mean() < p["contain_frac_min"]:
            return False, "contain_frac"
        feats = {
            "t0": int(t0), "lo": float(lo), "hi": float(hi),
            "hgt": float(hgt), "abr": float(abr),
            "age_min": int((i - t0) * 5),
            "prom_min": float(min(top.prom, bot.prom)),
            "prom_sum": float(top.prom + bot.prom),
            "struct_any": int(top.struct or bot.struct),
            "struct_both": int(top.struct and bot.struct),
            "contacts": int(top.contacts + bot.contacts),
            "contain_frac": float(inside.mean()),
            "n_piv": int(top.n_piv + bot.n_piv),
            # R9a/levellab barrier, identity version: edge level itself
            # pre-dates the run.  r33: ANTI-predictive on this stream
            # (P(right|barrier=0)=0.9% vs 0.2% for >=1) — golden edges
            # are FRESH pivots, not reused old levels.
            "barrier": int(top.t_first < t0 and top.contacts >= 2)
                       + int(bot.t_first < t0 and bot.contacts >= 2),
        }
        # proximity version (NOTES_FOR_BOXLAB): a defended level within
        # 3p of the edge, origin before the run, touched within 60 bars.
        bn = 0
        for lv in self._tops:
            if lv is not top and abs(lv.price - hi) <= 3.0 and \
                    lv.t_first < t0 and lv.contacts >= 2 and \
                    lv.exts and i - lv.exts[-1] <= 60:
                bn += 1
                break
        for lv in self._bots:
            if lv is not bot and abs(lv.price - lo) <= 3.0 and \
                    lv.t_first < t0 and lv.contacts >= 2 and \
                    lv.exts and i - lv.exts[-1] <= 60:
                bn += 1
                break
        feats["barrier_near"] = int(bn)
        k = max(1, len(closes) // 3)
        mid = 0.5 * (lo + hi)
        feats["lean_top"] = float((closes[-k:] > mid).mean())
        # Envelope test (R11.4b): a real box edge is the defended
        # extreme — no confirmed non-spike pivot may sit deeper than
        # tease_tol beyond an edge inside the window.  Interior bands
        # that let price poke to a deeper reversal are not the box.
        allow = p["tease_tol_pips"]
        deep = 0
        for lv in self._tops + self._bots:
            for e, px, sp in zip(lv.exts, lv.prices, lv.spike_flags):
                if e < t0 or e > i or sp:
                    continue
                if px > hi + allow or px < lo - allow:
                    deep += 1
        feats["deep_piv"] = int(deep)
        # edge-to-extreme gap on the window's own wicks (audit: golden
        # hi edge ~= p95 of window highs, gap ~0.05 p).  Interior bands
        # sit pips inside the true extremes -> large gap.
        hs = np.array([x["h"] for x in self.bars[t0:i + 1]])
        ls = np.array([x["l"] for x in self.bars[t0:i + 1]])
        feats["edge_gap"] = float(
            max(0.0, np.percentile(hs, 95) - hi)
            + max(0.0, lo - np.percentile(ls, 5)))
        # r30 — deeper_lv: defended levels (contacts>=2) deeper than the
        # band's own edge within ~1 ABR.  The golden edge IS the deepest
        # defended pivot of its side (lone spikes don't count); a nested
        # inner band always has the golden's edge level deeper than its
        # own -> penalised.  Window-independent (fixes r29: the deciding
        # pivot often precedes the band's contained run).
        rng = max(1.0 * abr, 6.0)
        deeper = 0
        for lv in self._tops:
            if lv is not top and lv.contacts >= 2 and \
                    hi < lv.price <= hi + rng:
                deeper += 1
        for lv in self._bots:
            if lv is not bot and lv.contacts >= 2 and \
                    lo - rng <= lv.price < lo:
                deeper += 1
        feats["deeper_lv"] = int(deeper)
        return True, feats

    def _try_form(self, i):
        p = self.p
        tops = self._prune(self._tops, i)
        bots = self._prune(self._bots, i)
        if self._prov is not None:
            (tops if self._prov.dir == 1 else bots).append(self._prov)
        for top in tops:
            for bot in bots:
                ok, feats = self._band_ok(top, bot, i)
                if not ok:
                    continue
                key = (top.uid, bot.uid)
                sig = (round(top.price * 2) / 2, round(bot.price * 2) / 2,
                       top.contacts // 3, bot.contacts // 3)
                last = self._emitted.get(key)
                if last is not None:
                    lsig, li = last
                    if lsig == sig and i - li < p["reemit_bars"]:
                        continue
                self._emitted[key] = (sig, i)
                self._emit(top, bot, i, feats)

    def _emit(self, top, bot, i, feats):
        p = self.p
        fe, le = self._edge_pivs_in_run(feats["lo"], feats["hi"],
                                      feats["t0"])
        # r39 anchors: per-edge first in-run touch.  Golden bs is
        # usually a mid-band pivot bar well after run start — often the
        # earlier edge's first in-run touch (mn_touch) or the later
        # edge's own first contact (tf_max), measured on the 18
        # start-miss goldens.
        ft = [x for x in top.exts if x >= feats["t0"]]
        fb = [x for x in bot.exts if x >= feats["t0"]]
        amap = {"run": feats["t0"], "first_edge": fe, "last_piv": le,
                "first_piv": self._first_inrun_piv(feats["t0"]),
                "prev_piv": self._prev_piv(feats["t0"]),
                "mn_touch": min(min(ft), min(fb)) if ft and fb else None,
                "mx_touch": max(min(ft), min(fb)) if ft and fb else None,
                "tf_max": max(top.t_first, bot.t_first)}
        # r42: oracle probe — one cand per recent in-run pivot bar.
        # Golden bs sits on a confirmed pivot ~97% of the time (X2);
        # the funnel needs |t0-bs| <= 20 min, so dense pivot anchors
        # cover the in_window_wrong_t0 miss class.
        allpiv = sorted({e for lv in self._tops + self._bots
                         for e in lv.exts if e >= feats["t0"]})[-8:]
        anchors = []
        seen = set()
        for tag in p["emit_anchors"]:
            t0 = amap.get(tag)
            if t0 is not None and t0 not in seen:
                seen.add(t0)
                anchors.append((tag, t0))
        if not anchors:
            anchors = [("run", feats["t0"])]
        born_t0 = amap.get(p["born_anchor"])
        if born_t0 is None:
            born_t0 = feats["t0"]
        for tag, t0 in anchors:
            cand = {"kind": "BOX", "idx": i,
                    "cet_min": self.bars[i]["cet_min"],
                    "route": "piv_pair_%s" % tag,
                    "outcome": "proposed",
                    "t0": int(t0), "t1": i,
                    "lo": feats["lo"], "hi": feats["hi"],
                    **{k: v for k, v in feats.items()
                       if k not in ("t0", "lo", "hi")}}
            self.cand_log.append(cand)
        for t0 in allpiv:
            self.cand_log.append(
                {"kind": "BOX", "idx": i,
                 "cet_min": self.bars[i]["cet_min"],
                 "route": "piv_pair_allpiv", "outcome": "proposed",
                 "t0": int(t0), "t1": i,
                 "lo": feats["lo"], "hi": feats["hi"],
                 **{k: v for k, v in feats.items()
                    if k not in ("t0", "lo", "hi")}})
        # r47: wick-tip variant — edges at the run's p99/p01 wick
        # extremes (golden edges sit on lone spikes my level design
        # excludes; measured on the residual no-edge misses).
        t0r = feats["t0"]
        w_hs = np.array([x["h"] for x in self.bars[t0r:i + 1]])
        w_ls = np.array([x["l"] for x in self.bars[t0r:i + 1]])
        if len(w_hs) >= 3:
            whi = float(np.percentile(w_hs, 99))
            wlo = float(np.percentile(w_ls, 1))
            if wlo < feats["lo"] - 0.5 or whi > feats["hi"] + 0.5:
                for tag, t0 in anchors[:3]:
                    self.cand_log.append(
                        {"kind": "BOX", "idx": i,
                         "cet_min": self.bars[i]["cet_min"],
                         "route": "piv_pair_wick_%s" % tag,
                         "outcome": "proposed",
                         "t0": int(t0), "t1": i,
                         "lo": wlo, "hi": whi,
                         **{k: v for k, v in feats.items()
                            if k not in ("t0", "lo", "hi")}})
            # r48: absolute extremes (lone-spike tips included)
            ahi, alo = float(w_hs.max()), float(w_ls.min())
            if (alo, ahi) != (wlo, whi):
                for tag, t0 in anchors[:3]:
                    self.cand_log.append(
                        {"kind": "BOX", "idx": i,
                         "cet_min": self.bars[i]["cet_min"],
                         "route": "piv_pair_abs_%s" % tag,
                         "outcome": "proposed",
                         "t0": int(t0), "t1": i,
                         "lo": alo, "hi": ahi,
                         **{k: v for k, v in feats.items()
                            if k not in ("t0", "lo", "hi")}})
        prev = self._watch.get((top.uid, bot.uid), {})
        best = prev.get("best")
        if best is None or self._score(feats) > self._score(best):
            best = feats            # argmax-score geometry snapshot:
            # level repricing drifts the band; the author's draw moment
            # already passed while the edges were right (r35).
        # r46: also emit the watch's best-ever edges — level repricing
        # moves the pair off the golden prices mid-window and the
        # right-edge cand then never exists inside the scored window
        # (the no_intime_emit class, repriced variant).
        if best is not feats and \
                (abs(best["lo"] - feats["lo"]) > 0.5 or
                 abs(best["hi"] - feats["hi"]) > 0.5):
            for t0 in anchors[:2] + [("best", best["t0"])]:
                self.cand_log.append(
                    {"kind": "BOX", "idx": i,
                     "cet_min": self.bars[i]["cet_min"],
                     "route": "piv_pair_best_%s" % t0[0],
                     "outcome": "proposed",
                     "t0": int(t0[1]), "t1": i,
                     "lo": best["lo"], "hi": best["hi"],
                     **{k: v for k, v in best.items()
                        if k not in ("t0", "lo", "hi")}})
        self._watch[(top.uid, bot.uid)] = {
            "feats": feats, "best": best,
            "born_t0": prev.get("born_t0", born_t0),
            "firstq": prev.get("firstq", i),
            "lastq": i, "born": prev.get("born", False),
            "top": top, "bot": bot}
        if self.p.get("shuffle_feats"):
            self._feat_pool.append(feats)

    # ---------------- selection ---------------- #

    def _score(self, feats):
        """Birth competition score (heuristic — the fold-AUC protocol
        found no feature >=0.60 on every fold, so this is a
        gate-serving score flagged for Lead review, same status as
        LINE-LAB's).  Direction: golden bands are SHORT (hgt AUC .66
        inverted), have STRONG edges (prom_abr .75, R16.4), and rest
        on pre-existing barriers (R9a / NOTES_FOR_BOXLAB), and sit AT
        the defended extremes (r30: deeper_lv — defended levels deeper
        than the edge within ~1 ABR; window-independent, unlike the r22
        edge_gap and r29 deep_piv terms which both failed on nested
        episodes).  hgt term kept in the lab pending a production-stream
        replacement (R20 §20.2 says it is not evidence — flag for Lead);
        removing it collapsed every score below the birth floor (r30).
        score = prom_min/abr + (8 - hgt_abr) - 0.75*barrier
                - 0.8*edge_gap - 1.5*deeper_lv
        (r33: barrier sign flipped — identity barrier is anti-
        predictive: fresh-edge bands are right 4x more often)"""
        if self.p.get("shuffle_feats") and self._feat_pool:
            feats = dict(feats)
            pick = self._feat_pool[self._rng.randrange(
                len(self._feat_pool))]
            for f in self.p["shuffle_feats"]:
                feats[f] = pick.get(f, feats.get(f))
        abr = max(feats["abr"], 1.0)
        return feats["prom_min"] / abr + max(0.0, 8.0 - feats["hgt"] / abr) \
            - 0.75 * feats.get("barrier", 0) \
            - 0.8 * feats.get("edge_gap", 0.0) \
            - 1.5 * feats.get("deeper_lv", 0.0)

    def _gate(self, feats):
        p = self.p
        if feats["hgt"] > p["gate_hgt_pips"]:
            return False
        if feats["prom_sum"] < p["gate_prom_abr"] * max(feats["abr"], 1.0):
            return False
        if feats["n_piv"] > p["gate_n_piv"]:
            return False
        return True

    def _birth_edge_ok(self, lv, i):
        """Birth-time edge evidence (stricter than the emit gate):
        >=2 contacts, or a non-spike pivot that persisted >=3 bars —
        a lone spike can never be an edge (known-answer T3)."""
        if lv.contacts >= 2:
            return True
        return lv.n_piv >= 1 and not all(lv.spike_flags) \
            and i - lv.t_first >= 3

    def _birth_window(self, w, i):
        """(bs, be) for a watch record at bar i — on the best-ever
        qualified edges (r35), not the possibly-drifted latest ones."""
        p = self.p
        feats = w["best"]
        lo, hi = feats["lo"], feats["hi"]
        be = i
        while be > 0 and not (lo - p["run_eps"] <=
                              self.bars[be]["c"] <= hi + p["run_eps"]):
            be -= 1
        bs = w["born_t0"]
        if bs >= be:
            bs = be
            while bs > 0 and lo - p["run_eps"] <= \
                    self.bars[bs - 1]["c"] <= hi + p["run_eps"]:
                bs -= 1
        return bs, be

    def _birth(self, w, i, why):
        """Create the born BOX object from a watch record — geometry
        from the best-ever qualified edges (r35: the author's draw
        moment is past; frozen edges, golden boxes are static)."""
        p = self.p
        feats = w["best"]
        lo, hi = feats["lo"], feats["hi"]
        # build_end = last bar <= i whose close sat inside the band.
        # build_start = the anchor recorded at last qualification —
        # measured IoU: right-cand proposal windows hit >=0.5 vs the
        # golden window in 83% of cases; recomputing from the break
        # bar collapses onto a post-drift micro-run instead.
        bs, be = self._birth_window(w, i)
        o = Obj("BOX", i, {"top": hi, "bottom": lo,
                           "build_start": bs,
                           "build_end": be, "t1_drawn": None,
                           "src_top": w["top"], "src_bot": w["bot"]},
                why="piv_pair", t_left=bs)
        o.id = "LAB%04d" % self._uid
        self._uid += 1
        o.events.append([i, "born", why])
        o.geometry["score"] = self._score(feats)
        self.objects.append(o)
        w["born"] = True
        day = self.bars[i]["t"] // 86400 if self.bars[i].get("t") else 0
        self._born_day[day] = self._born_day.get(day, 0) + 1
        cet = self.bars[i]["cet_min"]
        if cet is not None:
            self._last_birth_min[day] = cet
        if why == "break":
            self._break(o, i, "break_at_birth")
        return o

    def _birth_ok(self, w, i):
        """Live budget (R17.3): free slot, else free one by cutting a
        broken tail (a broken box is dead weight), else displace the
        weakest live box when the new band outscores it by
        displace_hyst — the §16.4 displacement pattern."""
        p = self.p
        live = [o for o in self.objects if o.type == "BOX"
                and o.state in ("ACTIVE", "BROKEN")]
        if len(live) < p["max_live"]:
            return True
        broken = [o for o in live if o.state == "BROKEN"]
        if broken:
            self._close(min(broken,
                            key=lambda o: o.geometry.get("break_bar", 0)),
                        i, "tail_cut")
            return True
        s = self._score(w["best"])
        weak = min(live, key=lambda o: o.geometry.get("score", 0.0))
        if s > weak.geometry.get("score", 0.0) + p["displace_hyst"]:
            self._close(weak, i, "displaced")
            return True
        return False

    def _same_episode(self, g, lo, hi, bs, be):
        """Is born-box geometry g the same congestion episode as the
        candidate band?  r36: same-edge NMS only — the nested-window
        branch let a band born with right edges but a wrong window
        block every later right watch of the same episode (the r35
        m_dup mass: blockers scored 7.7 vs right watches 4.3).
        r37: same edges AND window IoU >= nest_iou_min — a band born
        with right edges but the wrong window must not preempt the
        same-episode band whose window is right."""
        p = self.p
        if abs(g["top"] - hi) <= p["nms_edge_pips"] and \
                abs(g["bottom"] - lo) <= p["nms_edge_pips"]:
            s0 = max(g["build_start"], bs)
            s1 = min(g["build_end"], be)
            union = max(g["build_end"], be) - min(g["build_start"], bs)
            if union > 0 and (s1 - s0) / union >= p["nest_iou_min"]:
                return True
        return False

    def _dup_hit(self, lo, hi, bs, be, i, new_score):
        """Return (blocker, [weaker same-episode live boxes]) for a
        candidate band.  blocker = strongest already-born same-episode
        box; the caller births only when the new band outranks it, and
        supersede closes the weaker live ones — so each episode's
        best-scoring band is what survives, not the first (R9.3)."""
        p = self.p
        day = self.bars[i]["t"] // 86400 if self.bars[i].get("t") else 0
        best, weaker = None, []
        for o in self.objects:
            if o.type != "BOX":
                continue
            oday = self.bars[o.t_birth]["t"] // 86400 \
                if self.bars[o.t_birth].get("t") else 0
            if oday != day:
                continue
            g = o.geometry
            if not self._same_episode(g, lo, hi, bs, be):
                continue
            if best is None or g.get("score", 0.0) > \
                    best.geometry.get("score", 0.0):
                best = o
            if o.state == "ACTIVE" and \
                    g.get("score", 0.0) < new_score:
                weaker.append(o)
        return best, weaker

    def _check_breaks(self, i, b):
        """Birth a watched band when it decisively breaks (max-evidence
        moment, lands ~build_end+5 min — inside the funnel window)."""
        p = self.p
        # birth as many same-event breakers as the live budget allows,
        # best score first — the single-winner rule strangled bands
        # whose break shared a bar with a stronger rival.
        cands = []
        for key, w in self._watch.items():
            if w["born"]:
                continue
            if i - w["lastq"] > p["watch_bars"]:
                self._rej["stale"] = self._rej.get("stale", 0) + 1
                continue
            feats = w["best"]      # break + birth on best-ever edges
            if not (b["c"] > feats["hi"] + p["break_tol_pips"]
                    or b["c"] < feats["lo"] - p["break_tol_pips"]):
                continue
            if not self._gate(feats):
                self._rej["gate"] = self._rej.get("gate", 0) + 1
                continue
            if self._score(feats) < p["birth_score_min"]:
                self._rej["floor"] = self._rej.get("floor", 0) + 1
                continue
            if feats.get("deep_piv", 0) > p["max_deep_piv"]:
                self._rej["env"] = self._rej.get("env", 0) + 1
                continue
            if not (self._birth_edge_ok(w["top"], i) and
                    self._birth_edge_ok(w["bot"], i)):
                self._rej["edge"] = self._rej.get("edge", 0) + 1
                continue
            if w["lastq"] - w["firstq"] < p["birth_min_persist"]:
                self._rej["persist"] = self._rej.get("persist", 0) + 1
                continue
            cands.append(w)
        cands.sort(key=lambda w: -self._score(w["best"]))
        for w in cands:
            feats = w["best"]
            bs, be = self._birth_window(w, i)
            if be - bs < p["birth_min_span"]:
                self._rej["span"] = self._rej.get("span", 0) + 1
                continue
            sc = self._score(feats)
            blocker, weaker = self._dup_hit(feats["lo"], feats["hi"],
                                            bs, be, i, sc)
            if blocker is not None and \
                    blocker.geometry.get("score", 0.0) >= sc:
                self._rej["dup"] = self._rej.get("dup", 0) + 1
                continue
            if self._birth_ok(w, i):
                for old in weaker:
                    self._close(old, i, "superseded")
                self._birth(w, i, "break")
            else:
                self._rej["budget"] = self._rej.get("budget", 0) + 1

    def _check_mature(self, i):
        """Slow path: a band still qualified after mature_bars is drawn
        even without an observed break (break may lie beyond w1)."""
        p = self.p
        cands_m = []
        for key, w in self._watch.items():
            if w["born"]:
                continue
            if i - w["lastq"] > p["watch_bars"]:
                self._rej["m_stale"] = self._rej.get("m_stale", 0) + 1; w["last_rej"]=(i,"m_stale")
                continue
            if i - w["firstq"] < p["mature_bars"]:
                self._rej["m_young"] = self._rej.get("m_young", 0) + 1; w["last_rej"]=(i,"m_young")
                continue
            if not self._gate(w["best"]):
                self._rej["m_gate"] = self._rej.get("m_gate", 0) + 1; w["last_rej"]=(i,"m_gate")
                continue
            if self._score(w["best"]) < p["birth_score_min"]:
                self._rej["m_floor"] = self._rej.get("m_floor", 0) + 1; w["last_rej"]=(i,"m_floor")
                continue
            if w["best"].get("deep_piv", 0) > p["max_deep_piv"]:
                self._rej["m_env"] = self._rej.get("m_env", 0) + 1; w["last_rej"]=(i,"m_env")
                continue
            if not (self._birth_edge_ok(w["top"], i) and
                    self._birth_edge_ok(w["bot"], i)):
                self._rej["m_edge"] = self._rej.get("m_edge", 0) + 1; w["last_rej"]=(i,"m_edge")
                continue
            if w["lastq"] - w["firstq"] < p["birth_min_persist"]:
                self._rej["m_persist"] = self._rej.get("m_persist", 0) + 1; w["last_rej"]=(i,"m_persist")
                continue
            cands_m.append(w)
        cands_m.sort(key=lambda w: -self._score(w["best"]))
        for w in cands_m:
            feats = w["best"]
            bs, be = self._birth_window(w, i)
            if be - bs < p["birth_min_span"]:
                self._rej["m_span"] = self._rej.get("m_span", 0) + 1; w["last_rej"]=(i,"m_span")
                continue
            sc = self._score(feats)
            blocker, weaker = self._dup_hit(feats["lo"], feats["hi"],
                                            bs, be, i, sc)
            if blocker is not None and \
                    blocker.geometry.get("score", 0.0) >= sc:
                self._rej["m_dup"] = self._rej.get("m_dup", 0) + 1; w["last_rej"]=(i,"m_dup")
                continue
            if self._birth_ok(w, i):
                for old in weaker:
                    self._close(old, i, "superseded")
                self._birth(w, i, "mature")
            else:
                self._rej["m_budget"] = self._rej.get("m_budget", 0) + 1; w["last_rej"]=(i,"m_budget")

    # ---------------- lifecycle ---------------- #

    def _maintain(self, i, b):
        p = self.p
        for o in self.active("BOX"):
            g = o.geometry
            # edge tracking (r21) is OFF since r35: born edges come from
            # the watch's best-ever snapshot — golden boxes are static
            # once drawn; a deeper reprice after the draw moment must
            # NOT move the edge.
            st, sb = (g.get("src_top"), g.get("src_bot")) \
                if p.get("edge_track") else (None, None)
            if st is not None and sb is not None:
                new_hi, new_lo = st.price, sb.price
                if abs(new_hi - g["top"]) > 0.05 or \
                        abs(new_lo - g["bottom"]) > 0.05:
                    o.events.append([i, "edge_move",
                                     [g["top"], g["bottom"]],
                                     [new_hi, new_lo]])
                    g["top"], g["bottom"] = new_hi, new_lo
                    g["build_start"] = min(
                        g["build_start"],
                        self._run_start(new_lo, new_hi, i))
                    o.t_left = g["build_start"]
            top, bot = g["top"], g["bottom"]
            if b["c"] > top + p["break_tol_pips"]:
                self._break(o, i, "break_top")
            elif b["c"] < bot - p["break_tol_pips"]:
                self._break(o, i, "break_bot")
            else:
                g["build_end"] = i
                if b["h"] > top + p["tease_tol_pips"] or \
                        b["l"] < bot - p["tease_tol_pips"]:
                    o.events.append([i, "poke", "deep_tease"])
        # broken boxes keep drawing their tail (author keeps the box
        # on the chart after the break), then close for real.
        for o in self.objects:
            if o.type == "BOX" and o.state == "BROKEN" and \
                    i - o.geometry["break_bar"] >= p["tail_bars"]:
                self._close(o, i, "tail_end")

    def _break(self, o, i, why):
        """First decisive close beyond an edge: containment ends here
        (build_end = this bar, the golden convention) but the box stays
        drawn for its tail — it is still live at tau = build_end."""
        o.state = "BROKEN"
        o.geometry["break_bar"] = i
        o.geometry["build_end"] = i
        o.events.append([i, why, "close beyond edge"])

    def _close(self, o, i, why):
        o.state = "CLOSED"
        o.t_right = i
        o.geometry.setdefault("break_bar", i)
        o.geometry["t1_drawn"] = i
        o.events.append([i, why, "close beyond edge"])

    def active(self, otype=None):
        return [o for o in self.objects if o.state == "ACTIVE"
                and (otype is None or o.type == otype)]
