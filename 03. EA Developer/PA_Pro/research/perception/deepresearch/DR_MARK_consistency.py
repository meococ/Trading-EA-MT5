"""DR_MARK_consistency.py — E3b: stability / flicker / determinism of
the event marks (BRACKET, LABEL_TF, SQUEEZE, FALSE_EXT-facts).

Same perturbation battery as DR_LINE_consistency (base, base2 for
determinism; shift 1/2/3/5/10; jitter seeds 1-3 at +-0.3 pip; m15),
but the tracked objects are the mark families:

  retention  — per BASE engine mark (not golden): does a same-type,
               same-side, +-10 min mark exist in the perturbed run?
               (self-consistency — a stable mark survives feed noise)
  letter flip— retained mark whose letter changed (T<->F, M<->W family)
  relabel    — count of T->F relabel events per run (flicker channel)
  bracket    — retained = same letter family + span coverage >= 0.3 of
               the base engine bracket's span
  squeeze    — retained = coverage >= 0.3
  fx facts   — false_high/low event times +-10 min
  churn/h    — (births + closes + relabels) / panel hours for mark kinds

Output: DR_MARK_consistency.jsonl + printed tables.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, os.path.join(PERC, "..", "..", "lib"))

import numpy as np                      # noqa: E402

import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import common as C                     # noqa: E402
import engine as ENG                   # noqa: E402

OUT = os.path.join(HERE, "DR_MARK_consistency.jsonl")


def run_feed(m, t, o, h, l, c, w1):
    e = ENG.PerceptionEngine()
    e.cand_log = []
    for j in np.where(m <= w1)[0]:
        e.update(int(t[j]), float(o[j]) / 1e4, float(h[j]) / 1e4,
                 float(l[j]) / 1e4, float(c[j]) / 1e4,
                 cet_min=int(m[j]))
    return e


def canon(e, m, w0, w1):
    recs = V2.eng_objects(e, m, w0, w1)
    return json.dumps(recs, sort_keys=True, default=str)


def mark_recs(e, m, w0, w1):
    """Engine marks/brackets/squeezes as retention keys."""
    out = []
    for o in e.objects:
        if o.type not in ("LABEL_TF", "BRACKET", "SQUEEZE"):
            continue
        tb = V2._min(m, o.t_birth)
        t0m = V2._min(m, o.t_left)
        t1_src = o.geometry.get("t1_drawn") or \
            (o.t_right if o.t_right is not None else len(e.bars) - 1)
        t1m = V2._min(m, t1_src)
        if t1m < w0 or t0m > w1:
            continue
        g = o.geometry
        out.append({"type": o.type, "t_birth": tb,
                    "t0": max(t0m, w0), "t1": min(t1m, w1),
                    "letter": g.get("letter"), "side": g.get("side")})
    return out


def fx_times(e, m, w0, w1):
    out = []
    for i, f in enumerate(e.bar_facts):
        if i >= len(m):
            break
        if w0 <= int(m[i]) <= w1:
            if "false_high" in f:
                out.append((int(m[i]), "h"))
            if "false_low" in f:
                out.append((int(m[i]), "l"))
    return out


def churn(e, m, w0, w1):
    n_birth = n_close = n_rel = 0
    in_win = lambda j: j is not None and \
        w0 <= int(m[min(j, len(m) - 1)]) <= w1
    for o in e.objects:
        if o.type not in ("LABEL_TF", "BRACKET", "SQUEEZE"):
            continue
        if in_win(o.t_birth):
            n_birth += 1
        if in_win(o.t_right):
            n_close += 1
        n_rel += sum(1 for ev in o.events
                     if ev[1] == "relabel" and in_win(ev[0]))
    hrs = max((w1 - w0) / 60.0, 0.5)
    return {"birth": n_birth, "close": n_close, "relabel": n_rel,
            "churn_h": (n_birth + n_close + n_rel) / hrs}


def _cov(e0, e1, g0, g1):
    ov = max(0, min(e1, g1) - max(e0, g0))
    return ov / max(g1 - g0, 1)


def _fam(s):
    return (s or "").replace("m", "").replace("w", "").replace("i", "")


def retained(base_mk, mks):
    """(hit, letter_flip) — does a corresponding mark exist in mks?"""
    for mk in mks:
        if mk["type"] != base_mk["type"]:
            continue
        if base_mk["type"] == "LABEL_TF":
            if abs(mk["t_birth"] - base_mk["t_birth"]) > 10:
                continue
            if base_mk["side"] and mk["side"] and \
                    base_mk["side"] != mk["side"]:
                continue
            return True, (mk["letter"] != base_mk["letter"])
        if _fam(mk["letter"]) != _fam(base_mk["letter"]):
            continue
        if _cov(mk["t0"], mk["t1"], base_mk["t0"], base_mk["t1"]) >= 0.3:
            return True, (mk["letter"] != base_mk["letter"])
    return False, False


def variants(t, m, o, h, l, c):
    yield "base", (t, m, o, h, l, c)
    yield "base2", (t, m, o, h, l, c)
    for k in (1, 2, 3, 5, 10):
        yield "shift%d" % k, (t[k:], m[k:], o[k:], h[k:], l[k:], c[k:])
    for s in (1, 2, 3):
        rng = np.random.RandomState(s)
        jo = o + rng.uniform(-0.3, 0.3, len(o))
        jh = h + rng.uniform(-0.3, 0.3, len(h))
        jl = l + rng.uniform(-0.3, 0.3, len(l))
        jc = c + rng.uniform(-0.3, 0.3, len(c))
        jh = np.maximum.reduce([jh, jo, jc])
        jl = np.minimum.reduce([jl, jo, jc])
        yield "jitter%d" % s, (t, m, jo, jh, jl, jc)
    n15 = len(t) // 3
    t15 = t[:n15 * 3].reshape(-1, 3)[:, 0]
    m15 = m[:n15 * 3].reshape(-1, 3)[:, 0]
    o15 = o[:n15 * 3].reshape(-1, 3)[:, 0]
    h15 = h[:n15 * 3].reshape(-1, 3).max(1)
    l15 = l[:n15 * 3].reshape(-1, 3).min(1)
    c15 = c[:n15 * 3].reshape(-1, 3)[:, 2]
    yield "m15", (t15, m15, o15, h15, l15, c15)


def main():
    recs = C.load_tune()
    rows = []
    det_fail = []
    for k, rec in enumerate(recs):
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        base_marks = base_fx = base_hash = None
        for vn, (tt, mm, oo, hh, ll, cc) in variants(t, m, o, h, l, c):
            e = run_feed(mm, tt, oo, hh, ll, cc, w1)
            if vn == "base":
                base_hash = hashlib.sha256(
                    canon(e, mm, w0, w1).encode()).hexdigest()
                base_marks = mark_recs(e, mm, w0, w1)
                base_fx = fx_times(e, mm, w0, w1)
            if vn == "base2":
                h2 = hashlib.sha256(
                    canon(e, mm, w0, w1).encode()).hexdigest()
                if h2 != base_hash:
                    det_fail.append(rec["id"])
            mks = mark_recs(e, mm, w0, w1)
            fx = fx_times(e, mm, w0, w1)
            ch = churn(e, mm, w0, w1)
            row = {"panel": rec["id"], "variant": vn,
                   "n_marks": len(mks), "n_fx": len(fx), **ch}
            if vn not in ("base", "base2"):
                keep = []
                for bm in base_marks:
                    hit, flip = retained(bm, mks)
                    keep.append({"type": bm["type"], "hit": hit,
                                 "flip": flip})
                fxkeep = sum(1 for (bt, bd) in base_fx
                             if any(abs(ft - bt) <= 10 and fd == bd
                                    for ft, fd in fx))
                row["keep"] = keep
                row["fx_keep"] = (fxkeep, len(base_fx))
            rows.append(row)
        if (k + 1) % 20 == 0:
            print("panel %d/%d" % (k + 1, len(recs)), flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("\n=== determinism: %d panels differ on identical re-run ==="
          % len(det_fail))
    if det_fail:
        print(det_fail[:10])

    agg = {}
    for r in rows:
        if r["variant"] in ("base", "base2"):
            continue
        for k2 in r.get("keep", []):
            a = agg.setdefault((k2["type"], r["variant"]), [0, 0, 0])
            a[1] += 1
            a[0] += k2["hit"]
            a[2] += k2["flip"]
        if r.get("fx_keep"):
            a = agg.setdefault(("FALSE_EXT", r["variant"]), [0, 0, 0])
            a[0] += r["fx_keep"][0]
            a[1] += r["fx_keep"][1]
    print("\n=== retention by type x variant "
          "(kept / base marks, letter flips) ===")
    for (ty, vn), (hit, tot, fl) in sorted(agg.items()):
        print("%-10s %-8s keep=%.2f (%d/%d)  flips=%d"
              % (ty, vn, hit / max(tot, 1), hit, tot, fl))
    print("\n=== churn (mark-kind events/hour) ===")
    for vn in ("base", "shift3", "jitter1", "m15"):
        vals = [r["churn_h"] for r in rows if r["variant"] == vn]
        if vals:
            print("%-8s churn/h med=%.2f p90=%.2f"
                  % (vn, float(np.median(vals)),
                     float(np.percentile(vals, 90))))


if __name__ == "__main__":
    main()
