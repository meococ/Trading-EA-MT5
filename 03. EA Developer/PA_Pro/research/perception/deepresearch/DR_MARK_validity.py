"""DR_MARK_validity.py — E3c: value-blind path statistics on DESIGN
2016-2021, exactly as pre-registered in DR_MARK_LOG.md (06:23Z).

Loads DESIGN EURUSD M5 through scale/design_loader.py only.  Feeds the
real engine day by day (for its causal pivot stream + bar_facts + ABR),
then applies the PRE-REGISTERED RESEARCH DETECTORS on that stream —
not the engine's born objects (selection must not gate validity):

  EDGE      level where >=2 confirmed same-dir pivots agree within
            max(3p, 0.5*ABR), members confirmed within last 200 bars;
            edge level = extreme member price.  Active while
            i - last member t_ext <= 200.
  POKE(T)   wick beyond active edge > tol && close back inside &&
            depth <= 1.5*ABR.  Knowable at the poke bar.  One event per
            edge per excursion (re-arms when bar no longer exceeds edge).
  FBREAK(F) close beyond edge > tol, then close back inside within
            <=3 bars.  Knowable at the re-entry bar.
  COMPRESS  >=3 consecutive bars with range <= 0.8*ABR AND the run sits
            between an upper EDGE and a lower EDGE (each within
            2.0*ABR).  Knowable at the 3rd bar; one event per run.
  FALSE_EXT engine bar_facts false_high / false_low (3-bar pattern).
  BRACKET   M/W completed: pivot p confirms with an earlier same-dir
            pivot q, |p.price-q.price| <= max(3p,0.5*ABR),
            4 <= p.t_ext - q.t_ext <= 40, and an intervening opposite
            pivot r with |r.price - mean(p,q)| >= 0.5*ABR.
            mid = r.price (the formation midpoint).  Knowable at
            p.t_conf.

Measurement (value-blind): from event bar j and its level, the first
k>j (<=24 bars) where close >= level+0.5*ABR (exit UP) or close <=
level-0.5*ABR (exit DOWN); time-to-exit; max excursion toward the poke
side within the horizon.  All prices in pips (engine internal unit).
BRACKET: first revisit of `mid` (range touches mid +- 0.25*ABR), then
the first +-0.5*ABR close-exit from mid.

Controls (per pre-registration):
  CTRL_POKE  same wick-beyond-extreme geometry at a RAW running
             extreme (max/min of bars [i-50, i-3]) at bars where NO
             detected EDGE sits within 2*tol — same geometry without a
             defended level.  For C1 (F vs T) the T/F events themselves
             carry depth_abr + speed so matching is done in analysis.
  CTRL_FX    3-bar reversal that shares the first two legs of
             false_high/low (new extreme + counter close) but LACKS the
             undercut leg — isolates what leg 3 adds.
  CTRL_QUIET >=3 consecutive <=0.8*ABR bars NOT between two edges —
             C3 control (time to first +-0.5*ABR exit only).
  CTRL_SWING plain confirmed pivots not used as a bracket anchor —
             C4 control (same revisit->exit measurement).

Matching covariates stored per event: depth_abr, speed
(|c_i - c_{i-3}|/3/ABR), side, hour bucket, ABR decile (analysis-side).
Support < 30 -> non-identifiable, descriptive only.

Output: DR_MARK_validity.jsonl + printed counts.  No outcome, PnL,
trade simulation or setup logic anywhere.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, os.path.join(PERC, "..", "..", "lib"))
sys.path.insert(0, os.path.join(PERC, "scale"))

import design_loader as DL             # noqa: E402
import engine as ENG                   # noqa: E402

OUT = os.path.join(HERE, "DR_MARK_validity.jsonl")
HOR = 24          # bars forward
EXIT = 0.5        # * ABR
EDGE_WIN = 200    # bars (pre-reg)
EDGE_EQ_P = 3.0   # pips
EDGE_EQ_ABR = 0.5
POKE_MAX_ABR = 1.5
FB_WIN = 3        # bars to re-enter
SQ_ABR = 0.8
SQ_MIN = 3
SQ_WALL_ABR = 2.0
SEP_MIN, SEP_MAX = 4, 40
MID_MIN_ABR = 0.5


def first_exit(bars, level, j, abr, hor=HOR, ex=EXIT):
    up = level + ex * abr
    dn = level - ex * abr
    for k in range(j + 1, min(j + 1 + hor, len(bars))):
        if bars[k]["c"] >= up:
            return "up", k - j
        if bars[k]["c"] <= dn:
            return "down", k - j
    return None, None


def max_excursion(bars, level, j, side, hor=HOR):
    mx = 0.0
    for k in range(j + 1, min(j + 1 + hor, len(bars))):
        d = (bars[k]["h"] - level) if side == "above" \
            else (level - bars[k]["l"])
        mx = max(mx, d)
    return mx


def mid_revisit_exit(bars, mid, j, abr, hor=HOR, ex=EXIT):
    rv = None
    for k in range(j + 1, min(j + 1 + hor, len(bars))):
        if bars[k]["l"] - 0.25 * abr <= mid <= bars[k]["h"] + 0.25 * abr:
            rv = k
            break
    if rv is None:
        return None, None, None
    s, lag = first_exit(bars, mid, rv, abr, hor, ex)
    return rv - j, s, lag


def collect_day(e, m, day):
    """Pre-registered detectors replayed causally over the fed day."""
    n = len(e.bars)
    bars = e.bars
    abr = [e.abr[i] if i < len(e.abr) and e.abr[i] > 0 else 1.0
           for i in range(n)]
    pivs = sorted(e.book.seq, key=lambda p: p.t_conf)
    evts = []

    def add(kind, j, level, side, extra=None):
        if level is None or j is None or j >= n - 2:
            return
        s, lag = first_exit(bars, level, j, abr[j])
        rec = {"day": day, "kind": kind, "j": int(j),
               "t": int(m[j]) if j < len(m) else None,
               "hour": int(m[j] // 60) if j < len(m) else None,
               "level": float(level), "side": side,
               "abr": float(abr[j]),
               "exit": s, "lag": lag,
               "mx_poke": float(max_excursion(bars, level, j, side))
               if side else None}
        if extra:
            rec.update(extra)
        evts.append(rec)

    def speed(j):
        return abs(bars[j]["c"] - bars[j - 3]["c"]) / 3.0 / abr[j] \
            if j >= 3 else 0.0

    # ---- causal replay: edges form as pivots confirm -------------- #
    edges = []          # dicts: dir, lvl, members[t_ext], last_ext
    pend = {}           # edge id -> break bar
    pendepth = {}       # edge id -> max close-beyond depth (pips)
    poke_on = {}        # edge id -> excursion active
    seen_brk = set()
    pi = 0              # next pivot to confirm
    small_run = 0       # consecutive <=0.8*ABR bars
    sq_fired = False

    for i in range(n):
        b = bars[i]
        tol = max(1.0, 0.25 * abr[i])
        eqtol = max(EDGE_EQ_P, EDGE_EQ_ABR * abr[i])

        # confirm pivots due at bar i
        while pi < len(pivs) and pivs[pi].t_conf <= i:
            p = pivs[pi]
            pi += 1
            # (a) EDGE: if no live same-dir edge already covers this
            # pivot's level, pair with the most recent same-dir
            # confirmed pivot within eqtol/<=200 bars and open one edge.
            covered = False
            for eid, ed in enumerate(edges):
                if ed["dir"] == p.dir and \
                        abs(ed["lvl"] - p.price) <= eqtol and \
                        i - ed["last_ext"] <= EDGE_WIN:
                    ed["last_ext"] = max(ed["last_ext"], p.t_ext)
                    covered = True
            if not covered:
                qs = [q for q in pivs[:pi - 1]
                      if q.dir == p.dir and
                      abs(q.price - p.price) <= eqtol and
                      1 <= p.t_ext - q.t_ext <= EDGE_WIN]
                if qs:
                    q = max(qs, key=lambda x: x.t_ext)
                    lvl = max(q.price, p.price) if p.dir > 0 else \
                        min(q.price, p.price)
                    edges.append({"dir": p.dir, "lvl": lvl,
                                  "born": p.t_conf,
                                  "last_ext": max(q.t_ext, p.t_ext)})
                    eid = len(edges) - 1
                    pend[eid] = None
                    pendepth[eid] = 0.0
                    poke_on[eid] = False
            # (b) BRACKET: every qualifying same-dir pair is an M/W
            # candidate regardless of edge dedup.
            for q in pivs[:pi - 1]:
                if q.dir != p.dir:
                    continue
                if abs(q.price - p.price) > eqtol:
                    continue
                if not (SEP_MIN <= p.t_ext - q.t_ext <= SEP_MAX):
                    continue
                mid_r = None
                for r in pivs[:pi]:
                    if r.dir == -p.dir and \
                            q.t_ext < r.t_ext < p.t_ext:
                        if mid_r is None or (
                                p.dir > 0 and
                                r.price < mid_r.price) or (
                                p.dir < 0 and
                                r.price > mid_r.price):
                            mid_r = r
                if mid_r is not None and abs(
                        mid_r.price - (p.price + q.price) / 2.0
                        ) >= MID_MIN_ABR * abr[i]:
                    key = (q.t_ext, p.t_ext)
                    if key not in seen_brk:
                        seen_brk.add(key)
                        mid = mid_r.price
                        lvl = max(q.price, p.price) if p.dir > 0 else \
                            min(q.price, p.price)
                        rv, s2, lg2 = mid_revisit_exit(
                            bars, mid, p.t_conf, abr[p.t_conf])
                        add("BRACKET", int(p.t_conf), mid, None,
                            {"letter": "M" if p.dir > 0 else "W",
                             "edge": lvl,
                             "revisit_lag": rv,
                             "mid_exit": s2,
                             "mid_exit_lag": lg2})

        # expire edges older than EDGE_WIN bars since last member
        live = [eid for eid, ed in enumerate(edges)
                if ed["born"] <= i and i - ed["last_ext"] <= EDGE_WIN]

        # ---- POKE / FBREAK per live edge -------------------------- #
        for eid in live:
            ed = edges[eid]
            lvl = ed["lvl"]
            if ed["dir"] > 0:            # resistance
                depth = b["h"] - lvl
                broke = b["c"] > lvl + tol
                reenter = pend[eid] is not None and b["c"] <= lvl
                poke = depth > tol and b["c"] <= lvl
            else:                        # support
                depth = lvl - b["l"]
                broke = b["c"] < lvl - tol
                reenter = pend[eid] is not None and b["c"] >= lvl
                poke = depth > tol and b["c"] >= lvl
            if broke:
                if pend[eid] is None:
                    pend[eid] = i
                    pendepth[eid] = 0.0
                pendepth[eid] = max(pendepth[eid],
                                    abs(b["c"] - lvl))
                poke_on[eid] = False
            elif reenter:
                if i - pend[eid] <= FB_WIN:
                    add("FBREAK", i, lvl,
                        "above" if ed["dir"] > 0 else "below",
                        {"depth_abr": round(
                            pendepth[eid] / abr[i], 2),
                         "speed": round(speed(i), 2),
                         "brk_lag": i - pend[eid]})
                pend[eid] = None
                pendepth[eid] = 0.0
            elif pend[eid] is not None:
                pendepth[eid] = max(pendepth[eid],
                                    abs(b["c"] - lvl))
                if i - pend[eid] > FB_WIN:
                    pend[eid] = None
                    pendepth[eid] = 0.0
            if poke and depth <= POKE_MAX_ABR * abr[i] and \
                    not poke_on[eid]:
                add("POKE", i, lvl,
                    "above" if ed["dir"] > 0 else "below",
                    {"depth_abr": round(depth / abr[i], 2),
                     "speed": round(speed(i), 2)})
                poke_on[eid] = True
            if not poke and not broke and \
                    (depth <= tol if ed["dir"] > 0 else depth <= tol):
                poke_on[eid] = False

        # ---- COMPRESS --------------------------------------------- #
        if b["h"] - b["l"] <= SQ_ABR * abr[i]:
            small_run += 1
        else:
            small_run = 0
            sq_fired = False
        if small_run == SQ_MIN and not sq_fired:
            run_hi = max(x["h"] for x in bars[i - SQ_MIN + 1:i + 1])
            run_lo = min(x["l"] for x in bars[i - SQ_MIN + 1:i + 1])
            has_top = any(ed["dir"] > 0 and
                          0 < ed["lvl"] - run_hi <= SQ_WALL_ABR * abr[i]
                          for ed in (edges[e] for e in live))
            has_bot = any(ed["dir"] < 0 and
                          0 < run_lo - ed["lvl"] <= SQ_WALL_ABR * abr[i]
                          for ed in (edges[e] for e in live))
            mid = (run_hi + run_lo) / 2.0
            if has_top and has_bot:
                add("SQUEEZE", i, mid, None,
                    {"top": run_hi, "bot": run_lo})
            else:
                add("CTRL_QUIET", i, mid, None,
                    {"top": run_hi, "bot": run_lo})
            sq_fired = True

        # ---- FALSE_EXT (engine bar_facts, pre-reg detector) -------- #
        if i < len(e.bar_facts):
            f = e.bar_facts[i]
            if "false_high" in f and i >= 1:
                add("FX_H", i, bars[i - 1]["h"], "above",
                    {"speed": round(speed(i), 2)})
            if "false_low" in f and i >= 1:
                add("FX_L", i, bars[i - 1]["l"], "below",
                    {"speed": round(speed(i), 2)})
            # CTRL_FX: same first two legs, no undercut leg
            if i >= 2:
                b0, b1 = bars[i - 2], bars[i - 1]
                if b1["h"] > b0["h"] and b1["c"] < b1["o"] and \
                        b["l"] >= b1["l"] and "false_high" not in f:
                    add("CTRL_FX_H", i, b1["h"], "above",
                        {"speed": round(speed(i), 2)})
                if b1["l"] < b0["l"] and b1["c"] > b1["o"] and \
                        b["h"] <= b1["h"] and "false_low" not in f:
                    add("CTRL_FX_L", i, b1["l"], "below",
                        {"speed": round(speed(i), 2)})

        # ---- CTRL_POKE: raw extreme, no edge ----------------------- #
        if i >= 52:
            run_hi = max(x["h"] for x in bars[i - 50:i - 2])
            run_lo = min(x["l"] for x in bars[i - 50:i - 2])
            live_lvls = [edges[e]["lvl"] for e in live]
            for sd, ext, lvl in (("above", b["h"], run_hi),
                                 ("below", b["l"], run_lo)):
                depth = (ext - lvl) if sd == "above" else (lvl - ext)
                if depth <= tol or depth > POKE_MAX_ABR * abr[i]:
                    continue
                inside = (b["c"] <= lvl) if sd == "above" else \
                    (b["c"] >= lvl)
                if not inside:
                    continue
                if live_lvls and min(abs(x - lvl)
                                     for x in live_lvls) <= 2 * tol:
                    continue
                add("CTRL_POKE", i, lvl, sd,
                    {"depth_abr": round(depth / abr[i], 2),
                     "speed": round(speed(i), 2)})

    # ---- CTRL_SWING: plain pivots not anchoring a bracket ---------- #
    used = set()
    for a, b_ in seen_brk:
        used.add(a)
        used.add(b_)
    cand = [p for p in pivs if p.t_conf < n - 2
            and p.t_ext not in used]
    step = max(1, len(cand) // 5)
    for p in cand[::step][:5]:
        rv, s2, lg2 = mid_revisit_exit(
            bars, p.price, int(p.t_conf), abr[int(p.t_conf)])
        add("CTRL_SWING", int(p.t_conf), p.price, None,
            {"revisit_lag": rv, "mid_exit": s2, "mid_exit_lag": lg2})
    return evts


def main():
    days = DL.day_list("EURUSD")
    days = [d for k, d in enumerate(days) if k % 3 == 0]   # prereg idx%3
    print("DESIGN days sampled: %d" % len(days), flush=True)
    all_ev = []
    for k, day in enumerate(days):
        b5 = DL.load_m5("EURUSD", day + " 00:00", day + " 23:55")
        m = b5["cet_min"]
        e = ENG.PerceptionEngine(feed="DESIGN")
        e.cand_log = []
        for j in range(len(b5["t"])):
            e.update(int(b5["t"][j]), float(b5["o"][j]),
                     float(b5["h"][j]), float(b5["l"][j]),
                     float(b5["c"][j]), cet_min=int(m[j]))
        all_ev.extend(collect_day(e, m, day))
        if (k + 1) % 50 == 0:
            print("day %d/%d events=%d" % (k + 1, len(days), len(all_ev)),
                  flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in all_ev:
            fh.write(json.dumps(r) + "\n")
    print("wrote %d events" % len(all_ev))
    import collections
    print(collections.Counter(r["kind"] for r in all_ev))


if __name__ == "__main__":
    main()
