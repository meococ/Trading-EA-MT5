"""_revive_count.py — REQ-1(b): how many rate-limited right proposals
are revivals of closed same-geometry structures?

A revival = candidate whose kind matches a CLOSED object and whose
band overlaps that object's band (grave-band semantics: shared mass
>= half the thinner band for wide bands, center proximity for thin),
closed at most `win` bars before the cand's rate_limited bar.

Usage: python _revive_count.py <hash>
"""
import collections
import sys

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")

import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
import funnel as F


def band_of_obj(o):
    g = o.geometry
    if g.get("bottom") is not None and g.get("top") is not None:
        return g["bottom"], g["top"]
    for k in ("price", "level"):
        if g.get(k) is not None:
            return g[k], g[k]
    if g.get("p0") is not None and o.t_right is not None:
        p = g["p0"] + g.get("slope", 0.0) * (o.t_right - g["t0"])
        return p, p
    return None


def band_of_cand(cd):
    lo = cd.get("lo", cd.get("bottom"))
    hi = cd.get("hi", cd.get("top"))
    if lo is not None and hi is not None:
        return lo, hi
    for k in ("price", "level"):
        if cd.get(k) is not None:
            return cd[k], cd[k]
    if cd.get("p0") is not None:
        p = cd["p0"] + cd.get("slope", 0.0) * (cd["idx"] - cd["t0"])
        return p, p
    return None


def overlap(cb, ob, tol):
    """grave-style: shared mass >= half the thinner band, or centers
    within tol for thin/point bands."""
    if cb is None or ob is None:
        return False
    ch = cb[1] - cb[0]
    oh = ob[1] - ob[0]
    ov = min(cb[1], ob[1]) - max(cb[0], ob[0])
    if min(ch, oh) <= 2 * tol:
        return abs(0.5 * (cb[0] + cb[1]) - 0.5 * (ob[0] + ob[1])) <= tol
    return ov >= 0.5 * min(ch, oh)


def main():
    eng_hash = sys.argv[1]
    import engine
    cls = engine.PerceptionEngine
    recs = C.load_tune()
    per_kind = collections.Counter()
    per_kind_right = collections.Counter()
    rev = collections.Counter()          # (kind, right) -> count
    rev_win = collections.Counter()      # window -> (kind,right) counts
    rl_total = 0
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o_, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        tol = 2.0     # pips-ish structure tolerance
        dead = [(o.type, band_of_obj(o), o.t_right)
                for o in e.objects if o.t_right is not None]
        for cd in e.cand_log or []:
            if cd.get("outcome") != "rate_limited" or \
                    cd["kind"] in ("LABEL_TF", "BAR_MARKER"):
                continue
            r = F.cand_as_record(cd, m, w0, w1)
            if r is None:
                continue
            rl_total += 1
            bj = F.best_cand_match(r, g2, m)
            right = bj is not None
            per_kind[cd["kind"]] += 1
            per_kind_right[cd["kind"]] += right
            cb = band_of_cand(cd)
            hit_w = None
            for otype, ob, tr in dead:
                if otype != cd["kind"] or tr >= cd["idx"]:
                    continue
                if overlap(cb, ob, tol):
                    age = cd["idx"] - tr
                    hit_w = age if hit_w is None else min(hit_w, age)
            if hit_w is not None:
                rev[(cd["kind"], right)] += 1
                for w in (24, 48, 144, 10**9):
                    if hit_w <= w:
                        rev_win[(w, cd["kind"], right)] += 1
    print("rate_limited cands total:", rl_total)
    print("per kind (rate_limited | right):")
    for k in sorted(per_kind):
        print("  %-14s %4d | %4d" % (k, per_kind[k], per_kind_right[k]))
    print("\nrevivals among rate_limited (kind, right) -> n:")
    for (k, r), n in sorted(rev.items()):
        print("  %-14s right=%s : %d" % (k, r, n))
    print("\nby close-age window (win, kind, right) -> n:")
    for (w, k, r), n in sorted(rev_win.items()):
        print("  win=%-4s %-14s right=%s : %d" % (w, k, r, n))


if __name__ == "__main__":
    main()
