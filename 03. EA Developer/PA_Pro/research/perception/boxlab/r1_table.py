"""r1_table.py -- R56 s.56.4 R1.1: author-vs-engine table, all box goldens.

Per scorable BOX golden at its official tau (tau_of -> build_end):
  panel, gi, golden edges/times, engine box@1 pick (edges, score, route,
  age), best edge-matching candidate (route, score + every score term,
  resolution), funnel bucket.

Buckets: hit | below_min_score | outranked | rate_limited | expired |
log_only | no_coverage | pending.

Reads c1r_p_base pickles only -- never runs the engine.
Usage: CM_HASH=<h> CM_VAR=<v> python -B boxlab/r1_table.py > table.csv
"""
import sys, os, pickle, collections, csv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "evalcheck"))
sys.path.insert(0, os.path.join(HERE, ".."))

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import cache as CA                         # noqa: E402
import recall_at_k as RK                   # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
import importlib.util                      # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "cm", os.path.join(HERE, "c1_missed.py"))
cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cm)

HASH = os.environ.get("CM_HASH", "ee2cbf1202db47b6")
VAR = os.environ.get("CM_VAR", "c1r_p_base")
CACHE = os.path.join(HERE, "..", "evalcheck", "_cache")
PIP = C.PIP
DEATHS = ("close", "superseded", "outranked", "pierced", "traversed")
BORN = ("born", "revived")


def _pk(rec, bar):
    f = os.path.join(CACHE, "run_%s_%s_%s_%s.pkl"
                     % (VAR, HASH, rec["date"], bar))
    return pickle.load(open(f, "rb")) if os.path.exists(f) else None


def main():
    w = csv.writer(sys.stdout)
    w.writerow(["panel", "gi", "tau", "g_lo", "g_hi", "g_t0",
                "bucket",
                "pick_lo", "pick_hi", "pick_sc", "pick_route",
                "pick_birth", "pick_match",
                "cand_route", "cand_sc", "cand_prom", "cand_contain",
                "cand_touch", "cand_barr", "cand_deep", "cand_res"])
    n = collections.Counter()
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        if _pk(rec, w1) is None:
            continue
        t, m, o, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for gi, g in enumerate(g2):
            if EV.FAMILY.get(g["spec_type"]) != "box":
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            e_t = _pk(rec, tau)
            if e_t is None:
                continue
            live, _em = live_records(e_t, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e_t))
            fam = [r for r in ranked
                   if EV.FAMILY.get(r["type"]) == "box"]
            hit = any(V2.match(g, er, m) for er in fam[:1])
            tol = V2.tol_px(g)
            glo, ghi = g["price_lo"] / PIP, g["price_hi"] / PIP

            # engine pick = fam[0]
            pk_lo = pk_hi = pk_sc = pk_birth = ""
            pk_route = ""
            pk_match = ""
            if fam:
                top = fam[0]
                ob = next((o for o in e_t.objects
                           if o.id == top["id"]), None)
                if ob is not None:
                    geo = getattr(ob, "geometry", {}) or {}
                    pk_lo = geo.get("bottom", "")
                    pk_hi = geo.get("top", "")
                    pk_sc = "%.2f" % (top.get("score") or 0)
                    pk_route = getattr(ob, "why", "") or ""
                    pk_birth = top.get("t_birth") or ""
                    pk_match = "MATCH" if (
                        isinstance(pk_lo, float)
                        and abs(pk_hi - ghi) <= tol
                        and abs(pk_lo - glo) <= tol) else "wrong"
                    if isinstance(pk_birth, int):
                        pk_birth = "%d(age%d)" % (pk_birth, tau - pk_birth)

            # candidates matching golden edges
            mc = [cd for cd in (e_t.cand_log or [])
                  if cd.get("kind") == "BOX"
                  and (cd.get("cet_min") or 0) <= tau
                  and cm.edge_match(cd, g, tol)
                  and cm.span_overlap(cd, g, m, w0, tau)]
            cands = collections.defaultdict(list)
            for cd in mc:
                cands[cm.ckey(cd)].append(cd)
            res = {}
            for k, rr in cands.items():
                rr.sort(key=lambda cd: cd.get("cet_min") or 0)
                fin = next((cd for cd in reversed(rr)
                            if cd.get("outcome") != "proposed"), None)
                res[k] = (fin["outcome"], fin.get("score"), fin) \
                    if fin else ("pending", None, rr[-1])
            pooled = {k: v for k, v in res.items()
                      if v[0] != "pending" or
                      any(cd.get("score") is not None
                          for cd in cands[k])}
            # best pooled cand by score (or any if hit)
            best = None
            for k, (oc, sc, fin) in pooled.items():
                if best is None or (sc or -999) > (best[1] or -999):
                    best = (k, sc, oc, fin)
            if hit:
                bucket = "hit"
            elif not mc:
                bucket = "no_coverage"
            elif not pooled:
                bucket = "log_only"
            else:
                oc = collections.Counter(v[0] for v in pooled.values())
                bucket = oc.most_common(1)[0][0]
            n[bucket] += 1
            crow = ["", "", "", "", "", "", ""]
            if best is not None:
                k, sc, oc, fin = best
                crow = [k[0],
                        "%.2f" % sc if sc is not None else "",
                        fin.get("prom_abr"), fin.get("contain"),
                        fin.get("touches"), fin.get("barrier"),
                        fin.get("deeper_lv"), oc]
            w.writerow([rec["id"], gi, tau,
                        "%.1f" % glo, "%.1f" % ghi,
                        g.get("t0"), bucket,
                        pk_lo if pk_lo == "" else "%.1f" % pk_lo,
                        pk_hi if pk_hi == "" else "%.1f" % pk_hi,
                        pk_sc, pk_route, pk_birth, pk_match] + crow)
    print("buckets:", dict(n), file=sys.stderr)


if __name__ == "__main__":
    main()
