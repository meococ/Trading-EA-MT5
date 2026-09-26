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

import gates
from swings import DCStream, SwingBook
from boxes import BoxBook
from lines import LineBook
from levels import LevelBook
from patterns import PatternBook
from salience import Salience, budget_class

PIP = 1e4

_DEFAULT_PARAMS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "params_v1_1.json")


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

class Obj:
    """One drawn (or stored-fact) object — schema per
    schema/perception_v1.json."""

    def __init__(self, otype, style, t_birth, geometry, why, role="",
                 oid=None):
        self.id = oid or "%s?" % otype[:3]
        self.type = otype
        self.style = style
        self.t_birth = t_birth          # bar index of first ink
        self.t_left = t_birth           # drawn span start
        self.t_right = None             # bar idx when closed
        self.geometry = geometry        # dict, pips / bar indices
        self.state = "ACTIVE"
        self.touches = []
        self.events = []                # (bar_idx, code, detail)
        self.role = role
        self.why = why
        self.priority = 5
        self.score = None               # live salience score (output only)

    def close(self, i, why):
        self.t_right = i
        self.state = "CLOSED"
        self.events.append((i, "close", why))

    def event(self, i, code, detail=""):
        self.events.append((i, code, detail))

    def to_dict(self):
        return {"id": self.id, "type": self.type, "style": self.style,
                "t_birth": self.t_birth, "t_left": self.t_left,
                "t_right": self.t_right, "geometry": self.geometry,
                "state": self.state, "touches": self.touches,
                "events": self.events, "role": self.role,
                "why": self.why, "priority": self.priority,
                "score": self.score}


# ------------------------------------------------------------------ #
# engine
# ------------------------------------------------------------------ #

class PerceptionEngine:
    """Causal M5 perception engine (Volman chart grammar), v1."""

    def __init__(self, params=None, feed=None):
        self.p = params or load_params()
        self.feed = (feed or self.p.get("feed_clock") or "BOOK").upper()
        self.bars = []                  # dicts: t,cet_min,o,h,l,c (pips)
        self.ema = []                   # EMA25 on close (pips)
        self.abr = []                   # ABR in pips
        self.objects = []               # all objects ever drawn
        self.domes = []                 # (idx, height_pips, side)
        self.bar_facts = []             # per-bar fact list
        self.pressure = {"state": "NEUTRAL", "since": 0, "conf": 0.0}
        self._ema_k = 2.0 / (self.p["ema_len"] + 1)
        sp = self.p["swing"]
        self.book = SwingBook(sp["pmin_abr"], sp["pstruct_abr"],
                              abr_fn=self._abr)
        self.dc = DCStream(self._theta, self._spike)
        self.boxes = BoxBook(self)
        self.lines = LineBook(self)
        self.levels = LevelBook(self)
        self.patterns = PatternBook(self)
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

    def active(self, otype=None):
        return [o for o in self.objects if o.state == "ACTIVE"
                and (otype is None or o.type == otype)]

    def _mk(self, otype, style, t_birth, geometry, why, role=""):
        o = Obj(otype, style, t_birth, geometry, why, role,
                oid="%s%04d" % (otype[:3], len(self.objects)))
        self.objects.append(o)
        self._prev_birth_i, self._last_birth_i = \
            self._last_birth_i, t_birth
        return o

    def _birth(self, cand, i, score):
        """Candidate wins a slot -> object ink.  Geometry is frozen."""
        g = dict(cand.geom)
        g["sali"] = {"feats": dict(cand.feats), "score": score,
                     "consumed": 0}
        style = {"BOX": "solid", "RANGE_OPEN": "open_lines",
                 "CONTEXT_RANGE": "dotted", "PATTERN_LINE": "solid",
                 "CONTEXT_LINE": "dotted", "LEVEL_CARRIED": "long_dashed",
                 "MINI_LEVEL": "dashed", "BRACKET": "bracket",
                 "SQUEEZE": "dashed_ellipse", "LABEL_TF": "letter",
                 "BAR_MARKER": "tick"}.get(cand.kind, "solid")
        o = self._mk(cand.kind, style, i, g, why=cand.route,
                     role=str(cand.meta.get("parent", "")))
        o.t_left = cand.t0
        o.score = score
        o.priority = {"BOX": 1, "PATTERN_LINE": 2, "SQUEEZE": 3,
                      "LEVEL_CARRIED": 3, "MINI_LEVEL": 3,
                      "BRACKET": 4, "RANGE_OPEN": 2,
                      "CONTEXT_RANGE": 2, "CONTEXT_LINE": 2,
                      "LABEL_TF": 4, "BAR_MARKER": 4}.get(cand.kind, 5)
        for k, v in cand.meta.items():
            if k == "parent":
                continue
            g.setdefault("meta_" + k, v)
        if cand.meta.get("live_tracker") and self.boxes._asia:
            self.boxes._asia["ro"] = o
        if cand.kind == "BOX" and cand.meta.get("thin"):
            o.event(i, "thin_range", "false-break prone (9.40a)")
        o.event(i, "born", "%s score=%.2f" % (cand.route, score))
        return o

    # ---------------- main update -------------------------------- #

    def update(self, t, o, h, l, c, cet_min=None):
        """Feed one closed M5 bar.  Prices in absolute terms."""
        i = len(self.bars)
        if cet_min is None:
            off = 0 if self.feed == "BOOK" else 3600   # DESIGN: EET->CET
            cet_min = int(((int(t) - off) % 86400) // 60)
        bar = {"i": i, "t": int(t), "cet_min": cet_min,
               "o": o * PIP, "h": h * PIP, "l": l * PIP, "c": c * PIP}
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
        self.ema.append(c * PIP if i == 0 else
                        self.ema[-1] + self._ema_k *
                        (c * PIP - self.ema[-1]))
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
            self.patterns.on_pivot(i, piv)
            self.levels.on_pivot(i, piv)
            # the box *touch* may be a micro pivot — tight buildups
            # (9.44a) never confirm a theta2 pivot inside; the windows
            # and the alternation prior still anchor on the theta2
            # stream inside on_pivot (DN_BOX §5).  CONTEXT_RANGE keeps
            # the structural trigger (session-scale object).
            self.boxes.on_pivot(i, piv)
            if self.book.is_structural(piv):
                self.boxes.reanchor_check(i, piv)
                self.boxes.propose_context_range(i)
            self.lines.on_pivot(i, piv)

        # ---- trackers + lifecycle ----
        self.boxes.asia_update(i)
        # bar-driven buildup route: tight congestions that never
        # confirm a pivot inside (9.44a, DN_BOX §6 false negatives)
        self.boxes.congestion_scan(i)
        self.levels.session_update(i)
        self.boxes.maintain(i)
        self.lines.maintain(i)
        self.levels.maintain(i)
        self.patterns.squeeze_scan(i)
        # Ruling 11 section 11.4a zombie retirement, after the books'
        # own maintain passes and before selection
        self._retire(i)

        # ---- selection ----
        self.salience.round(i)
        self._pressure_update(i)

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
