"""cache.py — shared bars/ABR/engine-output cache (mandate item 4).

Three layers, all under evalcheck/_cache/:

  * bars(date)   -> (t, cet_min, o, h, l, c) exactly as eval.day_bars
                    returns (pips scale).  Persisted per day as npz.
  * abr(date)    -> causal ABR(50) in pips (linelab/bars_cache.py
                    semantics: rolling mean of last 50 closed ranges).
  * run(tag, cls, rec) -> the finished engine object `e`, pickled,
                    keyed by (engine hash, day, w1).  Bit-identical to
                    a fresh run — `test_cache.py` proves it.

Usage:
    import cache
    t, m, o, h, l, c = cache.bars(rec["date"])
    e = cache.run("v1", engine.PerceptionEngine, rec)   # hash from
                                                          # funnel.code_hash
    python evalcheck/cache.py --bench      # cold-vs-warm timing
"""
import hashlib
import os
import pickle
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402

CACHE = os.path.join(HERE, "_cache")


def _ensure():
    os.makedirs(CACHE, exist_ok=True)


# ------------------------------------------------------------------ #
# bars + ABR (per day)
# ------------------------------------------------------------------ #

def bars(date):
    """eval.day_bars() equivalent, disk-cached.  Returns the same
    tuple (t, cet_min, o, h, l, c) in pips."""
    _ensure()
    f = os.path.join(CACHE, "bars_%s.npz" % date)
    if os.path.exists(f):
        z = np.load(f)
        return (z["t"], z["m"], z["o"], z["h"], z["l"], z["c"])
    t, m, o, h, l, c = EV.day_bars(date)
    np.savez(f, t=t, m=m, o=o, h=h, l=l, c=c)
    return t, m, o, h, l, c


def abr(date, n=50):
    """Causal ABR(n) in pips — same formula as linelab/bars_cache.abr
    (rolling mean of last n closed-bar ranges)."""
    _ensure()
    f = os.path.join(CACHE, "abr%d_%s.npy" % (n, date))
    if os.path.exists(f):
        return np.load(f)
    _t, _m, _o, h, l, _c = bars(date)
    rng = h - l
    out = np.empty(len(rng))
    acc = 0.0
    for i in range(len(rng)):
        acc += rng[i]
        if i >= n:
            acc -= rng[i - n]
        out[i] = acc / min(i + 1, n)
    np.save(f, out)
    return out


# ------------------------------------------------------------------ #
# engine outputs (engine hash, day, w1)
# ------------------------------------------------------------------ #

def run(eng_hash, cls, rec, store=True, variant=""):
    """The finished engine object, keyed by (variant, engine hash, day,
    w1).  Loads the pickle if present; otherwise runs fresh and stores
    it.  store=False skips the pickle write (unpicklable engines).
    `variant` (R14 §14.2) separates paired A/B arms so arm A's runs are
    never served to arm B; the empty variant keeps the old filenames."""
    _ensure()
    w1 = rec["window"]["x1"] or 1439
    f = os.path.join(CACHE, "run_%s%s_%s_%s.pkl"
                     % (variant + "_" if variant else "",
                        eng_hash, rec["date"], w1))
    if os.path.exists(f):
        try:
            with open(f, "rb") as fh:
                return pickle.load(fh)
        except Exception:
            pass            # zero-byte / truncated / stale-class pkl
                            # (R26 §26.4): never serve, re-run fresh
    t, m, o, h, l, c = bars(rec["date"])
    e = EV.run_engine(cls, m, t, o, h, l, c, w1,
                      w0=rec["window"]["x0"])
    if store:
        try:
            with open(f, "wb") as fh:
                pickle.dump(e, fh, protocol=4)
        except (pickle.PicklingError, AttributeError, TypeError):
            pass
    return e


def canonical(e):
    """Deterministic byte string for an engine result: pickled canonical
    form of objects + cand_log + bars.  Used by test_cache.
    R72 s.72.5(b): tuple extended with score / priority / touches so
    identity checks catch arbiter-relevant drift, not just geometry."""
    objs = []
    for o in e.objects:
        objs.append((o.type, o.why, o.t_birth, o.t_left, o.t_right,
                     o.state, o.id, _canon(o.geometry),
                     _canon(o.events),
                     getattr(o, "score", None),
                     getattr(o, "priority", None),
                     _canon(getattr(o, "touches", None))))
    return pickle.dumps((objs, _canon(e.cand_log), list(e.bars)),
                        protocol=4)


def _canon(x):
    if isinstance(x, dict):
        return {k: _canon(v) for k, v in sorted(x.items(),
                                                key=lambda kv:
                                                str(kv[0]))}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    return x


# ------------------------------------------------------------------ #
# benchmark: cold vs warm full eval
# ------------------------------------------------------------------ #

def _bench():
    import engine as ENG_V1
    import engine_v0 as ENG_V0
    from funnel import code_hash, V0_FILES, V1_FILES
    recs = C.load_tune()
    hashes = {"v0": code_hash(V0_FILES), "v1": code_hash(V1_FILES)}

    # warm bars+abr first (they feed both runs)
    for r in recs:
        bars(r["date"])
        abr(r["date"])

    def sweep(warm):
        t0 = time.time()
        for tag, cls in (("v0", ENG_V0.PerceptionEngine),
                         ("v1", ENG_V1.PerceptionEngine)):
            for rec in recs:
                if warm:
                    run(hashes[tag], cls, rec)
                else:
                    t, m, o, h, l, c = bars(rec["date"])
                    w1 = rec["window"]["x1"] or 1439
                    EV.run_engine(cls, m, t, o, h, l, c, w1,
                                  w0=rec["window"]["x0"])
        return time.time() - t0

    cold = sweep(warm=False)
    # populate cache
    sweep(warm=True)
    warm = sweep(warm=True)
    print("bars+ABR cache files:", len(os.listdir(CACHE)))
    print("cold 2x198 engine runs: %.1fs" % cold)
    print("warm 2x198 engine runs: %.1fs" % warm)
    print("speed-up: %.1fx" % (cold / max(warm, 1e-9)))


if __name__ == "__main__":
    if "--bench" in sys.argv:
        _bench()
