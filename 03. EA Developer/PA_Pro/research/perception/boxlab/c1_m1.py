"""c1_m1.py — run the build lane's _m1.py harness over BOX-LAB arm
pickles, cache-only (R36 §36.6 / R37 §37.5: keep-rule numbers count
only when they come from _m1.py — clutter = median per-panel ratio
INCLUDING LABEL_TF marks, the STABLE=5.00 scale).

_m1.panel_rows(eng_hash, cls, recs, variant) hits CA.run's cache; we
pass a factory that raises on construction so a cache miss fails loud
instead of silently running under the wrong code/params.

Arm -> (variant, hashlabel) map reflects the one-process frozen sweep:
the label fragmented on disk drift, the behaviour did not (params were
frozen at process start, code at import — logged in BOX_LOG).

Usage: python c1_m1.py            # all arms
       python c1_m1.py wd tail6   # subset
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "linelab"))

import common as C                      # noqa: E402
import funnel as F                     # noqa: E402
import engine_v0 as ENG_V0             # noqa: E402
import _m1                             # noqa: E402

# variant -> hash label under which its pickles were stored
ARM_HASH = {
    "base": "b9f968b121629ce6", "leg": "b9f968b121629ce6",
    "wick": "b9f968b121629ce6", "dense": "b9f968b121629ce6",
    "dedup": "b9f968b121629ce6",
    "watch": "ffd74452b8523cbc", "tail": "ffd74452b8523cbc",
    "watchtail": "ffd74452b8523cbc",
    "score": "e62f2dc9ee7fa6e2",
    "all": "3ab5f3aa9d085cc5", "watch_fl": "3ab5f3aa9d085cc5",
    # probe arms at e62f2dc9 (same process as base/score rerun)
    "base_e62": "e62f2dc9ee7fa6e2", "wd": "e62f2dc9ee7fa6e2",
    "tail6": "e62f2dc9ee7fa6e2", "gen": "e62f2dc9ee7fa6e2",
    "wdtail": "e62f2dc9ee7fa6e2",
    # R38 follow-up arms (one process each, params frozen; label =
    # hash at that process's start — drift logged in BOX_LOG)
    "wd_ext": "2ca5c67f620291d8", "wd_ext_fl": "2ca5c67f620291d8",
    "wd_wb": "fd6f9305958f0d08", "wd_kde": "fd6f9305958f0d08",
    "wd_wb_kde": "fd6f9305958f0d08",
    "wd_watch": "1ea3f02a05713d8e", "wd_wait": "1ea3f02a05713d8e",
    "wd_wb_wait": "1ea3f02a05713d8e",
    "wdw_wait": "dd96c5fe49c28d74",
    # build-lane supersede arms (R40 §40.3): own harness, own variant
    # names — measured cache-only from their pickles
    "bxsup_off": "cfb862d40c805a25", "bxsup_on": "cfb862d40c805a25",
    "bxsupp_off": "cfb862d40c805a25", "bxsupp_on": "cfb862d40c805a25",
    # R42 probes on the kept parent (one process, params frozen)
    "p_base": "10c34e28826ef587", "p_dense": "10c34e28826ef587",
    "p_wait": "10c34e28826ef587", "p_wb": "10c34e28826ef587",
    "p_dense_wait": "10c34e28826ef587",
    # R44 §44.3 cong_trigger arms (p2_ = second p-series hash)
    "p2_base": "4dcc44d73e081c02", "p2_cong": "4dcc44d73e081c02",
    "p2_cong_lev": "4dcc44d73e081c02",
    "p2_cong_k3": "4dcc44d73e081c02", "p2_cong_k55": "4dcc44d73e081c02",
    "p2_cong_n8": "4dcc44d73e081c02",
    # R45: post-leak-fix hash — the leak-era 4dcc numbers above are
    # superseded; canonical arms measured on the fixed code
    "p3_base": "df79ade35a496978", "p3_cong": "df79ade35a496978",
    "p3_cong_k55": "df79ade35a496978", "p3_cong_lev": "df79ade35a496978",
    # R46 §46.3: K6 parent + wick-density edge variant
    "p4_base": "0a10080655a4e5de", "p4_dens": "0a10080655a4e5de",
    "p4_base_qh": "13b3f53dcead9fbf", "p4_dens_q": "13b3f53dcead9fbf",
    "p4_base_sh": "5928a0e2b5837aec", "p4_sub": "5928a0e2b5837aec",
    # R49 §49.3: pivot-seeded cong edges (null-tested sources only)
    "p5_base": "edd97b05a3bbfdb5", "p5_pedg": "edd97b05a3bbfdb5",
    "p6_base": "fcd56aafb9e136cd", "p6_pedg": "fcd56aafb9e136cd",
    "p7_base": "91c446777813034a", "p7_pedg": "91c446777813034a",
}
VAR = {"base_e62": "c1r_base",          # second base arm, same variant
       "bxsup_off": "bxsup_off", "bxsup_on": "bxsup_on",
       "bxsupp_off": "bxsupp_off", "bxsupp_on": "bxsupp_on",
       "p2_base": "c1r_p_base", "p2_cong": "c1r_p_cong",
       "p2_cong_lev": "c1r_p_cong_lev",
       "p2_cong_k3": "c1r_p_cong_k3", "p2_cong_k55": "c1r_p_cong_k55",
       "p2_cong_n8": "c1r_p_cong_n8",
       "p3_base": "c1r_p_base", "p3_cong": "c1r_p_cong",
       "p3_cong_k55": "c1r_p_cong_k55", "p3_cong_lev": "c1r_p_cong_lev",
       "p4_base": "c1r_p_base", "p4_dens": "c1r_p_dens",
       "p4_base_qh": "c1r_p_base", "p4_dens_q": "c1r_p_dens_q",
       "p4_base_sh": "c1r_p_base", "p4_sub": "c1r_p_sub",
       "p5_base": "c1r_p_base", "p5_pedg": "c1r_p_pedg",
       "p6_base": "c1r_p_base", "p6_pedg": "c1r_p_pedg",
       "p7_base": "c1r_p_base", "p7_pedg": "c1r_p_pedg"}


class _CacheOnly(Exception):
    pass


def _refuse():
    raise _CacheOnly("no pickle — refusing to run under live code")


def main():
    names = [a for a in sys.argv[1:] if a in ARM_HASH] or \
        list(ARM_HASH)
    recs = C.load_tune()
    v0 = _m1.panel_rows(F.code_hash(F.V0_FILES), ENG_V0.PerceptionEngine,
                        recs, "m1_v0")
    _m1.report("v0", v0)
    for n in names:
        var = VAR.get(n, "c1r_" + n)
        rows = _m1.panel_rows(ARM_HASH[n], _refuse, recs, var)
        _m1.report("arm %s (%s @ %s)" % (n, var, ARM_HASH[n][:8]),
                   rows, v0)


if __name__ == "__main__":
    main()
