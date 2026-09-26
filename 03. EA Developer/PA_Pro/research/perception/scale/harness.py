"""harness.py — shared SCALE-lane machinery (R37).

Everything here imports the engine ONLY from the frozen snapshot
``scale/engine_e62f2dc9/`` (R36 §36.7: the live files keep moving).
``get_engine`` hard-asserts that every engine module was resolved from
inside the snapshot dir — the wall is in code, not in convention.

Arms:
  STABLE — params_stable.json (every C-round flag OFF; verified equal to
           9283b389 on cached TUNE runs, see verify_stable.py);
  KEPT   — params_v1_1.json as snapshotted (line.lab_score ON, the only
           keep in C1_M1.md at snapshot time).

Feed: DESIGN runs pass feed="DESIGN" (engine derives cet_min =
server-1 h, the verified DESIGN-feed offset, D3).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
# C-round-2 resume (R48 §48.4): the snapshot under test is selectable —
# SCALE_SNAP names the dir under scale/ (default: the C-round-1
# snapshot).  Arm C1 = engine_9acaa206 + its params_v1_1.json defaults
# (K1-K6 ON); arm V1 = engine_e62f2dc9 + params_stable.json (=9283b389).
SNAP = os.path.abspath(os.path.join(
    HERE, os.environ.get("SCALE_SNAP", "engine_e62f2dc9")))

sys.path.insert(0, HERE)
import design_loader as DL                        # noqa: E402

FAMILY = {   # eval.py's family map, duplicated (evalcheck is read-only)
    "BOX": "box", "RANGE_OPEN": "box", "CONTEXT_RANGE": "box",
    "PATTERN_LINE": "line", "CONTEXT_LINE": "line",
    "LEVEL_CARRIED": "level", "MINI_LEVEL": "level",
    "BRACKET": "bracket", "SQUEEZE": "squeeze",
    "LABEL_TF": "annot", "BAR_MARKER": "annot",
}
FAMILIES = ("box", "line", "level", "bracket", "squeeze", "annot")
ANNOT = {"LABEL_TF", "BAR_MARKER"}

# the book's three panel windows, CET minutes — the same partition the
# engine's own level.session_windows_cet parameter encodes
SESSIONS = (("asia", 0, 480), ("eu", 480, 840), ("us", 840, 1140))

# object events that LOG an edge move (spec §6.1 "except logged
# re-anchors"); everything else that changes an edge sig is unlogged.
# asia_convert finalises a still-forming RANGE_OPEN's edges into a BOX
# (boxes.py:755) — a logged type+edge transition, not a frozen-edge move.
LOGGED_MOVE = {"re_anchor", "reprice", "tighten", "refit",
               "asia_convert"}

_eng_mod = None


def get_engine():
    """The snapshot engine module (imported once, path-asserted)."""
    global _eng_mod
    if _eng_mod is None:
        if SNAP not in sys.path:
            sys.path.insert(0, SNAP)
        # a stale live-tree module under these names would silently
        # bind; refuse rather than run the wrong code
        for name in ("engine", "boxes", "lines", "levels", "patterns",
                     "salience", "swings", "gates", "cet"):
            mod = sys.modules.get(name)
            if mod is not None and \
                    not os.path.abspath(getattr(mod, "__file__", SNAP)
                                        ).startswith(SNAP):
                raise RuntimeError(
                    "module %r already imported from %s — not the "
                    "snapshot" % (name, mod.__file__))
        import engine as E
        import cet                                    # noqa: F401
        for name in ("engine", "boxes", "lines", "levels", "patterns",
                     "salience", "swings", "gates", "cet"):
            f = os.path.abspath(sys.modules[name].__file__)
            assert f.startswith(SNAP), (name, f)
        _eng_mod = E
    return _eng_mod


def make_engine(arm, feed="DESIGN"):
    """Fresh snapshot engine for one arm.  cand_log stays off at scale
    (the audit channel is not needed for drawing statistics)."""
    E = get_engine()
    pfile = ("params_stable.json" if arm in ("STABLE", "V1")
             else "params_v1_1.json")
    params = E.load_params(os.path.join(SNAP, pfile))
    return E.PerceptionEngine(params=params, feed=feed)


def edge_sig(o):
    """The drawn-edge signature of one object: only the fields a chart
    would show.  Internal bookkeeping keys (_far_n, sali, broke, ...)
    are deliberately excluded — they are not ink."""
    g = o.geometry
    t = o.type
    if t in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE", "SQUEEZE"):
        return (t, round(g.get("top", 0), 3), round(g.get("bottom", 0), 3))
    if t in ("PATTERN_LINE", "CONTEXT_LINE"):
        return (t, round(g.get("p0", 0), 3), round(g.get("slope", 0), 6),
                g.get("t0"))
    if t in ("LEVEL_CARRIED", "MINI_LEVEL"):
        return (t, round(g.get("price", 0), 3))
    if t == "BRACKET":
        return (t, round(g.get("level", 0), 3), g.get("letter"))
    if t in ("LABEL_TF", "BAR_MARKER", "FALSE_EXT"):
        return (t, round(g.get("price", 0), 3), g.get("letter"),
                g.get("side"))
    return (t,)


def live_sigs(e):
    """{oid: edge_sig} for objects drawn on the chart right now."""
    return {o.id: edge_sig(o) for o in e.objects
            if o.state == "ACTIVE"}


def session_of(cet_min):
    for name, lo, hi in SESSIONS:
        if lo <= cet_min < hi:
            return name
    return "other"


def run_bars(e, t, m, o, h, l, c, on_bar=None):
    """Feed bars into engine e (absolute prices).  on_bar(i, e) is
    called after each update for stat collection."""
    for j in range(len(t)):
        e.update(int(t[j]), float(o[j]), float(h[j]), float(l[j]),
                 float(c[j]), cet_min=int(m[j]))
        if on_bar is not None:
            on_bar(j, e)
    return e


def canon_bytes(e):
    """Deterministic byte form of a finished run (evalcheck canonical
    semantics: objects + cand_log + bars)."""
    import pickle

    def cn(x):
        if isinstance(x, dict):
            return {k: cn(v) for k, v in sorted(x.items(),
                                                key=lambda kv: str(kv[0]))}
        if isinstance(x, (list, tuple)):
            return [cn(v) for v in x]
        if isinstance(x, np.generic):
            return x.item()
        if isinstance(x, np.ndarray):
            return x.tolist()
        return x
    objs = [(o.type, o.why, o.t_birth, o.t_left, o.t_right, o.state,
             o.id, cn(o.geometry), cn(o.events)) for o in e.objects]
    return pickle.dumps((objs, cn(e.cand_log), list(e.bars)),
                        protocol=4)
