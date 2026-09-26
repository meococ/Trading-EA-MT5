"""c1_supersede.py — offline estimate of a box_score_pick flag
(the build lane's lc_score_pick mechanism, fam=="box").

Mechanism (salience.py ~L716-775): inside the rate-blocked branch, a
candidate scoring > the in-window slot holder + hyst_margin
supersedes it — the slot MOVES to the new birth (ledger conserved,
no extra ink), the incumbent closes "superseded".

Anatomy showed 26/42 covered goldens have right cands killed by
rate_limited, and the right cand usually out-scores the tau top-1.
This script asks: would supersede have fired?

Per BOX golden covered under wd:
  right cands = funnel.cand_right matches (records + raw log rows)
  for each raw row with outcome == 'rate_limited' at bar i, score s:
      holder = the BOX 'born' log row with bar b in (i-WIN, i]
               (the birth that occupies the window)
      fire   = s > holder.score + HYST
Predicted gain = goldens where any blocked right row fires.

Usage: python c1_supersede.py [variant hash]   (default c1r_wd e62f2dc9)
"""
import collections
import glob
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import funnel as F                     # noqa: E402
from scoreboard import panel_cands     # noqa: E402

WIN = 72          # salience rate_window_bars
HYST = 3.0        # salience hyst_margin


def _pkl(variant, h8, date, w1):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (variant, h8, date, w1))
    if os.path.exists(f):
        return f
    g = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%s.pkl" % (variant, h8, date, w1)))
    return g[0] if g else None


def _bar(row):
    """bar index of a raw cand_log row."""
    for k in ("idx", "i", "bar", "t"):
        if k in row:
            return row[k]
    return None


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else "c1r_wd"
    h8 = sys.argv[2] if len(sys.argv) > 2 else "e62f2dc9"
    recs = C.load_tune()
    stats = collections.Counter()
    fire_rows = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        f = _pkl(variant, h8, rec["date"], w1)
        if not f:
            continue
        e = pickle.load(open(f, "rb"))
        raw = [cd for cd in e.cand_log or [] if cd.get("kind") == "BOX"]
        # births that can hold a rate slot (fam==box births)
        births = [( _bar(cd), cd.get("score"))
                  for cd in raw if cd.get("outcome") == "born"]
        pairs_ = []
        for cd in e.cand_log or []:
            if cd["kind"] == "LABEL_TF":
                continue
            r = F.cand_as_record(cd, m, w0, w1)
            if r is not None:
                pairs_.append((r, cd))
        cands = [pr for pr in pairs_
                 if EV.FAMILY.get(pr[0]["type"]) == "box"]
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for g in g2:
            if g["spec_type"] != "BOX":
                continue
            right = [(r, cd) for r, cd in cands
                     if F.cand_right(g, r, m)]
            if not right:
                continue
            stats["covered"] += 1
            blocked = [( _bar(cd), cd.get("score"))
                       for _r, cd in right
                       if cd.get("outcome") == "rate_limited"
                       and cd.get("score") is not None]
            if not blocked:
                stats["not_rate_killed"] += 1
                continue
            stats["rate_killed"] += 1
            fired_birth = fired_w1 = False
            for bi, s in blocked:
                if bi is None:
                    continue
                holders = [(b, hs) for b, hs in births
                           if b is not None and bi - WIN < b <= bi]
                if not holders:
                    continue
                hb, hs = min(holders)     # earliest holder = the block
                # lc_score_pick compares act_scores (holder's CURRENT
                # score at the block bar) — bracket it: birth score
                # is the strict bound, w1 (decayed) score the loose.
                ho = next((o for o in e.objects
                           if o.type == "BOX" and o.t_birth == hb),
                          None)
                hw1 = getattr(ho, "score", None) if ho is not None \
                    else None
                if hs is not None and s > hs + HYST:
                    fired_birth = True
                if hw1 is not None and s > hw1 + HYST:
                    fired_w1 = True
                    fire_rows.append((rec["id"], bi, round(s, 2),
                                      hb, round(hs or -1, 2),
                                      round(hw1, 2),
                                      fired_birth))
                    break
            if fired_birth:
                stats["fire_vs_birth(strict)"] += 1
            elif fired_w1:
                stats["fire_vs_w1(loose)"] += 1
            else:
                stats["no_fire"] += 1
    print("variant=%s hash=%s hyst=%.1f win=%d" % (variant, h8, HYST, WIN))
    print(dict(stats))
    print("predicted box@1 delta: +%d (strict) to +%d (loose)" % (
        stats["fire_vs_birth(strict)"],
        stats["fire_vs_birth(strict)"] + stats["fire_vs_w1(loose)"]))
    print("\nfire rows (panel, blocked_bar, right_sco, holder_bar, "
          "holder_birth_sco, holder_w1_sco, strict?):")
    for r in fire_rows:
        print("  %s i=%s %.2f > holder@%s birth=%s w1=%s strict=%s" % r)


if __name__ == "__main__":
    main()
