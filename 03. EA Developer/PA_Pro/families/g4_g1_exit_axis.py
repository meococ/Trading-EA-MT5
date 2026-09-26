"""g4_g1_exit_axis.py — SF02 G4 (rung 3): exit-axis variant of G1.

Identical entry logic to g1_htf_pullback v2 (imported verbatim — the
mandate: "change only the S and tp_mult grid, never the entry logic").
The grid sweeps tp_mult x S_pips to measure whether the exit axis —
fixed-R TP vs intraday flats — is the binding constraint on the G1
entry.  Autopsy A1 showed TP-reach collapses as S and tp grow (flats);
A2 showed positive exit-free edge dies at the exits for momentum
families.  G4 asks the same question for the pullback entry.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import g1_htf_pullback as g1   # noqa: E402

FAMILY = "g4_g1_exit_axis"
ROUND = "SF02"
SYMBOLS = g1.SYMBOLS
DEFAULTS = g1.DEFAULTS
PAIRED_RANDOM = True                      # same LIMIT-order baseline

# exit-axis grid: 2 S rungs x 3 tp_mult x 2 gen x 2 tr_src = 24 cells
GRID = {
    "S_pips": [18.0, 55.0],
    "tp_mult": [1.0, 2.0, 3.0],
    "gen": ["line1_cluster", "sd_base"],
    "tr_src": ["h1", "h4"],
}


def spec_dict(params=None):
    p = dict(g1.DEFAULTS)
    p.update(params or {})
    s = g1.spec_dict(p)
    s["family"] = FAMILY
    s["version"] = "g4-v1"
    s["grid"] = {k: list(v) for k, v in GRID.items()}
    s["engine"]["tp_mult"] = p["tp_mult"]
    return s


entries_fn = g1.entries_fn


def paired_random_entries(symbol, bars, spec, K=20, seed=20260921):
    return g1.paired_random_entries(symbol, bars, spec, K=K, seed=seed)


def make_spec(params=None, **extra):
    s = spec_dict(params)
    s.update(s["engine"])
    s["entries_fn"] = entries_fn
    for k, v in extra.items():
        s[k] = v
    return s


# detector cache is per-family-module; share g1's
detect = g1.detect
