"""arm_ab.py — R24 §24.3: runtime-flagged A/B arms at ONE engine hash.

Each arm is the same PerceptionEngine code with a deepcopied params
dict and one flag flipped — both arms share the code hash, satisfy
the pairing rule, and cache under `run_<variant>_<hash>_...`.

Usage:
    python evalcheck/arm_ab.py --arms base reviveON markerON tailON \
        budgetGOLD
    python evalcheck/arm_ab.py --hash a62edc195a154775   # pin source
"""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                       # noqa: E402
import funnel as F                       # noqa: E402
import cache as CA                       # noqa: E402
import scoreboard as SB                  # noqa: E402


def _set(p, dotted, val):
    ks = dotted.split(".")
    d = p
    for k in ks[:-1]:
        d = d[k]
    d[ks[-1]] = val


ARMS = {
    "base": {},
    "reviveON": {"salience.revive_exempt": True},
    "markerON": {"marker.day_extreme_only": True},
    "tailON": {"box.tail_bars": 12},
    "budgetGOLD": {"salience.budget_signal": 2,
                   "salience.budget_context": 1,
                   "salience.budget_annot": 2,
                   "salience.budget_hard": 4},
    # LEVEL-LAB defended-origin route (R24 §24.1; LEVER_TABLE.md)
    "labON": {"level.defended_origin": True},
    "labV2": {"level.defended_origin": True,
              "level.def_mini_off": True},
    "labV2B": {"level.defended_origin": True,
               "level.def_mini_off": True,
               "level.def_all_lc": True},
    # R27 §27.2 — per-family ledger arms (independent verification)
    "famledger": {"salience.fam_ledger": True},
    "famledgerV2": {"salience.fam_ledger": True,
                    "level.defended_origin": True,
                    "level.def_mini_off": True},
}


def make_cls(over):
    import engine
    def factory():
        p = copy.deepcopy(engine.load_params())
        for k, v in over.items():
            _set(p, k, v)
        return engine.PerceptionEngine(p)
    return factory


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+",
                    default=list(ARMS))
    ap.add_argument("--hash", default="")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    import engine
    h = args.hash or F.code_hash(F.V1_FILES)
    recs = C.load_tune()
    print("hash %s  arms=%s" % (h[:16], ",".join(args.arms)))
    for name in args.arms:
        over = ARMS[name]
        row = SB.measure(make_cls(over), h, recs, quick=args.quick,
                         variant="ab_" + name)
        h2 = F.code_hash(F.V1_FILES)
        flag = "" if h2 == h else "  !!! HASH MOVED %s" % h2[:8]
        fams = ["BOX", "PATTERN_LINE", "LEVEL_CARRIED", "BRACKET"]
        print("%-10s %s  snapR=%s  clutter=%s%s" % (
            name,
            " ".join("%s=%s/%s" % (
                f,
                SB.fmt(row["rec"].get(f)),
                SB.fmt(row["prec"].get(f))) for f in fams),
            SB.fmt(row["snap_recall"]), SB.fmt(row["clutter"]), flag))
        if h2 != h:
            print("ABORT: source moved mid-run; rerun both arms")
            sys.exit(2)


if __name__ == "__main__":
    main()
