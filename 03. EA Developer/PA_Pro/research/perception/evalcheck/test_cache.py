"""test_cache.py — cache must be bit-identical to a fresh run.

Checks:
  * cache.bars(date) == eval.day_bars(date) element-wise, dtypes incl.
  * cache.abr(date) == the linelab rolling-mean formula;
  * cache.run(hash, cls, rec) == a fresh EV.run_engine() — canonical
    pickle bytes of (objects, cand_log, bars) identical.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import cache                                    # noqa: E402
from funnel import code_hash, V0_FILES, V1_FILES  # noqa: E402

recs = C.load_tune()[:6]

import engine as ENG_V1                        # noqa: E402
import engine_v0 as ENG_V0                     # noqa: E402

HASH = {"v0": code_hash(V0_FILES), "v1": code_hash(V1_FILES)}

# --- bars + ABR ------------------------------------------------------
for rec in recs:
    d = rec["date"]
    fresh = EV.day_bars(d)
    warm = cache.bars(d)
    for i, name in enumerate(("t", "m", "o", "h", "l", "c")):
        assert fresh[i].dtype == warm[i].dtype, (d, name)
        assert np.array_equal(fresh[i], warm[i]), (d, name)
    fresh_abr = cache.abr(d)
    rng = fresh[3] - fresh[4]                   # h - l in pips
    n = 50
    ref = np.empty(len(rng))
    acc = 0.0
    for i in range(len(rng)):
        acc += rng[i]
        if i >= n:
            acc -= rng[i - n]
        ref[i] = acc / min(i + 1, n)
    assert np.array_equal(fresh_abr, ref), d
print("bars+ABR bit-identical on %d days" % len(recs))

# --- engine outputs ---------------------------------------------------
for tag, cls in (("v0", ENG_V0.PerceptionEngine),
                 ("v1", ENG_V1.PerceptionEngine)):
    for rec in recs:
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        w1 = rec["window"]["x1"] or 1439
        fresh = EV.run_engine(cls, m, t, o, h, l, c, w1)
        warm = cache.run(HASH[tag], cls, rec)
        a = cache.canonical(fresh)
        b = cache.canonical(warm)
        assert a == b, (tag, rec["id"], "canonical bytes differ")
        assert len(fresh.objects) == len(warm.objects)
        assert len(fresh.cand_log) == len(warm.cand_log)
    print("%s engine-output cache bit-identical on %d panels"
          % (tag, len(recs)))

# --- variant is part of the run-cache key (R14 §14.2) ---------------
# in a throwaway cache dir so the shared cache is not polluted
import tempfile                                   # noqa: E402
rec = recs[0]
h = HASH["v0"]
with tempfile.TemporaryDirectory() as td:
    real = cache.CACHE
    cache.CACHE = td
    try:
        base = cache.run(h, ENG_V0.PerceptionEngine, rec)
        armA = cache.run(h, ENG_V0.PerceptionEngine, rec,
                         variant="armA")
        assert cache.canonical(base) == cache.canonical(armA), \
            "same engine under variant key must be identical"
        f_base = os.path.join(
            td, "run_%s_%s_%s.pkl"
            % (h, rec["date"], rec["window"]["x1"] or 1439))
        f_armA = os.path.join(
            td, "run_armA_%s_%s_%s.pkl"
            % (h, rec["date"], rec["window"]["x1"] or 1439))
        assert os.path.exists(f_base) and os.path.exists(f_armA), \
            "variant run must land on its own cache file"
        # arm B must never be served arm A's pickle: a second arm-B
        # run hits its own file (mtime unchanged if not rewritten)
        import time
        t0 = os.path.getmtime(f_armA)
        time.sleep(0.02)
        cache.run(h, ENG_V0.PerceptionEngine, rec, variant="armB")
        f_armB = os.path.join(
            td, "run_armB_%s_%s_%s.pkl"
            % (h, rec["date"], rec["window"]["x1"] or 1439))
        assert os.path.exists(f_armB), "armB must write its own file"
        assert os.path.getmtime(f_armA) == t0, \
            "armB run must not touch armA's cache file"
    finally:
        cache.CACHE = real
print("variant cache key separates A/B arms")

print("\nALL CACHE TESTS PASSED")
