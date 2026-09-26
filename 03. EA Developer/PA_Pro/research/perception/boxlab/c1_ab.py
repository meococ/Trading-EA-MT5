"""c1_ab.py — C-round 1 same-hash A/B harness for the box.* flags.

Arm = current engine code + deepcopied params with box.* flags set
(arm_ab.py pattern, R24 §24.3).  Cache keyed by (variant, code hash,
date, w1) — arms never share pickles (R14 §14.2).

Per arm it reports (queue item §34.8.2.1):
  - engine BOX oracle (cand_right on the proposal stream, per
    scoreboard.measure);
  - box@1 / level@1 / line@2 at the author's budget (recall_at_k
    semantics: object score -> born cand_log score -> recency);
  - box@1 under box_rank (hypothetical lab-ranker ranking — the
    build lane wires it if kept; reported separately, labelled);
  - born recall + births/panel per family (matched counts, not just
    fractions);
  - clutter median (live objects at tau) + clutter ratio median;
  - per-family goldens matched (hit_g counts).

Usage:
  python c1_ab.py base leg wick dense dedup watch tail watchtail score
  python c1_ab.py --all        # every arm in ARMS order
  python c1_ab.py --check X    # identity: X-off objects vs 'base' arm
"""
import collections
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
EVAL = os.path.join(PERC, "evalcheck")
sys.path.insert(0, EVAL)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "..", "lib"))

import numpy as np                         # noqa: E402

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import cache as CA                         # noqa: E402
import funnel as F                         # noqa: E402
import engine as ENG                       # noqa: E402
import pa_slots                            # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
from scoreboard import panel_cands         # noqa: E402

OUT = os.path.join(HERE, "c1_runs")
os.makedirs(OUT, exist_ok=True)

FAM_K = {"box": 1, "line": 2, "level": 1, "bracket": 1}


def _p(p0, **overrides):
    # p0 = params snapshot frozen once per process (R35 §35.4: the
    # params file moves under the build lane; re-reading it per panel
    # would make one arm run two param regimes).  Every engine in this
    # invocation gets a deepcopy of the same snapshot -> true same-hash.
    p = copy.deepcopy(p0)
    for path, v in overrides.items():
        node = p
        ks = path.split(".")
        for k in ks[:-1]:
            node = node[k]
        node[ks[-1]] = v
    return p


def mk(overrides, p0):
    """Module-level-safe factory -> plain PerceptionEngine (pickles as
    engine.PerceptionEngine, loadable by any process)."""
    def factory():
        return ENG.PerceptionEngine(params=_p(p0, **copy.deepcopy(
            overrides)))
    return factory


ARMS = collections.OrderedDict([
    ("base",      {}),
    # --- generation (oracle) levers, ordered by lab gain/ink ---
    ("leg",       {"box.leg_edges": True}),
    ("wick",      {"box.wick_edges": True}),
    ("dense",     {"box.dense_anchors": True}),
    # --- selection / lifecycle levers ---
    ("dedup",     {"box.dedup_iou": True}),
    ("watch",     {"box.watch_birth": True}),
    ("tail",      {"box.tail_bars": 12}),
    ("watchtail", {"box.watch_birth": True, "box.tail_bars": 12}),
    ("score",     {"box.rank_score": True}),
    ("all",       {"box.leg_edges": True, "box.wick_edges": True,
                   "box.dense_anchors": True, "box.dedup_iou": True,
                   "box.watch_birth": True, "box.tail_bars": 12,
                   "box.rank_score": True}),
    # R27 dependency probe: does the pay only show under famledger?
    # fam_budget = build lane's per-family NMS/live budget (famlive_box=1
    # is the author's own budget); fam_ledger = per-family birth rate.
    ("watch_fl",  {"box.watch_birth": True, "salience.fam_ledger": True,
                   "salience.fam_budget": True}),
    # --- follow-up probes after first sweep ---
    ("wd",        {"box.wick_edges": True, "box.dedup_iou": True}),
    ("tail6",     {"box.tail_bars": 6}),
    ("gen",       {"box.leg_edges": True, "box.wick_edges": True,
                   "box.dense_anchors": True, "box.dedup_iou": True}),
    ("wdtail",    {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.tail_bars": 12}),
    # the rate-window unlock (R38 anatomy: 26/42 right props die
    # rate_limited on ttl 24 << window 72).  Existing salience flag —
    # measured here, owned by the build lane.
    ("wd_ext",    {"box.wick_edges": True, "box.dedup_iou": True,
                   "salience.rate_blocked_extend": True}),
    ("wd_ext_fl", {"box.wick_edges": True, "box.dedup_iou": True,
                   "salience.rate_blocked_extend": True,
                   "salience.fam_ledger": True,
                   "salience.fam_budget": True}),
    # R38 §38.3.2 born-side wick arm + §38.3.3 kde edge source.
    ("wd_wb",     {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.wick_birth": True}),
    ("wd_kde",    {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.kde_edges": True}),
    ("wd_wb_kde", {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.wick_birth": True, "box.kde_edges": True}),
    # deferred birth vs the rate gate: under watch the early weak box
    # never spends the window; the matured right band emits at break.
    ("wd_watch",  {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.watch_birth": True}),
    # box-side TTL: survive one full rate window so a rate-blocked
    # right cand is still alive when the slot frees.
    ("wd_wait",   {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.wait_ttl": True}),
    ("wd_wb_wait", {"box.wick_edges": True, "box.dedup_iou": True,
                    "box.wick_birth": True, "box.wait_ttl": True}),
    ("wdw_wait",  {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.watch_birth": True, "box.wait_ttl": True}),
    ("wd_wb_fl",  {"box.wick_edges": True, "box.dedup_iou": True,
                   "box.wick_birth": True,
                   "salience.fam_ledger": True,
                   "salience.fam_budget": True}),
    # --- R42 probes on the KEPT parent (bxcombo + famcaps + K4
    # supersede all default ON; flags below toggle only the probe).
    # p_dense: the wrong-t0 class retest — dense_anchors re-anchors a
    # qualified band's edges at in-run pivot t0s; it lost pre-supersede
    # (same-band flooding), the slot-recycle may now absorb it.
    ("p_base",    {}),
    ("p_dense",   {"box.dense_anchors": True}),
    # p_wait: under supersede a surviving blocked cand gets repeated
    # supersede attempts as the holder's act score decays.
    ("p_wait",    {"box.wait_ttl": True}),
    # p_wb: born-side wick retest — wick cands can now supersede too.
    ("p_wb",      {"box.wick_birth": True}),
    ("p_dense_wait", {"box.dense_anchors": True, "box.wait_ttl": True}),
    # p_lev: old-level edge source — when no clustered band qualifies,
    # retry with pivot levels formed BEFORE the proposal window (the
    # author's edges are ~7h-old structure; clustering can't emit them).
    ("p_lev",     {"box.level_edges": True}),
    ("p_lev_wait", {"box.level_edges": True, "box.wait_ttl": True}),
    # p_cong (R44 §44.3): pivot-free bar-driven congestion trigger —
    # envelope run >= cong_min_bars under cong_h_abr*ABR, edges = run
    # extremes; p_cong_lev adds the old-level snap (box.level_edges).
    ("p_cong",     {"box.cong_trigger": True}),
    ("p_cong_lev", {"box.cong_trigger": True, "box.level_edges": True}),
    # sensitivity grid — is the +2 fragile to N/k?
    ("p_cong_k3",  {"box.cong_trigger": True, "box.cong_h_abr": 3.0}),
    ("p_cong_k55", {"box.cong_trigger": True, "box.cong_h_abr": 5.5}),
    ("p_cong_n8",  {"box.cong_trigger": True, "box.cong_min_bars": 8}),
    # p_dens (R46 §46.3.2): wick-tip KDE edges on the cong band —
    # outermost density peaks (merge < cong_dens_space_abr*ABR),
    # quantile fallback; edges replace run extremes under fix_edges.
    ("p_dens",     {"box.cong_trigger": True, "box.cong_density": True}),
    ("p_dens_q",   {"box.cong_trigger": True, "box.cong_density": True,
                    "box.cong_dens_mode": "q"}),
    # p_sub (R46): densest legal-height sub-band inside an over-cap
    # envelope — targets the blocked:too_tall class (11/38).
    ("p_sub",      {"box.cong_trigger": True, "box.cong_subband": True}),
    # p_pedg (R49 §49.3.2): pivot-cluster-seeded edges inside K6-
    # qualifying cong runs — null test kept pivots (79% vs p95 31.6%).
    ("p_pedg",     {"box.cong_trigger": True, "box.cong_pivedge": True}),
    ("p_pedg3",    {"box.cong_trigger": True, "box.cong_pivedge": True,
                    "box.cong_piv_topk": 3}),
    ("p_pedgm2",   {"box.cong_trigger": True, "box.cong_pivedge": True,
                    "box.cong_piv_minmem": 2}),
    ("p_pedgi7",   {"box.cong_trigger": True, "box.cong_pivedge": True,
                    "box.cong_piv_mininside": 0.7}),
    ("p_pedgs4",   {"box.cong_trigger": True, "box.cong_pivedge": True,
                    "box.cong_piv_minsup": 4}),
    ("p_pedgr2",   {"box.cong_trigger": True, "box.cong_pivedge": True,
                    "box.cong_piv_minrun": 2, "box.cong_piv_npairs": 6}),
    ("p_pedgn3",   {"box.cong_trigger": True, "box.cong_pivedge": True,
                    "box.cong_piv_npairs": 3}),
    # p_wick (R50 §50.4 anatomy follow-up): 11/46 covered-but-missed
    # goldens were matched ONLY by the log-only cluster_range_wick
    # stream. wick_birth pools those variants for real.
    ("p_wick",     {"box.wick_birth": True}),
    # p_deep0 (PLAYBOOK_C2 X3): the -1.5*deeper_lv term is the dominant
    # deficit on the below_min_score bucket (starved deeper med 4 vs
    # born med 1).  Stated value BEFORE the A/B: 0.0 — the only value
    # with reach over the 5.0 floor (0.75 clears zero of the starved
    # cands); the nesting penalty is misapplied to congestion bands
    # that are nested by construction.
    ("p_deep0",    {"box.deeper_w": 0.0}),
])


def fam_of(st):
    return EV.FAMILY.get(st)


def measure_arm(eng_hash, cls, variant, recs):
    """One arm over all panels -> metrics dict (mirrors
    scoreboard.measure + recall_at_k per-family, variant-aware)."""
    gold_n = collections.Counter()
    hit_g = collections.Counter()
    eng_n = collections.Counter()
    hit_e = collections.Counter()
    orc_g = collections.Counter()
    orc_h = collections.Counter()
    born_kind = collections.Counter()
    clutter = []
    ratio = []
    # recall@k at family budget (engine ranking) + box_rank ranking
    fk_g = collections.Counter()
    fk_h = collections.Counter()
    fkr_h = collections.Counter()          # ranked by box_rank
    n_live_tau = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec, variant=variant)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        pairs, _mp = C.match_panel(g2, eboxes, [], [], m,
                                   V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        he = {ei for _, ei in pairs}
        for gi, g in enumerate(g2):
            st = g["spec_type"]
            gold_n[st] += 1
            hit_g[st] += gi in hg
        for ei, er in enumerate(eboxes):
            eng_n[er["type"]] += 1
            hit_e[er["type"]] += ei in he
        nb = 0
        for cd in e.cand_log or []:
            if cd.get("outcome") == "born":
                born_kind[cd["kind"]] += 1
                nb += cd["kind"] == "BOX"
        # funnel oracle: right proposal in cand_log or born match
        cands = panel_cands(e, m, w0, w1)
        for gi, g in enumerate(g2):
            st = g["spec_type"]
            if st != "BOX":
                continue
            orc_g[st] += 1
            same = [r for r in cands
                    if EV.FAMILY.get(r["type"]) == "box"]
            orc_h[st] += (gi in hg) or any(
                F.cand_right(g, r, m) for r in same)
        if g2:
            ratio.append(len(eboxes) / len(g2))
        # ---- per-tau family recall@k ----
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t, variant=variant)
            live, _em = live_records(e_t, m, w0, tau)
            osc = {o.id: getattr(o, "score", None) for o in e_t.objects}
            brk_ = {o.id: o.geometry.get("meta_box_rank")
                    for o in e_t.objects}
            smap = {}
            for cd in e_t.cand_log or []:
                if cd.get("outcome") != "born" or \
                        cd.get("kind") == "LABEL_TF":
                    continue
                key = (cd["kind"], cd.get("cet_min"))
                smap[key] = max(smap.get(key, 0.0),
                                cd.get("score") or 0.0)
            for r in live:
                r["score"] = osc.get(r["id"])
                r["box_rank"] = brk_.get(r["id"])
            n_live_tau.append(len(live))
            clutter.append(len(live))

            def _key(r):
                s = r.get("score")
                if s is None:
                    s = smap.get((r["type"], r.get("t_birth")))
                if s is not None:
                    return (0, -s, -(r.get("t_birth") or 0))
                return (1, -(r.get("t_birth") or 0), 0)

            def _key_rank(r):
                s = r.get("box_rank")
                if s is not None:
                    return (0, -s, -(r.get("t_birth") or 0))
                return _key(r)

            ranked = sorted(live, key=_key)
            ranked_r = sorted(live, key=_key_rank)
            fam_live = collections.defaultdict(list)
            fam_live_r = collections.defaultdict(list)
            for r in ranked:
                f = EV.FAMILY.get(r["type"])
                if f:
                    fam_live[f].append(r)
            for r in ranked_r:
                f = EV.FAMILY.get(r["type"])
                if f:
                    fam_live_r[f].append(r)
            for g in gs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                k = FAM_K.get(fg)
                if k is None:
                    continue
                fk_g[fg] += 1
                if any(V2.match(g, er, m)
                       for er in fam_live.get(fg, [])[:k]):
                    fk_h[fg] += 1
                if any(V2.match(g, er, m)
                       for er in fam_live_r.get(fg, [])[:k]):
                    fkr_h[fg] += 1
    npan = len(recs)
    return {
        "gold_n": dict(gold_n), "hit_g": dict(hit_g),
        "eng_n": dict(eng_n), "hit_e": dict(hit_e),
        "born": dict(born_kind),
        "born_box_per_panel": born_kind.get("BOX", 0) / npan,
        "oracle_box": orc_h["BOX"] / orc_g["BOX"] if orc_g["BOX"] else
        None,
        "oracle_box_n": [orc_h["BOX"], orc_g["BOX"]],
        "clutter": float(np.median(clutter)) if clutter else None,
        "clutter_ratio": float(np.median(ratio)) if ratio else None,
        "live_at_tau_med": float(np.median(n_live_tau))
        if n_live_tau else None,
        "fam_at_budget": {f: [fk_h[f], fk_g[f]]
                          for f in sorted(fk_g)},
        "fam_at_budget_rankscore": {f: [fkr_h[f], fk_g[f]]
                                    for f in sorted(fk_g)},
    }


def identity_report(h_new, var_new, h_old, var_old, recs):
    """flag-OFF arm objects vs parent-hash objects (canonical compare,
    identity_check.py semantics on objects AND cand_log)."""
    import pickle
    import glob
    diff = miss = 0
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        fa = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl" % (
            var_new + "_" if var_new else "", h_new, rec["date"], w1))
        if not os.path.exists(fa):
            g = glob.glob(os.path.join(
                CA.CACHE, "run_%s%s*_%s_%s.pkl" % (
                    var_new + "_" if var_new else "", h_new[:8],
                    rec["date"], w1)))
            fa = g[0] if g else None
        fb = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl" % (
            var_old + "_" if var_old else "", h_old, rec["date"], w1))
        if not os.path.exists(fb):
            g = glob.glob(os.path.join(
                CA.CACHE, "run_%s%s*_%s_%s.pkl" % (
                    var_old + "_" if var_old else "", h_old[:8],
                    rec["date"], w1)))
            fb = g[0] if g else None
        if not fa or not fb:
            miss += 1
            continue
        try:
            ea = pickle.load(open(fa, "rb"))
            eb = pickle.load(open(fb, "rb"))
        except Exception:
            miss += 1
            continue
        if CA.canonical(ea) != CA.canonical(eb):
            diff += 1
    return {"panels": len(recs), "missing": miss, "diff": diff}


DROP_KEYS = {"box_rank", "deeper_lv", "meta_box_rank"}


def canon_strip(e, drop):
    """CA.canonical() minus the output-only rank fields — the score
    arm's behavioural-identity proof: everything else must equal."""
    import pickle as _p
    def cs(x):
        if isinstance(x, dict):
            return {k: cs(v) for k, v in sorted(
                x.items(), key=lambda kv: str(kv[0]))
                if k not in drop}
        if isinstance(x, (list, tuple)):
            return [cs(v) for v in x]
        if isinstance(x, np.generic):
            return x.item()
        if isinstance(x, np.ndarray):
            return x.tolist()
        return x
    objs = []
    for o in e.objects:
        objs.append((o.type, o.why, o.t_birth, o.t_left, o.t_right,
                     o.state, o.id, cs(o.geometry), cs(o.events)))
    return _p.dumps((objs, cs(e.cand_log), list(e.bars)), protocol=4)


def identity_strip(h_a, var_a, h_b, var_b, recs):
    """var_a objects/cand_log vs var_b, ignoring DROP_KEYS."""
    import pickle
    import glob

    def find(var, h8, date, w1):
        f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                         % (var, h8, date, w1))
        if os.path.exists(f):
            return f
        g = glob.glob(os.path.join(
            CA.CACHE, "run_%s_%s*_%s_%s.pkl" % (var, h8, date, w1)))
        return g[0] if g else None

    diff = miss = 0
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        fa = find(var_a, h_a, rec["date"], w1)
        fb = find(var_b, h_b, rec["date"], w1)
        if not (fa and fb):
            miss += 1
            continue
        ea = pickle.load(open(fa, "rb"))
        eb = pickle.load(open(fb, "rb"))
        if canon_strip(ea, DROP_KEYS) != canon_strip(eb, DROP_KEYS):
            diff += 1
    return {"panels": len(recs), "missing": miss, "diff": diff}


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return
    recs = C.load_tune()
    if "--check2" in args:
        # score-arm behavioural identity: strip the new output fields,
        # everything else must be byte-equal (same hash, same params).
        i = args.index("--check2")
        hspec = args[i + 1]
        h_a, _, h_b = hspec.partition(":")
        out = identity_strip(h_a, "c1r_score", h_b or h_a, "c1r_base",
                             recs)
        print("score vs base (fields stripped):", out, flush=True)
        return
    p0 = ENG.load_params()          # frozen params for the whole sweep
    h = F.code_hash(F.V1_FILES)
    json.dump(p0, open(os.path.join(
        OUT, "params_frozen_%s.json" % h[:8]), "w"), indent=1,
        default=str)
    print("engine hash %s (params frozen at process start)" % h,
          flush=True)
    names = list(ARMS) if "--all" in args else [a for a in args
                                              if a in ARMS]
    for name in names:
        over = ARMS[name]
        var = "c1r_" + name   # c1r_: fresh variants, no reuse of
                              # pickles that may carry drifted params
        r = measure_arm(h, mk(over, p0), var, recs)
        r["arm"] = name
        r["overrides"] = over
        r["hash"] = h
        outp = os.path.join(OUT, "%s_%s.json" % (var, h[:8]))
        json.dump(r, open(outp, "w"), indent=1, default=str)
        fb = r["fam_at_budget"].get("box", [0, 0])
        fbr = r["fam_at_budget_rankscore"].get("box", [0, 0])
        fl = r["fam_at_budget"].get("level", [0, 0])
        fln = r["fam_at_budget"].get("line", [0, 0])
        print("%-10s orc=%s box@1=%d/%d boxRank@1=%d/%d lvl@1=%d/%d "
              "line@2=%d/%d born/pan=%.2f clut=%s cr=%s live@tau=%s"
              % (name,
                 "%.3f" % r["oracle_box"] if r["oracle_box"] else "-",
                 fb[0], fb[1], fbr[0], fbr[1], fl[0], fl[1],
                 fln[0], fln[1],
                 r["born_box_per_panel"],
                 "%.1f" % r["clutter"] if r["clutter"] else "-",
                 "%.2f" % r["clutter_ratio"]
                 if r["clutter_ratio"] else "-",
                 "%.1f" % r["live_at_tau_med"]
                 if r["live_at_tau_med"] is not None else "-"),
              flush=True)
        h2 = F.code_hash(F.V1_FILES)
        if h2 != h:
            # disk drift only — this process's code was fixed at import
            # and params are frozen in p0, so every arm still runs the
            # same behaviour.  Keep the t0 label: it names the frozen
            # state the pickles actually contain.
            print("!!! disk hash moved (label stays %s): -> %s"
                  % (h[:8], h2[:8]))


if __name__ == "__main__":
    with pa_slots.slot("boxlab-c1ab", timeout=7200):
        main()
