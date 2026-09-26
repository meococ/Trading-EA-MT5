"""VPA detector core — incremental, O(1)/O(k) per bar, no repaint.

Implements FEATURE_SPEC.md (bias, EMA25, causal pivots, touch-cluster barrier
engine, pressure, buildup, chop, squeeze, room, signal bar + stop entry) and the
three setup detectors (pattern break, combi, pullback reversal) with arbitration
and first-class skip reasons.

Design rules:
  - decision time = close of a completed M5 bar; only bars <= t are used;
  - every state update is O(1) or bounded (pivot confirmation O(L), barrier
    list <= 8 active, buildup windows <= 20 bars);
  - deterministic: no randomness, no wall clock, no future bars.
"""

import statistics

DEFAULTS = {
    # engine
    "pivot_lag": 2,
    "barrier_scan": 17,
    "barrier_t_min": 2,
    "barrier_expiry": 12,
    "barrier_eps_atr": 0.10,
    "barrier_break_atr": 0.05,
    "dedupe_atr": 0.10,
    "tombstone_keep": 48,
    # pressure
    "pressure_window": 6,
    "disp_min": 0.60,
    "er_min": 0.55,
    "clv_min": 0.20,
    "slope_min": 0.10,
    "pressure_dur_min": 2,
    # bias
    "bias_slope_lookback": 6,
    "bias_slope_min": 0.10,
    "bias_side_min": -0.20,
    # buildup
    "buildup_max": 8,
    "buildup_min": 3,
    "buildup_lower_atr": -0.05,
    "buildup_upper_atr": 0.35,
    "buildup_touch_atr": 0.10,
    "contraction_max": 0.75,
    "overlap_min": 0.50,
    "progression_min": 2.0 / 3.0,
    "counter_max": 0.80,
    # chop (Brooks barbwire proxy)
    "chop_lookback": 4,
    "chop_overlap_min": 0.65,
    "chop_prog_max": 1.0 / 3.0,
    "chop_body_max": 0.35,
    # bracket / execution contract
    "stop_pips": 8.0,
    "target_r": 2.0,
    "entry_buffer_pips": 1.0,
    "order_valid_bars": 3,
    "room_r_min": 2.0,
    "cost_pips": 1.0,
    "rho_max": 0.20,
    # sessions (UTC minutes of bar close)
    "london": (300, 660),
    "ny": (690, 1050),
    # combi
    "combi_body_atr": 0.35,
    "combi_clv": 0.50,
    "combi_inside_ratio": 0.75,
    # pullback reversal
    "pr_m_min": 2,
    "pr_m_max": 6,
    "pr_leg_bars": 7,
    "pr_leg_amp_atr": 1.20,
    "pr_depth_lo": 0.40,
    "pr_depth_hi": 0.60,
    "pr_corr_er_max": 0.55,
    "pr_contact_atr": 0.10,
    "pr_release_atr": 0.05,
    "warmup_bars": 50,
}


def _median(xs):
    return statistics.median(xs) if xs else float("nan")


class Detector:
    def __init__(self, bars, cfg=None):
        self.b = bars  # dict of numpy arrays -> lists
        self.cfg = dict(DEFAULTS)
        if cfg:
            self.cfg.update(cfg)
        self.n = len(bars["t"])
        self.records = []
        self.counters = {}
        self._init_state()

    # ---------------- state ----------------
    def _init_state(self):
        n = self.n
        self.tr = [0.0] * n
        self.atr = [float("nan")] * n
        self.ema = [float("nan")] * n
        self.clv = [0.0] * n
        self.pressure = [False] * n
        self.pdir = [0] * n
        self.pdur = [0] * n
        self.bias = [0] * n
        self.active = []       # barriers
        self.tombstones = []   # (side, level, lock_idx, exp_idx, broken_idx)
        self.last_barrier_break = {"up": -10**9, "dn": -10**9}
        self.last_pressure_end = -10**9
        self.last_pressure_side = 0

    def _cnt(self, key, n=1):
        self.counters[key] = self.counters.get(key, 0) + n

    # ---------------- indicator updates ----------------
    def _update_bar(self, t):
        b = self.b
        h, l, c = b["h"], b["l"], b["c"]
        tr = h[t] - l[t]
        if t > 0:
            tr = max(tr, abs(h[t] - c[t - 1]), abs(l[t] - c[t - 1]))
        self.tr[t] = tr
        if t == 13:
            self.atr[t] = sum(self.tr[0:14]) / 14.0
        elif t > 13:
            self.atr[t] = (13.0 * self.atr[t - 1] + tr) / 14.0
        if t == 24:
            self.ema[t] = sum(c[0:25]) / 25.0
        elif t > 24:
            self.ema[t] = (2.0 / 26.0) * c[t] + (24.0 / 26.0) * self.ema[t - 1]
        rng = h[t] - l[t]
        self.clv[t] = (2.0 * c[t] - h[t] - l[t]) / rng if rng > 0 else 0.0
        # pressure
        if t >= 5 and self.atr[t] == self.atr[t] and self.atr[t] > 0:
            cp = self._pressure_components(t, +1)
            if cp["ok"]:
                self.pdir[t] = 1
            else:
                cn = self._pressure_components(t, -1)
                if cn["ok"]:
                    self.pdir[t] = -1
            if self.pdir[t] != 0:
                self.pressure[t] = True
                if self.pdir[t - 1] == self.pdir[t]:
                    self.pdur[t] = self.pdur[t - 1] + 1
                else:
                    self.pdur[t] = 1
                self.last_pressure_end = t
                self.last_pressure_side = self.pdir[t]
        # bias
        if t >= self.cfg["bias_slope_lookback"] and self.atr[t] == self.atr[t] and self.atr[t] > 0:
            lb = self.cfg["bias_slope_lookback"]
            slope = (self.ema[t] - self.ema[t - lb]) / self.atr[t]
            side = (c[t] - self.ema[t]) / self.atr[t]
            if slope >= self.cfg["bias_slope_min"] and side >= self.cfg["bias_side_min"]:
                self.bias[t] = 1
            elif slope <= -self.cfg["bias_slope_min"] and side <= -self.cfg["bias_side_min"]:
                self.bias[t] = -1
            else:
                self.bias[t] = 0

    def _pressure_components(self, u, d):
        cfg = self.cfg
        w = cfg["pressure_window"]
        if u < w or self.atr[u] != self.atr[u] or self.atr[u] <= 0:
            return {"ok": False}
        c = self.b["c"]
        disp = d * (c[u] - c[u - w + 1]) / self.atr[u]
        den = sum(abs(c[k] - c[k - 1]) for k in range(u - w + 2, u + 1))
        er = d * (c[u] - c[u - w + 1]) / den if den > 0 else 0.0
        if den <= 0:
            return {"ok": False}
        mean_clv = d * sum(self.clv[u - w + 1:u + 1]) / w
        slope = d * (self.ema[u] - self.ema[u - w + 1]) / self.atr[u]
        ok = (disp >= cfg["disp_min"] and er >= cfg["er_min"]
              and mean_clv >= cfg["clv_min"] and slope >= cfg["slope_min"])
        return {"ok": ok, "disp": disp, "er": er, "clv": mean_clv, "slope": slope}

    # ---------------- pivots & barriers ----------------
    def _confirm_pivots(self, t):
        cfg = self.cfg
        L = cfg["pivot_lag"]
        i = t - L
        if i < L:
            return
        h, l = self.b["h"], self.b["l"]
        left_h = max(h[i - L:i])
        right_h = max(h[i + 1:i + L + 1])
        if h[i] > left_h and h[i] >= right_h:
            self._try_lock(i, +1)
        left_l = min(l[i - L:i])
        right_l = min(l[i + 1:i + L + 1])
        if l[i] < left_l and l[i] <= right_l:
            self._try_lock(i, -1)

    def _try_lock(self, i, side):
        cfg = self.cfg
        A = self.atr[i]
        if A != A or A <= 0:
            return
        eps = cfg["barrier_eps_atr"] * A
        h, l, c = self.b["h"], self.b["l"], self.b["c"]
        px = h[i] if side > 0 else l[i]
        touches = [i]
        prices = [px]
        j = i - 2
        limit = max(0, i - cfg["barrier_scan"])
        while j >= limit:
            p = h[j] if side > 0 else l[j]
            if abs(p - px) <= eps and all(abs(j - k) >= 2 for k in touches):
                touches.append(j)
                prices.append(p)
            j -= 1
        B = _median(prices)
        if len(touches) < cfg["barrier_t_min"]:
            self._cnt("skip_barrier_insufficient_touches")
            return
        if side > 0 and c[i] > B + cfg["barrier_break_atr"] * A:
            self._cnt("skip_barrier_already_broken")
            return
        if side < 0 and c[i] < B - cfg["barrier_break_atr"] * A:
            self._cnt("skip_barrier_already_broken")
            return
        for bar in self.active:
            if bar["side"] == side:
                if abs(bar["level"] - B) <= cfg["dedupe_atr"] * A:
                    self._cnt("skip_duplicate_barrier")
                    return
                shared = len(set(touches) & set(bar["touches"]))
                if shared >= 2:
                    self._cnt("skip_duplicate_barrier")
                    return
        self.active.append({
            "side": side, "level": B, "lock_idx": i, "exp_idx": i + cfg["barrier_expiry"],
            "touches": touches, "atr_lock": A,
        })

    def _barrier_update(self, t):
        cfg = self.cfg
        c, atr = self.b["c"], self.atr
        if atr[t] != atr[t] or atr[t] <= 0:
            return
        keep = []
        for bar in self.active:
            if t > bar["exp_idx"]:
                self.tombstones.append((bar["side"], bar["level"], bar["lock_idx"], bar["exp_idx"], None))
                self._cnt("barrier_expired")
                continue
            B = bar["level"]
            if bar["side"] > 0:
                if c[t - 1] <= B and c[t] >= B + cfg["barrier_break_atr"] * atr[t]:
                    self._on_break(bar, t)
                    self.tombstones.append((bar["side"], B, bar["lock_idx"], bar["exp_idx"], t))
                    continue
            else:
                if c[t - 1] >= B and c[t] <= B - cfg["barrier_break_atr"] * atr[t]:
                    self._on_break(bar, t)
                    self.tombstones.append((bar["side"], B, bar["lock_idx"], bar["exp_idx"], t))
                    continue
            keep.append(bar)
        self.active = keep
        self.tombstones = [x for x in self.tombstones if t - (x[3] or x[2]) <= cfg["tombstone_keep"]]

    # ---------------- setup evaluation ----------------
    def _on_break(self, bar, t):
        self.last_barrier_break["up" if bar["side"] > 0 else "dn"] = t
        self._cnt("raw_break")
        rec = self._eval_pattern_break(bar, t)
        if rec is not None:
            self.records.append(rec)

    def _session_of(self, t):
        m = self.b["utc_min"][t]
        lo, hi = self.cfg["london"]
        if lo <= m < hi:
            return "london"
        lo, hi = self.cfg["ny"]
        if lo <= m < hi:
            return "ny"
        return None

    def _bias_ok(self, t, d):
        return self.bias[t] != -d

    def _chop_at(self, t):
        cfg = self.cfg
        k = cfg["chop_lookback"]
        if t < k:
            return False
        o, h, l, c = self.b["o"], self.b["h"], self.b["l"], self.b["c"]
        overlaps = []
        doji = 0
        for i in range(t - k + 1, t + 1):
            rng = max(min(h[i] - l[i], h[i - 1] - l[i - 1]), 1e-12)
            overlaps.append(max(0.0, min(h[i], h[i - 1]) - max(l[i], l[i - 1])) / rng)
            body = abs(c[i] - o[i])
            if h[i] - l[i] > 0 and body / (h[i] - l[i]) <= cfg["chop_body_max"]:
                doji += 1
        overlap = sum(overlaps) / len(overlaps)
        # progression of support sequence
        seq = [l[i] for i in range(t - k + 1, t + 1)]
        ok = sum(1 for i in range(1, len(seq)) if (seq[i] - seq[i - 1]) >= 0)
        prog = ok / (len(seq) - 1)
        return overlap >= cfg["chop_overlap_min"] and prog <= cfg["chop_prog_max"] and doji >= 1

    def _room_pips(self, t, d, entry_level, pip):
        cfg = self.cfg
        best = None
        for bar in self.active:
            if bar["side"] != d:
                continue
            if d > 0 and bar["level"] > entry_level:
                dist = bar["level"] - entry_level
            elif d < 0 and bar["level"] < entry_level:
                dist = entry_level - bar["level"]
            else:
                continue
            if best is None or dist < best:
                best = dist
        return (best / pip) if best is not None else float("inf")

    def _buildup(self, t, d, B, A_B):
        cfg = self.cfg
        h, l, c = self.b["h"], self.b["l"], self.b["c"]
        best = None
        for n in range(cfg["buildup_max"], cfg["buildup_min"] - 1, -1):
            s = t - n
            if s < 1:
                continue
            inside = all(cfg["buildup_lower_atr"] * A_B <= d * (B - c[i]) <= cfg["buildup_upper_atr"] * A_B
                         for i in range(s, t))
            if not inside:
                self._cnt("buildup_fail_inside")
                continue
            touch_px = [h[i] if d > 0 else l[i] for i in range(s, t)]
            close_touches = sum(1 for p in touch_px if abs(p - B) <= cfg["buildup_touch_atr"] * A_B)
            if close_touches < 2:
                self._cnt("buildup_fail_touches")
                continue
            tr_w = self.tr[s:t]
            tr_prev = self.tr[max(0, s - 12):s]
            if not tr_w or not tr_prev:
                continue
            contraction = _median(tr_w) / _median(tr_prev) if _median(tr_prev) > 0 else 9.9
            if contraction > cfg["contraction_max"]:
                self._cnt("buildup_fail_contraction")
                continue
            overlaps = []
            for i in range(s + 1, t):
                den = max(min(h[i] - l[i], h[i - 1] - l[i - 1]), 1e-12)
                overlaps.append(max(0.0, min(h[i], h[i - 1]) - max(l[i], l[i - 1])) / den)
            overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
            if overlap < cfg["overlap_min"]:
                self._cnt("buildup_fail_overlap")
                continue
            sup = [l[i] if d > 0 else h[i] for i in range(s, t)]
            prog = sum(1 for i in range(1, len(sup)) if d * (sup[i] - sup[i - 1]) >= -0.05 * A_B) / (len(sup) - 1)
            if prog < cfg["progression_min"]:
                self._cnt("buildup_fail_progression")
                continue
            x = [d * (B - sup[i]) for i in range(len(sup))]
            recent = x[-2:]
            early = x[:2]
            denom = max(sum(early) / len(early), 1e-12)
            counter = (sum(recent) / len(recent)) / denom
            if counter > cfg["counter_max"]:
                self._cnt("buildup_fail_counter")
                continue
            best = {"n": n, "contraction": contraction, "overlap": overlap,
                    "progression": prog, "counter": counter, "start": s}
            break
        return best

    def _eval_pattern_break(self, bar, t):
        cfg = self.cfg
        d = bar["side"]
        B = bar["level"]
        pip = self.b["pip"]
        A_B = bar["atr_lock"]
        session = self._session_of(t)
        base = {
            "time": int(self.b["t"][t]), "bar_idx": t, "side": d, "level": B,
            "lock_idx": bar["lock_idx"], "touches": list(bar["touches"]),
            "session": session, "atr": self.atr[t], "ema": self.ema[t],
            "bias": self.bias[t], "setup": "pattern_break", "n": 0,
            "contraction": None, "overlap": None, "progression": None,
            "counter": None, "pressure_side": 0, "room_pips": None, "rho": None,
            "skip_reason": None, "executable": False,
            "entry_level": None, "invalidation": None, "buildup_start": None,
            "active_others": [(b["side"], b["level"]) for b in self.active
                              if not (b["side"] == bar["side"] and b["lock_idx"] == bar["lock_idx"])],
        }
        # ordered gates
        if t < cfg["warmup_bars"]:
            return self._reject(base, "skip_warmup")
        if session is None:
            return self._reject(base, "skip_session")
        if not self._bias_ok(t, d):
            return self._reject(base, "skip_bias")
        if self._chop_at(t):
            return self._reject(base, "skip_chop")
        # pressure somewhere in the recent pre-break window
        n_press = 0
        for u in range(max(0, t - cfg["buildup_max"] - 1), t + 1):
            if self.pdir[u] == d and self.pdur[u] >= cfg["pressure_dur_min"]:
                n_press = u
                break
        if not n_press:
            return self._reject(base, "skip_no_pressure")
        base["pressure_side"] = d
        bu = self._buildup(t, d, B, A_B)
        if bu is None:
            return self._reject(base, "skip_no_buildup")
        base.update({"n": bu["n"], "contraction": bu["contraction"], "overlap": bu["overlap"],
                     "progression": bu["progression"], "counter": bu["counter"],
                     "buildup_start": bu["start"]})
        entry_level = (self.b["h"][t] + cfg["entry_buffer_pips"] * pip) if d > 0 else (self.b["l"][t] - cfg["entry_buffer_pips"] * pip)
        inv = min(self.b["l"][bu["start"]:t]) if d > 0 else max(self.b["h"][bu["start"]:t])
        base.update({"entry_level": entry_level, "invalidation": inv})
        room = self._room_pips(t, d, entry_level, pip)
        base["room_pips"] = round(room, 3) if room != float("inf") else float("inf")
        rho = cfg["cost_pips"] / cfg["stop_pips"]
        base["rho"] = rho
        if room < cfg["room_r_min"] * cfg["stop_pips"]:
            return self._reject(base, "skip_room")
        if rho > cfg["rho_max"]:
            return self._reject(base, "skip_cost")
        # combi arbitration: pressure bar + inside bar immediately before trigger
        combi = self._combi_bars(t, d, B)
        if combi:
            base["setup"] = "combi"
            base["combi"] = combi
        base["executable"] = True
        self._cnt("executable_" + base["setup"])
        return base

    def _combi_bars(self, t, d, B):
        cfg = self.cfg
        if t < 2:
            return None
        p, q = t - 2, t - 1
        o, h, l, c = self.b["o"], self.b["h"], self.b["l"], self.b["c"]
        atr_p = self.atr[p]
        if atr_p != atr_p or atr_p <= 0 or (h[p] - l[p]) <= 0:
            return None
        if d * (c[p] - o[p]) < cfg["combi_body_atr"] * atr_p:
            return None
        if d * self.clv[p] < cfg["combi_clv"]:
            return None
        if h[q] > h[p] + 0.5 * self.b["tick"] or l[q] < l[p] - 0.5 * self.b["tick"]:
            return None
        if (h[q] - l[q]) / (h[p] - l[p]) > cfg["combi_inside_ratio"]:
            return None
        if d * (c[p] - B) > 0 or d * (c[q] - B) > 0:
            return None
        return {"p": p, "q": q}

    def _reject(self, base, reason):
        base["skip_reason"] = reason
        self._cnt(reason)
        self.records.append(base)
        return None

    # ---------------- main loop ----------------
    def run(self, max_bars=None):
        n = self.n if max_bars is None else min(self.n, max_bars)
        for t in range(n):
            self._update_bar(t)
            if t > 14:
                self._confirm_pivots(t)
                self._barrier_update(t)
            if t >= self.cfg["warmup_bars"]:
                self._maybe_pr(t)
        return self.records, self.counters

    # ---------------- pullback reversal ----------------
    def _pr_at(self, t, m):
        cfg = self.cfg
        d = 1 if self.pdir[self.last_pressure_end] == 1 else -1
        k = t - m - 1
        if k - cfg["pr_leg_bars"] < 0 or k < 1:
            return None
        if not (self.pdir[k] == d and self.pdur[k] >= cfg["pressure_dur_min"]):
            return None
        c, h, l = self.b["c"], self.b["h"], self.b["l"]
        if self.atr[k] != self.atr[k] or self.atr[k] <= 0:
            return None
        leg_amp = d * (c[k] - c[k - cfg["pr_leg_bars"]])
        if leg_amp < cfg["pr_leg_amp_atr"] * self.atr[k]:
            return None
        corr = range(k + 1, t)
        if len(list(corr)) < 2:
            return None
        Xc = min(l[i] for i in range(k + 1, t)) if d > 0 else max(h[i] for i in range(k + 1, t))
        depth = d * (c[k] - Xc) / leg_amp
        if not (cfg["pr_depth_lo"] <= depth <= cfg["pr_depth_hi"]):
            return None
        den = sum(abs(c[i] - c[i - 1]) for i in range(k + 2, t))
        corr_er = -d * (c[t - 1] - c[k]) / den if den > 0 else 0.0
        if not (0.0 <= corr_er <= cfg["pr_corr_er_max"]):
            return None
        if d * (c[t - 1] - c[t - 2]) < -0.10 * self.atr[k]:
            return None
        if d * self.clv[t - 1] < -0.10:
            return None
        # contact: structure or ema25
        struct = False
        for bar in self.active:
            if bar["lock_idx"] <= k - cfg["pr_leg_bars"] and abs(bar["level"] - Xc) <= cfg["pr_contact_atr"] * self.atr[k]:
                struct = True
                break
        ema_hit = any(l[i] - cfg["pr_contact_atr"] * self.atr[i] <= self.ema[i] <= h[i] + cfg["pr_contact_atr"] * self.atr[i]
                      for i in range(k + 1, t)) if self.ema[k] == self.ema[k] else False
        if not (struct or ema_hit):
            return None
        # release
        if d > 0:
            if not (c[t] >= h[t - 1] + cfg["pr_release_atr"] * self.atr[t]):
                return None
        else:
            if not (c[t] <= l[t - 1] - cfg["pr_release_atr"] * self.atr[t]):
                return None
        if d * (c[t] - self.b["o"][t]) <= 0 or d * self.clv[t] < 0.50:
            return None
        # PBP exclusion: no same-direction barrier break inside the correction
        if self.last_barrier_break["up" if d > 0 else "dn"] >= k - cfg["pr_leg_bars"]:
            self._cnt("skip_pbp_excluded")
            return None
        return {"d": d, "k": k, "m": m, "depth": depth, "corr_er": corr_er,
                "leg_amp": leg_amp, "struct": struct, "ema_hit": ema_hit}

    def _maybe_pr(self, t):
        # cheap precondition: a pressure leg ended 3..9 bars ago
        gap = t - self.last_pressure_end
        if not (3 <= gap <= 9):
            return
        for m in range(self.cfg["pr_m_min"], self.cfg["pr_m_max"] + 1):
            got = self._pr_at(t, m)
            if got is None:
                continue
            session = self._session_of(t)
            if session is None:
                self._cnt("pr_skip_session")
                return
            if not self._bias_ok(t, got["d"]):
                self._cnt("pr_skip_bias")
                return
            if self._chop_at(t):
                self._cnt("pr_skip_chop")
                return
            rec = {
                "time": int(self.b["t"][t]), "bar_idx": t, "side": got["d"], "level": None,
                "lock_idx": None, "touches": [], "session": session, "atr": self.atr[t],
                "ema": self.ema[t], "bias": self.bias[t], "setup": "pullback_reversal",
                "n": got["m"], "contraction": None, "overlap": None, "progression": None,
                "counter": None, "pressure_side": got["d"], "room_pips": None,
                "rho": self.cfg["cost_pips"] / self.cfg["stop_pips"], "skip_reason": None,
                "executable": True, "entry_level": None, "invalidation": None,
                "buildup_start": got["k"], "pr_depth": round(got["depth"], 4),
                "pr_corr_er": round(got["corr_er"], 4), "pr_struct": got["struct"],
                "pr_ema": got["ema_hit"],
                "active_others": [(b["side"], b["level"]) for b in self.active],
            }
            self.records.append(rec)
            self._cnt("executable_pullback_reversal")
            return
        return


def run_detector(bars, cfg=None, max_bars=None):
    return Detector(bars, cfg).run(max_bars=max_bars)
