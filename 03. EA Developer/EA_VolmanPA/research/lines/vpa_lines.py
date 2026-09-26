"""vpa_lines.py — "draw lines like a pro": causal armed-line engine (T-VPA-LINE-1).

The DR3 "barrier" is a micro-line: 2 nearby lag-2 pivots within 0.1xATR,
horizontal, alive 20 bars.  A Volman trader instead prepares SIGNIFICANT lines
in advance and waits for price to build up against them.  This module returns,
at every closed M5 bar, the set of ARMED lines a pro would have on the chart.

Book grounding (page = printed page of Bob Volman, *Understanding Price Action*;
paraphrases in `PLAN/book/notes/*.md` and `PLAN/book/RULEBOOK.md`):

  * horizontal level, ceiling/floor that held several times: tr. 39-41
    ("ceiling test"), tr. 90/94/99 ("cang nhieu lan cham duong bien thi duong
    bien cang chac"), tr. 25/27 (buildup at the boundary of the range).
  * box / range boundary, aspect ~1:3: tr. 156 ("ve hop bao vung hanh vi gia
    ... ty le rong:dai ~1:3; bien tren/duoi la 2 muc phong thu chinh").
  * trendline through the important highs/lows, adjusted on later touches:
    tr. 109 ("duong xu huong khong the thay the"); signal bar closing right at
    the trendline: tr. 95 (bar 13).
  * flag (pole-flag-wave) and triangle/arch boundaries: tr. 113, tr. 101/105.
  * double tops / double bottoms / M-W structures: tr. 157, 170, 172 (handled
    here as a horizontal level through equal highs/lows).
  * round numbers 00/50 (low-vol grid 20): tr. 43, 45; tr. 417.
  * prior-day and session extremes as magnets / range borders: tr. 42/44 and
    tr. 98-99 (old highs/lows pull price), tr. 234/244 (old high becomes
    resistance), tr. 355/362 (Asia range broken at the EU/UK open).
  * integrity ("a ceiling must hold"): tr. 39-41; DR3 decision F2c used "no
    close beyond B by more than 0.10xATR between first touch and signal".
  * touch count = strength: tr. 90/94/99.

Causality contract
------------------
Decision time = the close of completed bar t.  `LineEngine.run()` is a single
forward pass; every piece of state is built from bars <= t only:

  * pivots are confirmed `lag` bars late (a lag-3 swing at i is known at i+3);
  * boxes/flags/triangles use the rolling window [s..t] and bars before s;
  * round numbers / PDH-PDL / session H-L use the running day/session clocks;
  * a line exists only from `created_idx` (the bar at which its last anchor
    became knowable) and never before;
  * `armed_at(t)` recomputes the state from bars[born..t] through the same
    `_step_line` code path the pass used, so there is one source of truth.

`test_vpa_lines.py` re-runs the engine on bars[:t+1] and asserts the same armed
set (prefix invariance).  No outcomes (fills, PnL, win rate) exist anywhere in
this module.
"""

import bisect
import collections
import statistics

DEFAULTS = {
    # ---------------- engine ----------------
    "warmup_bars": 20,           # ATR is valid from bar 13; swings from bar 6
    "atr_period": 14,
    "ema_period": 25,
    "min_touch_sep": 2,          # bars between two counted touches

    # ---------------- horizontal levels (tr. 39-41, 90, 94, 99) ----------
    "level_pivot_lag": 3,        # a swing that stands out over +-3 bars
    "level_eps_atr": 0.35,       # touch tolerance (a pro line is a zone)
    "level_scan_bars": 240,      # pivots older than this cannot seed a level
    "level_min_touches": 2,
    "level_seed_ttl": 96,        # 1-touch seed dies if never re-tested
    "level_max_age": 288,        # 24h
    "level_break_atr": 0.25,     # close through by more than this = broken
    "level_break_keep": 48,      # bars a broken line stays as role reversal
    "level_dedupe_atr": 0.30,    # two levels closer than this are one line
    "level_max_per_side": 5,     # keep the chart tidy (tr. 87/88)
    "stale_bars": 192,           # no touch for 16h -> redraw the chart (tr. 148)

    # ---------------- boxes (tr. 156, aspect 1:3) ------------------------
    "box_min_bars": 12,
    "box_max_height_atr": 5.0,   # a range can be tall; the aspect test rules
    "box_min_aspect": 3.0,       # width_price / height >= 3
    "box_touch_atr": 0.35,
    "box_break_atr": 0.25,
    "box_break_keep": 48,

    # ---------------- trendlines (tr. 95, 109) ---------------------------
    "tl_lookback": 160,
    "tl_max_pivots": 8,
    "tl_touch_atr": 0.35,
    "tl_slope_min_atr": 0.02,    # below this it is a horizontal level
    "tl_slope_max_atr": 0.40,    # too steep to trade (tr. 122)
    "tl_max_age": 240,
    "tl_break_atr": 0.25,
    "tl_break_keep": 24,
    "tl_dedupe_slope_atr": 0.02,
    "tl_max_per_side": 2,        # a pro keeps one or two trendlines (tr. 87/88)

    # ---------------- flags / triangles (tr. 113, 101, 105) --------------
    "pole_min_atr": 2.5,
    "pole_max_bars": 60,         # the flag can be hours long (tr. 113)
    "flag_min_bars": 6,
    "flag_pole_frac": 0.5,       # the flag is small vs the pole (tr. 113/153)
    "flag_max_height_atr": 5.0,  # same scale as the box window
    "tri_slope_eps_atr": 0.02,
    "pattern_break_atr": 0.25,
    "pattern_break_keep": 48,

    # ---------------- round numbers (tr. 43, 45, 417) --------------------
    "round_grid_pips": 50.0,
    "round_near_atr": 8.0,
    "round_touch_atr": 0.35,
    "round_max_age": 480,

    # ---------------- prior day / session extremes (tr. 42/44, 362) ------
    "pd_max_age": 576,
    "sess_windows": {"eu": (300, 660), "us": (690, 1050)},
    "sess_max_age": 144,

    # ---------------- higher-timeframe swings (M15/H1 proxies) -----------
    "htf_lags": (3, 6, 12),
    "htf_tol_atr": 0.60,
    "htf_weights": {3: 0.5, 6: 0.8, 12: 1.0},
    "htf_recent_swings": 32,     # alignment looks at the newest N per lag

    # ---------------- significance score ---------------------------------
    "score_w_touch": 0.35,
    "score_w_age": 0.20,
    "score_w_vis": 0.25,
    "score_w_htf": 0.20,
    "score_touch_full": 4.0,     # 4 touches saturate the touch term
    "score_age_full": 96.0,      # 8 hours saturate the age term
    "score_vis_full": 3.0,       # 3 ATR of travel away saturate visibility
    "score_threshold": 0.50,     # armed = score >= threshold

    # ---------------- pruning (chart hygiene) ----------------------------
    "max_lines": 8,
    "max_per_kind": 2,
    "prune_merge_atr": 0.15,     # two lines at the same price are one line
    "index_bucket": 512,         # bars per query-index bucket
}

#: kinds that carry a fixed geometric side (upper boundary = +1, lower = -1).
#: horizontal kinds take their side from the close at the query bar instead.
DIAGONAL_KINDS = ("trendline", "box_top", "box_bottom", "flag_upper",
                  "flag_lower", "tri_upper", "tri_lower")
HORIZONTAL_KINDS = ("level", "round", "pdh", "pdl", "sess_hi", "sess_lo")

#: kinds that expire when price has not tested them for `stale_bars`
_PATTERN_KINDS = ("level", "trendline", "box_top", "box_bottom", "flag_upper",
                  "flag_lower", "tri_upper", "tri_lower")

KIND_LABEL = {
    "level": "LEVEL", "box_top": "BOX-T", "box_bottom": "BOX-B",
    "trendline": "TREND", "flag_upper": "FLAG+", "flag_lower": "FLAG-",
    "tri_upper": "TRI+", "tri_lower": "TRI-", "round": "ROUND",
    "pdh": "PDH", "pdl": "PDL", "sess_hi": "SESS-H", "sess_lo": "SESS-L",
}

#: side of the line relative to price, for the display legend
SIDE_LABEL = {1: "ceiling", -1: "floor"}


def _median(xs):
    return statistics.median(xs) if xs else float("nan")


def _fit_line(xs, ys):
    """Least-squares slope/intercept; degenerate input -> flat line."""
    n = len(xs)
    if n < 2:
        return 0.0, (ys[0] if ys else 0.0)
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        return 0.0, my
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return slope, my - slope * mx


def _fresh_state():
    return {"touch_idx": [], "vis": 0.0, "run": 0.0, "last": -10 ** 9,
            "broken": None}


class _RollWin:
    """Rolling [s..t] window kept under a height cap with monotonic deques."""

    __slots__ = ("s", "hq", "lq")

    def __init__(self):
        self.s = 0
        self.hq = collections.deque()
        self.lq = collections.deque()

    def push(self, i, h, l, cap):
        while self.hq and self.hq[-1][1] <= h:
            self.hq.pop()
        self.hq.append((i, h))
        while self.lq and self.lq[-1][1] >= l:
            self.lq.pop()
        self.lq.append((i, l))
        while self.s < i and (self.hq[0][1] - self.lq[0][1]) > cap:
            self.s += 1
            while self.hq and self.hq[0][0] < self.s:
                self.hq.popleft()
            while self.lq and self.lq[0][0] < self.s:
                self.lq.popleft()
        return self.s, self.hq[0][1], self.lq[0][1]


class Line:
    """One drawn line.  Geometry is a step function of bar index: every change
    appends `(idx, slope, intercept)` to `g_idx`/`g_hist` (causal by idx)."""

    __slots__ = ("lid", "kind", "side_hint", "born_idx", "created_idx", "anchors",
                 "g_idx", "g_hist", "st", "end_idx", "meta")

    def __init__(self, lid, kind, side_hint, born_idx, created_idx, anchors,
                 geom, end_idx, meta=None):
        self.lid = lid
        self.kind = kind
        self.side_hint = side_hint
        self.born_idx = born_idx
        self.created_idx = created_idx
        self.anchors = tuple(anchors)
        self.g_idx = [created_idx]
        self.g_hist = [geom]
        self.st = _fresh_state()
        self.end_idx = end_idx
        self.meta = dict(meta or {})

    # ---- geometry ----
    def geom_at(self, t):
        k = bisect.bisect_right(self.g_idx, t) - 1
        if k < 0:
            k = 0        # before the first recorded step: creation geometry
        return self.g_hist[k]

    def price_at(self, t):
        s, b = self.geom_at(t)
        return s * t + b

    def set_geom(self, t, slope, intercept):
        s0, b0 = self.g_hist[-1]
        if abs(slope - s0) > 1e-12 or abs(intercept - b0) > 1e-12:
            self.g_idx.append(t)
            self.g_hist.append((slope, intercept))

    def side_at(self, t, close):
        """Ceiling (+1) / floor (-1).  Diagonal lines keep their hint; a
        horizontal line is a ceiling while price is below it (role reversal)."""
        if self.kind in HORIZONTAL_KINDS:
            return 1 if self.price_at(t) >= close else -1
        return self.side_hint


class ArmedLine:
    """Immutable view returned by `armed_at` (recomputed from bars <= t)."""

    __slots__ = ("lid", "kind", "side", "level", "slope", "intercept", "anchors",
                 "touches", "n_touches", "age", "integrity", "broken_idx",
                 "visibility_atr", "htf", "score", "parts", "meta")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def label(self):
        return KIND_LABEL.get(self.kind, self.kind.upper())

    def as_dict(self):
        return {
            "lid": self.lid, "kind": self.kind, "side": self.side,
            "level": self.level, "slope": self.slope,
            "anchors": list(self.anchors), "touches": list(self.touches),
            "n_touches": self.n_touches, "age": self.age,
            "integrity": self.integrity, "broken_idx": self.broken_idx,
            "visibility_atr": self.visibility_atr, "htf": self.htf,
            "score": self.score, "parts": dict(self.parts), "meta": dict(self.meta),
        }


class LineEngine:
    """Single forward pass over closed M5 bars; armed lines on demand."""

    def __init__(self, bars, cfg=None):
        self.b = bars
        self.cfg = dict(DEFAULTS)
        if cfg:
            for k, v in cfg.items():
                if k == "sess_windows":
                    self.cfg["sess_windows"] = dict(v)
                elif k == "htf_weights":
                    self.cfg["htf_weights"] = dict(v)
                else:
                    self.cfg[k] = v
        self.n = len(bars["t"])
        self.pip = float(bars["pip"])
        self.tick = float(bars["tick"])
        self._init_state()

    # ------------------------------------------------------------------ state
    def _init_state(self):
        n = self.n
        cfg = self.cfg
        self.atr = [float("nan")] * n
        self.ema = [float("nan")] * n
        self.lines = {}
        self.active = []
        self._next_lid = 1
        # HTF swings: lag k -> list of (idx, price, side, confirm_idx).  The
        # parallel `swing_j`/`swing_conf` arrays are bisect keys: both are
        # non-decreasing, so a query at bar t only ever looks at entries whose
        # confirm index is <= t (no future leak, prefix invariant).
        self.swings = {int(k): [] for k in cfg["htf_lags"]}
        self.swing_j = {int(k): [] for k in cfg["htf_lags"]}
        self.swing_conf = {int(k): [] for k in cfg["htf_lags"]}
        self._new_swings = []
        # day / session
        self.cur_day = None
        self.cur_day_high = None
        self.cur_day_low = None
        self.pdh = None
        self.pdl = None
        self.cur_sess = None
        self.sess_hi_line = None
        self.sess_lo_line = None
        # rounds
        self.round_grid = float(cfg["round_grid_pips"]) * self.pip
        self.round_lines = {}
        # rolling box/pattern window (one window, height-capped)
        self._tight = _RollWin()
        self._pattern_key = None
        self._pattern_lines = []
        # query index (built after the pass)
        self._buckets = None
        self._bucket_size = int(cfg["index_bucket"])
        self.counters = {}
        self._state_cache = {}

    def _cnt(self, key, n=1):
        self.counters[key] = self.counters.get(key, 0) + n

    def _new_line(self, kind, side_hint, born_idx, created_idx, anchors, geom,
                  end_idx, meta=None):
        ln = Line(self._next_lid, kind, side_hint, born_idx, created_idx, anchors,
                  geom, end_idx, meta)
        self._next_lid += 1
        self.lines[ln.lid] = ln
        self.active.append(ln)
        self._prime(ln, created_idx)
        return ln

    # ------------------------------------------------------------- indicators
    def _update_bar(self, t):
        b = self.b
        h, l, c = b["h"], b["l"], b["c"]
        tr = h[t] - l[t]
        if t > 0:
            tr = max(tr, abs(h[t] - c[t - 1]), abs(l[t] - c[t - 1]))
        p = self.cfg["atr_period"]
        if t == p - 1:
            self.atr[t] = sum(h[i] - l[i] for i in range(0, t + 1)) / float(t + 1)
        elif t >= p:
            self.atr[t] = ((p - 1) * self.atr[t - 1] + tr) / float(p)
        ep = self.cfg["ema_period"]
        if t == ep - 1:
            self.ema[t] = sum(c[0:ep]) / float(ep)
        elif t >= ep:
            self.ema[t] = (2.0 / (ep + 1.0)) * c[t] + ((ep - 1.0) / (ep + 1.0)) * self.ema[t - 1]

    def _update_day(self, t):
        b = self.b
        day = int(b["t"][t]) // 86400
        h, l = b["h"][t], b["l"][t]
        if self.cur_day is None or day != self.cur_day:
            if self.cur_day_high is not None:
                self.pdh = self.cur_day_high
                self.pdl = self.cur_day_low
                self._seed_pd(t)
            self.cur_day = day
            self.cur_day_high = h
            self.cur_day_low = l
        else:
            if h > self.cur_day_high:
                self.cur_day_high = h
            if l < self.cur_day_low:
                self.cur_day_low = l

    def _seed_pd(self, t):
        """Prior-day high/low (tr. 42/44, 98-99, 234/244): known at the first
        closed bar of the new UTC day, from bars that are all closed."""
        cfg = self.cfg
        for level, kind in ((self.pdh, "pdh"), (self.pdl, "pdl")):
            if level is None:
                continue
            self._new_line(kind, 0, t, t, (t,), (0.0, level),
                           t + cfg["pd_max_age"], {"src": "prev_day"})

    def _session_of(self, t):
        m = self.b["utc_min"][t]
        for name, (lo, hi) in self.cfg["sess_windows"].items():
            if lo <= m < hi:
                return name
        return None

    def _update_session(self, t):
        cfg = self.cfg
        sess = self._session_of(t)
        A = self.atr[t]
        if sess != self.cur_sess:
            self.cur_sess = sess
            self.sess_hi_line = None
            self.sess_lo_line = None
            if sess is not None and A == A and A > 0:
                self.sess_hi_line = self._new_line("sess_hi", 0, t, t, (t,),
                                                   (0.0, self.b["h"][t]),
                                                   t + cfg["sess_max_age"], {"session": sess})
                self.sess_lo_line = self._new_line("sess_lo", 0, t, t, (t,),
                                                   (0.0, self.b["l"][t]),
                                                   t + cfg["sess_max_age"], {"session": sess})
        elif sess is not None:
            if self.sess_hi_line is not None and self.b["h"][t] > self.sess_hi_line.g_hist[-1][1]:
                self.sess_hi_line.set_geom(t, 0.0, self.b["h"][t])
            if self.sess_lo_line is not None and self.b["l"][t] < self.sess_lo_line.g_hist[-1][1]:
                self.sess_lo_line.set_geom(t, 0.0, self.b["l"][t])

    def _update_rounds(self, t):
        """00/50 grid (tr. 43) armed once price comes within `round_near_atr`."""
        cfg = self.cfg
        A = self.atr[t]
        if A != A or A <= 0 or self.round_grid <= 0:
            return
        c = self.b["c"][t]
        near = cfg["round_near_atr"] * A
        for g in range(int((c - near) / self.round_grid), int((c + near) / self.round_grid) + 1):
            level = g * self.round_grid
            if level in self.round_lines:
                continue
            self.round_lines[level] = self._new_line(
                "round", 0, t, t, (t,), (0.0, level),
                t + cfg["round_max_age"], {"grid": self.round_grid})
            self._cnt("round_seeded")

    def _confirm_swings(self, t):
        """Confirm the pivot at j = t - k for every k in htf_lags; the lag-3
        swings are also the level/trendline seeds (a swing that stands out over
        3 bars either side is the pro's "obvious" high/low)."""
        h, l = self.b["h"], self.b["l"]
        self._new_swings = []
        for k in self.cfg["htf_lags"]:
            j = t - k
            if j < k or j + k > t:
                continue
            if h[j] > max(h[j - k:j]) and h[j] >= max(h[j + 1:j + k + 1]):
                self.swings[k].append((j, h[j], +1, t))
                self.swing_j[k].append(j)
                self.swing_conf[k].append(t)
                self._new_swings.append((k, j, h[j], +1))
            if l[j] < min(l[j - k:j]) and l[j] <= min(l[j + 1:j + k + 1]):
                self.swings[k].append((j, l[j], -1, t))
                self.swing_j[k].append(j)
                self.swing_conf[k].append(t)
                self._new_swings.append((k, j, l[j], -1))

    def _swings_between(self, k, lo, hi, side=None):
        """Swings of lag k with lo <= idx <= hi, already confirmed by hi + k
        (both bisect keys are non-decreasing)."""
        js = self.swing_j[int(k)]
        i0 = bisect.bisect_left(js, lo)
        i1 = bisect.bisect_right(js, hi)
        out = self.swings[int(k)][i0:i1]
        if side is None:
            return out
        return [s for s in out if s[2] == side]

    # ------------------------------------------------------------ line seeding
    def _seed_levels(self, t):
        cfg = self.cfg
        A = self.atr[t]
        if A != A or A <= 0:
            return
        lag = int(cfg["level_pivot_lag"])
        for (k, j, price, side) in self._new_swings:
            if k != lag:
                continue
            if t - j > cfg["level_scan_bars"]:
                continue
            eps = cfg["level_dedupe_atr"] * A
            dup = False
            for ln in self.active:
                if ln.kind != "level" or ln.side_hint != side:
                    continue
                if abs(ln.price_at(t) - price) <= eps:
                    dup = True
                    break
            if dup:
                self._cnt("level_seed_dup")
                continue
            self._new_line("level", side, j, t, (j,), (0.0, price),
                           min(j + cfg["level_max_age"], j + cfg["level_seed_ttl"]),
                           {"seed_side": side})
            self._cnt("level_seed")
            self._retire_excess("level", side, cfg["level_max_per_side"], t,
                                protect=self.active[-1])

    def _seed_trendlines(self, t):
        cfg = self.cfg
        A = self.atr[t]
        if A != A or A <= 0:
            return
        lag = int(cfg["level_pivot_lag"])
        for side in (+1, -1):
            piv = [(j, p) for (j, p, s, conf) in
                   self._swings_between(lag, t - cfg["tl_lookback"], t, side)]
            piv = piv[-int(cfg["tl_max_pivots"]):]
            if len(piv) < 2:
                continue
            best = None
            pairs = [(piv[i], piv[-1]) for i in range(max(0, len(piv) - 6), len(piv) - 1)]
            pairs.append((piv[-2], piv[-1]))
            for (ja, pa), (jb, pb) in pairs:
                if jb <= ja:
                    continue
                slope = (pb - pa) / float(jb - ja)
                if abs(slope) < cfg["tl_slope_min_atr"] * A or abs(slope) > cfg["tl_slope_max_atr"] * A:
                    continue
                inter = pa - slope * ja
                touches = 0
                for (j, p) in piv:
                    if abs(p - (slope * j + inter)) <= cfg["tl_touch_atr"] * A:
                        touches += 1
                if touches < 2:
                    continue
                if not self._tl_integrity(slope, inter, side, ja, t, A):
                    continue
                score = (touches, jb)
                if best is None or score > best[0]:
                    best = (score, slope, inter, ja, jb)
            if best is None:
                continue
            _, slope, inter, ja, jb = best
            v_now = slope * t + inter
            dup = False
            for ln in self.active:
                if ln.kind != "trendline" or ln.side_hint != side:
                    continue
                s0, b0 = ln.g_hist[-1]
                if (abs(s0 - slope) <= cfg["tl_dedupe_slope_atr"] * A
                        and abs((s0 * t + b0) - v_now) <= cfg["tl_touch_atr"] * A):
                    dup = True
                    break
            if dup:
                self._cnt("tl_seed_dup")
                continue
            ln = self._new_line("trendline", side, ja, t, (ja, jb), (slope, inter),
                                min(ja + cfg["tl_max_age"], t + cfg["tl_max_age"]),
                                {"anchors": (ja, jb)})
            self._cnt("tl_seed")
            self._retire_excess("trendline", side, cfg["tl_max_per_side"], t, protect=ln)

    def _retire_excess(self, kind, side, max_keep, t, protect=None):
        """Chart hygiene (tr. 87/88: keep the chart clean, one line or one box
        is enough): a pro does not stack trendlines; retire the weakest."""
        act = [ln for ln in self.active
               if ln.kind == kind and ln.side_hint == side and ln.end_idx >= t
               and ln.st["broken"] is None and ln is not protect]
        if len(act) < max_keep:
            return
        act.sort(key=lambda ln: (len(ln.st["touch_idx"]), ln.born_idx))
        for ln in act[:len(act) - max_keep + 1]:
            ln.end_idx = min(ln.end_idx, t)
            self._cnt("line_retired_" + kind)

    def _tl_integrity(self, slope, inter, side, ja, t, A):
        """No close beyond the line by more than `tl_break_atr` since the first
        anchor (tr. 109: a trendline that price closed through is gone)."""
        c = self.b["c"]
        eps = self.cfg["tl_break_atr"] * A
        for j in range(ja + 1, t + 1):
            v = slope * j + inter
            if side > 0 and c[j] > v + eps:
                return False
            if side < 0 and c[j] < v - eps:
                return False
        return True

    # --------------------------------------------------------- box / patterns
    def _window_update(self, t):
        cfg = self.cfg
        h, l = self.b["h"], self.b["l"]
        A = self.atr[t]
        cap = (cfg["box_max_height_atr"] * A) if (A == A and A > 0) else float("inf")
        ts, thi, tlo = self._tight.push(t, h[t], l[t], cap)
        if A != A or A <= 0:
            return
        kind = None
        born = ts
        geom = None
        pole_dir, pole_amp = 0, 0.0
        twidth = t - ts + 1
        theight = thi - tlo
        if twidth >= cfg["box_min_bars"] and theight > 0:
            pole_dir, pole_amp = self._pole_dir(ts, t, A)
            sh, bh, sl, bl = self._envelope_fit(ts, t)
            if sh is not None:
                if (sh < -cfg["tri_slope_eps_atr"] * A and sl > cfg["tri_slope_eps_atr"] * A):
                    kind = "triangle"
                    geom = (kind, sh, bh, sl, bl)
                elif (pole_dir != 0 and twidth >= cfg["flag_min_bars"]
                      and theight <= cfg["flag_pole_frac"] * pole_amp
                      and theight <= cfg["flag_max_height_atr"] * A):
                    kind = "flag"
                    geom = (kind, sh, bh, sl, bl)
            if kind is None:
                mean_range = sum(h[i] - l[i] for i in range(ts, t + 1)) / float(twidth)
                aspect = (twidth * mean_range) / theight if theight > 0 else 0.0
                if mean_range > 0 and aspect >= cfg["box_min_aspect"]:
                    kind = "box"
                    geom = (kind, 0.0, thi, 0.0, tlo)
        if kind is None:
            return
        key = (born, kind)
        if key == self._pattern_key:
            self._pattern_refresh(t, geom)
            return
        # a new pattern instance: a superseded, unbroken boundary is no longer
        # the pattern; a broken one stays as a role-reversal level (tr. 20/27)
        for ln in self._pattern_lines:
            if ln.st["broken"] is None:
                ln.end_idx = min(ln.end_idx, t)
            else:
                ln.end_idx = min(ln.end_idx, ln.st["broken"] + cfg["pattern_break_keep"])
        self._pattern_key = key
        self._pattern_lines = []
        if kind == "box":
            for tag, side, lvl in (("box_top", +1, geom[2]), ("box_bottom", -1, geom[4])):
                if self._pattern_dup(tag, side, lvl, A, t):
                    continue
                self._pattern_lines.append(self._new_line(
                    tag, side, born, t, (born,), (0.0, lvl), t + cfg["level_max_age"],
                    {"window": (born, t)}))
            self._cnt("box_seeded")
        else:
            tags = (("flag_upper", +1), ("flag_lower", -1)) if kind == "flag" \
                else (("tri_upper", +1), ("tri_lower", -1))
            for (tag, side), (slope, inter) in zip(tags, ((geom[1], geom[2]), (geom[3], geom[4]))):
                if self._pattern_dup(tag, side, slope * t + inter, A, t):
                    continue
                self._pattern_lines.append(self._new_line(
                    tag, side, born, t, (born,), (slope, inter), t + cfg["tl_max_age"],
                    {"window": (born, t), "pole_dir": pole_dir, "pole_amp_atr": pole_amp / A}))
            self._cnt("pattern_seeded_" + kind)

    def _pattern_refresh(self, t, geom):
        if not self._pattern_lines:
            return
        if geom[0] == "box":
            for ln, lvl in zip(self._pattern_lines, (geom[2], geom[4])):
                ln.set_geom(t, 0.0, lvl)
                ln.meta["window"] = (self._tight.s, t)
        else:
            for ln, (slope, inter) in zip(self._pattern_lines,
                                          ((geom[1], geom[2]), (geom[3], geom[4]))):
                ln.set_geom(t, slope, inter)
                ln.meta["window"] = (self._tight.s, t)

    def _pattern_dup(self, kind, side, price_now, A, t):
        """One boundary per price zone: retire an older unbroken twin (the new
        window draws the same line), keep a broken one (role reversal)."""
        eps = self.cfg["level_dedupe_atr"] * A
        for ln in self.active:
            if ln.kind != kind or ln.side_hint != side or ln.end_idx < t:
                continue
            if abs(ln.price_at(t) - price_now) > eps:
                continue
            if ln.st["broken"] is None:
                ln.end_idx = min(ln.end_idx, t)
                return False
            return True
        return False

    def _envelope_fit(self, s, t):
        """Boundary slopes from the swing highs/lows inside the window (a pro
        draws through the swing points, tr. 109).  Returns (None,)*4 when the
        window does not carry at least two swings per side: two points are the
        minimum for a line."""
        cfg = self.cfg
        lag = int(cfg["level_pivot_lag"])
        sw_hi = [(j, p) for (j, p, sd, conf) in
                 self._swings_between(lag, s, t, +1)]
        sw_lo = [(j, p) for (j, p, sd, conf) in
                 self._swings_between(lag, s, t, -1)]
        if len(sw_hi) < 2 or len(sw_lo) < 2:
            return None, None, None, None
        sh, bh = _fit_line([j for j, _ in sw_hi], [p for _, p in sw_hi])
        sl, bl = _fit_line([j for j, _ in sw_lo], [p for _, p in sw_lo])
        return sh, bh, sl, bl

    def _pole_dir(self, s, t, A):
        """Direction/amplitude of the impulse leg that precedes the window
        (tr. 113: a flag hangs on a pole).  Causal: scans bars < s only."""
        cfg = self.cfg
        c = self.b["c"]
        lo = max(0, s - int(cfg["pole_max_bars"]))
        if s <= lo:
            return 0, 0.0
        base = c[s]
        best = 0.0
        best_k = None
        for k in range(lo, s):
            amp = abs(base - c[k])
            if amp > best:
                best = amp
                best_k = k
        if best < cfg["pole_min_atr"] * A or best_k is None:
            return 0, best
        return (1 if base > c[best_k] else -1), best

    # -------------------------------------------------------- line step logic
    def _tolerances(self, kind, A):
        cfg = self.cfg
        if kind == "trendline":
            return cfg["tl_touch_atr"] * A, cfg["tl_break_atr"] * A
        if kind in ("box_top", "box_bottom", "flag_upper", "flag_lower",
                    "tri_upper", "tri_lower"):
            return cfg["box_touch_atr"] * A, cfg["pattern_break_atr"] * A
        if kind == "round":
            return cfg["round_touch_atr"] * A, cfg["round_touch_atr"] * A
        if kind == "level":
            return cfg["level_eps_atr"] * A, cfg["level_break_atr"] * A
        return cfg["round_touch_atr"] * A, cfg["level_break_atr"] * A

    def _step_line(self, ln, j, st):
        """One bar of a line's life.  Shared by the pass and by `_state_at`,
        so the reported state is exactly the state that was built."""
        cfg = self.cfg
        b = self.b
        A = self.atr[j]
        if A != A or A <= 0 or j < ln.born_idx:
            return
        v = ln.price_at(j)
        tol, brk = self._tolerances(ln.kind, A)
        side = ln.side_at(j, b["c"][j])
        if side > 0:
            touched = b["h"][j] >= v - tol and b["c"][j] <= v + brk
            exc = max(0.0, (v - b["l"][j]) / A)
        else:
            touched = b["l"][j] <= v + tol and b["c"][j] >= v - brk
            exc = max(0.0, (b["h"][j] - v) / A)
        if touched and (j - st["last"]) >= cfg["min_touch_sep"]:
            st["vis"] = max(st["vis"], st["run"])
            st["run"] = 0.0
            st["touch_idx"].append(j)
            st["last"] = j
        else:
            st["run"] = max(st["run"], exc)
        if st["broken"] is None and ln.kind != "round" and j > ln.born_idx:
            prev = b["c"][j - 1]
            v_prev = ln.price_at(j - 1)
            side_prev = ln.side_at(j - 1, prev)
            if side_prev > 0:
                crossed = prev <= v_prev + brk and b["c"][j] > v + brk
            else:
                crossed = prev >= v_prev - brk and b["c"][j] < v - brk
            if crossed:
                st["broken"] = j
                ln.end_idx = min(ln.end_idx, j + (cfg["tl_break_keep"] if ln.kind in DIAGONAL_KINDS
                                                  else cfg["level_break_keep"]))

    def _prime(self, ln, t):
        for j in range(ln.born_idx, t + 1):
            self._step_line(ln, j, ln.st)

    def _advance(self, t):
        keep = []
        for ln in self.active:
            if t > ln.end_idx:
                self._cnt("line_expired")
                continue
            self._step_line(ln, t, ln.st)
            if (ln.kind == "level" and len(ln.st["touch_idx"]) < self.cfg["level_min_touches"]
                    and t >= ln.born_idx + self.cfg["level_seed_ttl"]):
                ln.end_idx = min(ln.end_idx, t)
            if ln.kind in _PATTERN_KINDS and self.cfg["stale_bars"] > 0:
                last = ln.st["touch_idx"][-1] if ln.st["touch_idx"] else ln.born_idx
                if t - last > self.cfg["stale_bars"]:
                    ln.end_idx = min(ln.end_idx, t)
                    self._cnt("line_stale")
            keep.append(ln)
        self.active = keep

    # ------------------------------------------------------------------ score
    def _score_parts(self, ln, t, st):
        cfg = self.cfg
        A = self.atr[t]
        if A != A or A <= 0:
            return None
        n = len(st["touch_idx"])
        vis = max(st["vis"], st["run"])
        touch_term = min(1.0, n / cfg["score_touch_full"])
        age_term = min(1.0, max(0, t - ln.born_idx) / cfg["score_age_full"])
        vis_term = min(1.0, vis / cfg["score_vis_full"])
        htf = self._htf_align(ln, t)
        score = (cfg["score_w_touch"] * touch_term + cfg["score_w_age"] * age_term
                 + cfg["score_w_vis"] * vis_term + cfg["score_w_htf"] * htf)
        return {"touch": touch_term, "age": age_term, "visibility": vis_term,
                "htf": htf, "score": score, "vis_atr": vis}

    def _htf_align(self, ln, t):
        """Best matching higher-timeframe swing (lags 3/6/12 = M15/H1 proxy),
        looked up among the newest `htf_recent_swings` CONFIRMED by bar t."""
        cfg = self.cfg
        A = self.atr[t]
        if A != A or A <= 0:
            return 0.0
        tol = cfg["htf_tol_atr"] * A
        diag = ln.kind in DIAGONAL_KINDS
        best = 0.0
        recent = int(cfg["htf_recent_swings"])
        for k, w in cfg["htf_weights"].items():
            cut = bisect.bisect_right(self.swing_conf[int(k)], t)
            if cut <= 0:
                continue
            for (j, price, side, conf) in self.swings[int(k)][max(0, cut - recent):cut]:
                if diag and side != ln.side_hint:
                    continue
                ref = ln.price_at(j) if diag else ln.price_at(t)
                if abs(price - ref) <= tol:
                    best = max(best, float(w))
        return best

    # ------------------------------------------------------------ public view
    def _state_at(self, ln, t, use_cache=True):
        """Full causal state of `ln` at bar t, recomputed from bars[born..t]."""
        if t < ln.created_idx or t > ln.end_idx:
            return None
        key = (ln.lid, t)
        if use_cache and key in self._state_cache:
            return self._state_cache[key]
        A = self.atr[t]
        if A != A or A <= 0:
            return None
        st = _fresh_state()
        for j in range(ln.born_idx, t + 1):
            self._step_line(ln, j, st)
        parts = self._score_parts(ln, t, st)
        if parts is None:
            return None
        diag = ln.kind in DIAGONAL_KINDS
        slope, intercept = ln.geom_at(t)
        out = ArmedLine(
            lid=ln.lid, kind=ln.kind, side=ln.side_at(t, self.b["c"][t]),
            level=(slope * t + intercept if diag else intercept),
            slope=(slope if diag else 0.0), intercept=intercept,
            anchors=ln.anchors, touches=list(st["touch_idx"]),
            n_touches=len(st["touch_idx"]), age=t - ln.born_idx,
            integrity=(st["broken"] is None), broken_idx=st["broken"],
            visibility_atr=parts["vis_atr"], htf=parts["htf"],
            score=parts["score"], parts=parts, meta=dict(ln.meta),
        )
        if use_cache:
            if len(self._state_cache) > 200000:
                self._state_cache.clear()
            self._state_cache[key] = out
        return out

    def _candidates(self, t):
        if self._buckets is None:
            self._build_index()
        return [self.lines[lid] for lid in self._buckets.get(t // self._bucket_size, ())]

    def _build_index(self):
        self._buckets = {}
        bs = self._bucket_size
        for ln in self.lines.values():
            b0 = ln.created_idx // bs
            b1 = max(b0, ln.end_idx // bs)
            for b in range(b0, b1 + 1):
                self._buckets.setdefault(b, []).append(ln.lid)

    def armed_at(self, t, prune=True, threshold=None):
        """Armed lines at bar t: score >= threshold, recomputed from bars <= t.
        `prune=True` applies the chart-hygiene cap (max_lines / max_per_kind /
        same-price merge)."""
        th = self.cfg["score_threshold"] if threshold is None else threshold
        out = []
        for ln in self._candidates(t):
            a = self._state_at(ln, t)
            if a is not None and a.score >= th:
                out.append(a)
        out.sort(key=lambda a: (-a.score, a.lid))
        return self.prune(out, t) if prune else out

    def prune(self, armed, t=None):
        """A pro chart stays readable: cap the total, cap per kind, and merge
        lines that sit at the same price at the decision bar."""
        cfg = self.cfg
        out = []
        per_kind = {}
        eps = 0.0
        if t is not None:
            A = self.atr[t]
            if A == A and A > 0:
                eps = cfg["prune_merge_atr"] * A
        for a in armed:
            if len(out) >= cfg["max_lines"]:
                break
            if per_kind.get(a.kind, 0) >= cfg["max_per_kind"]:
                continue
            if eps > 0 and any(abs(a.level - b.level) <= eps for b in out):
                continue
            per_kind[a.kind] = per_kind.get(a.kind, 0) + 1
            out.append(a)
        return out

    def line_near(self, t, level, side=None, tol=None, threshold=None):
        """Best-scoring armed line at t whose price is within `tol` of `level`
        (used by the audit to test whether a broken boundary was on the chart).
        Price pre-filter runs before the state recomputation: cheap on the
        ~60k DR3 barrier locks."""
        A = self.atr[t]
        if A != A or A <= 0:
            return None
        tol = (0.25 * A) if tol is None else tol
        th = self.cfg["score_threshold"] if threshold is None else threshold
        best = None
        for ln in self._candidates(t):
            if t < ln.created_idx or t > ln.end_idx:
                continue
            if abs(ln.price_at(t) - level) > tol:
                continue
            if side is not None and ln.side_at(t, self.b["c"][t]) != side:
                continue
            a = self._state_at(ln, t)
            if a is None or a.score < th:
                continue
            if best is None or a.score > best.score:
                best = a
        return best

    # ------------------------------------------------------------------- run
    def run(self, max_bars=None):
        n = self.n if max_bars is None else min(self.n, max_bars)
        cfg = self.cfg
        for t in range(n):
            self._update_bar(t)
            self._update_day(t)
            self._confirm_swings(t)
            self._window_update(t)
            if t >= 14:
                self._update_session(t)
                self._update_rounds(t)
            if t >= cfg["warmup_bars"]:
                self._seed_levels(t)
                self._seed_trendlines(t)
            self._advance(t)
        self._build_index()
        return self


def run_lines(bars, cfg=None, max_bars=None):
    return LineEngine(bars, cfg).run(max_bars=max_bars)
