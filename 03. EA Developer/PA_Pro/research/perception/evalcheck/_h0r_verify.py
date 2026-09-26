"""_h0r_verify.py — EVAL-AUDIT independent verification of H0-R
(practice/baselines/h0r_hybrid.py, R81 s81.5(4), R82 s82.6).

Independent legs:
  1. hit recount from h0r_{a,b}.jsonl (per-family totals + flips);
  2. clutter recount under THREE census conventions:
       (A) their convention  : killed-in-window objects removed;
       (B) published formula on effective die (die = min(nat,rule),
           count iff birth<=w1 and die>w0) — the strict reading of
           'published census clutter';
       (C) natural die only  : rule kills ignored for census
           (objects counted like engine DELETED spans);
  3. first-set check: for sampled killed objects, MY OWN bar-by-bar
     predicate scan must find no rule firing at kill_bar-1 and the
     recorded rules firing at kill_bar (their adapter only verified
     kill_bar/jend, not death-1);
  4. prefix invariance spot-check on truncated bars (5 panels).

Run from PA_Pro cwd:
  python research/perception/evalcheck/_h0r_verify.py [--limit N]
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
BASE = os.path.join(PERC, "practice", "baselines")
for _p in (HERE, PERC, os.path.join(PERC, "deepresearch"), BASE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import trade_tags as TT                         # noqa: E402
import DR_RULES_measure as M                    # noqa: E402
import DR_RULES_baselines as FB                 # noqa: E402
import h0r_hybrid as HR                         # noqa: E402
import h0_hybrid as H0                          # noqa: E402

EMITS = HR.EMITS
ARMS = HR.ARMS


def fam_of(src):
    return "level" if src == "donchian" else "line"


def census_variants(died_src, fam, w0, w1, j1w, mp, cp, ema,
                    abr20, pivots, nfed, rule):
    """Counts under conventions A (theirs), B (eff-die published
    formula), C (natural die).  Pick filter applied identically."""
    out = {"A": 0, "B": 0, "C": 0}
    for x in died_src:
        if x["birth"] > w1:
            continue
        nat = x["nat_die"]
        eff = x["die"]
        inA = (eff is None or eff > w0) and not (
            x["rule_killed"] and x["rule_die_min"] <= w1)
        inB = eff is None or eff > w0
        inC = nat is None or nat > w0
        if not (inA or inB or inC):
            continue
        ok = FB.passes(
            FB.feats(x, fam, j1w, mp, cp, ema, abr20, pivots, nfed),
            fam, rule, {})
        if not ok:
            continue
        out["A"] += inA
        out["B"] += inB
        out["C"] += inC
    return out


def my_first_set(x, fam, jb, jend, mp, hp, lp, cp, abr):
    """Independent bar-by-bar scan: first bar j in [jb, jend] where
    any die rule sets, evaluating the imported predicates directly
    at every bar (no incremental state of my own)."""
    g = HR._geom(x, fam)
    for j in range(jb, jend + 1):
        fired = set()
        st = TT.s_stale_far(fam, g, jb, j, hp, lp, cp, abr)
        if st["stale"]:
            fired.add("stale_far")
        if fam == "line" and \
                TT.s_line_broken(g, jb, j, cp, abr)["lbroken"]:
            fired.add("line_broken")
        if fam == "level" and \
                TT.s_c7(0, j, cp, abr,
                        lambda _j: x["price"])["c7_sw"] > 2:
            fired.add("zombie")
        if fired:
            return int(mp[j]), sorted(fired)
    return None, []


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--kill-check", type=int, default=40)
    args = ap.parse_args()
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]

    # ---------- leg 1: hit recount from artifacts -------------------
    print("=== leg 1: hit recount from jsonl ===")
    for arm in "ab":
        rows = [json.loads(x) for x in open(
            os.path.join(BASE, "h0r_%s.jsonl" % arm),
            encoding="utf8")]
        cnt = collections.Counter()
        tot = collections.Counter()
        fl_c3 = collections.defaultdict(lambda: [0, 0])
        fl_h0 = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            tot[r["fam"]] += 1
            cnt[r["fam"]] += r["hit"]
            k = (r["panel"], r["fam"])
            if r["hit"] and not r["c3_hit"]:
                fl_c3[k][0] += 1
            elif r["c3_hit"] and not r["hit"]:
                fl_c3[k][1] += 1
            if r["hit"] and not r["h0_hit"]:
                fl_h0[k][0] += 1
            elif r["h0_hit"] and not r["hit"]:
                fl_h0[k][1] += 1
        print("arm %s: %s | flips_c3 +%d/-%d | flips_h0 +%d/-%d"
              % (arm, {f: "%d/%d" % (cnt[f], tot[f])
                       for f in sorted(tot)},
                 sum(v[0] for v in fl_c3.values()),
                 sum(v[1] for v in fl_c3.values()),
                 sum(v[0] for v in fl_h0.values()),
                 sum(v[1] for v in fl_h0.values())))
        if arm == "a":
            lvl_lost = sorted(p for (p, f), v in fl_h0.items()
                              if f == "level" and v[1])
            print("  level lost vs H0:", lvl_lost)

    # ---------- legs 2+3: census variants + first-set check ---------
    print("=== legs 2+3: census variants + independent kill check ===")
    emit_cache = {}
    died_cache = {}
    census = {a: {"A": [], "B": [], "C": []} for a in "ab"}
    kill_pool = collections.defaultdict(list)
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        if not g2:
            continue
        if rec["date"] not in emit_cache:
            abr50 = CA.abr(rec["date"])
            t2, m2, o2, h2, l2, c2 = CA.bars(rec["date"])
            emit_cache[rec["date"]] = {
                nm: fn(t2, np.asarray(m2), o2, h2, l2, c2, abr50)
                or [] for nm, fn in EMITS.items()}
        day_raw = emit_cache[rec["date"]]
        dk = (rec["date"], w1)
        if dk not in died_cache:
            e_full = M.pickled(rec["date"], w1)
            died = {}
            if e_full is not None:
                mp = np.array([b["cet_min"] for b in e_full.bars])
                hp = np.array([b["h"] for b in e_full.bars])
                lp = np.array([b["l"] for b in e_full.bars])
                cp = np.array([b["c"] for b in e_full.bars])
                abr = np.asarray(e_full.abr)
                for fam_, (src, _r) in ARMS["c"].items():
                    d, _v = HR.apply_dies(day_raw[src], fam_, mp, hp,
                                          lp, cp, abr)
                    died[src] = d
            died_cache[dk] = died
        day_died = died_cache[dk]
        e_full = M.pickled(rec["date"], w1)
        if e_full is None:
            continue
        erec = V2.eng_objects(
            e_full, np.asarray(CA.bars(rec["date"])[1]), w0, w1)
        eboxes = [r for r in erec if r["type"] != "LABEL_TF"]
        emarks = [r for r in erec if r["type"] == "LABEL_TF"]
        n_c3 = len(eboxes) + len(emarks)
        mp = np.array([b["cet_min"] for b in e_full.bars])
        cp = np.array([b["c"] for b in e_full.bars])
        ema = np.asarray(e_full.ema)
        abr20 = np.asarray(e_full.abr)
        pivots = e_full.book.seq
        nfed = len(e_full.bars) - 1
        j1w = min(M.jle(mp, w1), nfed)
        c3_fam_n = collections.Counter(
            EV.FAMILY.get(r["type"]) for r in eboxes)
        for arm, subs in ARMS.items():
            if arm == "c":
                continue
            n_a = n_b = n_c = n_c3
            for fam, (src, rule) in subs.items():
                n_a -= c3_fam_n[fam]
                n_b -= c3_fam_n[fam]
                n_c -= c3_fam_n[fam]
                cv = census_variants(day_died.get(src, []), fam, w0,
                                     w1, j1w, mp, cp, ema, abr20,
                                     pivots, nfed, rule)
                n_a += cv["A"]
                n_b += cv["B"]
                n_c += cv["C"]
            ng = len(g2)
            census[arm]["A"].append(n_a / ng)
            census[arm]["B"].append(n_b / ng)
            census[arm]["C"].append(n_c / ng)
        for fam_, (src, _r) in ARMS["c"].items():
            for x in day_died.get(src, []):
                if x["rule_killed"] and x["birth"] <= w1 and \
                        w0 < x["rule_die_min"] <= w1:
                    kill_pool[(src, rec["date"], w1)].append(x)
    for arm in "ab":
        c = census[arm]
        print("arm %s census med: A=%.4f B=%.4f C=%.4f (n=%d)"
              % (arm, float(np.median(c["A"])),
                 float(np.median(c["B"])),
                 float(np.median(c["C"])), len(c["A"])))

    # ---------- leg 3: independent first-set on a sample ------------
    import random
    rng = random.Random(20260923)
    keys = sorted(kill_pool)
    samp = rng.sample(keys, min(args.kill_check, len(keys)))
    bad = []
    n_checked = 0
    for key in samp:
        src, date, w1 = key
        xs = kill_pool[key]
        x = rng.choice(xs)
        e_full = M.pickled(date, w1)
        mp = np.array([b["cet_min"] for b in e_full.bars])
        hp = np.array([b["h"] for b in e_full.bars])
        lp = np.array([b["l"] for b in e_full.bars])
        cp = np.array([b["c"] for b in e_full.bars])
        abr = np.asarray(e_full.abr)
        fam_ = fam_of(src)
        jb = TT.jle(mp, x["birth"])
        if jb is None:
            jb = 0
        kj_bar = int(np.searchsorted(mp, x["rule_die_min"]))
        mine_min, mine_rules = my_first_set(
            x, fam_, jb, kj_bar, mp, hp, lp, cp, abr)
        n_checked += 1
        # first-set: nothing fires strictly before kill bar, and the
        # recorded kill bar must itself fire with recorded rules
        if mine_min is not None and mine_min < x["rule_die_min"]:
            bad.append((key, "earlier-set@%d<%d"
                        % (mine_min, x["rule_die_min"])))
        elif mine_min != x["rule_die_min"] or \
                mine_rules != x["killers"]:
            bad.append((key, "killbar mismatch mine=%s/%s rec=%s/%s"
                        % (mine_min, mine_rules, x["rule_die_min"],
                           x["killers"])))
    print("first-set check: %d objects, %d mismatches %s"
          % (n_checked, len(bad), bad[:8]))

    # ---------- leg 4: prefix invariance spot (5 panels) ------------
    print("=== leg 4: prefix invariance spot-check ===")
    import random as _r
    rr = _r.Random(78)
    pref_recs = rr.sample(recs, 5)
    for src, fn in EMITS.items():
        fam_ = fam_of(src)
        for rec in pref_recs:
            w1 = rec["window"]["x1"] or 1439
            t, m, o, h, l, c = CA.bars(rec["date"])
            m = np.asarray(m)
            taus = sorted({min(HR.tau_of(g), w1)
                           for g in EV.gold_objects(rec)[0]
                           if V2.scorable(g, rec["window"]["x0"], w1)
                           and HR.tau_of(g) is not None
                           and rec["window"]["x0"] <= HR.tau_of(g)})
            if not taus:
                continue
            tau = taus[0]
            jt = int(np.searchsorted(m, tau, side="right"))
            abr50 = CA.abr(rec["date"])
            full = fn(t, m, o, h, l, c, abr50) or []
            cut = fn(t[:jt], m[:jt], o[:jt], h[:jt], l[:jt],
                     c[:jt], abr50[:jt]) or []
            e = M.pickled(rec["date"], tau)
            if e is None:
                continue
            mp = np.array([b["cet_min"] for b in e.bars])
            hp = np.array([b["h"] for b in e.bars])
            lp = np.array([b["l"] for b in e.bars])
            cp = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            d_full, _ = HR.apply_dies(full, fam_, mp, hp, lp, cp, abr)
            d_cut, _ = HR.apply_dies(cut, fam_, mp, hp, lp, cp, abr)

            def key(x):
                return (x["type"], x["birth"], x["birth_drawn"],
                        repr(x.get("lo")), repr(x.get("hi")),
                        repr(x.get("price")), repr(x.get("p0")),
                        repr(x.get("slope")),
                        repr(x.get("rule_die_min")))
            lf = {key(x) for x in d_full
                  if x["birth"] <= tau and
                  (x["die"] is None or x["die"] > tau)}
            lc = {key(x) for x in d_cut
                  if x["birth"] <= tau and
                  (x["die"] is None or x["die"] > tau)}
            print("  %s %s tau=%d full=%d cut=%d match=%s"
                  % (src, rec["id"], tau, len(lf), len(lc),
                     lf == lc))


if __name__ == "__main__":
    main()
