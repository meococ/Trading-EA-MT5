"""ceiling_sample.py -- F-B3 seeded panel sampler (HUMAN_CEILING_PROTOCOL).

Draws the 10-panel ceiling set from TUNE 198: 4 EU / 3 US / 3 Asia by
window midpoint (CET); 5 sparse (<=2 scorable goldens) / 5 busy (>=4);
every panel carries goldens from >=2 of box/level/line.

Asia has exactly ONE busy panel at >=4 (TUNE is EU-heavy), so the busy
quota there is the single qualifying panel; the remaining busy slots go
to EU/US.  Seed + panel list are logged BEFORE rendering (s.55.3 F-B3).

Read-only.  Usage: python ceiling_sample.py <seed>
"""
import sys, os, json, random, collections
sys.path.insert(0, 'evalcheck'); sys.path.insert(0, '.')
import common as C          # noqa: E402
import eval as EV           # noqa: E402
import eval_v2 as V2        # noqa: E402
from snapshot import tau_of  # noqa: E402

M1F = {"box", "level", "line"}


def session_of(rec):
    mid = (rec["window"]["x0"] + (rec["window"]["x1"] or 1439)) / 2
    return "asia" if mid < 420 else ("eu" if mid < 780 else "us")


def panel_stats(rec):
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    g2 = [g for g in EV.gold_objects(rec)[0] if V2.scorable(g, w0, w1)]
    fams = {EV.FAMILY.get(g["spec_type"]) for g in g2} & M1F
    taus = [tau_of(g) for g in g2]
    taus = [t for t in taus if t is not None]
    return g2, fams, (min(max(taus), w1) if taus else w1)


def draw(seed=20260922):
    recs = C.load_tune()
    rng = random.Random(seed)
    pool = collections.defaultdict(list)
    for r in recs:
        g2, fams, tau = panel_stats(r)
        if len(fams) < 2:
            continue
        dens = "busy" if len(g2) >= 4 else ("sparse" if len(g2) <= 2
                                            else "mid")
        pool[(session_of(r), dens)].append((r, len(g2), tau))
    quota = [("eu", "sparse", 2), ("eu", "busy", 2),
             ("us", "sparse", 1), ("us", "busy", 2),
             ("asia", "sparse", 2), ("asia", "busy", 1)]
    pick = []
    for sess, dens, n in quota:
        bag = pool[(sess, dens)]
        rng.shuffle(bag)
        pick += [(sess, dens) + t for t in bag[:n]]
    return pick


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 20260922
    for sess, dens, rec, ng, tau in draw(seed):
        print("%-8s %-6s %-6s goldens=%d tau=%s" %
              (rec["id"], sess, dens, ng, tau))
