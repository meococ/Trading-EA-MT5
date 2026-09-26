"""R83 s.83.4 arm Y measure (build lane).

Variants (fixed): Y1 = box_yield=1 (box_broken kills the box, incl.
UIP incumbents); Y2 = box_yield=2 (box_broken OR stale_far).
Engine runs are fresh (flag ON); parent numbers come from
DR_RULES_events.jsonl parent picks and boxlab/e3_diag.jsonl.

Measures per variant:
  M1 row   - golden-object hits per family at decision taus (fam
             budgets box1/line2/level1/bracket1, V2.match on ranked
             live records; the same enumeration as DR_RULES_S2).
  census   - published method: eng_objects on the w1-full run,
             per-panel n_eng/n_gold, median.
  flips    - per parent-hit event: Y pick ids / hit vs parent.
  E3       - e3_diag.diagnose imported on the Y engine: four-way
             table + parent BUDGET_CUT misses that become hits.
  prefix   - 20 panels: object state at tau from a stop-at-tau run
             == the filtered view of the run to w1_end.

Output: boxlab/y_measure_<arm>.jsonl + printed summary.
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "boxlab"))
sys.path.insert(0, os.path.join(HERE, "deepresearch"))

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import engine as ENG                   # noqa: E402
import e3_diag as E3                   # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
from recall_at_k import rank_live, score_map  # noqa: E402
from kernel import FAMILY              # noqa: E402

P = json.load(open(os.path.join(HERE, "params_v1_1.json"),
                   encoding="utf8"))["params"]
FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
DR = os.path.join(HERE, "deepresearch")


def factory(flag):
    return lambda: ENG.PerceptionEngine(dict(P, box_yield=flag))


def ranked_at(e, m_day, w0, tau):
    live, _em = live_records(e, m_day, w0, tau)
    osc = {o.id: getattr(o, "score", None) for o in e.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    return rank_live(live, score_map(e))


def picks_of(ranked, ggs, m_day):
    """fam -> [(rec, matched-against-fam-goldens)]."""
    out = {}
    for f, k in FAM_BUDGET.items():
        gf = [g for g in ggs if g["fam_g"] == f]
        top = [r for r in ranked if FAMILY.get(r["type"]) == f][:k]
        out[f] = [(r, gf and any(V2.match(g, r, m_day) for g in gf))
                  for r in top]
    return out


def state_at(ob, j_tau):
    """Causal view of one object at bar j_tau (for prefix check)."""
    if ob.t_birth is None or ob.t_birth > j_tau:
        return None
    evs = tuple((b, cd, d) for (b, cd, d) in ob.events
                if b <= j_tau)
    tr = ob.t_right if (ob.t_right is not None
                        and ob.t_right <= j_tau) else None
    st = "CLOSED" if tr is not None else "ACTIVE"
    return (ob.type, ob.t_birth, ob.t_left, tr, st, evs)


def geom_eq(a, b):
    if set(a) != set(b):
        return False
    for k in a:
        x, y = a[k], b[k]
        if isinstance(x, float) or isinstance(y, float):
            if abs((x or 0.0) - (y or 0.0)) > 1e-9:
                return False
        elif x != y:
            return False
    return True


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    recs = list(C.load_tune())
    rec_by_id = {r["id"]: r for r in recs}
    events = [json.loads(x) for x in open(
        os.path.join(DR, "DR_RULES_events.jsonl"), encoding="utf8")]
    obj_events = [e for e in events if e["is_tau_event"]]
    evs_by_key = collections.defaultdict(list)
    claim_w0 = {}                                # (date,w1) -> w0
    for ev in obj_events:
        evs_by_key[(ev["date"], ev["tau"])].append(ev)
        claim_w0.setdefault((ev["date"], ev["tau"]),
                            rec_by_id[ev["panel"]]["window"]["x0"])

    # E3 golden-box decisions (e3_diag enumeration, un-named rows)
    e3_jobs = collections.defaultdict(list)
    parent_cls = {}
    for row in (json.loads(x) for x in open(
            os.path.join(HERE, "boxlab", "e3_diag.jsonl"),
            encoding="utf8")):
        if not row.get("named"):
            parent_cls[(row["panel"], row["tau"])] = row["cls"]
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        claim_w0.setdefault((rec["date"], w1), w0)
        gobjs, _u, _to = EV.gold_objects(rec)
        for g in gobjs:
            if g["spec_type"] not in V2.BOX_TYPES or \
                    not V2.scorable(g, w0, w1):
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            if (g.get("t1") or w1) < tau - 15:
                continue
            e3_jobs[(rec["date"], tau)].append((rec, g, tau))
            claim_w0.setdefault((rec["date"], tau), w0)

    need = collections.defaultdict(set)
    for (d, w1), w0 in claim_w0.items():
        need[d].add(w1)
    lim = int(os.environ.get("Y_LIMIT", "0"))   # smoke: first N dates
    if lim:
        need = collections.defaultdict(
            set, sorted(need.items())[:lim])
    n_runs = sum(len(v) for v in need.values())
    print("engine runs needed per variant:", n_runs, flush=True)

    for arm, flag in (("y1", 1), ("y2", 2)):
        if which not in ("both", arm):
            continue
        print("\n########## ARM %s (box_yield=%d) ##########"
              % (arm, flag), flush=True)
        eng = factory(flag)
        ghit = collections.Counter()
        gtot = collections.Counter()
        flip_rows = []
        census = {}
        e3_rows = []
        g2_by_panel = {}
        done = 0
        for date in sorted(need):
            t, m_day, _o, _h, _l, _c = CA.bars(date)
            for w1 in sorted(need[date]):
                w0 = claim_w0[(date, w1)]
                e = EV.run_engine(eng, m_day, t, _o, _h, _l, _c, w1,
                                  w0=w0)
                done += 1
                if done % 100 == 0:
                    print("  %s runs %d/%d" % (arm, done, n_runs),
                          flush=True)
                # ---- M1 events at (date,w1) ----
                for ev in evs_by_key.get((date, w1), ()):
                    rec_ = rec_by_id[ev["panel"]]
                    w0_ = rec_["window"]["x0"]
                    w1_ = rec_["window"]["x1"] or 1439
                    if rec_["id"] not in g2_by_panel:
                        gobjs, _u, _to = EV.gold_objects(rec_)
                        g2_by_panel[rec_["id"]] = [
                            g for g in gobjs
                            if V2.scorable(g, w0_, w1_)]
                    ggs = [dict(g, fam_g=EV.FAMILY.get(g["spec_type"]))
                           for g in g2_by_panel[rec_["id"]]
                           if tau_of(g) is not None
                           and tau_of(g) >= w0_
                           and min(tau_of(g), w1_) == ev["tau"]]
                    ranked = ranked_at(e, m_day, w0_, ev["tau"])
                    picks = picks_of(ranked, ggs, m_day)
                    # golden-object hits (M1 row definition)
                    for f in FAM_BUDGET:
                        for g in (x for x in ggs if x["fam_g"] == f):
                            gtot[f] += 1
                            if any(V2.match(g, r, m_day)
                                   for r, _m in picks[f]):
                                ghit[f] += 1
                    # flips vs parent picks
                    y_by_fam = {f: [(r["id"], bool(m))
                                    for r, m in prs]
                                for f, prs in picks.items()}
                    fam_hit = {f: any(m for _r, m in prs)
                               for f, prs in picks.items()}
                    for pr in ev["picks"]:
                        yp = y_by_fam[pr["fam"]]
                        if pr["matched"] != fam_hit[pr["fam"]] or \
                                pr["id"] not in [i for i, _ in yp]:
                            flip_rows.append({
                                "panel": ev["panel"],
                                "tau": ev["tau"], "fam": pr["fam"],
                                "parent_pick": pr["id"],
                                "parent_hit": pr["matched"],
                                "y_picks": yp,
                                "y_hit": fam_hit[pr["fam"]]})
                # ---- census (w1 == a rec window end) ----
                rec_ = next((r for r in recs if r["date"] == date
                             and (r["window"]["x1"] or 1439) == w1),
                            None)
                if rec_ is not None:
                    w0_ = rec_["window"]["x0"]
                    if rec_["id"] not in g2_by_panel:
                        gobjs, _u, _to = EV.gold_objects(rec_)
                        g2_by_panel[rec_["id"]] = [
                            g for g in gobjs
                            if V2.scorable(g, w0_, w1)]
                    eobjs = V2.eng_objects(e, m_day, w0_, w1)
                    census[rec_["id"]] = {
                        "n_eng": sum(1 for r in eobjs),
                        "n_gold": len(g2_by_panel[rec_["id"]])}
                # ---- E3 re-diagnosis ----
                for (rec_, g, tau) in e3_jobs.get((date, w1), ()):
                    _t, m, o, h, l, c = CA.bars(date)
                    abr = CA.abr(date)
                    row = E3.diagnose(e, g, m, c, E3.ema25(c), abr,
                                      rec_["window"]["x0"],
                                      rec_["window"]["x1"] or 1439,
                                      tau)
                    row["panel"] = rec_["id"]
                    row["tau"] = int(tau)
                    row["parent_cls"] = parent_cls.get(
                        (rec_["id"], int(tau)))
                    e3_rows.append(row)

        print("\n== %s M1 row (golden hits) ==" % arm)
        for f in ("box", "level", "line", "bracket"):
            print("  %-8s %d/%d" % (f, ghit[f], gtot[f]))
        ratios = [v["n_eng"] / v["n_gold"]
                  for v in census.values() if v["n_gold"]]
        print("  census clutter median %.2f (panels %d)"
              % (float(np.median(ratios)), len(ratios)))
        print("\n== %s flips vs parent ==" % arm)
        for fr in flip_rows:
            print("  %s@%d %-7s par %s hit=%s -> y %s hit=%s"
                  % (fr["panel"], fr["tau"], fr["fam"],
                     fr["parent_pick"], fr["parent_hit"],
                     fr["y_picks"], fr["y_hit"]))
        print("\n== %s E3 re-diagnosis ==" % arm)
        print("  classes:", dict(collections.Counter(
            r["cls"] for r in e3_rows)))
        bc = [r for r in e3_rows if r["parent_cls"] == "BUDGET_CUT"]
        bc_hit = [r for r in bc if r["cls"] == "HIT"]
        print("  parent BUDGET_CUT %d -> HIT under %s: %d"
              % (len(bc), arm, len(bc_hit)))
        for r in bc_hit[:14]:
            print("    %s@%s" % (r["panel"], r["tau"]))
        out = os.path.join(HERE, "boxlab",
                           "y_measure_%s.jsonl" % arm)
        with open(out, "w", encoding="utf8") as fh:
            for r in e3_rows:
                fh.write(json.dumps(r, default=str) + "\n")
            for fr in flip_rows:
                fh.write(json.dumps({"flip": fr}) + "\n")
        print("  wrote", out)

        # ---- prefix invariance: 20 panels -------------------------
        # project definition (_idchk_tt): canonical() at bar k inside
        # the full run == canonical() of the stop-at-k engine.
        print("\n== %s prefix invariance (20 panels) ==" % arm)
        n_ok = n_tot = 0
        p_recs = recs[:lim or 20]
        for rec_ in p_recs:
            w0_ = rec_["window"]["x0"]
            w1_ = rec_["window"]["x1"] or 1439
            t, m_day, _o, _h, _l, _c = CA.bars(rec_["date"])
            taus = sorted({ev["tau"] for (d, tau), evs_ in
                           evs_by_key.items() if d == rec_["date"]
                           for ev in evs_
                           if ev["panel"] == rec_["id"]})
            if not taus:
                continue
            j_of_tau = {tau: int(np.where(m_day <= tau)[0][-1])
                        for tau in taus}
            snap_at = {j_of_tau[tau]: tau for tau in taus}
            idx = np.where(m_day <= w1_)[0]
            # full run, snapshotting canonical() at each decision tau
            e2 = ENG.PerceptionEngine(dict(P, box_yield=flag))
            e2.w0_min = w0_
            e2.cand_log = []
            snap = {}
            for j in idx:
                e2.update(int(t[j]), float(_o[j]) * 1e-4,
                          float(_h[j]) * 1e-4, float(_l[j]) * 1e-4,
                          float(_c[j]) * 1e-4, cet_min=int(m_day[j]))
                if j in snap_at:
                    snap[snap_at[j]] = CA.canonical(e2)
            for tau in taus:
                e_s = EV.run_engine(eng, m_day, t, _o, _h, _l, _c,
                                    tau, w0=w0_)
                n_tot += 1
                ok = CA.canonical(e_s) == snap[tau]
                n_ok += bool(ok)
                if not ok:
                    print("  PREFIX DIFF %s@%d" % (rec_["id"], tau))
        print("  prefix invariance: %d/%d" % (n_ok, n_tot))


if __name__ == "__main__":
    main()
