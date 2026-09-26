"""engine_runs — run v0/v1 engines per TUNE panel, cache cand_log.

BOX-LAB local cache of finished engine objects (same keying scheme as
evalcheck/cache.py but stored under boxlab/cache/runs/).  Read-only import
of eval.py + both engines; a pa_slots slot is held for the sweep and the
process runs BelowNormal via pa_slots import side effect.
"""
import os
import pickle
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
_EVALC = os.path.join(_PERC, "evalcheck")
for _p in (_EVALC, _PERC, os.path.join(_PERC, "golden"),
           os.path.join(_PERC, "..", "..", "lib")):
    if _p not in sys.path:
        sys.path.insert(0, os.path.abspath(_p))

import pa_slots                     # noqa: E402  BelowNormal + thread caps
import eval as EV                   # noqa: E402
import common as C                  # noqa: E402
import funnel as FN                 # noqa: E402

RUNS = os.path.join(_HERE, "cache", "runs")


def run_cached(tag, cls, rec):
    w1 = rec["window"]["x1"] or 1439
    os.makedirs(RUNS, exist_ok=True)
    f = os.path.join(RUNS, "%s_%s_%d.pkl" % (tag, rec["date"], w1))
    if os.path.exists(f):
        with open(f, "rb") as fh:
            return pickle.load(fh)
    t, m, o, h, l, c = EV.day_bars(rec["date"])
    e = EV.run_engine(cls, m, t, o, h, l, c, w1)
    with open(f, "wb") as fh:
        pickle.dump(e, fh, protocol=4)
    return e


def sweep():
    import engine as ENG_V1
    import engine_v0 as ENG_V0
    recs = C.load_tune()
    hashes = {"v0": FN.code_hash(FN.V0_FILES),
              "v1": FN.code_hash(FN.V1_FILES)}
    print("engine hashes:", hashes)
    with pa_slots.slot("boxlab engine sweep", timeout=3600):
        for tag, cls in (("v0", ENG_V0.PerceptionEngine),
                         ("v1", ENG_V1.PerceptionEngine)):
            for i, rec in enumerate(recs):
                run_cached(tag, cls, rec)
                if i % 40 == 0:
                    print(tag, i, flush=True)
    print("done")


if __name__ == "__main__":
    sweep()
