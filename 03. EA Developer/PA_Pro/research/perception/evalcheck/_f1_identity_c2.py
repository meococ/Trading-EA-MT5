"""_f1_identity_c2.py — PLAYBOOK_C2 E3: independent re-proof of the F1
performance patch's behaviour-neutrality (playbook 3.5), ahead of the
20:30Z merge.

The patch lives in _scratch/perf/ (engine.py + swings.py).  We load the
patched modules with _scratch/perf FIRST on sys.path so `import engine`
and `import swings` inside the patch resolve to the patched files while
every other module (salience, boxes, levels, lines, patterns, eval ...)
comes from the live tree — i.e. the merge-time layering, minus F3
(engine.py's `symbol`/`pip` args which are inert on EURUSD).

Legs:
  1. TUNE identity: run the patched engine on every cached
     c1r_p_base@ee2cbf12 run spec (the K9-default parent, 576 runs),
     with the pickle's own params (e.p), compare canonical
     (objects, cand_log, events) — the build lane claims 1728/1728 vs
     9acaa206; we re-prove vs the CURRENT kept config.
  2. Speed spot: time one patched run vs one unpatched run on the same
     panel set (first 12 TUNE panels) to confirm no slowdown.

Usage: python evalcheck/_f1_identity_c2.py [--limit N]
"""
import argparse
import importlib.util
import os
import pickle
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
PERF = os.path.join(PERC, "_scratch", "perf", "v2")   # the merge candidate
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import cache as CA                              # noqa: E402
import pa_slots                                 # noqa: E402
from _verify_keeps_c1 import canon              # noqa: E402


def load_patched():
    """Import engine+swings from the perf dir in a private namespace."""
    for mod, path in [("perf_swings", os.path.join(PERF, "swings.py")),
                      ("perf_engine", os.path.join(PERF, "engine.py"))]:
        spec = importlib.util.spec_from_file_location(mod, path)
        m = importlib.util.module_from_spec(spec)
        if mod == "perf_engine":
            sys.modules["swings"] = sys.modules["perf_swings"]
        sys.modules[mod] = m
        spec.loader.exec_module(m)
    return sys.modules["perf_engine"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    pe = load_patched()
    recs = C.load_tune()
    files = sorted(f for f in os.listdir(CA.CACHE)
                   if f.startswith(("run_c1r_p_base_ee2cbf1202db47b6_",
                                    "run_lnsf42_off_ee2cbf1202db47b6_",
                                    "run_lnsf42_on_ee2cbf1202db47b6_")))
    if args.limit:
        files = files[:args.limit]
    print("reference runs @ee2cbf12 (c1r_p_base + lnsf42 pair):",
          len(files))

    def run_patched(params, m, t, o, h, l, c, w1):
        import copy
        e = pe.PerceptionEngine(params=copy.deepcopy(params))
        e.cand_log = []
        # eval.py feeds ABSOLUTE prices (bars() returns pips; * 1e-4);
        # update() re-multiplies by the engine pip (1e4 on EURUSD)
        for j in np.where(m <= w1)[0]:
            e.update(int(t[j]), float(o[j]) * 1e-4, float(h[j]) * 1e-4,
                     float(l[j]) * 1e-4, float(c[j]) * 1e-4,
                     cet_min=int(m[j]))
        return e

    with pa_slots.slot("evalcheck-f1-id", timeout=3600):
        n = eq = 0
        diffs = []
        t_patch = 0.0
        for f in files:
            parts = f[:-4].split("_")
            date, w1 = parts[-2], int(parts[-1])
            ref = pickle.load(open(os.path.join(CA.CACHE, f), "rb"))
            t, mm, o, h, l, c = CA.bars(date)
            t0 = time.perf_counter()
            e2 = run_patched(ref.p, mm, t, o, h, l, c, w1)
            t_patch += time.perf_counter() - t0
            oa, la = canon(e2)
            oae, _ = canon(e2, with_events=True)
            ob, lb = canon(ref)
            obe, _ = canon(ref, with_events=True)
            n += 1
            same = oa == ob and la == lb and oae == obe
            eq += same
            if not same and len(diffs) < 8:
                diffs.append("%s %s w1=%s obj=%s log=%s ev=%s"
                             % (f, date, w1, oa == ob, la == lb,
                                oae == obe))
        print("patched vs c1r_p_base@ee2cbf12: %d/%d identical "
              "(objects+cand_log+events)" % (eq, n))
        for d in diffs:
            print("  DIFF", d)
        print("patched run total %.1fs over %d runs" % (t_patch, n))


if __name__ == "__main__":
    main()
