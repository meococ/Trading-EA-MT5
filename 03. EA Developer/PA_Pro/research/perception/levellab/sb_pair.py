"""sb_pair.py — append BOTH scoreboard rows for a levellab A/B in one
invocation, at ONE engine hash (R24 §24.3).

Usage: python sb_pair.py --on v2
"""
import argparse
import datetime
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "linelab"))
sys.path.insert(0, _HERE)

import bars_cache  # noqa: E402
import funnel as F  # noqa: E402
import engine as ENG  # noqa: E402
import ab_engine as A  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", choices=["flag_on", "v2", "v2b"],
                    required=True)
    args = ap.parse_args()
    import scoreboard as SB
    import pa_slots
    recs = bars_cache.tune_records()
    eng_hash = F.code_hash(F.V1_FILES)
    ruler_hash = SB.file_hash(
        os.path.join(_PERC, "evalcheck", "eval_v2.py"))
    utc = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%MZ")
    arms = [("flag_off", ENG.PerceptionEngine),
            (args.on, A.ARMS[args.on])]
    with pa_slots.slot("levellab-ab", timeout=1200):
        rows = {tag: SB.measure(cls, eng_hash, recs, variant=tag)
                for tag, cls in arms}
    for tag, _ in arms:
        line = SB.append_row(utc, "v1", eng_hash, ruler_hash,
                             rows[tag], lane="levellab", variant=tag)
        print(line)
    print("engine hash (both rows):", eng_hash)


if __name__ == "__main__":
    main()
