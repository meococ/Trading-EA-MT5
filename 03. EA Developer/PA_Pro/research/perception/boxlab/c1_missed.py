"""c1_missed.py -- R50 s.50.4 covered-but-missed anatomy at 9acaa206.

For every scorable BOX golden whose edges were matched by an engine
proposal ("covered") but which was NOT hit at tau under the official
recall_at_k ranking ("missed"), classify:

  1) covered only by LOG-ONLY variant proposals (cluster_range_wick /
     cluster_range_kde 'proposed' rows -- wick_birth OFF, never pooled)
     -> generation-level: the right geometry was computed but never
        entered the salience pool.
  2) covered by a POOLED cand, never born -> last resolution <= tau
     (below_min_score / rate_limited / outranked / nms_suppressed /
      expired / fam_capped / joint_capped) -- "pending" if the cand
      was still unresolved at tau.
  3) born -> alive at tau? if dead, the death event; if alive, rank
     and what outranked it (why, score, age).

A candidate's rows share (route, top, bottom, t0, t1); resolutions
carry the score, log-only 'proposed' rows carry score=None.

Read-only: loads m1_v1 pickles at the STABLE hash, never runs the engine.
"""
import sys, os, pickle, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "evalcheck"))
sys.path.insert(0, os.path.join(HERE, ".."))

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import cache as CA                         # noqa: E402
import recall_at_k as RK                   # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402

HASH = os.environ.get("CM_HASH", "9acaa206c8d386dc")
VAR = os.environ.get("CM_VAR", "m1_v1")
CACHE = os.path.join(HERE, "..", "evalcheck", "_cache")
PIP = C.PIP
DEATHS = ("close", "superseded", "outranked", "pierced", "traversed")
BORN = ("born", "revived")


def _pk(rec, w1):
    f = os.path.join(CACHE, "run_%s_%s_%s_%s.pkl"
                     % (VAR, HASH, rec["date"], w1))
    if not os.path.exists(f):
        return None
    try:
        return pickle.load(open(f, "rb"))
    except Exception:
        return None


def ckey(cd):
    return (cd.get("route"), round(cd.get("top") or 0, 1),
            round(cd.get("bottom") or 0, 1),
            cd.get("t0"), cd.get("t1"))


def edge_match(cd, g, tol):
    glo, ghi = g["price_lo"] / PIP, g["price_hi"] / PIP
    return (cd.get("top") is not None and cd.get("bottom") is not None
            and abs(cd["top"] - ghi) <= tol
            and abs(cd["bottom"] - glo) <= tol)


def link_obj(cd, e_t):
    """Born cand -> engine object: same edges (0.5 pip), birth ~= cet_min."""
    for ob in e_t.objects:
        if getattr(ob, "type", getattr(ob, "kind", None)) != "BOX":
            continue
        lo = getattr(ob, "lo", getattr(ob, "bottom", None))
        hi = getattr(ob, "hi", getattr(ob, "top", None))
        tb = getattr(ob, "t_birth", None)
        if lo is None or hi is None or tb is None:
            continue
        if (abs(hi - cd["top"]) <= 0.5 * PIP
                and abs(lo - cd["bottom"]) <= 0.5 * PIP
                and abs(tb - (cd.get("cet_min") or tb)) <= 15):
            return ob
    return None


def main():
    rows = []
    n_missed = n_cov_pooled = n_cov_log = 0
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        if _pk(rec, w1) is None:
            continue
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        by_tau = collections.defaultdict(list)
        for gi, g in enumerate(g2):
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append((gi, g))
        for tau, gs in sorted(by_tau.items()):
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
            for gi, g in gs:
                if EV.FAMILY.get(g["spec_type"]) != "box":
                    continue
                hit = any(V2.match(g, er, m) for er in fam[:1])
                tol = V2.tol_px(g)
                glo = g["price_lo"] / PIP
                # all cand rows matching edges; group into candidates
                mc = [cd for cd in (e_t.cand_log or [])
                      if cd.get("kind") == "BOX"
                      and (cd.get("cet_min") or 0) <= tau
                      and edge_match(cd, g, tol)
                      and span_overlap(cd, g, m, w0, tau)]
                if not mc:
                    continue
                # candidate identity -> its last resolution <= tau
                cands = collections.defaultdict(list)
                for cd in mc:
                    cands[ckey(cd)].append(cd)
                res = {}          # key -> (outcome, cet_min, score)
                for k, rr in cands.items():
                    rr.sort(key=lambda cd: cd.get("cet_min") or 0)
                    final = next((cd for cd in reversed(rr)
                                  if cd.get("outcome") != "proposed"),
                                 None)
                    res[k] = (final["outcome"],
                              final.get("cet_min"),
                              final.get("score")) if final else \
                        ("pending", rr[-1].get("cet_min"), None)
                pooled = {k: v for k, v in res.items()
                          if v[0] != "pending" or
                          any(cd.get("score") is not None
                              for cd in cands[k])}
                logonly = {k: v for k, v in res.items()
                           if k not in pooled}
                if pooled:
                    n_cov_pooled += 1
                else:
                    n_cov_log += 1
                if hit:
                    continue
                n_missed += 1
                rows.append(_classify(rec, g, gi, tau, tol,
                                      cands, res, pooled, e_t, fam,
                                      w0, m, live))
    print("missed %d  (covered: pooled %d, log-only %d)"
          % (n_missed, n_cov_pooled, n_cov_log))
    agg = collections.Counter(r["bucket"] for r in rows)
    print("\n-- buckets --")
    for k, v in agg.most_common():
        print("  %-34s %d" % (k, v))
    print("\n-- rows --")
    for r in rows:
        print("%-6s g%d t%-4d %-26s %-16s %s"
              % (r["panel"], r["gi"], r["tau"], r["bucket"],
                 r["cause"], r["detail"]))


def span_overlap(cd, g, m, w0, tau):
    ct0, ct1 = cd.get("t0"), cd.get("t1")
    if ct0 is None or ct1 is None:
        return True
    ct0 = int(max(0, min(ct0, len(m) - 1)))
    ct1 = int(max(0, min(ct1, len(m) - 1)))
    c0, c1 = int(m[ct0]), int(m[ct1])
    g0 = g.get("t0") if g.get("t0") is not None else w0
    return min(c1, tau) - max(c0, g0) >= -15


def _classify(rec, g, gi, tau, tol, cands, res, pooled,
              e_t, fam, w0, m, live):
    glo, ghi = g["price_lo"] / PIP, g["price_hi"] / PIP
    row = {"panel": rec["id"], "gi": gi, "tau": tau,
           "g": "%.1f-%.1f" % (glo, ghi)}
    # born path first
    born_k = [k for k, v in res.items() if v[0] in BORN]
    if born_k:
        cd = next(cd for k in born_k for cd in cands[k]
                  if cd.get("outcome") in BORN)
        obj = link_obj(cd, e_t)
        row["bucket"] = "born"
        if obj is None:
            row["cause"] = "unlinked"
            row["detail"] = ""
            return row
        live_ids = {r["id"] for r in live}
        if obj.id in live_ids:
            pos = next((i + 1 for i, r in enumerate(fam)
                        if r["id"] == obj.id), None)
            row["bucket"] = "alive_rank%s" % pos
            top = fam[0] if fam else None
            if top is not None and top["id"] != obj.id:
                row["cause"] = "outranked_by"
                row["detail"] = (
                    "%s sc=%.2f age=%d"
                    % (top.get("why"), top.get("score") or 0,
                       tau - (top.get("t_birth") or tau)))
            else:
                row["cause"] = "rank1_nomatch"
                row["detail"] = ""
            return row
        cause, detail = "dead", ""
        for bar, name, d in sorted(getattr(obj, "events", [])):
            if name in DEATHS:
                cause, detail = name, "@bar%s %s" % (bar, d)
        row["bucket"] = "died"
        row["cause"] = cause
        row["detail"] = detail
        row["t_birth"] = getattr(obj, "t_birth", None)
        return row
    if not pooled:
        routes = collections.Counter(k[0] for k in cands)
        row["bucket"] = "log_only"
        row["cause"] = ";".join("%s:%d" % kv
                                for kv in routes.most_common())
        row["detail"] = "props=%d" % sum(len(v) for v in cands.values())
        return row
    # pooled but unborn -> dominant final resolution
    oc = collections.Counter(v[0] for v in pooled.values())
    top_cause = oc.most_common(1)[0][0]
    row["bucket"] = "not_born:" + top_cause
    row["cause"] = ";".join("%s:%d" % kv for kv in oc.most_common())
    mx = max((v[2] or -999) for v in pooled.values())
    row["detail"] = "maxscore=%.2f npooled=%d" % (mx, len(pooled))
    return row


if __name__ == "__main__":
    main()
