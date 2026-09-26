"""Symbol-decode round trip across all four analyzers (REVIEW_2 F3).

Each module's key_ints encodes the symbol index at a module-specific
coefficient (M3: 2772 incl. approach decile; M5: 2772 / x3=8316 with the
slope class; M4/M4b: 252 / x3=756 with the height tercile).
run_contrast must decode with the SAME factor.  We assert:
  - every module round-trips all 4 symbols under its declared factor;
  - the pre-fix factors (2772/8316 on M4 keys) collapse everything to
    EURUSD — demonstrating the F3 failure mode.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mk_common as K                                   # noqa: E402
import mk_m3_analyze as A3                              # noqa: E402
import mk_m4_analyze as A4                              # noqa: E402
import mk_m4b_analyze as A4b                            # noqa: E402
import mk_m5_analyze as A5                              # noqa: E402

SYM_I = A3.SYM_I


def _d(n=40, seed=0, with_hgt=True, with_slope=True, with_app=True):
    rng = np.random.default_rng(seed)
    d = {"side": rng.choice([-1, 1], n).astype(np.float64),
         "dow": rng.integers(0, 5, n).astype(np.float64),
         "utc_min": rng.integers(0, 1440, n).astype(np.float64),
         "abr": np.abs(rng.normal(1.0, 0.3, n)) + 0.2}
    if with_app:
        d["approach_atr"] = np.abs(rng.normal(2.0, 1.0, n))
    if with_hgt:
        d["hgt_abr"] = np.abs(rng.normal(5.0, 2.0, n))
    if with_slope:
        d["slope_abr"] = rng.normal(0.0, 0.02, n)
    return d


QA = np.quantile(np.abs(np.random.default_rng(1).normal(1, .3, 500)) + .2,
                 [0, 1 / 3, 2 / 3, 1.0])
QP = np.quantile(np.abs(np.random.default_rng(2).normal(2, 1, 500)),
                 np.linspace(0, 1, 11))
QH = np.quantile(np.abs(np.random.default_rng(3).normal(5, 2, 500)),
                 [0, 1 / 3, 2 / 3, 1.0])


def test_m3_decode_roundtrip():
    for sym, si in SYM_I.items():
        k = A3.key_ints(_d(), sym, QA, QP)
        assert (k // A3.SYM_FACTOR == si).all(), sym


def test_m5_decode_roundtrip():
    for sym, si in SYM_I.items():
        k = A5.key_ints(_d(), sym, QA, QP, slope_in_key=False)
        assert (k // 2772 == si).all(), sym
        ks = A5.key_ints(_d(), sym, QA, QP, slope_in_key=True)
        assert (ks // 8316 == si).all(), sym


def test_m4_decode_roundtrip():
    for sym, si in SYM_I.items():
        k = A4.key_ints(_d(), sym, QA)                  # no hgt -> 252
        assert (k // 252 == si).all(), sym
        kh = A4.key_ints(_d(with_hgt=True), sym, QA, QH)  # hgt -> 756
        assert (kh // 756 == si).all(), sym


def test_m4b_decode_roundtrip():
    for sym, si in SYM_I.items():
        k = A4b.key_ints(_d(), sym, QA)
        assert (k // 252 == si).all(), sym
        kh = A4b.key_ints(_d(with_hgt=True), sym, QA, QH)
        assert (kh // 756 == si).all(), sym


def test_old_factors_collapse_to_eurusd():
    """Pre-fix decode (2772/8316 on M4 keys) maps every symbol to 0 —
    this is exactly the F3 artifact the reviewer found."""
    for sym in SYM_I:
        k = A4.key_ints(_d(), sym, QA)
        assert (k // 2772 == 0).all()          # everything = EURUSD
        kh = A4b.key_ints(_d(with_hgt=True), sym, QA, QH)
        assert (kh // 8316 == 0).all()


def test_no_key_overflow_ambiguity():
    """Symbol coefficient must exceed the max pre-symbol key mass so the
    decode is unambiguous (k < 252*si_lower encodings never alias)."""
    for sym, si in SYM_I.items():
        k = A4.key_ints(_d(n=400, seed=7), sym, QA)
        rem = k - 252 * si
        assert (rem >= 0).all() and (rem < 252).all(), sym


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("test_decode: all pass")
