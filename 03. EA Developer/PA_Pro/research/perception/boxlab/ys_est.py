"""ys_est.py — R85 s85.3: arm YS "yield without death" estimate.

Read-only.  Same canonical-identical caches as Y3_EST
(run_uip2_pbbirth_8361fe85* == C-3 @e7d13384 geometry; tau-keyed
runs per the official M1).  Tag predicates imported from
trade_tags.py — never re-derived.

Yield model (both variants): the incumbent loses the box slot but
stays ACTIVE (facts kept, still ink for structure/derivations).
The freed slot is filled at the yield bar by the top-scored pending
box cand (alive in the pool at that bar).  The successor becomes
the new holder and may itself yield later — path dependence is
iterated to tau.

  YS-a: holder yields at its first stale_far onset
        (TT.s_stale_far verbatim).
  YS-b: a box_broken holder (TT.s_box_broken -> exit_bar) yields at
        the first bar where a pending box cand born STRICTLY AFTER
        exit_bar is alive; successor = top-scored such cand.

Outputs: boxlab/ys_est.jsonl + printed tables -> YS_EST.md.
"""
import glob
import json
import os
import pickle
import re
import sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import trade_tags as TT                # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
from recall_at_k import rank_live, score_map  # noqa: E402
from kernel import FAMILY              # noqa: E402

VAR, HASH = "uip2_pbbirth", "8361fe85"
BOXK = {"BOX", "CONTEXT_RANGE", "RANGE_OPEN"}
RE_W = re.compile(r"\[([\d.]+),([\d.]+)\]\s*t0=(\d+)")
TERM = {"born", "uip_birth", "expired", "nms_suppressed",
        "dedup_existing", "route_shadow", "revived",
        "vetoed_height", "vetoed_cooldown", "vetoed_irrelevant",
        "below_min_score", "lvfree_seed_veto", "uip_skip_pb",
        "uip_rewrite", "uip_spent"}


def pkl_for(date, tau):
    fs = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%d.pkl" % (VAR, HASH, date, tau)))
    return pickle.load(open(fs[0], "rb")) if fs else None


def ema25(c):
    k = 2.0 / 26.0
    out = np.empty(len(c))
    v = c[0]
    for i in range(len(c)):
        v = v + k * (c[i] - v)
        out[i] = v
    return out


def jb(m, cet):
    return min(int(np.searchsorted(m, cet)), len(m) - 1)


def ranked_at(e, m, w0, cet):
    live, _em = live_records(e, m, w0, cet)
    osc = {o.id: getattr(o, "score", None) for o in e.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    return rank_live(live, score_map(e))


def band_seq(o, e):
    if (o.why or "").startswith("ev_") and o.type == "BOX":
        seq = []
        b = [cd for cd in e.cand_log
             if cd.get("outcome") == "uip_birth"
             and cd.get("idx") == o.t_birth]
        if b:
            seq.append((int(o.t_birth), float(b[-1]["bottom"]),
                        float(b[-1]["top"]), int(b[-1].get("t0") or 0)))
        for ev in o.events:
            if ev[1] == "uip_rewrite":
                mm = RE_W.search(str(ev[2]))
                if mm:
                    seq.append((int(ev[0]), float(mm.group(1)),
                                float(mm.group(2)),
                                int(mm.group(3))))
        if not seq:
            g = o.geometry
            seq = [(int(o.t_birth), float(g["bottom"]),
                    float(g["top"]), int(g.get("t0") or 0))]
        return seq
    g = o.geometry
    if "bottom" in g and "top" in g:
        return [(int(o.t_birth), float(g["bottom"]), float(g["top"]),
                 int(g.get("t0") or o.t_left or 0))]
    return []


def band_at(seq, j):
    cur = seq[0]
    for v in seq:
        if v[0] <= j:
            cur = v
        else:
            break
    return cur


def stale_at(lo, hi, jb_, j, h, l, c, abr):
    return TT.s_stale_far("box", {"bottom": lo, "top": hi}, jb_, j,
                          h, l, c, abr)


def cand_alive_map(e):
    """signature -> (first_idx, last_idx, terminal_idx or None,
                     best_score, brief)."""
    out = {}
    for cd in e.cand_log:
        if cd.get("kind") not in BOXK or cd.get("idx") is None:
            continue
        sig = (cd.get("route"), round(cd.get("bottom") or 0, 1),
               round(cd.get("top") or 0, 1), cd.get("t0"))
        r = out.setdefault(sig, {"first": cd["idx"], "last": cd["idx"],
                                 "term": None, "score": -1e18,
                                 "route": cd.get("route"),
                                 "lo": cd.get("bottom"),
                                 "hi": cd.get("top"),
                                 "t0": cd.get("t0")})
        r["first"] = min(r["first"], cd["idx"])
        r["last"] = max(r["last"], cd["idx"])
        if cd.get("score") is not None:
            r["score"] = max(r["score"], cd["score"])
        if cd.get("outcome") in TERM and r["term"] is None:
            r["term"] = cd["idx"]
    return out


def pending_at(cmap, j, born_after=None):
    """pool box cands alive at bar j — entries are logged per-bar, so
    alive = first<=j<=last and no terminal outcome at <=j."""
    res = []
    for sig, r in cmap.items():
        if r["first"] > j or r["last"] < j:
            continue
        if r["term"] is not None and r["term"] <= j:
            continue
        if born_after is not None and r["first"] <= born_after:
            continue
        res.append(r)
    return res


class Holder(object):
    """a box-slot holder: real object or virtual (born of a cand)."""
    def __init__(self, birth, seq, name, why, obj=None):
        self.birth = birth
        self.seq = seq
        self.name = name
        self.why = why or ""
        self.obj = obj

    def band(self, j):
        return band_at(self.seq, j)


def simulate(e, j_tau, h, l, c, abr, variant):
    """iterate yield events to tau.  Returns list of events:
    {bar, holder, onset/exit, successor(brief|None)}."""
    real = []
    for o in e.objects:
        if o.type not in BOXK or o.t_birth is None:
            continue
        seq = band_seq(o, e)
        if not seq:
            continue
        real.append(Holder(int(o.t_birth), seq, o.id, o.why, o))
    cmap = cand_alive_map(e)
    holders = list(real)
    yielded = set()
    events = []

    def alive(hd, j):
        if hd.birth > j or hd.name in yielded:
            return False
        if hd.obj is not None and hd.obj.t_right is not None \
                and hd.obj.t_right <= j:
            return False
        return True

    def holder_at(j):
        act = [x for x in holders if alive(x, j)]
        if not act:
            return None
        evs = [x for x in act if (x.why or "").startswith("ev_")]
        if evs:
            return evs[0]        # one UIP object per panel
        return max(act, key=lambda x: (
            getattr(x.obj, "score", None) or -1e18
            if x.obj is not None else -1e18, -x.birth))

    def birth_feasible(j):
        """salience.py:790-799 under ev_uip_lvfree: UIP-persist objects
        count toward nothing; dead/broke actives reclass to context.
        A successor box (signal class) needs sig_live < budget_signal
        (3) and n_act < budget_hard (9)."""
        sig = nact = 0
        for x in holders:
            if not alive(x, j):
                continue
            if x.obj is not None and \
                    x.obj.geometry.get("meta_uip_persist"):
                continue
            nact += 1
            g = x.obj.geometry if x.obj is not None else {}
            dead = g.get("dead") or g.get("broke")
            otype = x.obj.type if x.obj is not None else "BOX"
            cls = "context" if dead else {
                "BOX": "signal", "RANGE_OPEN": "context",
                "CONTEXT_RANGE": "context",
                "LEVEL_CARRIED": "signal", "MINI_LEVEL": "signal",
                "PATTERN_LINE": "signal", "CONTEXT_LINE": "context",
                "BRACKET": "signal"}.get(otype, "annot")
            if cls == "signal":
                sig += 1
        return sig < 3 and nact < 9

    for j in range(j_tau + 1):
        hd = holder_at(j)
        if hd is None:
            continue
        _b, lo, hi, _t0 = hd.band(j)
        if variant == "a":
            s = stale_at(lo, hi, hd.birth, j, h, l, c, abr)
            if not s["stale"]:
                continue
            pool = [r for r in pending_at(cmap, j)
                    if not (r["lo"] == lo and r["hi"] == hi)]
            suc = max(pool, key=lambda r: r["score"], default=None)
            if suc is not None and not birth_feasible(j):
                suc = None     # successor birth blocked by class/hard cap
            evt = dict(bar=j, holder=hd.name, why=hd.why,
                       cause="stale_far", suc=suc)
        else:  # YS-b succession
            jfrom = int(hd.obj.t_left) if hd.obj is not None \
                and hd.obj.t_left is not None else (_t0 or 0)
            bb = TT.s_box_broken(lo, hi, jfrom, j, c, abr)
            if not bb["bbroken"]:
                continue
            xb = bb["exit_bar"]
            pool = [r for r in pending_at(cmap, j, born_after=xb)
                    if not (r["lo"] == lo and r["hi"] == hi)]
            suc = max(pool, key=lambda r: r["score"], default=None)
            if suc is None or not birth_feasible(j):
                continue       # keeps slot until a successor exists
            evt = dict(bar=j, holder=hd.name, why=hd.why,
                       cause="succession", exit_bar=xb, suc=suc)
        events.append(evt)
        yielded.add(hd.name)
        if suc:
            holders.append(Holder(
                int(evt["bar"]),
                [(int(suc["first"]), float(suc["lo"]),
                  float(suc["hi"]), int(suc.get("t0") or 0))],
                "cand:%s[%.1f,%.1f]" % (suc["route"], suc["lo"],
                                       suc["hi"]),
                suc["route"]))
    return events


def main():
    recs = C.load_tune()
    byid = {r["id"]: r for r in recs}
    e3 = [json.loads(x) for x in
          open(os.path.join(HERE, "e3_diag.jsonl"), encoding="utf-8")]
    NAMED12 = ("9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
               "9.36c", "9.40a", "9.42b", "9.48b", "9.52a", "9.57b")
    ecache, bcache = {}, {}

    def eng(date, tau):
        if (date, tau) not in ecache:
            ecache[(date, tau)] = pkl_for(date, tau)
        return ecache[(date, tau)]

    def day(date):
        if date not in bcache:
            _t, m, o, h, l, c = CA.bars(date)
            bcache[date] = (m, o, h, l, c, CA.abr(date), ema25(c))
        return bcache[date]

    # ---- all decisions (all families) ----
    dec = []
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        m, o, h, l, c, abr, ema = day(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        for g in gobjs:
            fam = EV.FAMILY.get(g["spec_type"])
            if fam not in ("box", "level", "line", "bracket") or \
                    not V2.scorable(g, w0, w1):
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            if (g.get("t1") or w1) < tau - 15:
                continue
            e = eng(rec["date"], tau)
            if e is None:
                continue
            j_tau = jb(m, tau)
            ranked = ranked_at(e, m, w0, tau)
            top = [r for r in ranked if FAMILY.get(r["type"]) == fam]
            k = {"box": 1, "level": 1, "line": 2, "bracket": 1}[fam]
            hit = any(V2.match(g, er, m) for er in top[:k])
            hitrec = next((r for r in top[:k]
                           if V2.match(g, r, m)), None)
            dec.append(dict(panel=rec["id"], date=rec["date"],
                            tau=int(tau), j_tau=j_tau, w0=w0, fam=fam,
                            hit=hit, hit_id=hitrec["id"]
                            if hitrec else None, g=g, e=e))
    fc = Counter((d["fam"], d["hit"]) for d in dec)
    print("decisions per (fam,hit):", dict(fc))

    out = []
    sim_a, sim_b = {}, {}

    def sims(d):
        key = (d["date"], d["tau"])
        if key not in sim_a:
            e = d["e"]
            m, o, h, l, c, abr, ema = day(d["date"])
            sim_a[key] = simulate(e, d["j_tau"], h, l, c, abr, "a")
            sim_b[key] = simulate(e, d["j_tau"], h, l, c, abr, "b")
        return sim_a[key], sim_b[key]

    # ---------- ITEM 1: box hits lost ----------
    print("\n=== ITEM 1: box hits (16) — lost per variant ===")
    for variant in ("a", "b"):
        lost = []
        for d in dec:
            if d["fam"] != "box" or not d["hit"]:
                continue
            evs = sims(d)[0 if variant == "a" else 1]
            direct = any(x["holder"] == d["hit_id"]
                         for x in evs if x["bar"] <= d["j_tau"])
            # the hit object is the successor iff a yield event's
            # successor matches its own birth cand's band+route
            hit_obj = next((o for o in d["e"].objects
                            if o.id == d["hit_id"]), None)
            is_suc = False
            if hit_obj is not None:
                hseq = band_seq(hit_obj, d["e"])
                _b, hlo, hhi, _t = band_at(
                    hseq, int(hit_obj.t_birth))
                for x in evs:
                    s = x.get("suc")
                    if s and abs(s["lo"] - hlo) <= 1.0 and \
                            abs(s["hi"] - hhi) <= 1.0 and \
                            s["route"] == (hit_obj.why or ""):
                        is_suc = True
            path = [x for x in evs if x["bar"] <= d["j_tau"]
                    and x.get("suc") and not is_suc]
            lost_flag = direct or bool(path)
            if lost_flag:
                lost.append((d["panel"], d["tau"], d["hit_id"],
                             "direct" if direct else "path",
                             [(x["holder"], x["bar"],
                               (x["suc"] or {}).get("route"))
                              for x in evs]))
            out.append(dict(item="hit_loss", variant=variant,
                            panel=d["panel"], tau=d["tau"],
                            id=d["hit_id"], direct=direct,
                            path=bool(path), is_successor=is_suc,
                            lost=bool(lost_flag)))
        print("  YS-%s lost: %d -> %s" % (variant, len(lost), lost))

    # ---------- ITEM 2: freed edge-matched cands ----------
    print("\n=== ITEM 2: BUDGET_CUT freed ===")
    bc = [r for r in e3 if r["cls"] == "BUDGET_CUT"]
    for variant in ("a", "b"):
        n_free = n_free_e = n_top = 0
        uq = set()
        for r in bc:
            rec = byid[r["panel"]]
            key = dict(panel=r["panel"], date=rec["date"],
                       tau=r["tau"], j_tau=None, w0=rec["window"]["x0"],
                       fam="box", hit=False, hit_id=None, g=None,
                       e=eng(rec["date"], r["tau"]))
            m, o, h, l, c, abr, ema = day(rec["date"])
            j_tau = jb(m, r["tau"])
            key["j_tau"] = j_tau
            evs = sims(key)[0 if variant == "a" else 1]
            inc_id = r["box1"]["id"]
            # yield events on THE incumbent while the cand alive
            w0c = 0
            if r["cand"]:
                _i = [cd["idx"] for cd in key["e"].cand_log
                      if cd.get("kind") in BOXK
                      and cd.get("route") == r["cand"]["route"]
                      and round(cd.get("bottom") or 0, 1)
                      == round(r["cand"]["lo"], 1)
                      and round(cd.get("top") or 0, 1)
                      == round(r["cand"]["hi"], 1)]
                w0c = min(_i) if _i else int(r["cand"]["idx"])
            pend_end = j_tau if r["killer"] == "proposed" \
                else int(r["kill_bar"])
            free = False
            top_suc = False
            for x in evs:
                if x["holder"] != inc_id:
                    continue
                if not (w0c <= x["bar"] <= pend_end):
                    continue   # yield must land inside cand's window
                if variant == "b" and w0c <= (x.get("exit_bar") or 0):
                    continue   # cand born before/at exit_bar
                free = True
                s = x.get("suc")
                if s and r["cand"] and \
                        round(s["lo"], 1) == round(
                            r["cand"]["lo"], 1) and \
                        round(s["hi"], 1) == round(
                            r["cand"]["hi"], 1) and \
                        s["route"] == r["cand"]["route"]:
                    top_suc = True
            n_free += free
            n_free_e += (free and r.get("edge_matched"))
            n_top += (free and r.get("edge_matched") and top_suc)
            if free and r.get("edge_matched"):
                uq.add((r["panel"], inc_id))
            out.append(dict(item="freed", variant=variant,
                            panel=r["panel"], tau=r["tau"],
                            inc=inc_id, edge=bool(r["edge_matched"]),
                            free=free, top_successor=top_suc,
                            evs=[(x["holder"], x["bar"], x["cause"])
                                 for x in evs]))
        print("  YS-%s: incumbent yielded while cand pending %d | "
              "edge-matched %d (%d unique inc) | cand is top "
              "successor %d" % (variant, n_free, n_free_e,
                                len(uq), n_top))

    # ---------- ITEM 3: cross-family at-risk ----------
    print("\n=== ITEM 3: cross-family at-risk ===")
    for variant in ("a", "b"):
        risk = defaultdict(list)
        for d in dec:
            if d["fam"] == "box" or not d["hit"]:
                continue
            evs = sims(d)[0 if variant == "a" else 1]
            evs = [x for x in evs if x["bar"] <= d["j_tau"]]
            if not evs:
                continue
            # touch channels: (a) level derived at the yielding
            # box's edge; (b) successor birth fills the signal class
            # cap (3) or budget_hard (9) -> a later-born hit object
            # of a signal family could have been blocked (lvfree:
            # UIP excluded from all counts; dead/broke -> context)
            hit_obj = next((o for o in d["e"].objects
                            if o.id == d["hit_id"]), None)
            why = []
            for x in evs:
                yb = next((o for o in d["e"].objects
                           if o.id == x["holder"]), None)
                if yb is not None and hit_obj is not None:
                    hg = hit_obj.geometry
                    yseq = band_seq(yb, d["e"])
                    _b, ylo, yhi, _t = band_at(yseq, x["bar"])
                    if hit_obj.type in ("LEVEL_CARRIED",
                                        "MINI_LEVEL") and \
                            hg.get("price") is not None and \
                            min(abs(hg["price"] - ylo),
                                abs(hg["price"] - yhi)) <= \
                            TT.tol_e(abr[x["bar"]]):
                        why.append("level-at-yielding-edge")
                sig_live = nact = 0
                for o in d["e"].objects:
                    if o.t_birth is None or o.t_birth > x["bar"]:
                        continue
                    if o.t_right is not None \
                            and o.t_right <= x["bar"]:
                        continue
                    if o.geometry.get("meta_uip_persist"):
                        continue
                    nact += 1
                    g = o.geometry
                    if g.get("dead") or g.get("broke"):
                        continue          # context class
                    if o.type in ("BOX", "LEVEL_CARRIED",
                                  "MINI_LEVEL", "PATTERN_LINE",
                                  "BRACKET"):
                        sig_live += 1
                late = hit_obj is not None and \
                    hit_obj.t_birth is not None and \
                    hit_obj.t_birth > x["bar"]
                if x.get("suc") is not None and late:
                    if sig_live + 1 >= 3:
                        why.append("signal_cap3")
                    if nact + 1 >= 9:
                        why.append("budget_hard9")
            if why:
                risk[d["fam"]].append((d["panel"], d["tau"],
                                       d["hit_id"], why))
        for fam in ("level", "line", "bracket"):
            print("  YS-%s %s at-risk: %d %s"
                  % (variant, fam, len(risk[fam]), risk[fam]))
            out.append(dict(item="x_atrisk", variant=variant, fam=fam,
                            rows=risk[fam]))

        # arm-Y gross losses (boxlab/y_measure_y1.jsonl flips:
        # parent_hit & !y_hit) — would a YS yield event land on the
        # lost hit's panel before its tau?
        yflips = [json.loads(l)["flip"] for l in open(
            "boxlab/y_measure_y1.jsonl", encoding="utf8")
            if '"flip"' in l]
        ylost = [f for f in yflips
                 if f["parent_hit"] and not f["y_hit"]
                 and f["fam"] in ("level", "line", "bracket")]
        yleg = []
        for f in ylost:
            d = next((x for x in dec
                      if x["panel"] == f["panel"]
                      and x["tau"] == f["tau"]), None)
            if d is None:
                yleg.append((f["panel"], f["tau"], f["fam"],
                             f["parent_pick"], None))
                continue
            evs = [x for x in sims(d)[0 if variant == "a" else 1]
                   if x["bar"] <= d["j_tau"]]
            yleg.append((f["panel"], f["tau"], f["fam"],
                         f["parent_pick"], len(evs)))
        print("  YS-%s arm-Y lost hits (level/line/bracket): %s"
              % (variant, yleg))
        out.append(dict(item="x_armY", variant=variant, rows=yleg))

    # ---------- ITEM 4: 12 fixed review panels ----------
    print("\n=== ITEM 4: fixed review panels ===")
    review = json.load(open(
        os.path.join(PERC, "review", "review_panels.json")))
    for p in review["panels"]:
        if p["name"] not in NAMED12:
            continue
        rec = byid.get(p["name"])
        if rec is None:
            continue
        tau = int(p["tau"])
        e = eng(rec["date"], tau)
        if e is None:
            continue
        m, o, h, l, c, abr, ema = day(rec["date"])
        j_tau = jb(m, tau)
        d = dict(panel=p["name"], date=rec["date"], tau=tau,
                 j_tau=j_tau, w0=rec["window"]["x0"], fam="box",
                 hit=False, hit_id=None, g=None, e=e)
        eva, evb = sims(d)
        gobjs, _u, _to = EV.gold_objects(rec)
        gs = [g for g in gobjs if g["spec_type"] in V2.BOX_TYPES]
        for vn, evs in (("a", eva), ("b", evb)):
            ok_edge = ok_auth = False
            for x in evs:
                s = x.get("suc")
                if s is None:
                    continue
                for g in gs:
                    tol = V2.tol_px(g)
                    glo, ghi = g["price_lo"] * 1e4, g["price_hi"] * 1e4
                    if abs(s["lo"] - glo) <= tol and \
                            abs(s["hi"] - ghi) <= tol:
                        ok_edge = True
                    er = dict(type="BOX", lo=s["lo"], hi=s["hi"],
                              t0=int(m[min(int(s["first"]),
                                          len(m) - 1)]),
                              t1=int(tau), w0=d["w0"], w1=int(tau))
                    try:
                        if V2.match(g, er, m):
                            ok_auth = True
                    except Exception:
                        pass
            print("  %-6s YS-%s yields=%d suc-edge=%s suc-author=%s %s"
                  % (p["name"], vn, len(evs), ok_edge, ok_auth,
                     [(x["holder"], x["bar"],
                       (x["suc"] or {}).get("route"))
                      for x in evs]))
            out.append(dict(item="review", variant=vn, panel=p["name"],
                            yields=len(evs), suc_edge=ok_edge,
                            suc_author=ok_auth,
                            evs=[(x["holder"], x["bar"], x["cause"],
                                  (x["suc"] or {}).get("route"))
                                 for x in evs]))

    with open(os.path.join(HERE, "ys_est.jsonl"), "w",
              encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, default=str) + "\n")
    print("\nwrote ys_est.jsonl (%d rows)" % len(out))


if __name__ == "__main__":
    main()
