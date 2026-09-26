"""h0r_hybrid.py — R81 s81.5(4) + R82 s82.6: H0-R, hybrid generators
with TT-2 lifetime tags as DIE RULES.

Same pipeline/scoring/parent as h0_hybrid (imported, not forked).
Arms:
  H0R-a = H0-a (donchian|C1@1.0 levels @1) + die rules on the levels
  H0R-b = H0-b (tdlines k2|C7@2 lines @2)  + die rules on the lines
  H0R-c = both, only reported if a and b both pass the keep rule.

Die rules (substituted family's objects only; C-3 families untouched):
  stale_far   (all):  dist(close_t, object) > 3*ABR20 AND last touch
                      (bar range within tol) > 24 bars before t;
  line_broken (line): >=2 consecutive closes beyond the line on its
                      non-defended side by > tol since birth;
  zombie      (level): TT zombie predicate = C7f@2, full-history close
                      side-switches > 2.
Object dies at the FIRST bar t where any rule sets (bars <= t), and
never returns.  Predicates imported from research/perception/
trade_tags.py (single source); the thin adapter below turns the
baseline object's dict shape into the geometry dict the predicates
expect, computes the first-set bar incrementally, and VERIFIES every
kill/survival decision against the imported functions themselves.

Census convention (published cumulative, S2-analogue): an emitted
object killed by a die rule before its natural end and inside the
window is "not drawn, not counted" — subtracted from the window
census.  Naturally-retired objects (generator's own break rule) stay
counted, like the engine's own DELETED objects.

Usage (PA_Pro cwd):
  python research/perception/practice/baselines/h0r_hybrid.py [--limit N]
Outputs: practice/baselines/h0r_{a,b,c}.jsonl + h0r_summary.json
"""
import collections
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PRACTICE = os.path.dirname(HERE)
PERC = os.path.dirname(PRACTICE)
for _p in (os.path.join(PERC, "evalcheck"), PERC,
           os.path.join(PERC, "deepresearch"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402
import trade_tags as TT                         # noqa: E402
import DR_RULES_measure as M                    # noqa: E402
import DR_RULES_baselines as FB                 # noqa: E402
from bl_common import _rec                      # noqa: E402
import h0_hybrid as H0                          # noqa: E402

FAM_BUDGET = H0.FAM_BUDGET
ARMS = {"a": {"level": ("donchian", "C1@1.0")},
        "b": {"line": ("tdlines", "C7@2")},
        "c": {"level": ("donchian", "C1@1.0"),
              "line": ("tdlines", "C7@2")}}
EMITS = H0.EMITS
SEED = 78


# ------------------------------------------------------------------ #
# thin adapter: baseline-object dict -> TT predicate geometry + first-
# set bar.  Every returned kill is verified against the imported
# predicates at the death bar (and all-clear at death-1 / nfed).
# ------------------------------------------------------------------ #

def _geom(x, fam):
    if fam == "level":
        return {"price": x["price"], "side": x["side"]}
    return {"p0": x["p0"], "slope": x["slope"], "t0": x["t0_bar"],
            "side": x["side"]}


def rule_die_bar(x, fam, jb, jend, mp, hp, lp, cp, abr):
    """First bar j in [jb, jend] where a die rule sets -> (bar, rules)
    or (None, []).  Incremental state tracked bar-by-bar; the imported
    TT predicates verify the outcome before returning."""
    g = _geom(x, fam)
    # incremental trackers
    sw = 0                # zombie: c7 side-switch count over [0..j]
    sw_state = 0
    run = 0               # line_broken: consecutive beyond-side closes
    last_touch = None     # stale_far: last j where bar range covered obj
    kill_j = None
    kill_rules = set()
    for j in range(0, jend + 1):
        # ---- per-bar values ----
        if fam == "level":
            val = x["price"]
            dist = abs(cp[j] - val)
        else:
            val = x["p0"] + x["slope"] * (j - x["t0_bar"])
            dist = abs(cp[j] - val)
        tol = TT.tol_e(abr[j])
        touched = lp[j] <= val + tol and hp[j] >= val - tol
        if touched:
            last_touch = j
        # zombie (level): full-history close side-switches
        if fam == "level":
            d = cp[j] - val
            s = 1 if d > tol else (-1 if d < -tol else 0)
            if s and sw_state and s != sw_state:
                sw += 1
            if s:
                sw_state = s
        # line_broken: consecutive closes on non-defended side
        if fam == "line":
            side = x.get("side")
            if side == "top":
                thru = cp[j] > val + tol
            elif side == "bottom":
                thru = cp[j] < val - tol
            else:
                thru = abs(cp[j] - val) > tol
            if j >= jb:
                run = run + 1 if thru else 0
        # ---- death check only at/after birth ----
        if j < jb:
            continue
        fired = set()
        if dist > TT.STALE_FAR_ABR * abr[j]:
            gap = (j - last_touch) if last_touch is not None \
                else (j - jb)
            if gap > TT.STALE_GAP_BARS:
                fired.add("stale_far")
        if fam == "line" and run >= TT.LINE_BREAK_N:
            fired.add("line_broken")
        if fam == "level" and sw > 2:
            fired.add("zombie")
        if fired:
            kill_j, kill_rules = j, fired
            break
    # ---- verify against the imported predicates ----
    ver = {"checked": 0, "bad": []}
    if kill_j is not None:
        ver["checked"] += 1
        st_far = TT.s_stale_far(fam, g, jb, kill_j, hp, lp, cp, abr)
        ok_s = ("stale_far" in kill_rules) == bool(st_far["stale"])
        ok_b = ok_z = True
        if fam == "line":
            ok_b = (("line_broken" in kill_rules) ==
                    TT.s_line_broken(g, jb, kill_j, cp, abr)["lbroken"])
        if fam == "level":
            ok_z = (("zombie" in kill_rules) ==
                    (TT.s_c7(0, kill_j, cp, abr,
                             lambda _j: x["price"])["c7_sw"] > 2))
        if not (ok_s and ok_b and ok_z):
            ver["bad"].append(("kill@%d" % kill_j))
    else:
        ver["checked"] += 1
        st_far = TT.s_stale_far(fam, g, jb, jend, hp, lp, cp, abr)
        ok = not st_far["stale"]
        if fam == "line":
            ok = ok and not TT.s_line_broken(
                g, jb, jend, cp, abr)["lbroken"]
        if fam == "level":
            ok = ok and not (TT.s_c7(0, jend, cp, abr,
                                     lambda _j: x["price"]
                                     )["c7_sw"] > 2)
        if not ok:
            ver["bad"].append(("survive@%d" % jend))
    return kill_j, sorted(kill_rules), ver


def apply_dies(objs, fam, mp, hp, lp, cp, abr):
    """Attach rule_die (bar), rule_die_min, eff_die and killers to a
    copy of each object.  die (natural) kept for census distinction."""
    out = []
    ver = {"checked": 0, "bad": []}
    for x in objs:
        jb = TT.jle(mp, x["birth"])
        jend = len(mp) - 1
        if jb is None:
            jb = 0
        kj, rules, v = rule_die_bar(x, fam, jb, jend, mp, hp, lp,
                                    cp, abr)
        ver["checked"] += v["checked"]
        ver["bad"] += v["bad"]
        y = dict(x)
        y["nat_die"] = x.get("die")
        y["rule_die_min"] = int(mp[kj]) if kj is not None else None
        y["killers"] = rules
        dies = [d for d in (x.get("die"), y["rule_die_min"])
                if d is not None]
        y["die"] = min(dies) if dies else None      # effective die
        y["rule_killed"] = (kj is not None and
                            (x.get("die") is None or
                             y["rule_die_min"] < x["die"]))
        out.append(y)
    return out, ver


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]

    emit_cache = {}          # date -> {src: (raw_objs, died_objs)}
    ver_tot = {"checked": 0, "bad": []}
    hits = {a: collections.defaultdict(dict) for a in "abc"}
    h0_hits = {a: collections.defaultdict(dict) for a in "abc"}
    c3_hits = collections.defaultdict(dict)
    gold_fam_of = {}
    census = {a: [] for a in "abc"}
    census["c3"] = []
    census["h0"] = {a: [] for a in "abc"}
    kill_ct = collections.defaultdict(collections.Counter)
    kill_ct_win = collections.defaultdict(collections.Counter)
    hit_kill = collections.defaultdict(collections.Counter)
    n_ev = n_miss = 0

    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        m = np.asarray(m)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        for gi, g in enumerate(g2):
            gold_fam_of[(rec["id"], gi)] = EV.FAMILY.get(
                g["spec_type"])
        by_tau = H0.events_for(rec, g2, gmarks, w0, w1)

        # ---------- emit + dies once per date (engine arrays @w1) ---
        if rec["date"] not in emit_cache:
            abr50 = CA.abr(rec["date"])
            t2, m2, o2, h2, l2, c2 = CA.bars(rec["date"])
            m2 = np.asarray(m2)
            emit_cache[rec["date"]] = {
                nm: fn(t2, m2, o2, h2, l2, c2, abr50) or []
                for nm, fn in EMITS.items()}
        day_raw = emit_cache[rec["date"]]
        died_cache_key = (rec["date"], w1)
        if "_died" not in emit_cache:
            emit_cache["_died"] = {}
        if died_cache_key not in emit_cache["_died"]:
            e_full = M.pickled(rec["date"], w1)
            died = {}
            if e_full is not None:
                mp = np.array([b["cet_min"] for b in e_full.bars])
                hp = np.array([b["h"] for b in e_full.bars])
                lp = np.array([b["l"] for b in e_full.bars])
                cp = np.array([b["c"] for b in e_full.bars])
                abr = np.asarray(e_full.abr)
                for fam, (src, _rule) in ARMS["c"].items():
                    d, v = apply_dies(day_raw[src], fam, mp, hp, lp,
                                      cp, abr)
                    ver_tot["checked"] += v["checked"]
                    ver_tot["bad"] += v["bad"]
                    died[src] = d
            emit_cache["_died"][died_cache_key] = died
        day_died = emit_cache["_died"][died_cache_key]

        # ---------- census at w1 ------------------------------------
        e_full = M.pickled(rec["date"], w1)
        if e_full is not None:
            erec = V2.eng_objects(e_full, m, w0, w1)
            eboxes = [r for r in erec if r["type"] != "LABEL_TF"]
            emarks = [r for r in erec if r["type"] == "LABEL_TF"]
            n_c3 = len(eboxes) + len(emarks)
            if g2:
                census["c3"].append(n_c3 / len(g2))
            mp = np.array([b["cet_min"] for b in e_full.bars])
            cp = np.array([b["c"] for b in e_full.bars])
            ema = np.asarray(e_full.ema)
            abr20 = np.asarray(e_full.abr)
            pivots = e_full.book.seq
            nfed = len(e_full.bars) - 1
            j1w = min(M.jle(mp, w1), nfed)
            c3_fam_n = collections.Counter()
            for r in eboxes:
                c3_fam_n[EV.FAMILY.get(r["type"])] += 1
            for arm, subs in ARMS.items():
                n_arm = n_c3
                n_arm_h0 = n_c3
                for fam, (src, rule) in subs.items():
                    n_arm -= c3_fam_n[fam]
                    n_arm_h0 -= c3_fam_n[fam]
                    # H0 census: emitted vis0 filtered at w1 (as H0)
                    vis = [x for x in day_raw[src]
                           if x["birth"] <= w1 and
                           (x["die"] is None or x["die"] > w0)]
                    nfv = sum(1 for x in vis
                              if FB.passes(
                                  FB.feats(x, fam, j1w, mp, cp, ema,
                                           abr20, pivots, nfed),
                                  fam, rule, {}))
                    n_arm_h0 += nfv
                    # H0-R census: survivors only
                    died_src = day_died.get(src, [])
                    # apply the pick filter too? NO — the census
                    # counts emitted objects, the rule filter gates
                    # picks; but Part F's filtered census DID apply
                    # the pick filter at w1.  Keep the same: killed
                    # objects removed first, then the rule filter.
                    surv = [x for x in died_src
                            if x["birth"] <= w1 and
                            (x["die"] is None or x["die"] > w0) and
                            not (x["rule_killed"] and
                                 x["rule_die_min"] <= w1)]
                    nfv_r = sum(1 for x in surv
                                if FB.passes(
                                    FB.feats(x, fam, j1w, mp, cp,
                                             ema, abr20, pivots,
                                             nfed), fam, rule, {}))
                    n_arm += nfv_r
                if g2:
                    census[arm].append(n_arm / len(g2))
                    census["h0"][arm].append(n_arm_h0 / len(g2))
            # per-rule kill counts (per panel: kills inside [w0,w1])
            for fam, (src, _r) in ARMS["c"].items():
                for x in day_died.get(src, []):
                    if not x["rule_killed"]:
                        continue
                    for k in x["killers"]:
                        kill_ct[src][k] += 1
                        if x["birth"] <= w1 and \
                                w0 < x["rule_die_min"] <= w1:
                            kill_ct_win[src][k] += 1

        # ---------- canonical tau events -----------------------------
        e_cache = {}
        for tau, ggs in sorted(by_tau.items()):
            if tau not in e_cache:
                e_cache[tau] = M.pickled(rec["date"], tau)
            e = e_cache[tau]
            if e is None:
                n_miss += 1
                continue
            n_ev += 1
            mp = np.array([b["cet_min"] for b in e.bars])
            cp = np.array([b["c"] for b in e.bars])
            ema = np.asarray(e.ema)
            abr20 = np.asarray(e.abr)
            pivots = e.book.seq
            nfed = len(e.bars) - 1
            live, _em = live_records(e, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                fam_ranked[EV.FAMILY.get(r["type"])].append(r)
            c3_picks = {f: fam_ranked[f][:k]
                        for f, k in FAM_BUDGET.items()}
            for gi, g in ggs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                c3_hits[(rec["id"], gi)] = any(
                    V2.match(g, r, mp) for r in c3_picks.get(fg, []))
            for arm, subs in ARMS.items():
                picks = {f: list(v) for f, v in c3_picks.items()}
                picks_h0 = {f: list(v) for f, v in c3_picks.items()}
                for fam, (src, rule) in subs.items():
                    # H0-R picks: died objects
                    kp, _fts, _a = H0.baseline_picks(
                        day_died.get(src, []), fam, rule, w0, tau,
                        mp, cp, ema, abr20, pivots, nfed)
                    picks[fam] = kp[:FAM_BUDGET[fam]]
                    # H0 picks: raw objects (comparison row)
                    kp0, _f0, _a0 = H0.baseline_picks(
                        day_raw[src], fam, rule, w0, tau,
                        mp, cp, ema, abr20, pivots, nfed)
                    picks_h0[fam] = kp0[:FAM_BUDGET[fam]]
                for gi, g in ggs:
                    fg = EV.FAMILY.get(g["spec_type"])
                    if not fg:
                        continue
                    hit = any(V2.match(g, r, mp)
                              for r in picks.get(fg, []))
                    hits[arm][(rec["id"], gi)] = hit
                    hit0 = any(V2.match(g, r, mp)
                               for r in picks_h0.get(fg, []))
                    h0_hits[arm][(rec["id"], gi)] = hit0
                    if hit0 and not hit and fg in subs:
                        # attribute: which killed object would have
                        # matched this golden at tau?
                        jl = min(M.jle(mp, tau), nfed)
                        for x in day_died.get(subs[fg][0], []):
                            if not x["rule_killed"] or \
                                    x["birth"] > tau or \
                                    x["rule_die_min"] > tau:
                                continue
                            # rec as H0 saw it: natural die, not the
                            # rule-clipped eff die (else the rec ends
                            # before the golden and cannot match)
                            r_x = _rec({**x, "die": x["nat_die"]},
                                       w0, tau, int(mp[jl]))
                            if V2.match(g, r_x, mp):
                                for k in x["killers"]:
                                    hit_kill[(arm, fg)][k] += 1
                                break

    # ---------------- aggregate -------------------------------------
    def fam_counts(hitmap):
        out = collections.Counter()
        tot = collections.Counter()
        for (pid, gi), ok in hitmap.items():
            fam = gold_fam_of[(pid, gi)]
            if fam:
                tot[fam] += 1
                out[fam] += bool(ok)
        return out, tot

    def med(v):
        vv = [x for x in v if not np.isnan(x)]
        return float(np.median(vv)) if vv else None

    summ = {"events": n_ev, "pkl_miss": n_miss,
            "adapter_verify": ver_tot, "arms": {}, "m1": {}}
    c3h, tot = fam_counts(c3_hits)
    summ["c3"] = {"hits": dict(c3h), "gold": dict(tot),
                  "clutter": med(census["c3"])}
    h0c = {}
    for arm in ARMS:
        h0h, _ = fam_counts(h0_hits[arm])
        ah, _ = fam_counts(hits[arm])
        h0c[arm] = {"hits": dict(h0h),
                    "clutter": med(census["h0"][arm])}
        fl_c3 = collections.defaultdict(lambda: [0, 0])
        fl_h0 = collections.defaultdict(lambda: [0, 0])
        for key, ok in hits[arm].items():
            fam = gold_fam_of[key]
            if ok and not c3_hits.get(key, False):
                fl_c3[(key[0], fam)][0] += 1
            elif c3_hits.get(key, False) and not ok:
                fl_c3[(key[0], fam)][1] += 1
            w0h = h0_hits[arm].get(key, False)
            if ok and not w0h:
                fl_h0[(key[0], fam)][0] += 1
            elif w0h and not ok:
                fl_h0[(key[0], fam)][1] += 1
        summ["arms"][arm] = {
            "hits": dict(ah), "gold": dict(tot),
            "clutter": med(census[arm]),
            "flips_c3": {"%s|%s" % k: v
                         for k, v in sorted(fl_c3.items())},
            "flips_h0": {"%s|%s" % k: v
                         for k, v in sorted(fl_h0.items())}}
    summ["h0"] = h0c
    summ["kill_counts"] = {k: dict(v) for k, v in kill_ct.items()}
    summ["kill_counts_win"] = {k: dict(v)
                               for k, v in kill_ct_win.items()}
    summ["hit_kills"] = {"%s|%s" % k: dict(v)
                         for k, v in hit_kill.items()}

    # ---------------- prefix invariance with die rules ---------------
    rng = random.Random(SEED)
    pool = []
    for r in recs:
        g2r = [g for g in EV.gold_objects(r)[0]
               if V2.scorable(g, r["window"]["x0"],
                              r["window"]["x1"] or 1439)]
        if any(tau_of(g) is not None and
               r["window"]["x0"] <= tau_of(g) <
               (r["window"]["x1"] or 1439) for g in g2r):
            pool.append(r)
    sample = rng.sample(pool, min(20, len(pool)))
    pref = {}
    for src, fn in EMITS.items():
        fam = "level" if src == "donchian" else "line"
        ok_ct = tot_ct = 0
        mism = []
        for rec in sample:
            w1 = rec["window"]["x1"] or 1439
            t, m, o, h, l, c = CA.bars(rec["date"])
            taus = sorted({min(tau_of(g), w1)
                           for g in EV.gold_objects(rec)[0]
                           if V2.scorable(g, rec["window"]["x0"], w1)
                           and tau_of(g) is not None
                           and rec["window"]["x0"] <= tau_of(g)})
            if not taus:
                continue
            tau = taus[0]
            jt = int(np.searchsorted(m, tau, side="right"))
            abr50 = CA.abr(rec["date"])
            full = fn(t, m, o, h, l, c, abr50) or []
            cut = fn(t[:jt], m[:jt], o[:jt], h[:jt], l[:jt],
                     c[:jt], abr50[:jt]) or []
            # engine arrays truncated at tau (pickle at tau)
            e = M.pickled(rec["date"], tau)
            if e is None:
                continue
            mp = np.array([b["cet_min"] for b in e.bars])
            hp = np.array([b["h"] for b in e.bars])
            lp = np.array([b["l"] for b in e.bars])
            cp = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            d_full, _v1 = apply_dies(full, fam, mp, hp, lp, cp, abr)
            d_cut, _v2 = apply_dies(cut, fam, mp, hp, lp, cp, abr)

            def key(x):
                return (x["type"], x["birth"], x["birth_drawn"],
                        repr(x.get("lo")), repr(x.get("hi")),
                        repr(x.get("price")), repr(x.get("p0")),
                        repr(x.get("slope")))
            lf = {key(x) for x in d_full if x["birth"] <= tau and
                  (x["die"] is None or x["die"] > tau)}
            lc = {key(x) for x in d_cut if x["birth"] <= tau and
                  (x["die"] is None or x["die"] > tau)}
            tot_ct += 1
            if lf == lc:
                ok_ct += 1
            else:
                mism.append(rec["id"])
        pref[src] = {"ok": ok_ct, "n": tot_ct, "mismatch": mism}
    summ["prefix"] = pref

    # ---------------- write outputs ----------------------------------
    for arm in ARMS:
        fp = os.path.join(HERE, "h0r_%s.jsonl" % arm)
        with open(fp, "w", encoding="utf8") as fh:
            for (pid, gi), ok in sorted(hits[arm].items()):
                fh.write(json.dumps({
                    "panel": pid, "gi": gi,
                    "fam": gold_fam_of[(pid, gi)],
                    "hit": bool(ok),
                    "h0_hit": bool(h0_hits[arm].get((pid, gi),
                                                  False)),
                    "c3_hit": bool(c3_hits.get((pid, gi), False))})
                    + "\n")
    with open(os.path.join(HERE, "h0r_summary.json"), "w",
              encoding="utf8") as fh:
        json.dump(summ, fh, indent=1, default=float)

    # ---------------- print ------------------------------------------
    print("events=%d pkl_miss=%d adapter %d checks %d bad"
          % (n_ev, n_miss, ver_tot["checked"], len(ver_tot["bad"])))
    print("C-3: %s cl %.2f"
          % ({f: "%d/%d" % (c3h[f], tot[f]) for f in tot},
             summ["c3"]["clutter"]))
    for arm in ARMS:
        a = summ["arms"][arm]
        h0a = h0c[arm]
        print("H0R-%s: %s cl %.2f | H0 was %s cl %.2f"
              % (arm,
                 {f: "%d/%d" % (a["hits"].get(f, 0), a["gold"][f])
                  for f in a["gold"]}, a["clutter"],
                 {f: "%d" % h0a["hits"].get(f, 0) for f in a["gold"]},
                 h0a["clutter"]))
    print("kill_counts:", summ["kill_counts"])
    print("kill_in_window:", summ["kill_counts_win"])
    for src in EMITS:
        p = pref[src]
        print("prefix %-9s %d/%d ok %s"
              % (src, p["ok"], p["n"], p["mismatch"] or ""))


if __name__ == "__main__":
    main()
