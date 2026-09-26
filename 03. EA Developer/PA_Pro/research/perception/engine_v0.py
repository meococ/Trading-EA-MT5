"""engine.py — PerceptionEngine v0 (spec §3, §4, §5).

Incremental, causal, deterministic.  Feed closed M5 bars via update();
objects at bar t depend on bars <= t only.  No outcomes, no future.

Bar input: dict or tuple with epoch ``t`` (server epoch = CET wall on the
BOOK feed, D3), ``o/h/l/c`` float prices.  All internal times are CET
minutes-of-day plus an absolute day index, so session rules (Asia 00:00,
EU 08:00, news 14:30/16:00 CET) work on the book's clock.

Object schema follows schema/perception_v1.json: id, type, style,
t_birth, t_left, t_right, geometry, state, touches[], events[], role,
why.  Prices are stored in pips (price * 1e4) to match the golden set.
"""

import json
import os

PIP = 1e4

# ------------------------------------------------------------------ #
# parameters
# ------------------------------------------------------------------ #

_DEFAULT_PARAMS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "params_v1.json")


def load_params(path=None):
    with open(path or _DEFAULT_PARAMS, encoding="utf8") as f:
        return json.load(f)


# ------------------------------------------------------------------ #
# objects
# ------------------------------------------------------------------ #

class Obj:
    """One drawn (or stored-fact) object."""

    def __init__(self, otype, style, t_birth, geometry, why, role="",
                 oid=None):
        self.id = oid or "%s?" % otype[:3]
        self.type = otype
        self.style = style
        self.t_birth = t_birth          # bar index
        self.t_left = t_birth
        self.t_right = None             # int bar idx when closed
        self.geometry = geometry        # dict, pips / bar indices
        self.state = "ACTIVE"
        self.touches = []               # (bar_idx, price) on edges
        self.events = []                # (bar_idx, code, detail)
        self.role = role
        self.why = why
        self.priority = 5

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
                "why": self.why, "priority": self.priority}


# ------------------------------------------------------------------ #
# engine
# ------------------------------------------------------------------ #

class PerceptionEngine:
    """Causal M5 perception engine (Volman chart grammar)."""

    def __init__(self, params=None):
        self.p = params or load_params()
        self.bars = []                  # dicts: t,cet_min,o,h,l,c (+day)
        self.ema = []                   # EMA25 on close (pips)
        self.abr = []                   # ABR in pips
        self.objects = []               # all objects ever created
        self.swings = []                # confirmed pivots: (idx, price, side)
        self.domes = []                 # (idx, height_pips, side)
        self.bar_facts = []             # per-bar fact list
        self.pressure = {"state": "NEUTRAL", "since": 0, "conf": 0.0}
        self._ema_k = 2.0 / (self.p["ema_len"] + 1)
        # leg/zigzag state
        self._leg = 0                   # +1 up leg, -1 down leg, 0 unknown
        self._ext_price = None          # current leg extreme (pips)
        self._ext_idx = 0
        self._leg_origin = None         # price of last confirmed pivot
        # Asia range state
        self._asia = None               # {"hi":p,"lo":p,"start":i}
        self._asia_day = None           # CET day already processed
        self._last_box_birth = -999
        self._last_squeeze = -999
        self._last_birth_i = None       # bar idx of latest _mk (cand_log)
        self._prev_birth_i = None       # the birth before it
        self._failed_attempts = {}      # round level -> count
        # daily range tracker for the 00/50 vs 20-grid switch (§2)
        self._cur_day = None
        self._day_hi = None
        self._day_lo = None
        self._day_ranges = []           # completed daily ranges, pips
        # Ruling 2 §2.2.3: candidate-universe audit channel.  When a list
        # is assigned, every structure the rules evaluate is appended —
        # born or vetoed — so drawn-vs-not-drawn can be measured without
        # birth-cap censorship.  None = off (zero overhead, unchanged
        # behaviour).
        self.cand_log = None

    # ---------------- helpers ------------------------------------ #

    def _cand(self, kind, idx, route, outcome, geom=None, **feats):
        if self.cand_log is None:
            return
        b = self.bars[idx]
        row = {"kind": kind, "idx": int(idx), "cet_min": b.get("cet_min"),
               "route": route, "outcome": outcome, "close": b["c"],
               "abr": round(self.abr[-1], 2) if self.abr else None,
               "ema": round(self.ema[idx], 2) if idx < len(self.ema)
               else None}
        # salience context, all causal (state as of this bar):
        #   since_birth_min — minutes since the previous structure born
        #   n_active        — live structures (excl. a just-born self)
        #   nearest_struct  — pips from candidate band mid to the closest
        #                     other live structure's band
        ref = self._prev_birth_i if outcome == "born" else \
            self._last_birth_i
        if ref is not None and ref < len(self.bars) and \
                b.get("cet_min") is not None:
            row["since_birth_min"] = b["cet_min"] - \
                self.bars[ref].get("cet_min", b["cet_min"])
        row["n_active"] = len(self.active()) - (1 if outcome == "born"
                                               else 0)
        if geom:
            row.update(geom)
        row.update(feats)
        lo, hi = self._geom_band(row, idx)
        if lo is not None:
            mid = (lo + hi) / 2.0
            ds = []
            for k, o in enumerate(self.objects):
                if o.state != "ACTIVE":
                    continue
                if outcome == "born" and k == len(self.objects) - 1:
                    continue            # the just-born object itself
                olo, ohi = self._obj_band(o, idx)
                if olo is None:
                    continue
                ds.append(0.0 if olo <= mid <= ohi else
                          min(abs(mid - olo), abs(mid - ohi)))
            row["nearest_struct_pips"] = round(min(ds), 2) if ds else None
        self.cand_log.append(row)

    def _geom_band(self, row, idx):
        """Candidate geom dict -> (lo, hi) band in pips."""
        if row.get("lo") is not None:
            return row["lo"], row["hi"]
        if row.get("bottom") is not None:
            return row["bottom"], row["top"]
        for k in ("price", "level"):
            if row.get(k) is not None:
                return row[k], row[k]
        if row.get("p0") is not None:
            p1 = row["p0"] + row.get("slope", 0.0) * \
                (idx - row.get("t0", idx))
            return min(row["p0"], p1), max(row["p0"], p1)
        return None, None

    def _obj_band(self, o, i):
        """Live object's (lo, hi) band in pips at bar i."""
        g = o.geometry
        if "bottom" in g and "top" in g:
            return g["bottom"], g["top"]
        if g.get("price") is not None:
            return g["price"], g["price"]
        if g.get("level") is not None:
            return g["level"], g["level"]
        if g.get("p0") is not None:
            p = g["p0"] + g.get("slope", 0.0) * (i - g["t0"])
            return p, p
        return None, None

    def _tol(self):
        p = self.p["edge_tol"]
        abr = self.abr[-1] if self.abr else 5.0
        return max(p["pips"], p["abr_frac"] * abr)

    def _grid_step(self):
        """00/50 grid by default; the 20-grid (00/20/40/60/80) in a
        declared low-volatility regime — rolling median daily range
        < 60 pips (p417)."""
        dp = self.p["derived"]
        if len(self._day_ranges) < 3:
            return 50
        r = sorted(self._day_ranges)
        med = r[len(r) // 2] if len(r) % 2 else \
            (r[len(r) // 2 - 1] + r[len(r) // 2]) / 2
        return 20 if med < dp["low_vol_daily_range_pips"] else 50

    def _swing_pull(self):
        s = self.p["swing"]
        abr = self.abr[-1] if self.abr else 5.0
        return max(s["confirm_pullback_pips"],
                   s["confirm_pullback_abr_frac"] * abr)

    def active(self, otype=None):
        return [o for o in self.objects if o.state == "ACTIVE"
                and (otype is None or o.type == otype)]

    def _mk(self, otype, style, t_birth, geometry, why, role=""):
        """Create + register an object with a deterministic per-run id."""
        o = Obj(otype, style, t_birth, geometry, why, role,
                oid="%s%04d" % (otype[:3], len(self.objects)))
        self.objects.append(o)
        self._prev_birth_i, self._last_birth_i = \
            self._last_birth_i, t_birth
        return o

    # ---------------- main update -------------------------------- #

    def update(self, t, o, h, l, c, cet_min=None):
        """Feed one closed M5 bar.  Prices in absolute terms."""
        i = len(self.bars)
        if cet_min is None:
            cet_min = int((t % 86400) // 60)   # server wall == CET (D3)
        bar = {"i": i, "t": int(t), "cet_min": cet_min,
               "o": o * PIP, "h": h * PIP, "l": l * PIP, "c": c * PIP}
        self.bars.append(bar)

        # daily range (for the 00/50 vs 20-grid regime switch)
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

        # EMA25 on close
        self.ema.append(c * PIP if i == 0 else
                        self.ema[-1] + self._ema_k * (c * PIP - self.ema[-1]))
        # ABR
        rng = bar["h"] - bar["l"]
        n = self.p["abr_len"]
        if i < n:
            self.abr.append(sum(b["h"] - b["l"] for b in self.bars) / (i + 1))
        else:
            self.abr.append(self.abr[-1] +
                            (rng - (self.bars[i - n]["h"] -
                                    self.bars[i - n]["l"])) / n)

        self._bar_facts(i)
        self._swing_update(i)
        self._asia_update(i)
        self._box_maintenance(i)
        self._line_update(i)
        self._carried_update(i)
        self._squeeze_update(i)
        self._pressure_update(i)
        self._budget(i)

    # ---------------- bar facts (§3.9) ---------------------------- #

    def _bar_facts(self, i):
        f = []
        b = self.bars[i]
        if i >= 1:
            p = self.bars[i - 1]
            if b["h"] > p["h"]:
                f.append("breakout_up")
            if b["l"] < p["l"]:
                f.append("breakout_down")
            tol_in = self.p["bar_facts"]["inside_protrusion_pips"]
            if b["h"] <= p["h"] + tol_in and b["l"] >= p["l"] - tol_in:
                f.append("inside")
            # strong/power bar: large vs neighbours, closes at far end
            lo = max(0, i - 5)
            neigh = [self.bars[k]["h"] - self.bars[k]["l"]
                     for k in range(lo, i)]
            avg = sum(neigh) / len(neigh) if neigh else rng_local(b)
            rng = b["h"] - b["l"]
            if rng >= self.p["bar_facts"]["strong_bar_vs_neighbours"] * avg:
                body = b["c"] - b["o"]
                if rng > 0 and (body > 0.6 * rng or body < -0.6 * rng):
                    f.append("strong_up" if body > 0 else "strong_down")
            # false high: up-break, bearish reply, reply broken down (p28)
            if i >= 2:
                b0, b1 = self.bars[i - 2], self.bars[i - 1]
                if (b1["h"] > b0["h"] and b1["c"] < b1["o"]
                        and b["l"] < b1["l"]):
                    f.append("false_high")
                if (b1["l"] < b0["l"] and b1["c"] > b1["o"]
                        and b["h"] > b1["h"]):
                    f.append("false_low")
        rng = b["h"] - b["l"]
        if rng > 0 and abs(b["c"] - b["o"]) <= \
                self.p["bar_facts"]["doji_body_frac"] * rng:
            f.append("doji")
        self.bar_facts.append(f)

    # ---------------- swings -------------------------------------- #

    def _swing_update(self, i):
        """Causal zigzag: a pivot confirms when price pulls back
        confirm_pullback beyond the leg extreme."""
        b = self.bars[i]
        pull = self._swing_pull()
        min_sw = self.p["swing"]["min_swing_pips"]
        if self._leg == 0:
            if i >= 2:
                self._leg = 1 if b["c"] > self.bars[0]["o"] else -1
                self._ext_price = b["h"] if self._leg > 0 else b["l"]
                self._ext_idx = i
                self._leg_origin = self.bars[0]["c"]
            return
        if self._leg > 0:                       # up leg, track highs
            if b["h"] >= self._ext_price:
                self._ext_price, self._ext_idx = b["h"], i
            # pivot confirms on a CLOSE pull below the extreme (wick dips
            # are noise); flip the tracking leg either way, record only
            # if the leg travelled >= min_swing
            if b["c"] <= self._ext_price - pull:
                if self._ext_price - self._leg_origin >= min_sw:
                    self._confirm_pivot(self._ext_idx, self._ext_price, +1)
                self._leg_origin = self._ext_price
                self._leg, self._ext_price, self._ext_idx = -1, b["l"], i
        else:                                   # down leg, track lows
            if b["l"] <= self._ext_price:
                self._ext_price, self._ext_idx = b["l"], i
            if b["c"] >= self._ext_price + pull:
                if self._leg_origin - self._ext_price >= min_sw:
                    self._confirm_pivot(self._ext_idx, self._ext_price, -1)
                self._leg_origin = self._ext_price
                self._leg, self._ext_price, self._ext_idx = +1, b["h"], i

    def _confirm_pivot(self, idx, price, side):
        """side +1 = pivot high, -1 = pivot low."""
        self.swings.append((idx, price, side))
        self._dome_update(idx, price, side)
        self._mw_update(idx, price, side)
        self._box_birth(idx, price, side)
        self._line_birth(idx, price, side)

    # ---------------- domes (§3.8) -------------------------------- #

    def _dome_update(self, idx, price, side):
        """Record swing height vs the level it rose from; flag shrinking
        sequences (facts only, never drawn)."""
        opp = [s for s in self.swings if s[2] == -side]
        if not opp:
            return
        base = opp[-1][1]
        height = (price - base) * side
        if height <= 0:
            return
        self.domes.append((idx, round(height, 2), side))
        seq = [d[1] for d in self.domes if d[2] == side][-4:]
        if len(seq) >= 3:
            shrinking = sum(seq[k] > seq[k + 1] for k in range(len(seq) - 1))
            if shrinking >= len(seq) - 1 - 0 or shrinking >= len(seq) - 2:
                pass  # mostly-shrinking flag read in snapshot()

    # ---------------- M/W brackets (§3.8) -------------------------- #

    def _mw_update(self, idx, price, side):
        """Two tops (or bottoms) within double-top tol, 4-28 bars apart
        -> BRACKET; the middle section is stored in geometry."""
        mw = self.p["mw"]
        tol = self.p["box"]["double_top_tol_pips"]
        same = [s for s in self.swings if s[2] == side]
        if len(same) < 2:
            return
        prev = same[-2]
        sep = idx - prev[0]
        letter = "M" if side > 0 else "W"
        cgeom = {"t0": prev[0], "t1": idx, "letter": letter,
                 "level": round(price, 2)}
        if not (mw["min_sep_bars"] <= sep <= mw["max_sep_bars"]):
            return
        if abs(price - prev[1]) > tol:
            return
        mid = min((b["l"] for b in self.bars[prev[0]:idx + 1]),
                  default=price) if side > 0 else \
            max((b["h"] for b in self.bars[prev[0]:idx + 1]), default=price)
        # the middle section must be a real dip/peak, not a flat pair
        if abs(price - mid) < self._swing_pull():
            self._cand("BRACKET", idx,
                       "mw_double_" + ("top" if side > 0 else "bottom"),
                       "vetoed_flat_mid", cgeom)
            return
        if any(o.type == "BRACKET" and o.state == "ACTIVE"
               and o.geometry.get("letter") == letter
               and o.t_left == prev[0] for o in self.objects):
            self._cand("BRACKET", idx,
                       "mw_double_" + ("top" if side > 0 else "bottom"),
                       "dedup_existing", cgeom)
            return
        # one live formation: an older bracket of the same family closes
        for o in self.active("BRACKET"):
            if o.geometry.get("letter") == letter:
                o.close(idx, "replaced_formation")
        cgeom["mid"] = round(mid, 2)
        br = self._mk("BRACKET", "bracket_" + letter.lower(), idx,
                      {"t0": prev[0], "t1": idx, "letter": letter,
                       "level": round(price, 2), "mid": round(mid, 2)},
                      why="mw_double_" + ("top" if side > 0 else "bottom"))
        self._cand("BRACKET", idx,
                   "mw_double_" + ("top" if side > 0 else "bottom"),
                   "born", cgeom)
        br.t_left = prev[0]
        br.priority = 4

    # ---------------- BOX (§3.1-3.3) ------------------------------- #

    def _box_birth(self, idx, price, side):
        """Routes (a) pullback-end and (b) double-top/bottom, evaluated on
        each confirmed pivot.  Route (c) Asia handled in _asia_update.

        Economy rule (spec §0): the chart is almost bare — at most one
        governing box at a time.  A new candidate is ignored while an
        active box still contains price; it replaces a broken/abandoned
        box only when its edges differ by more than tol.

        Candidate enumeration happens BEFORE the gates (Ruling 2 §2.2.3):
        the audit log sees every structure the routes would draw, vetoed
        or born.  Behaviour is unchanged: the double-top route is tried
        first; a second route candidate at the same pivot is shadowed.
        """
        bp = self.p["box"]
        tol = self._tol()
        win = self.p["window_bars"]
        b = self.bars[idx]
        same = [s for s in self.swings if s[2] == side and idx - s[0] <= win]
        opp = [s for s in self.swings if s[2] == -side and idx - s[0] <= win]

        # ---- candidates the routes find at this pivot ----
        cands = []
        # (b) range box: second extreme within double-top tol of a prior
        # one, separated by at least min_sep bars
        for prev in reversed(same[:-1]):
            if idx - prev[0] < bp["double_top_min_sep_bars"]:
                continue
            if abs(prev[1] - price) <= bp["double_top_tol_pips"]:
                lo_i = min(prev[0], idx)
                seg = self.bars[max(0, lo_i - 2):idx + 1]
                if side > 0:
                    top = max(prev[1], price)
                    bot = min(x["l"] for x in seg)
                else:
                    bot = min(prev[1], price)
                    top = max(x["h"] for x in seg)
                cands.append((bot, top, max(prev[0], 0),
                              "range_double_" +
                              ("top" if side > 0 else "bottom")))
                break
        # (a) pullback-end box: pivot confirms end of a correction
        if opp:
            last_opp = opp[-1]
            if side < 0:
                L, H = price, last_opp[1]
            else:
                L, H = last_opp[1], price
            t0a = min(idx, last_opp[0])
            if idx - t0a >= 3:
                cands.append((L, H, t0a, "pullback_end"))
        for c in cands[1:]:
            self._cand("BOX", idx, c[3], "route_shadow",
                       {"lo": c[0], "hi": c[1], "t_left": c[2]})

        # ---- gates, same order as before ----
        # while any box still brackets price it remains THE box — no new
        # birth (Volman keeps reading the same congestion, p89)
        for o in self.active("BOX"):
            if o.role == "NESTED":
                continue
            g = o.geometry
            if g["bottom"] - 3 * tol <= b["c"] <= g["top"] + 3 * tol:
                # re-anchor (p79,102; Fig 3.9): the frozen edge moves only
                # when a NEW double top/bottom lines up at a different
                # level; old poke extremes on that edge are then ignored
                edge = g["top"] if side > 0 else g["bottom"]
                move = abs(price - edge)
                if tol < move <= bp["reanchor_max_pips"] and \
                        idx - g.get("last_reanchor", -999) >= \
                        bp["reanchor_cooldown_bars"]:
                    pair = [s for s in self.swings
                            if s[2] == side and s[0] < idx and
                            idx - s[0] >= bp["double_top_min_sep_bars"] and
                            abs(s[1] - price) <=
                            bp["double_top_tol_pips"]]
                    if pair:
                        key = "top" if side > 0 else "bottom"
                        old = g[key]
                        g[key] = round(
                            max(price, pair[-1][1]) if side > 0
                            else min(price, pair[-1][1]), 2)
                        o.event(idx, "reanchor",
                                "%s %.1f->%.1f" % (key, old, g[key]))
                        g["last_reanchor"] = idx
                        o.touches = [tc for tc in o.touches
                                     if abs(tc[1] - old) > tol]
                        if side > 0:
                            g["touches_top"] = 0
                        else:
                            g["touches_bot"] = 0
                if cands:
                    c = cands[0]
                    self._cand("BOX", idx, c[3], "vetoed_governing",
                               {"lo": c[0], "hi": c[1], "t_left": c[2]})
                return
        if idx - self._last_box_birth < bp["birth_cooldown_bars"]:
            if cands:
                c = cands[0]
                self._cand("BOX", idx, c[3], "vetoed_cooldown",
                           {"lo": c[0], "hi": c[1], "t_left": c[2]})
            return
        if not cands:
            return
        # attempt the first candidate only — same behaviour as before
        # (route (b) preferred; a failed attempt does not fall through)
        lo, hi, t_left, why = cands[0]
        bx = self._make_box(idx, lo, hi, t_left, why)
        if bx is not None and bx.t_birth == idx:
            self._cand("BOX", idx, why, "born",
                       {"lo": lo, "hi": hi, "t_left": t_left})
        elif bx is not None:
            self._cand("BOX", idx, why, "dedup_existing",
                       {"lo": lo, "hi": hi, "t_left": t_left})
        else:
            env = (hi - lo < bp["height_min_pips"] - 0.01 or
                   hi - lo > bp["height_max_pips"] + 0.01)
            self._cand("BOX", idx, why,
                       "vetoed_envelope" if env else "vetoed_active",
                       {"lo": lo, "hi": hi, "t_left": t_left})

    def _make_box(self, i, lo, hi, t_left, why, role="", envelope=True,
                  force=False):
        bp = self.p["box"]
        if envelope and (hi - lo < bp["height_min_pips"] - 0.01 or
                         hi - lo > bp["height_max_pips"] + 0.01):
            return None
        b = self.bars[i]
        for o in self.active("BOX"):
            g = o.geometry
            if role == "NESTED" or o.role == "NESTED":
                continue
            # same structure -> keep the frozen one
            if abs(g["top"] - hi) <= self._tol() and \
                    abs(g["bottom"] - lo) <= self._tol():
                return o
            # old box still governs while price is inside it
            if not force and g["broke"] is None and \
                    g["bottom"] - self._tol() <= b["c"] <= \
                    g["top"] + self._tol():
                return None
            # supersede a broken/abandoned box only if materially new
            o.event(i, "superseded", "new_box %s" % why)
            o.state = "DELETED"
        bx = self._mk("BOX", "solid", i, {"top": round(hi, 2),
                                          "bottom": round(lo, 2)},
                      why=why, role=role)
        bx.t_left = int(t_left)
        bx.priority = 1
        bx.geometry["touches_top"] = 0
        bx.geometry["touches_bot"] = 0
        bx.geometry["broke"] = None
        self._last_box_birth = i
        return bx

    def _asia_update(self, i):
        """Route (c): RANGE_OPEN over 00:00-08:00 CET; convert to BOX on
        first close outside + follow-through, or at 08:00 if complete."""
        b = self.bars[i]
        ap = self.p["box"]["asia"]
        day = b["t"] // 86400
        if self._asia is None and self._asia_day != day and \
                b["cet_min"] <= ap["end_min_cet"]:
            # start at 00:00 if present, else at the first bar of the
            # session slice (partial Asia range — still tradeable)
            self._asia = {"hi": b["h"], "lo": b["l"], "start": i,
                          "range_obj": None}
        if self._asia is None:
            return
        a = self._asia
        if b["cet_min"] <= ap["end_min_cet"]:
            a["hi"] = max(a["hi"], b["h"])
            a["lo"] = min(a["lo"], b["l"])
            if a["range_obj"] is None and i - a["start"] >= 2:
                ro = self._mk("RANGE_OPEN", "open_lines", i,
                              {"top": round(a["hi"], 2),
                               "bottom": round(a["lo"], 2)},
                              why="asia_range")
                self._cand("RANGE_OPEN", i, "asia_range", "born",
                           {"lo": round(a["lo"], 2),
                            "hi": round(a["hi"], 2),
                            "t_left": a["start"]})
                ro.t_left = a["start"]
                ro.priority = 2
                a["range_obj"] = ro
            elif a["range_obj"] is not None:
                a["range_obj"].geometry["top"] = round(a["hi"], 2)
                a["range_obj"].geometry["bottom"] = round(a["lo"], 2)
        # conversion checks run every bar once the range exists
        if a["range_obj"] is not None and a["range_obj"].state == "ACTIVE":
            ro = a["range_obj"]
            outside = b["c"] > a["hi"] + self._tol() or \
                b["c"] < a["lo"] - self._tol()
            timed_out = b["cet_min"] >= ap["end_min_cet"]
            if outside or timed_out:
                ro.close(i, "asia_convert")
                thin = (a["hi"] - a["lo"]) <= ap["thin_height_pips"]
                bx = self._make_box(i, a["lo"], a["hi"], a["start"],
                                    "asia_session",
                                    role="ASIA", envelope=False,
                                    force=True)
                self._cand("BOX", i, "asia_session",
                           "born" if bx else "vetoed_active",
                           {"lo": round(a["lo"], 2),
                            "hi": round(a["hi"], 2),
                            "t_left": a["start"]})
                if bx and thin:
                    bx.event(i, "thin_range",
                             "false-break prone (9.40a)")
                self._asia = None
                self._asia_day = day
        elif a["range_obj"] is not None:
            self._asia = None
            self._asia_day = day

    def _box_maintenance(self, i):
        """Touches, pokes (T/F), freeze, re-anchor, break, right edge."""
        if not self.bars:
            return
        b = self.bars[i]
        tol = self._tol()
        bp = self.p["box"]
        for o in list(self.active("BOX")):
            g = o.geometry
            top, bot = g["top"], g["bottom"]
            hgt = top - bot
            # --- touches (for freeze accounting)
            if abs(b["h"] - top) <= tol or abs(b["c"] - top) <= tol:
                g["touches_top"] += 1
            if abs(b["l"] - bot) <= tol or abs(b["c"] - bot) <= tol:
                g["touches_bot"] += 1
            # --- break = close >= tol beyond edge
            broke_up = b["c"] > top + tol
            broke_dn = b["c"] < bot - tol
            if g["broke"] is None and (broke_up or broke_dn):
                side = "up" if broke_up else "down"
                edge_t = g["touches_top"] if broke_up else g["touches_bot"]
                # classify by buildup location (p24-27)
                recent = self.bars[max(0, i - 6):i]
                near = 1.2 * self.abr[i]
                if recent:
                    if broke_up:
                        rest = sum(abs(x["l"] - top) <= near
                                   for x in recent)
                    else:
                        rest = sum(abs(x["h"] - bot) <= near
                                   for x in recent)
                    if rest >= max(2, len(recent) // 2):
                        cls = "proper"
                    elif any(abs(x["l"] - top) <= near or
                             abs(x["h"] - bot) <= near
                             for x in recent):
                        cls = "tease"
                    else:
                        cls = "false"
                else:
                    cls = "false"
                if edge_t < bp["breakout_edge_min_touches"]:
                    cls += "_weak"      # <2 touches: break not meaningful
                g["broke"] = side
                g["break_class"] = cls
                g["break_bar"] = i
                o.event(i, "break", "%s %s" % (side, cls))
                # role reversal: broken edge -> LEVEL_CARRIED (p20,81)
                lvl = top if broke_up else bot
                self._spawn_carried(i, lvl,
                                    "broken_box_edge_%s" % side,
                                    side="below" if broke_up else "above")
            # --- right edge close 6-18 bars after break
            if g["broke"] is not None:
                nb = i - g["break_bar"]
                if nb >= bp["right_edge_min_bars_after_break"]:
                    # close when price no longer near box, or at max
                    near = not (b["l"] > top + 2 * tol or
                                b["h"] < bot - 2 * tol)
                    if not near or \
                            nb >= bp["right_edge_max_bars_after_break"]:
                        o.close(i, "post_break_window")
                        continue
            # --- pokes: wick beyond edge, close back inside (T/F);
            # and T->F relabels are evaluated every bar (they resolve on
            # the bars AFTER the poke)
            if g["broke"] is None:
                self._poke_check(o, i, b, top, bot, hgt, tol)
                self._tf_relabel(o, i, b, top, bot, hgt)
            # --- delete on unresolved chop
            if self._is_chop(i) and o.state == "ACTIVE" and i - \
                    o.t_birth > bp["width_max_bars"]:
                o.event(i, "delete", "chop_no_resolution")
                o.state = "DELETED"

    def _poke_check(self, o, i, b, top, bot, hgt, tol):
        bp = self.p["box"]
        # only established boxes attract labels (the edge must already
        # have been respected once)
        if o.geometry["touches_top"] + o.geometry["touches_bot"] < 2:
            return
        poke_up = b["h"] > top + bp["poke_min_pips"] and b["c"] <= top
        poke_dn = b["l"] < bot - bp["poke_min_pips"] and b["c"] >= bot
        if not (poke_up or poke_dn):
            return
        side = "above" if poke_up else "below"
        # one label per bar per box per side
        for o2 in self.objects:
            if o2.type == "LABEL_TF" and o2.role == o.id and \
                    o2.t_birth == i and o2.geometry["side"] == side:
                return
        depth = (b["h"] - top) if poke_up else (bot - b["l"])
        if depth > bp["poke_max_pips"] + tol:
            return                          # too deep: handled as break
        lbl = self._mk("LABEL_TF", "letter", i,
                       {"price": round(b["h"] if poke_up else b["l"], 2),
                        "side": "above" if poke_up else "below",
                        "letter": "T"},
                       why="poke_edge", role=o.id)
        self._cand("LABEL_TF", i, "poke_edge", "born",
                   {"price": round(b["h"] if poke_up else b["l"], 2),
                    "side": "above" if poke_up else "below"})
        lbl.t_left = i
        lbl.priority = 3
        o.touches.append((i, round(top if poke_up else bot, 2)))
        o.event(i, "poke", "T %s %.1f" % ("up" if poke_up else "down",
                                          depth))

    def _tf_relabel(self, o, i, b, top, bot, hgt):
        """Relabel T -> F when price closes back inside within 1-3 bars
        AND moves >= half the box height the other way (p76-77)."""
        bp = self.p["box"]
        for o2 in self.objects:
            if o2.type == "LABEL_TF" and o2.geometry["letter"] == "T" \
                    and o2.role == o.id and \
                    1 <= i - o2.t_birth <= bp["tf_relabel_bars"]:
                moved = (top - b["c"]) if o2.geometry["side"] == "above" \
                    else (b["c"] - bot)
                if moved >= bp["tf_relabel_frac_height"] * hgt and \
                        bot < b["c"] < top:
                    o2.geometry["letter"] = "F"
                    o2.event(i, "relabel", "T->F")

    def _is_chop(self, i):
        """Bars >= 2*ABR overlapping chaotically (§5 drop rule)."""
        n = self.p["derived"]["chop_overlap_bars"]
        if i < n:
            return False
        seg = self.bars[i - n + 1:i + 1]
        big = sum(1 for x in seg if x["h"] - x["l"] >=
                  self.p["derived"]["chop_bar_abr_mult"] * self.abr[x["i"]])
        if big >= n // 2:
            hi = max(x["h"] for x in seg)
            lo = min(x["l"] for x in seg)
            overlap = sum(min(x["h"], seg[k + 1]["h"]) -
                          max(x["l"], seg[k + 1]["l"])
                          for k, x in enumerate(seg[:-1]))
            return overlap > 0.6 * (hi - lo) * (n - 1) * 0.5
        return False

    # ---------------- PATTERN_LINE (§3.4) --------------------------- #

    def _line_birth(self, idx, price, side):
        """Trigger lines through same-side pivots (max touches within
        tol), honouring the slope rule for break-defining lines."""
        lp = self.p["pattern_line"]
        tol = max(lp["touch_tol_pips"], lp["touch_tol_abr_frac"] *
                  (self.abr[-1] if self.abr else 5.0))
        win = self.p["window_bars"]
        same = [s for s in self.swings
                if s[2] == side and idx - s[0] <= win]
        if len(same) < 2:
            return
        # freshness: a line is born only while it is being made — the
        # latest touch must be this pivot, and the line must either have
        # >=3 touches or sit within ~3 ABR of price (actionable trigger)
        if same[-1][0] != idx:
            return
        cur = self.bars[idx]["c"]
        # candidate lines through pivot pairs; keep the one with most
        # touches within tol
        best = None
        for a in range(len(same)):
            for bb in range(a + 1, len(same)):
                i0, p0 = same[a][0], same[a][1]
                i1, p1 = same[bb][0], same[bb][1]
                if i1 == i0:
                    continue
                slope = (p1 - p0) / (i1 - i0)
                # slope rule: a line through highs must be flat/falling
                # to define an upside break; through lows flat/rising
                # for a downside break (p49).  Context lines exempt.
                if side > 0 and slope > 0.30:
                    continue
                if side < 0 and slope < -0.30:
                    continue
                touches = [s for s in same
                           if abs(s[1] - (p0 + slope * (s[0] - i0)))
                           <= tol]
                if len(touches) >= lp["min_touches"]:
                    key = (len(touches), -(i1 - i0))
                    if best is None or key > best[0]:
                        best = (key, i0, p0, slope, touches)
        if best is None:
            return
        _, i0, p0, slope, touches = best
        sname = "top" if side > 0 else "bottom"
        cgeom = {"t0": i0, "p0": round(p0, 2), "slope": round(slope, 4),
                 "side": sname, "n_touches": len(touches)}
        # the new pivot must be on the line (it is what changed), and the
        # line must be actionable: >=3 touches or price within 3*ABR
        if touches[-1][0] != idx:
            self._cand("PATTERN_LINE", idx, "swing_line",
                       "vetoed_offline", cgeom)
            return
        line_now = p0 + slope * (idx - i0)
        if len(touches) < 3 and \
                abs(cur - line_now) > 3 * (self.abr[-1] or 5.0):
            self._cand("PATTERN_LINE", idx, "swing_line",
                       "vetoed_inactionable", cgeom)
            return
        # one active line per side: merge touches into the existing line,
        # or replace it only if the new fit is materially different
        for o in self.active("PATTERN_LINE"):
            g = o.geometry
            if g["side"] != sname:
                continue
            same_line = abs(g["slope"] - slope) * max(1, idx - i0) <= \
                2 * tol and abs(
                    g["p0"] + g["slope"] * (idx - g["t0"]) -
                    (p0 + slope * (idx - i0))) <= 2 * tol
            if same_line:
                if touches[-1][0] > g.get("last_touch", 0):
                    g["last_touch"] = touches[-1][0]
                    g["n_touches"] = max(g["n_touches"], len(touches))
                    o.event(idx, "touch", "%d" % touches[-1][0])
                self._cand("PATTERN_LINE", idx, "swing_line",
                           "merged_existing", cgeom)
                return
            # different line: keep the one with more/recent touches
            if touches[-1][0] <= g.get("last_touch", 0):
                self._cand("PATTERN_LINE", idx, "swing_line",
                           "vetoed_stale", cgeom)
                return
            o.close(idx, "replaced_by_newer_line")
        role = "trigger" if idx - i0 <= lp["trigger_bars"] else "pattern"
        ln = self._mk("PATTERN_LINE", "solid", idx,
                      {"t0": i0, "p0": round(p0, 2),
                       "slope": round(slope, 4),
                       "side": sname,
                       "last_touch": touches[-1][0],
                       "n_touches": len(touches)},
                      why="swing_line", role=role)
        self._cand("PATTERN_LINE", idx, "swing_line", "born", cgeom)
        ln.t_left = i0
        ln.priority = 2
        ln.geometry["pierced"] = False

    def _line_update(self, i):
        """Pierce policy: close through marks PIERCED (kept); extend
        3-17 bars past the break, then close."""
        lp = self.p["pattern_line"]
        b = self.bars[i]
        for o in list(self.active("PATTERN_LINE")):
            g = o.geometry
            price_at = g["p0"] + g["slope"] * (i - g["t0"])
            through = (b["c"] > price_at if g["side"] == "top"
                       else b["c"] < price_at)
            # a break-defining line is pierced when price crosses to the
            # breakout side: top line pierced upward, bottom downward
            pierced = (g["side"] == "top" and b["c"] > price_at + self._tol()) \
                or (g["side"] == "bottom" and b["c"] < price_at - self._tol())
            if pierced and not g["pierced"]:
                g["pierced"] = True
                g["pierce_bar"] = i
                o.event(i, "pierced", "close through line")
            if g["pierced"]:
                nb = i - g["pierce_bar"]
                # extend while pullbacks still reach the line (PBP)
                if abs(b["h"] - price_at) <= self._tol() or \
                        abs(b["l"] - price_at) <= self._tol():
                    g["last_touch"] = i
                if nb >= lp["extend_max_bars"] or \
                        (nb >= lp["extend_min_bars"] and
                         i - g.get("last_touch", g["pierce_bar"]) > 8):
                    o.close(i, "extension_done")

    # ---------------- LEVEL_CARRIED (§3.6) -------------------------- #

    def _spawn_carried(self, i, price, why, side="below"):
        # dedupe: an active same-side level within a few pips covers it
        dd = self.p["level_carried"]["dedupe_within_pips"]
        for o in self.active("LEVEL_CARRIED"):
            if o.geometry["side"] == side and \
                    abs(o.geometry["price"] - price) <= dd:
                self._cand("LEVEL_CARRIED", i, why, "dedup_existing",
                           {"price": round(price, 2), "side": side})
                return o
        lv = self._mk("LEVEL_CARRIED", "long_dashed", i,
                      {"price": round(price, 2), "side": side},
                      why=why)
        self._cand("LEVEL_CARRIED", i, why, "born",
                   {"price": round(price, 2), "side": side})
        lv.priority = 3
        return lv

    def _carried_update(self, i):
        """Consumed after one touch (p170)."""
        b = self.bars[i]
        tol = self._tol()
        for o in list(self.active("LEVEL_CARRIED")):
            p = o.geometry["price"]
            if b["l"] - tol <= p <= b["h"] + tol and i > o.t_birth:
                o.event(i, "touched", "consumed")
                o.close(i, "consumed_after_touch")

    # ---------------- SQUEEZE (§3.7) -------------------------------- #

    def _squeeze_update(self, i):
        sp = self.p["squeeze"]
        n = sp["preferred_bars"]
        if i < n + 3:
            return
        if i - getattr(self, "_last_squeeze", -999) < sp["cooldown_bars"]:
            return
        seg = self.bars[i - n + 1:i + 1]
        small = all(x["h"] - x["l"] <= sp["max_bar_range_abr"] *
                    self.abr[x["i"]] for x in seg)
        if not small:
            return
        hi = min(x["h"] for x in seg)
        lo = max(x["l"] for x in seg)
        gap = hi - lo
        if gap <= 0:
            return
        # the squeeze must be a compression (p57, p99): bar ranges inside
        # it materially smaller than the bars just before
        pre = self.bars[i - n - 2:i - n + 1]
        seg_rng = sum(x["h"] - x["l"] for x in seg) / n
        pre_rng = sum(x["h"] - x["l"] for x in pre) / len(pre)
        if seg_rng > sp["narrowing_frac"] * max(pre_rng, 0.5):
            return
        # between two opposing walls: structural edge/line vs EMA25/00-50
        walls = []
        for o in self.active("BOX"):
            walls += [o.geometry["top"], o.geometry["bottom"]]
        for o in self.active("PATTERN_LINE"):
            walls.append(o.geometry["p0"] +
                         o.geometry["slope"] * (i - o.geometry["t0"]))
        ema = self.ema[i]
        rn = round(seg[-1]["c"] / 50.0) * 50.0
        walls += [ema, rn]
        above = [w for w in walls if w >= hi - self._tol()]
        below = [w for w in walls if w <= lo + self._tol()]
        cgeom = {"t0": seg[0]["i"], "top": round(hi, 2),
                 "bottom": round(lo, 2), "mid": round((hi + lo) / 2, 2)}
        if not (above and below):
            self._cand("SQUEEZE", i, "small_bars_between_walls",
                       "vetoed_no_walls", cgeom)
            return
        if any(o.type == "SQUEEZE" and o.state == "ACTIVE"
               and abs(o.geometry["mid"] - (hi + lo) / 2) < 2
               for o in self.objects):
            self._cand("SQUEEZE", i, "small_bars_between_walls",
                       "dedup_existing", cgeom)
            return
        sq = self._mk("SQUEEZE", "dashed_ellipse", i,
                      {"t0": seg[0]["i"], "t1": i, "top": round(hi, 2),
                       "bottom": round(lo, 2),
                       "mid": round((hi + lo) / 2, 2)},
                      why="small_bars_between_walls")
        self._cand("SQUEEZE", i, "small_bars_between_walls", "born",
                   cgeom)
        sq.t_left = seg[0]["i"]
        sq.priority = 3
        self._last_squeeze = i

    # ---------------- §4 derived facts ------------------------------ #

    def _pressure_update(self, i):
        """EMA25 slope with hysteresis + curvature + structure (p21,47,
        101,227)."""
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
                # hysteresis: need persistence to flip
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
        # else: "flattening" keeps prior sign (p227)
        conf = min(1.0, abs(slope) / max(1.0, self.abr[i]))
        if curv * (1 if raw == "UP" else -1) < 0:
            conf *= 0.7
        self.pressure = {"state": raw, "since": i, "conf": round(conf, 2)}

    def stand_aside(self, i):
        """§4/§5 reasons to emit STAND_ASIDE."""
        out = []
        b = self.bars[i]
        for lo, hi in self.p["derived"]["news_windows_cet"]:
            if lo <= b["cet_min"] <= hi:
                out.append("news_window")
        if self._is_chop(i):
            out.append("chop")
        # round-number battle: a box straddling a 00/50
        c = b["c"]
        rn = round(c / 50.0) * 50.0
        for o in self.active("BOX"):
            if o.geometry["bottom"] < rn < o.geometry["top"]:
                out.append("round_number_battle")
        if not self.active("BOX") and not self.active("PATTERN_LINE") \
                and not self.active("SQUEEZE"):
            out.append("no_structure")
        return out

    def facts(self, i):
        """§4 derived facts for the setup layer."""
        b = self.bars[i]
        tol = self._tol()
        # round-number relations
        c = b["c"]
        rn_lo = (int(c) // 50) * 50.0
        rn_hi = rn_lo + 50.0
        # obstacles each direction: nearest level/edge/double-top
        obs_up, obs_dn = [], []
        for o in self.active():
            g = o.geometry
            if o.type == "BOX":
                obs_up.append((g["top"] - c, "box_edge", o.id))
                obs_dn.append((c - g["bottom"], "box_edge", o.id))
            elif o.type == "LEVEL_CARRIED":
                d = g["price"] - c
                (obs_up if d > 0 else obs_dn).append(
                    (abs(d), "level_carried", o.id))
            elif o.type == "PATTERN_LINE":
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

    # ---------------- budget (§5) ----------------------------------- #

    def _budget(self, i):
        """Keep at most structural_soft structural objects ACTIVE; hard
        cap structural_hard.  Priority per §5."""
        structural = [o for o in self.active()
                      if o.type in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE",
                                    "PATTERN_LINE", "CONTEXT_LINE",
                                    "LEVEL_CARRIED", "MINI_LEVEL",
                                    "SQUEEZE")]
        # drop objects that have left the 84-bar window
        win = self.p["window_bars"]
        for o in structural:
            if o.t_left < i - win and o.type not in (
                    "LEVEL_CARRIED", "RANGE_OPEN"):
                o.close(i, "left_window")
        structural = [o for o in self.active()
                      if o.type in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE",
                                    "PATTERN_LINE", "CONTEXT_LINE",
                                    "LEVEL_CARRIED", "MINI_LEVEL",
                                    "SQUEEZE")]
        if len(structural) <= self.p["budget"]["structural_soft"]:
            return
        structural.sort(key=lambda o: (o.priority, -o.t_birth))
        for o in structural[self.p["budget"]["structural_hard"]:]:
            o.close(i, "budget_cap")
        for o in structural[self.p["budget"]["structural_soft"]:
                            self.p["budget"]["structural_hard"]]:
            o.event(i, "parked", "over soft budget")

    # ---------------- snapshot -------------------------------------- #

    def snapshot(self, i=None):
        """JSON-able view at bar i (default: latest)."""
        i = len(self.bars) - 1 if i is None else i
        return {
            "bar": i,
            "objects": [o.to_dict() for o in self.objects
                        if o.state == "ACTIVE"
                        and (o.t_right is None or o.t_right >= i)],
            "facts": self.facts(i) if self.bars else {},
        }


def rng_local(b):
    return max(0.01, b["h"] - b["l"])


# ------------------------------------------------------------------ #
# convenience: feed a loader dict
# ------------------------------------------------------------------ #

def run(bars, params=None):
    """Feed a book_loader.load_m5() dict; return the engine."""
    eng = PerceptionEngine(params)
    for k in range(len(bars["t"])):
        eng.update(bars["t"][k], bars["o"][k], bars["h"][k],
                   bars["l"][k], bars["c"][k],
                   cet_min=int(bars["cet_min"][k]))
    return eng
