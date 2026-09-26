"""r1_render.py -- R56 s.56.4 R1.2: 30 lab renders for the author-vs-engine
study.  10 hits / 10 covered-but-missed / 10 no-coverage.

Each PNG (RGB): candles for the visible window, EMA25, dashed tau line,
and three rectangles:
  green  = author golden box (build span bs..be, price_lo..price_hi)
  red    = engine box@1 pick at tau (t_birth..tau)
  blue   = best edge-matching candidate (t0..t1)

Writes boxlab/r_renders/<panel>_g<i>_<bucket>.png and r_renders/INDEX.txt.
Lab renders only -- nothing under evalcheck/.
"""
import sys, os, pickle, collections, json, random

import numpy as np
from PIL import Image, ImageDraw

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
OUT = os.path.join(HERE, "r_renders")
PIP = C.PIP
GREEN = (20, 140, 40)
RED = (200, 30, 30)
BLUE = (30, 60, 220)
GRAY = (150, 150, 150)


def _pk(rec, bar):
    f = os.path.join(CACHE, "run_%s_%s_%s_%s.pkl"
                     % (VAR, HASH, rec["date"], bar))
    return pickle.load(open(f, "rb")) if os.path.exists(f) else None


class VMap:
    def __init__(self, t_lo, t_hi, p_lo, p_hi, W=1180, H=400):
        self.W, self.H = W, H
        self.x0, self.x1 = 46, W - 12
        self.y0, self.y1 = 16, H - 26
        self.t_lo, self.t_hi = t_lo, t_hi
        self.p_lo, self.p_hi = p_lo, p_hi

    def x(self, m):
        return self.x0 + (m - self.t_lo) / (self.t_hi - self.t_lo) \
            * (self.x1 - self.x0)

    def y(self, p):
        return self.y1 - (p - self.p_lo) / (self.p_hi - self.p_lo) \
            * (self.y1 - self.y0)


def dashed_rect(dr, x0, y0, x1, y1, color, w=2, dash=5):
    for x in np.arange(x0, x1, dash * 2):
        dr.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=w)
        dr.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=w)
    for y in np.arange(y0, y1, dash * 2):
        dr.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=w)
        dr.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=w)


def gather():
    """Per golden: bucket + geometry of golden/pick/best-cand."""
    rows = []
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
            if hit:
                bucket = "hit"
            elif not mc:
                bucket = "no_coverage"
            elif not pooled:
                bucket = "log_only"
            else:
                oc = collections.Counter(v[0] for v in pooled.values())
                bucket = oc.most_common(1)[0][0]
            best = None
            for k, (oc2, sc, fin) in pooled.items():
                if best is None or (sc or -999) > (best[1] or -999):
                    best = (k, sc, oc2, fin)
            if best is None and cands:
                # log-only: take the latest proposed row
                k = max(cands, key=lambda kk:
                        max(cd.get("cet_min") or 0 for cd in cands[kk]))
                best = (k, None, "logonly", cands[k][-1])
            pick = None
            if fam:
                ob = next((ob for ob in e_t.objects
                           if ob.id == fam[0]["id"]), None)
                if ob is not None:
                    geo = getattr(ob, "geometry", {}) or {}
                    pick = dict(lo=geo.get("bottom"),
                                hi=geo.get("top"),
                                tb=fam[0].get("t_birth"),
                                sc=fam[0].get("score"),
                                why=getattr(ob, "why", ""))
            rows.append(dict(rec=rec, gi=gi, g=g, tau=tau, m=m,
                             bucket=bucket, pick=pick,
                             cand=best[3] if best else None,
                             cand_sc=best[1] if best else None))
    return rows


def render(row, path):
    rec, g, tau, m = row["rec"], row["g"], row["tau"], row["m"]
    w0 = rec["window"]["x0"]
    w1 = rec["window"]["x1"] or 1439
    t, mm, o, h, l, c = CA.bars(rec["date"])
    g_lo, g_hi = g["price_lo"] / PIP, g["price_hi"] / PIP
    bs = g.get("build_start")
    be = g.get("build_end")
    t0 = max(0, (g.get("t0") or w0) - 90)
    t1 = min(1439, tau + 45)
    vis = (m >= t0) & (m <= t1)
    if not vis.any():
        return False
    hh, ll = h[vis], l[vis]
    p_lo = min(float(ll.min()), g_lo) - 6.0
    p_hi = max(float(hh.max()), g_hi) + 6.0
    vm = VMap(t0, t1, p_lo, p_hi)
    im = Image.new("RGB", (vm.W, vm.H), (255, 255, 255))
    dr = ImageDraw.Draw(im)

    p = int(p_lo / 50 + 1) * 50.0
    while p < p_hi:
        y = vm.y(p)
        dr.line([(vm.x0, y), (vm.x1, y)], fill=(230, 230, 230))
        p += 50.0

    idx = np.where(vis)[0]
    a = 2.0 / 26.0
    ema = np.zeros(len(c))
    e = None
    for k in range(len(c)):
        e = c[k] if e is None else e + a * (c[k] - e)
        ema[k] = e
    px = max(2, int((vm.x(t0 + 5) - vm.x(t0)) * 0.55))
    for k in idx:
        x = vm.x(int(m[k]))
        post = int(m[k]) > tau
        wick = (200, 200, 200) if post else (40, 40, 40)
        dr.line([(x, vm.y(h[k])), (x, vm.y(l[k]))], fill=wick)
        yo, yc = vm.y(o[k]), vm.y(c[k])
        top, bot = min(yo, yc), max(yo, yc)
        col = (170, 170, 170) if post else (
            (255, 255, 255) if c[k] >= o[k] else (40, 40, 40))
        dr.rectangle([x - px / 2, top, x + px / 2, max(bot, top + 1)],
                     outline=wick, fill=col)
    dr.line([(vm.x(int(m[k])), vm.y(ema[k])) for k in idx],
            fill=(90, 90, 90))
    dr.line([(vm.x0, vm.y1), (vm.x1, vm.y1)], fill=0)
    dr.line([(vm.x1, vm.y0), (vm.x1, vm.y1)], fill=0)
    # tau divider
    xt = vm.x(tau)
    for y in np.arange(vm.y0, vm.y1, 8):
        dr.line([(xt, y), (xt, min(y + 4, vm.y1))], fill=GRAY, width=1)

    # golden box (green, build span)
    gx0 = vm.x(bs if bs is not None else (g.get("t0") or w0))
    gx1 = vm.x(min(be if be is not None else (g.get("t1") or tau), t1))
    dr.rectangle([gx0, vm.y(g_hi), gx1, vm.y(g_lo)],
                 outline=GREEN, width=3)

    # engine pick (red solid)
    pk = row["pick"]
    if pk and pk["lo"] is not None:
        x0 = vm.x(pk["tb"] if pk["tb"] is not None else t0)
        dr.rectangle([x0, vm.y(pk["hi"]), xt, vm.y(pk["lo"])],
                     outline=RED, width=2)

    # best cand (blue dashed)
    cd = row["cand"]
    if cd is not None and cd.get("top") is not None:
        ct0 = int(m[max(0, min(cd.get("t0") or 0, len(m) - 1))])
        ct1 = int(m[max(0, min(cd.get("t1") or 0, len(m) - 1))])
        dashed_rect(dr, vm.x(ct0), vm.y(cd["top"]),
                    vm.x(min(ct1, t1)), vm.y(cd["bottom"]), BLUE, 2)

    dr.text((vm.x0 + 4, 3),
            "%s %s g%d tau=%d bucket=%s | gold[%.1f,%.1f] pick=%s cand_sc=%s"
            % (rec["id"], rec["date"], row["gi"], tau, row["bucket"],
               g_lo, g_hi,
               ("%.1f-%.1f sc%.1f" % (pk["lo"], pk["hi"], pk["sc"] or 0))
               if pk and pk["lo"] is not None else "none",
               ("%.2f" % row["cand_sc"]) if row["cand_sc"] else "-"),
            fill=(0, 0, 0))
    im.save(path)
    return True


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = gather()
    by = collections.defaultdict(list)
    for r in rows:
        by[r["bucket"]].append(r)
    picks = []
    picks += by["hit"][:10]
    rng = random.Random(22)
    missed = [r for b in ("below_min_score", "outranked",
                          "rate_limited", "expired", "log_only")
              for r in by[b]]
    rng.shuffle(missed)
    picks += missed[:10]
    noc = list(by["no_coverage"])
    rng.shuffle(noc)
    picks += noc[:10]
    idx = []
    for r in picks:
        fn = "%s_g%d_%s.png" % (r["rec"]["id"], r["gi"], r["bucket"])
        if render(r, os.path.join(OUT, fn)):
            idx.append("%s  %s g%d tau=%d clause=%s"
                       % (fn, r["rec"]["id"], r["gi"], r["tau"],
                          str(r["g"].get("clause"))[:80]))
    open(os.path.join(OUT, "INDEX.txt"), "w").write("\n".join(idx))
    print("rendered", len(idx))
    for line in idx:
        print(line)


if __name__ == "__main__":
    main()
