"""levels_lab — V4 causal LEVEL proposer (sandbox).

Same interface as linelab/lines_lab.py:
    e = LevelLabEngine(); e.cand_log = []
    e.update(t_epoch, o, h, l, c, cet_min=...)   # absolute prices
    e.objects -> engine-shaped objects (t_left/t_right/geometry/events)

Design (from LEVEL_ANATOMY.md V2):
- origin universe = confirmed theta1/theta2 pivots (engine swings.py)
  UNION running session/Asia extremes -> ~90% of trusted golden prices.
- a "level" = a defended price: >= min_defences distinct touch events
  (consecutive in-tol bars deduped) since its origin.
- draw trigger = APPROACH, not formation: golden levels are knowable
  ~6h before t0; the author starts drawing when price returns to
  ~1.6 ABR of the level (median dist_tau).  Birth when price comes
  within approach_abr of a defended origin.
- lifecycle: live while price stays within live_abr; dies on 2
  consecutive closes through by > tol (pierce) or after stale_retire
  bars without a touch; revive same-price closed level instead of
  new ink (anti-churn, like lines).
- NMS: one live level per +-nms_band pips band per side.

Every parameter carries provenance: meas / spec / yard / lab.
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)

from swings import DCStream, SwingBook  # noqa: E402

PIP = 1e4

PARAMS = {
    # swing stream (spec: params_v1_1 swing block)
    "k1_abr": 0.8, "pmin_abr": 0.5, "pstruct_abr": 2.5,
    "spike_abr_mult": 2.5, "abr_len": 50,
    # level proposal
    "touch_tol_pips": 1.5,        # yard: TOUCH_TOL
    "touch_tol_abr_frac": 0.25,   # spec: level touch tol
    "min_defences": 2,            # meas: V2 85% trusted LC have >=3
                                # touches incl. origin -> >=2 events
                                # after origin (~3 incl. origin)
    "approach_abr": 1.75,         # meas: V2 dist_tau p50 = 1.64 ABR
    "live_abr": 3.0,              # lab: retire when price leaves
    "pierce_dead_bars": 2,        # lab: 2 closes through (as lines)
    "stale_retire_bars": 60,      # meas: DR-MARKET v2 via R11 (~5h)
    "nms_band_pips": 3.0,         # meas: V2 zone width p50 5-8p
    "revive_bars": 96,            # lab: anti-churn (as lines extend)
    "sess_grace_bars": 48,        # lab: superseded session extreme has
                                # 4h to earn a defence, else dropped
    "min_score": 1.0,             # lab: birth floor (n_def>=2 needs
                                # dist<=1 ABR; >=3 any approach)
    "def_w": 1.0,                 # lab: weight per defence event
    "dist_w": 1.0,                # lab: weight per ABR of distance
    "asia_end_min": 420,          # meas: V2 asia-extreme origin class
    "mini_max_age": 90,           # lab: MINI_LEVEL when origin <90min
    "mini_max_span": 45,          # meas: MINI span p50 25min
    "level_min_age": 0,           # lab: min origin age for LC
    "emit_mini": True,            # lab: also emit MINI_LEVEL
    "price_mode": "edge",         # lab: 'edge' defended extreme |
                                # 'median' median | 'mode' 1p-bin mode
                                # of in-tol touches
    "leg_origins": False,         # lab R6: register the unconfirmed
                                # running DC leg extreme as an origin
                                # (defended but never-confirmed swings)
}

PROVENANCE = {
    "k1_abr": "spec", "pmin_abr": "spec", "pstruct_abr": "spec",
    "spike_abr_mult": "spec", "abr_len": "spec",
    "touch_tol_pips": "yard:validate.TOUCH_TOL",
    "touch_tol_abr_frac": "spec:line.touch_tol_abr_frac (level tol ~same)",
    "min_defences": "meas:V2 touches>=3 in 85% trusted LC",
    "approach_abr": "meas:V2 dist_tau p50=1.64",
    "live_abr": "lab",
    "pierce_dead_bars": "lab:golden tolerates teases (L1 lines)",
    "stale_retire_bars": "meas:DR-MARKET v2 via R11 (~5h, 48-96 bound)",
    "nms_band_pips": "meas:V2 zone width p50 5.4-7.5p",
    "sess_grace_bars": "lab:R5 sweep 24<48=72",
    "min_score": "lab:R5 1.0 births n_def>=2 on close approach",
    "def_w": "lab", "dist_w": "lab",
    "asia_end_min": "meas:V2 asia class m<420",
    "mini_max_age": "lab", "mini_max_span": "meas:V1 MINI span p50=25",
    "level_min_age": "lab", "emit_mini": "lab",
}


class LabObj:
    def __init__(self, otype, t_birth, geometry, why, oid):
        self.id = oid
        self.type = otype
        self.style = "solid"
        self.t_birth = t_birth
        self.t_left = t_birth
        self.t_right = None
        self.geometry = geometry
        self.state = "ACTIVE"
        self.events = []
        self.role = ""
        self.why = why
        self.priority = 2

    def close(self, i, why):
        self.t_right = i
        self.state = "CLOSED"
        self.events.append((i, "close", why))


class LevelLabEngineRv:
    """Variant: revive also reprices to the better-defended edge."""

    def __init__(self, params=None, cand_hook=None):
        self.p = dict(PARAMS)
        if params:
            self.p.update(params)
        self.bars = []
        self.abr = []
        self.objects = []
        self.cand_log = None
        self.cand_hook = cand_hook
        sp = self.p
        self.book = SwingBook(sp["pmin_abr"], sp["pstruct_abr"],
                              abr_fn=self._abr)
        self.dc = DCStream(
            lambda i: sp["k1_abr"] * self._abr(i),
            lambda i: self._spike(i))
        # origins: [{bar, price, dir(-1 low/+1 high), cls, n_def, last_t}]
        self.origins = []
        self._run_hi = -1e18
        self._run_lo = 1e18
        self._asia_hi = -1e18
        self._asia_lo = 1e18
        self._pending_sess = []         # session-extreme candidates
        self._leg_ext = None            # running DC leg extreme price
        self._leg_dir = 0

    # ---------------- plumbing ----------------------------------- #

    def _abr(self, i):
        return self.abr[i] if i < len(self.abr) else 5.0

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
        self.book.update_running(self.dc.dir, self.dc.ext_price)
        for pv in self.dc.update(i, bar["h"], bar["l"]):
            piv = self.book.add(pv)
            self._add_origin(piv.t_ext, piv.price, piv.dir,
                             "theta2" if self.book.is_structural(piv)
                             else "theta1")
        self._session_origins(i, bar)
        if self.p["leg_origins"]:
            self._leg_origins(i)
        self._expire_sweep(i)
        self._touch_sweep(i, bar)
        self._trigger(i, bar)
        self._maintain(i, bar)

    # ---------------- origins ------------------------------------- #

    def _add_origin(self, j, price, side, cls, sess=False):
        """Register a defended-price origin; merge into an existing
        origin within touch tol (same side)."""
        tol = self._tol(j)
        for og in self.origins:
            if og["dir"] != side:
                continue
            if abs(og["price"] - price) <= tol:
                # keep the defended EDGE price, not the mean: for lows
                # the level is the deepest low defended, for highs the
                # highest high (V4 miss audit: mean-averaging drifted
                # born prices 1.5-3p off golden).
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
                             "last_t": j, "_run": False, "sess": sess,
                             "prices": [price]})

    def _session_origins(self, i, bar):
        """Session/Asia extremes: keep only the CURRENT running extreme
        plus the finalized Asia range; a superseded extreme survives
        only if it already collected >= min_defences (then it is a real
        defended level, same as a pivot origin)."""
        p = self.p
        new_hi = bar["h"] > self._run_hi
        new_lo = bar["l"] < self._run_lo
        if new_hi:
            self._run_hi = bar["h"]
            self._mark_superseded(i, 1)
            self._add_origin(i, bar["h"], 1,
                             "asia" if bar["cet_min"] < p["asia_end_min"]
                             else "session", sess=True)
        if new_lo:
            self._run_lo = bar["l"]
            self._mark_superseded(i, -1)
            self._add_origin(i, bar["l"], -1,
                             "asia" if bar["cet_min"] < p["asia_end_min"]
                             else "session", sess=True)

    def _mark_superseded(self, i, side):
        """Superseded session extreme: mark its expiry bar; dropped in
        the sweep once grace expires without min_defences."""
        for og in self.origins:
            if og.get("sess") and og["dir"] == side \
                    and "expire" not in og:
                og["expire"] = i + self.p["sess_grace_bars"]

    def _leg_origins(self, i):
        """Unconfirmed running DC-leg extreme: a defended swing extreme
        whose reversal never confirmed inside the window still deserves
        an origin. Each extension supersedes the previous provisional
        extreme (grace to earn defences); on dir flip the extreme becomes
        a confirmed pivot origin (merge handles the duplicate)."""
        d, ext = self.dc.dir, self.dc.ext_price
        if d == 0 or ext is None:
            return
        if d != self._leg_dir or ext != self._leg_ext:
            for og in self.origins:
                if og.get("cls") == "leg" and "expire" not in og \
                        and (d != self._leg_dir or og["dir"] == d):
                    og["expire"] = i + self.p["sess_grace_bars"]
            self._add_origin(i, ext, d, "leg", sess=True)
            self._leg_dir, self._leg_ext = d, ext

    def _expire_sweep(self, i):
        self.origins = [og for og in self.origins
                        if not (og.get("expire") is not None
                                and i >= og["expire"]
                                and og["n_def"] < self.p["min_defences"])]

    # ---------------- defences ------------------------------------- #

    def _tol(self, i):
        return max(self.p["touch_tol_pips"],
                   self.p["touch_tol_abr_frac"] * self._abr(i))

    def _touch_sweep(self, i, bar):
        """A bar extreme within tol of an origin = a defence event;
        consecutive in-tol bars count once."""
        for og in self.origins:
            ext = bar["l"] if og["dir"] < 0 else bar["h"]
            hit = abs(ext - og["price"]) <= self._tol(i)
            if hit and not og["_run"]:
                og["n_def"] += 1
                og["last_t"] = i
                og["prices"].append(ext)
                if len(og["prices"]) > 40:
                    og["prices"] = og["prices"][-40:]
            og["_run"] = hit

    # ---------------- proposal ------------------------------------ #

    def _trigger(self, i, bar):
        """Birth when price approaches a defended origin."""
        p = self.p
        abr = max(self._abr(i), 1e-9)
        close = bar["c"]
        for og in self.origins:
            age = (i - og["bar"]) * 5
            if og["n_def"] < p["min_defences"]:
                continue
            if p["price_mode"] == "median":
                eprice = float(np.median(og["prices"]))
            elif p["price_mode"] == "mode":
                bins = np.round(np.asarray(og["prices"]))
                eprice = float(np.bincount(
                    bins.astype(int) - int(bins.min())).argmax()
                    + int(bins.min()))
            else:
                eprice = og["price"]
            dist = abs(close - eprice) / abr
            if dist > p["approach_abr"]:
                continue
            score = p["def_w"] * og["n_def"] - p["dist_w"] * dist
            feats = {"n_def": og["n_def"], "n_piv": og.get("n_piv", 1),
                     "age_min": age, "dist_abr": round(dist, 2),
                     "cls": og["cls"], "price": round(eprice, 2),
                     "score": round(score, 3), "i": i,
                     "side": og["dir"]}
            if self.cand_hook:
                self.cand_hook(i, dict(feats))
            if self.cand_log is not None:
                self.cand_log.append({"kind": "LEVEL_CARRIED",
                                      "idx": i, "price": eprice,
                                      "outcome": "proposed",
                                      "route": og["cls"], **feats})
            if score < p["min_score"]:
                continue
            kind = "LEVEL_CARRIED"
            if p["emit_mini"] and age <= p["mini_max_age"]:
                kind = "MINI_LEVEL"
            if kind == "LEVEL_CARRIED" and age < p["level_min_age"]:
                continue
            self._birth(i, og, eprice, score, kind)

    def _birth(self, i, og, eprice, score, kind):
        p = self.p
        band = p["nms_band_pips"]
        for o in self.active():
            g = o.geometry
            if abs(g["price"] - eprice) <= band:
                if og["n_def"] >= g.get("n_def0", 0):
                    # challenger at least as defended as the incumbent's
                    # origin: the level tracks the most defended edge in
                    # the band (side-free — a defended zone flips roles),
                    # keeping the early birth time.
                    g["price"] = eprice
                    g["n_def0"] = og["n_def"]
                    g["n_def"] = max(g.get("n_def", 0), og["n_def"])
                    o.events.append((i, "reprice",
                                     "edge def=%d" % og["n_def"]))
                return
        for o in reversed(self.objects):
            if o.state != "CLOSED":
                continue
            g = o.geometry
            if abs(g["price"] - eprice) <= band and \
                    i - (o.t_right or 0) <= p["revive_bars"]:
                o.state = "ACTIVE"
                o.t_right = None
                if og["n_def"] >= g.get("n_def0", 0):
                    g["price"] = eprice
                    g["n_def0"] = og["n_def"]
                g["n_def"] = max(g.get("n_def", 0), og["n_def"])
                o.events.append((i, "revive", "same price re-approach"))
                return
        g = {"price": eprice, "side": "above" if og["dir"] > 0
             else "below", "n_def": og["n_def"], "n_def0": og["n_def"],
             "cls": og["cls"], "last_touch": i, "pierced": False}
        o = LabObj(kind, i, g, og["cls"], "LVL%04d" % len(self.objects))
        o.events.append((i, "born", "score=%.2f def=%d"
                         % (score, og["n_def"])))
        self.objects.append(o)

    def active(self, otype=None):
        return [o for o in self.objects if o.state == "ACTIVE"
                and (otype is None or o.type == otype)]

    # ---------------- lifecycle ------------------------------------ #

    def _maintain(self, i, bar):
        p = self.p
        abr = max(self._abr(i), 1e-9)
        tol = self._tol(i)
        for o in list(self.active()):
            g = o.geometry
            dist = abs(bar["c"] - g["price"])
            hit = abs(bar["h"] - g["price"]) <= tol or \
                abs(bar["l"] - g["price"]) <= tol
            if hit:
                g["last_touch"] = i
                g["n_def"] += 1 if not g.get("_run") else 0
            g["_run"] = hit
            # death: far from price, pierced twice, or stale
            if dist > p["live_abr"] * abr:
                o.close(i, "price_left")
                continue
            # decisive traverse: close flips to the other side of the
            # level beyond tol, and stays there for pierce_dead_bars
            sgn = np.sign(bar["c"] - g["price"])
            if abs(bar["c"] - g["price"]) > tol and \
                    sgn != 0 and sgn != g.get("_last_sign", sgn):
                g["pierce_n"] = g.get("pierce_n", 0) + 1
                if g["pierce_n"] >= p["pierce_dead_bars"]:
                    o.close(i, "traversed")
                    continue
            else:
                g["pierce_n"] = 0
            if sgn != 0:
                g["_last_sign"] = sgn
            if i - g.get("last_touch", o.t_birth) > p["stale_retire_bars"]:
                o.close(i, "stale")
