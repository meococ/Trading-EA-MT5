"""dr_final.py -- DR-BOX (R64) consolidated hypothesis tests + upper bound.

Null protocol (stated BEFORE measurement):
  * within-panel label shuffle: for each golden, pool = cands born<=j_tau.
    Statistic = mean(feature[match]) - mean(feature[nonmatch]) across
    goldens that have >=1 of each. Null: 200 draws, within each golden
    permute match labels among avail cands, recompute statistic.
    Report obs diff and null p95 (two-sided |.| for direction-free feats,
    signed otherwise).
  * density-aware null for price-position features (round50/asia/dayopen):
    golden's own edges are positional; null draws a random AVAILABLE cand
    in the same panel and computes its anchor stat. 200 draws -> the null
    distribution of "a random live candidate's edge-anchor distance".
    This controls for edge density (a panel full of cands near 1.3250 will
    have low round50 distance by construction).
  * selection recall@1: rule picks ONE cand per golden (strict top; ties
    broken by cand index order, ties counted). Null: random pick within
    panel (200 draws), report null mean and p95.

Pools:
  AVAIL = born <= j_tau (causally born by tau).
  LIVE  = avail AND band touched by some bar within last 12 bars OR
          px inside band (still "alive" at tau). Parameter: live_win=12.

Features (all causal, bars<=j_tau): age_bars (neg => freshest), t0,
prom, leg, height, h_abr=height/abr, span_bars, pairsep, touches_hi+lo,
overlap_ratio, n_swings, compression, px_frac, dist_close_edge_abr,
bars_since_touch (neg), min_round50 (neg), min_asia (neg),
hi/lo_dayopen (neg min), hi/lo_dayext (neg min), route_is_rd.

Composite rules stated a priori (small fixed set):
  C1 youngest born among AVAIL
  C2 youngest born among LIVE
  C3 youngest born among LIVE with px_in_box
  C4 freshest touch (min bars_since_touch) among LIVE
  C5 among LIVE with px_in_box: max overlap_ratio
  C6 among AVAIL: max overlap_ratio
  C7 lexicographic: px_in_box first, then youngest (AVAIL)
  C8 lexicographic: bars_since_touch==0 first, then youngest (AVAIL)
  C9 cluster rule: cluster AVAIL cands (band IoU>=0.5 chaining), choose
     cluster with (contains px_tau, then most recent member birth), then
     youngest member within.
  C10 among LIVE: min |px_frac-0.5| (mid-band), tie youngest.

Post-tau (H-hind) is hypothesis-only, never a feature.
"""
import sys, os, pickle, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
import cache as CA  # noqa: E402

ROWS = pickle.load(open(os.path.join(HERE, "dr_rows.pkl"), "rb"))
rng = np.random.RandomState(20260923)
DRAWS = 200
LIVE_WIN = 12


def is_live(c, r):
    if not c["avail"]:
        return False
    if c.get("px_in_box"):
        return True
    return c.get("bars_since_touch", 999) <= LIVE_WIN


def pool_of(r, live):
    return [c for c in r["pool"] if (is_live(c, r) if live else c["avail"])]


def shuffle_null(rows, featfn, live, draws=DRAWS):
    """obs diff (match - nonmatch) vs within-panel label shuffle."""
    obs = []
    golds = []
    for r in rows:
        p = pool_of(r, live)
        m_ = [featfn(c, r) for c in p if c["match"]]
        n_ = [featfn(c, r) for c in p if not c["match"]]
        if m_ and n_:
            obs.append(np.mean(m_) - np.mean(n_))
            golds.append(r)
    if not obs:
        return None
    obs = float(np.mean(obs))
    null = []
    for _ in range(draws):
        ds = []
        for r in golds:
            p = pool_of(r, live)
            fv = np.array([featfn(c, r) for c in p], float)
            lab = np.array([c["match"] for c in p])
            lab = rng.permutation(lab)
            if lab.sum() and (~lab).sum():
                ds.append(fv[lab].mean() - fv[~lab].mean())
        null.append(np.mean(ds))
    null = np.array(null)
    p95 = np.percentile(null, 95)
    p05 = np.percentile(null, 5)
    return obs, p05, p95, int((null >= obs).sum()), len(golds)


def recall(rule, rows, live):
    """rule(r, pool) -> index or None; returns hits, ties."""
    hits = 0
    ties = 0
    tot = 0
    for r in rows:
        p = pool_of(r, live)
        if not any(c["match"] for c in p):
            continue
        tot += 1
        scores = np.array([rule(c, r) for c in p], float)
        if np.all(np.isnan(scores)):
            continue
        best = np.nanmax(scores)
        top = [i for i, s in enumerate(scores) if s == best]
        if len(top) > 1:
            ties += 1
        pick = top[0]
        if p[pick]["match"]:
            hits += 1
    return hits, ties, tot


def random_recall_null(rows, live, draws=DRAWS):
    vals = []
    for _ in range(draws):
        h = 0
        for r in rows:
            p = pool_of(r, live)
            if not any(c["match"] for c in p):
                continue
            h += p[rng.randint(len(p))]["match"]
        vals.append(h)
    return np.mean(vals), np.percentile(vals, 95)


def band_iou(c1, c2):
    i = min(c1["hi"], c2["hi"]) - max(c1["lo"], c2["lo"])
    u = max(c1["hi"], c2["hi"]) - min(c1["lo"], c2["lo"])
    return i / u if u > 0 else 0.0


def cluster_pick(r, live):
    """C9: chain-cluster by band IoU>=0.5; cluster score = (contains px,
    most recent member born); pick youngest member of best cluster."""
    p = pool_of(r, live)
    if not p:
        return None
    n = len(p)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for i in range(n):
        for j in range(i + 1, n):
            if band_iou(p[i], p[j]) >= 0.5:
                union(i, j)
    clus = collections.defaultdict(list)
    for i in range(n):
        clus[find(i)].append(i)
    best_key, best_mem = None, None
    for mem in clus.values():
        has_px = any(p[i].get("px_in_box") for i in mem)
        freshest = max(p[i]["born"] for i in mem)
        key = (1 if has_px else 0, freshest)
        if best_key is None or key > best_key:
            best_key, best_mem = key, mem
    # within cluster: youngest born
    return min(best_mem, key=lambda i: -p[i]["born"])


print("=" * 78)
print("POOL SIZES")
print("=" * 78)
na = [r["n_avail"] for r in ROWS]
nl = [len(pool_of(r, True)) for r in ROWS]
print("avail/panel: med %d (p25 %d p75 %d) | live: med %d (p25 %d p75 %d)"
      % (np.median(na), *np.percentile(na, [25, 75]),
         np.median(nl), *np.percentile(nl, [25, 75])))
reach_a = [r for r in ROWS if r["n_match"]]
reach_l = [r for r in ROWS
           if any(c["match"] for c in pool_of(r, True))]
print("reachable goldens: avail-pool %d/119 | live-pool %d/119"
      % (len(reach_a), len(reach_l)))

print()
print("=" * 78)
print("H-SHAPE + causal feature tests (match vs nonmatch, AVAIL pool)")
print("=" * 78)
FEATS = [
    ("age_bars (younger>0? diff)", lambda c, r: -c["age_bars"]),
    ("t0 (later>0)", lambda c, r: c["t0"]),
    ("prom", lambda c, r: c["prom"]),
    ("leg", lambda c, r: c["leg"]),
    ("height", lambda c, r: c["height"]),
    ("height/abr", lambda c, r: c["height"] / r["abr_tau"]),
    ("span_bars", lambda c, r: c["span_bars"]),
    ("pairsep", lambda c, r: c["pairsep"]),
    ("touches_hi+lo", lambda c, r: c.get("touches_hi", 0)
     + c.get("touches_lo", 0)),
    ("overlap_ratio", lambda c, r: c.get("overlap_ratio", np.nan)),
    ("n_swings", lambda c, r: c.get("n_swings", np.nan)),
    ("compression", lambda c, r: c.get("compression", np.nan)),
    ("px_frac", lambda c, r: c.get("px_frac", np.nan)),
    ("-dist_close_edge_abr", lambda c, r: -c.get("dist_close_edge_abr",
                                                  np.nan)),
    ("-bars_since_touch", lambda c, r: -c.get("bars_since_touch", 999)),
    ("route=rd", lambda c, r: 1.0 if c["route"] == "rd" else 0.0),
]
for name, fn in FEATS:
    res = shuffle_null(ROWS, lambda c, r, f=fn: (lambda v:
                                                 v if v == v else np.nan)(fn(c, r)), False)
    res2 = shuffle_null(ROWS, lambda c, r, f=fn: (lambda v:
                                                  v if v == v else np.nan)(fn(c, r)), True)
    for tag, rr in (("AVAIL", res), ("LIVE ", res2)):
        if rr is None:
            continue
        obs, p05, p95, nge, ng = rr
        flag = " <==" if (obs > p95 or obs < p05) else ""
        print("  %-26s %s diff=%+8.3f  null[p05,p95]=[%+7.3f,%+7.3f] ng=%d%s"
              % (name, tag, obs, p05, p95, ng, flag))

print()
print("=" * 78)
print("DENSITY-AWARE NULLS (H-round50, H-prior) — AVAIL pool")
print("=" * 78)
# golden edge anchor stat vs random-avail-cand null in same panel
def anchor_stat(edges_lo, edges_hi):
    return min(min(e % 50, 50 - e % 50) for e in (edges_lo, edges_hi))

# realized golden anchor distances
g_r50 = [anchor_stat(r["g_lo"], r["g_hi"]) for r in ROWS]
print("golden min-edge-to-00/50: med %.2f pips | <=1.5p: %d/119"
      % (np.median(g_r50), sum(1 for x in g_r50 if x <= 1.5)))
# null: random avail cand per golden
nul = []
for _ in range(DRAWS):
    d = []
    for r in ROWS:
        p = pool_of(r, False)
        if p:
            c = p[rng.randint(len(p))]
            d.append(min(c["min_round50"], 50 - 0))
    nul.append(np.mean(d))
print("  null mean edge-to-00/50: %.2f (p05 %.2f) | golden mean %.2f"
      % (np.mean(nul), np.percentile(nul, 5), np.mean(g_r50)))
nul_le = []
for _ in range(DRAWS):
    cnt = 0
    for r in ROWS:
        p = pool_of(r, False)
        if p:
            c = p[rng.randint(len(p))]
            cnt += c["min_round50"] <= 1.5
    nul_le.append(cnt)
print("  null P(edge<=1.5p of 00/50): mean %.1f p95 %.1f | golden %d"
      % (np.mean(nul_le), np.percentile(nul_le, 95),
         sum(1 for x in g_r50 if x <= 1.5)))

# match-vs-nonmatch on the anchor feats themselves
for name, fn in [
        ("-min_round50", lambda c, r: -c["min_round50"]),
        ("-min_asia", lambda c, r: -c.get("min_asia", 999)),
        ("-min_dayopen", lambda c, r: -min(c["hi_dayopen"],
                                           c["lo_dayopen"])),
        ("-min_dayext", lambda c, r: -min(c["hi_dayext"],
                                          c["lo_dayext"]))]:
    res = shuffle_null(ROWS, fn, False)
    if res:
        obs, p05, p95, nge, ng = res
        flag = " <==" if (obs > p95 or obs < p05) else ""
        print("  %-18s AVAIL diff=%+8.3f null[%+7.3f,%+7.3f] ng=%d%s"
              % (name, obs, p05, p95, ng, flag))

print()
print("=" * 78)
print("SELECTION recall@1 — stated rules (reachable goldens only)")
print("=" * 78)
for tag, live in (("AVAIL", False), ("LIVE", True)):
    mu, p95 = random_recall_null(ROWS, live)
    print("pool=%s random-pick null: mean %.1f p95 %.1f" % (tag, mu, p95))
rules = [
    ("C1 youngest@AVAIL",
     lambda c, r: -c["age_bars"], False),
    ("C2 youngest@LIVE",
     lambda c, r: -c["age_bars"], True),
    ("C3 youngest@LIVE+pxin",
     lambda c, r: (-c["age_bars"] if c.get("px_in_box") else np.nan),
     True),
    ("C4 freshest-touch@LIVE",
     lambda c, r: -c.get("bars_since_touch", 999), True),
    ("C5 max-overlap@LIVE+pxin",
     lambda c, r: (c.get("overlap_ratio", 0)
                   if c.get("px_in_box") else np.nan), True),
    ("C6 max-overlap@AVAIL",
     lambda c, r: c.get("overlap_ratio", 0), False),
    ("C7 pxin>youngest@AVAIL",
     lambda c, r: (1e6 if c.get("px_in_box") else 0) - c["age_bars"],
     False),
    ("C8 touch0>youngest@AVAIL",
     lambda c, r: (1e6 if c.get("bars_since_touch", 999) == 0 else 0)
     - c["age_bars"], False),
    ("C10 mid-band>youngest@LIVE",
     lambda c, r: -abs(c.get("px_frac", 0.5) - 0.5) * 1e3
     - c["age_bars"] * 1e-3, True),
]
for name, fn, live in rules:
    h, t, tot = recall(fn, ROWS, live)
    print("  %-28s hits %2d/%d  ties %d" % (name, h, tot, t))
# C9 cluster rule
h = 0
t = 0
tot = 0
for r in ROWS:
    p = pool_of(r, False)
    if not any(c["match"] for c in p):
        continue
    tot += 1
    idx = cluster_pick(r, False)
    if idx is not None and p[idx]["match"]:
        h += 1
print("  %-28s hits %2d/%d" % ("C9 cluster(px,fresh)@AVAIL", h, tot))

print()
print("=" * 78)
print("D4 UNION BOUND (AVAIL pool): any single feature strict-top")
print("=" * 78)
UNI = [
    ("neg_age", lambda c, r: -c["age_bars"]),
    ("t0", lambda c, r: c["t0"]),
    ("prom", lambda c, r: c["prom"]),
    ("leg", lambda c, r: c["leg"]),
    ("height", lambda c, r: c["height"]),
    ("h_abr", lambda c, r: c["height"] / r["abr_tau"]),
    ("span_bars", lambda c, r: c["span_bars"]),
    ("pairsep", lambda c, r: c["pairsep"]),
    ("touches", lambda c, r: c.get("touches_hi", 0)
     + c.get("touches_lo", 0)),
    ("overlap", lambda c, r: c.get("overlap_ratio", 0)),
    ("n_swings", lambda c, r: c.get("n_swings", 0)),
    ("compression", lambda c, r: c.get("compression", 0)),
    ("px_frac", lambda c, r: c.get("px_frac", -9)),
    ("neg_dist_edge", lambda c, r: -c.get("dist_close_edge_abr", 999)),
    ("neg_touch", lambda c, r: -c.get("bars_since_touch", 999)),
    ("neg_round50", lambda c, r: -c["min_round50"]),
    ("neg_asia", lambda c, r: -c.get("min_asia", 999)),
    ("neg_dayopen", lambda c, r: -min(c["hi_dayopen"], c["lo_dayopen"])),
    ("neg_dayext", lambda c, r: -min(c["hi_dayext"], c["lo_dayext"])),
]
any_hit = 0
indist = 0
tie_top = 0
for r in ROWS:
    p = pool_of(r, False)
    if not any(c["match"] for c in p):
        continue
    hit = False
    for _n, fn in UNI:
        sc = np.array([fn(c, r) for c in p], float)
        sc = np.nan_to_num(sc, nan=-1e18)
        top = np.where(sc == sc.max())[0]
        if len(top) == 1 and p[top[0]]["match"]:
            hit = True
        if len(top) > 1 and any(p[i]["match"] for i in top):
            tie_top += 1
    if hit:
        any_hit += 1
    else:
        indist += 1
print("goldens where SOME single causal feature strict-tops a match: "
      "%d/%d reachable" % (any_hit, len(reach_a)))
print("goldens indistinguishable under all single features: %d"
      % indist)
print("(feature-golden pairs where a match shares the TOP score, i.e. "
      "tied: %d)" % tie_top)

print()
print("=" * 78)
print("H-HIND quantification (post-tau, hypothesis only)")
print("=" * 78)
for tag, live in (("AVAIL", False), ("LIVE", True)):
    h = 0
    tot = 0
    for r in ROWS:
        p = pool_of(r, live)
        if not any(c["match"] for c in p):
            continue
        tot += 1
        bb = [c.get("brk_bar") if c.get("brk_bar") is not None else 1e9
              for c in p]
        if min(bb) >= 1e9:
            continue
        pick = int(np.argmin(bb))
        h += p[pick]["match"]
    print("  pick fastest-post-tau-break @%s: %d/%d" % (tag, h, tot))
# excursion-weighted
h = 0
tot = 0
for r in ROWS:
    p = pool_of(r, False)
    if not any(c["match"] for c in p):
        continue
    tot += 1
    sc = [c.get("post_exc_abr", 0) for c in p]
    pick = int(np.argmax(sc))
    h += p[pick]["match"]
print("  pick max post-break excursion @AVAIL: %d/%d" % (h, tot))

print()
print("=" * 78)
print("H-SETUP: setup tags vs reachability and youngest-rule success")
print("=" * 78)
import re
SETUP = re.compile(r"\b(dd|fb|sb|bb|rb|irb|arb|pb|pbc|pbp|tff|pr)\b")
def tags_of(r):
    s = set()
    for mk in r["marks"]:
        s.update(SETUP.findall(mk["raw"].lower()))
    cl = (r["clause"] or "").lower()
    if re.search(r"asia", cl):
        s.add("asia_box")
    if re.search(r"straddl|round number|the 1[,.]\d\d\b|on 1[,.]\d\d\b|"
                 r"under the 1[,.]|just above 1[,.]|centred on", cl):
        s.add("round_named")
    if re.search(r"w\b|m\b|ww|mm|shs|bracket", cl):
        s.add("pattern_container")
    if re.search(r"after|base|post-|spike|drop", cl):
        s.add("post_leg_base")
    return s

allt = collections.Counter()
re_t = collections.Counter()
for r in ROWS:
    ts = tags_of(r)
    for t_ in ts:
        allt[t_] += 1
        if r["n_match"]:
            re_t[t_] += 1
print("%-20s %6s %8s %8s" % ("tag", "n", "reach", "rate"))
for t_, n in allt.most_common():
    print("%-20s %6d %8d %8.2f" % (t_, n, re_t[t_], re_t[t_] / n))
# youngest-rule success by tag
print()
print("youngest-born rule hit-rate by tag:")
yt = collections.Counter()
yn = collections.Counter()
for r in ROWS:
    p = pool_of(r, False)
    if not any(c["match"] for c in p):
        continue
    pick = int(np.argmax([-c["age_bars"] for c in p]))
    ok = p[pick]["match"]
    for t_ in tags_of(r):
        yn[t_] += 1
        yt[t_] += ok
for t_, n in yn.most_common():
    print("  %-20s %2d/%d" % (t_, yt[t_], n))
