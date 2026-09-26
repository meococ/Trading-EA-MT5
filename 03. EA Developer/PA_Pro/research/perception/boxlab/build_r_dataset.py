"""build_r_dataset.py -- R56 s.56.5 item 3: the box-research dataset.

One row per BOX candidate per box-golden tau on TUNE, from the K9/STABLE
C-2 parent caches (c1r_p_base @ ee2cbf12 == 4c2df34d post-F1).

Row = candidate state at tau:
  - every cand_log field (kind, route, top, bottom, t0, t1, t_left,
    cet_min, score, outcome, touches, prom_abr, contain, barrier,
    pressure, compression, ema_guide, box_rank, deeper_lv, n_active)
  - raw features computed from bars <= tau only (H1-H7 hypothesis list):
      px_in_box, dist_close_edge_abr, bars_since_in_band,
      ema_slope_span, ema_in_band, probes_top, probes_bot,
      prior_leg_abr, recency_bars, h_rel_day, h_abr, overlap_ratio
  - labels: label_golden (eval_v2.match on the cand's drawn span),
    label_edge (lab edge_match+span_overlap convention), born_by_tau,
    is_engine_pick (top-ranked live box-family object at tau == cand)
  - ids: panel, date, tau, cand_key

Writes boxlab/r_dataset/rows.csv + DATA_DICT.md.  Read-only on caches.
"""
import sys, os, pickle, csv, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)
sys.path.insert(0, HERE)

import common as C           # noqa: E402
import eval as EV            # noqa: E402
import eval_v2 as V2         # noqa: E402
import cache as CA           # noqa: E402
import recall_at_k as RK     # noqa: E402
from snapshot import tau_of, live_records   # noqa: E402
from c1_missed import edge_match, span_overlap, ckey   # noqa: E402
from salience import FAMILY  # noqa: E402

HASH = "ee2cbf1202db47b6"
VAR = "c1r_p_base"
CACHE = os.path.join(PERC, "evalcheck", "_cache")
OUT = os.path.join(HERE, "r_dataset")
PIP = C.PIP


def pk(date, w1):
    f = os.path.join(CACHE, "run_%s_%s_%s_%s.pkl" % (VAR, HASH, date, w1))
    return pickle.load(open(f, "rb")) if os.path.exists(f) else None


def feats_at(e, cd, j_tau, srv):
    """Raw features from bars <= j_tau only.  e.bars rows are dicts in
    pips (o/h/l/c); srv = cet_min per bar."""
    top, bot = cd.get("top"), cd.get("bottom")
    t0, t1 = cd.get("t0"), cd.get("t1")
    if top is None or bot is None or t0 is None:
        return {}
    jt0 = min(int(t0), len(srv) - 1)     # cand t0/t1 are bar indices
    h = np.array([b["h"] for b in e.bars])
    l = np.array([b["l"] for b in e.bars])
    cl = np.array([b["c"] for b in e.bars])
    abr = float(e.abr[j_tau]) if j_tau < len(e.abr) else 5.0
    abr = abr or 5.0
    px = cl[j_tau]
    inside = bot <= px <= top
    # bars since close last inside band (0 if inside at tau)
    since = 0
    for j in range(j_tau, -1, -1):
        if bot <= cl[j] <= top:
            since = j_tau - j
            break
    else:
        since = j_tau + 1
    # EMA25 flatness over the box's own span (pips/bar) + in-band flag
    j1 = min(int(t1) if t1 is not None else j_tau, j_tau)
    j0s = min(jt0, j1)
    span = max(1, j1 - j0s)
    ema_slope = abs(e.ema[j1] - e.ema[j0s]) / span if j1 > j0s else 0.0
    ema_in = float(bot <= e.ema[j_tau] <= top) if j_tau < len(e.ema) \
        else 0.0
    # rejected probes at each edge: wick beyond, close back inside
    pt = pb = 0
    for j in range(jt0, j_tau + 1):
        if h[j] > top + 1.0 and cl[j] <= top:
            pt += 1
        if l[j] < bot - 1.0 and cl[j] >= bot:
            pb += 1
    # prior leg in ABR: last pivot confirmed before t0
    legs = [pv for pv in e.book.seq if pv.t_conf <= t0]
    prior_leg = (abs(legs[-1].leg) / abr) if legs else 0.0
    # recency: bars since structure end; and bars since last band touch
    rec = j_tau - j1
    touch = j_tau
    for j in range(j_tau, -1, -1):
        if l[j] <= top and h[j] >= bot:
            touch = j_tau - j
            break
    day_rng = float(h[:j_tau + 1].max() - l[:j_tau + 1].min())
    overlap = [j for j in range(jt0, j1 + 1) if l[j] <= top and h[j] >= bot]
    return {
        "px_in_box": float(inside),
        "dist_close_edge_abr": min(abs(px - top), abs(px - bot)) / abr,
        "bars_since_in_band": since,
        "ema_slope_span": ema_slope,
        "ema_in_band": ema_in,
        "probes_top": pt, "probes_bot": pb,
        "prior_leg_abr": prior_leg,
        "age_bars": j_tau - jt0,
        "recency_bars": rec,
        "bars_since_touch": touch,
        "h_rel_day": (top - bot) / max(day_rng, 1e-9),
        "h_abr": (top - bot) / abr,
        "overlap_ratio": len(overlap) / max(1, j1 - jt0 + 1),
        "abr_at_tau": abr,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    recs = C.load_tune()
    rows = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        e = pk(rec["date"], w1)
        if e is None:
            continue
        srv = np.array([b["cet_min"] for b in e.bars])
        t, m, o_, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        box_g = [(gi, g) for gi, g in enumerate(g2)
                 if EV.FAMILY.get(g["spec_type"]) == "box"]
        taus = sorted({min(tau_of(g), w1) for gi, g in box_g
                       if tau_of(g) is not None and tau_of(g) >= w0})
        if not taus:
            continue
        cl = [cd for cd in (e.cand_log or []) if cd.get("kind") == "BOX"]
        cands = collections.defaultdict(list)
        for cd in cl:
            cands[ckey(cd)].append(cd)
        for tau in taus:
            gs_t = [gi for gi, g in box_g if tau_of(g) == tau
                    or (tau_of(g) or 0) > tau]
            # goldens scored at this tau: those whose tau_of <= tau
            gs_t = [gi for gi, g in box_g
                    if tau_of(g) is not None and tau_of(g) <= tau]
            j_tau = int(np.searchsorted(srv, tau, "right")) - 1
            if j_tau < 0:
                continue
            # engine's top box pick at tau
            live, _em = live_records(e, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None) for ob in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            fam = [r for r in ranked
                   if EV.FAMILY.get(r["type"]) == "box"]
            pick_geo, pr = None, {}
            if fam:
                fr = fam[0]
                pick_geo = (round(fr.get("top") or fr.get("hi") or 0, 1),
                            round(fr.get("bottom") or fr.get("lo") or 0,
                                  1))
                pr = {"pick_type": fr["type"],
                      "pick_hi": fr.get("hi"),
                      "pick_lo": fr.get("lo"),
                      "pick_t0": fr.get("t0"),
                      "pick_t1": fr.get("t1"),
                      "pick_score": fr.get("score"),
                      "pick_id": fr.get("id")}
            for k, rr in cands.items():
                rr = [cd for cd in rr if (cd.get("cet_min") or 0) <= tau]
                if not rr:
                    continue
                last = next((cd for cd in reversed(rr)
                             if cd.get("outcome") != "proposed"), None)
                base = dict(rr[-1])
                out = last["outcome"] if last else "pending"
                f_ = feats_at(e, base, j_tau, srv)
                cand_rec = {"type": "BOX", "t0": base.get("t0"),
                            "t1": base.get("t1"), "lo": base.get("bottom"),
                            "hi": base.get("top"), "w0": w0, "w1": w1}
                lab, lab_edge = -1, -1
                for gi in gs_t:
                    g = g2[gi]
                    tol = V2.tol_px(g)
                    if V2.match(g, cand_rec, m) and lab < 0:
                        lab = gi
                    if edge_match(base, g, tol) and \
                            span_overlap(base, g, m, w0, tau) \
                            and lab_edge < 0:
                        lab_edge = gi
                born = any(cd.get("outcome") == "born" for cd in rr)
                row = {"panel": rec["id"], "date": rec["date"],
                       "tau": tau, "cand_key": str(k)}
                for kk in ("route", "top", "bottom", "t0", "t1",
                           "t_left", "touches", "prom_abr", "contain",
                           "barrier", "pressure", "compression",
                           "ema_guide", "box_rank", "deeper_lv",
                           "n_active"):
                    row[kk] = base.get(kk)
                row["last_outcome"] = out
                row["score_last"] = (last or rr[-1]).get("score")
                row["born_by_tau"] = int(born)
                row["is_engine_pick"] = int(
                    pick_geo is not None and
                    pick_geo == (round(base.get("top") or 0, 1),
                                 round(base.get("bottom") or 0, 1)))
                row["label_golden"] = lab
                row["label_edge"] = lab_edge
                row.update(pr)
                row.update(f_)
                rows.append(row)
    fields = list(rows[0].keys())
    with open(os.path.join(OUT, "rows.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("rows:", len(rows), "->", os.path.join(OUT, "rows.csv"))
    pos = sum(1 for r in rows if r["label_golden"] >= 0)
    print("rows matching a golden (V2):", pos)


if __name__ == "__main__":
    main()
