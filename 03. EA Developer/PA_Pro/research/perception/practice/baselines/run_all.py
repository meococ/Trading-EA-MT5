"""run_all.py — score the PA-ATLAS causal baselines on TUNE.

Wrap: python research/perception/tools/heavy_run.py --lane pa-atlas --
        python research/perception/practice/baselines/run_all.py

Each baseline is a standalone emit() over one day's M5 bars; this
runner applies the causal tau-slice (objects with birth <= tau < die)
and scores recall@k with evalcheck/eval_v2.py match — imported, never
copied.  Baselines emit ONLY their own object family; recall numbers
for other families are structural zeros, not failures.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bl_common as BL                     # noqa: E402
import b_darvas                            # noqa: E402
import b_tdlines                           # noqa: E402
import b_donchian                          # noqa: E402


def main():
    recs = BL.C.load_tune()
    print("TUNE panels:", len(recs))
    arms = [("darvas_n7", b_darvas.emit),
            ("tdlines_k2", b_tdlines.emit),
            ("donchian_alt", b_donchian.emit)]
    outs = {}
    for tag, fn in arms:
        res = BL.measure(fn, recs)
        outs[tag] = BL.report(tag, res)
    return outs


if __name__ == "__main__":
    main()
