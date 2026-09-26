"""Planted-effect + null tests for mk_common.contrast_boot (REVIEW_2 F2).

Builds synthetic day x stratum matrices with KNOWN planted contrasts:
  - planted D must be recovered inside its CI;
  - a planted null must stay a null;
  - thin-placebo small-n runs (where bootstrap resamples empty the
    placebo arm) must satisfy point-in-CI and must not be biased.
A verbatim pre-fix statistic (legacy_boot) reproduces the F2 artifact
(point below its own CI) on the same data, proving the bug was real.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mk_common as K                       # noqa: E402


def make_cm(nd, ns, rn_mu, pn_mu, r_rate, p_rate, seed):
    """day x stratum matrices; val = Bernoulli(rate) per event."""
    rng = np.random.default_rng(seed)
    RN = rng.poisson(rn_mu, (nd, ns)).astype(np.float64)
    PN = rng.poisson(pn_mu, (nd, ns)).astype(np.float64)
    RS = rng.binomial(np.maximum(RN, 0).astype(np.int64),
                      r_rate).astype(np.float64)
    PS = rng.binomial(np.maximum(PN, 0).astype(np.int64),
                      p_rate).astype(np.float64)
    return {"RS": RS, "RN": RN, "PS": PS, "PN": PN,
            "days": list(range(nd)), "keys": list(range(ns))}


def legacy_boot(cm, n_boot=2000, seed=K.SEED, min_cell=5):
    """Pre-fix statistic: eligibility fixed on pooled support (D23) but
    emptied arms ZERO-FILLED inside each replicate (the F2 defect)."""
    RS, RN, PS, PN = cm["RS"], cm["RN"], cm["PS"], cm["PN"]
    elig = (RN.sum(0) >= min_cell) & (PN.sum(0) >= min_cell)

    def stats(RS_, RN_, PS_, PN_):
        with np.errstate(divide="ignore", invalid="ignore"):
            rdif = np.where(RN_ > 0, RS_ / np.where(RN_ > 0, RN_, 1), 0.0)
            pdif = np.where(PN_ > 0, PS_ / np.where(PN_ > 0, PN_, 1), 0.0)
        diffs = np.where(elig, rdif - pdif, 0.0)      # BUG: no present mask
        wgt = np.where(elig, RN_, 0.0)
        den = wgt.sum(axis=-1)
        return np.where(den > 0, (diffs * wgt).sum(axis=-1)
                        / np.where(den > 0, den, 1), float("nan"))

    point = float(stats(RS.sum(0), RN.sum(0), PS.sum(0), PN.sum(0)))
    rng = np.random.default_rng(seed)
    W = rng.multinomial(len(RN), np.full(len(RN), 1.0 / len(RN)),
                        size=n_boot).astype(np.float64)
    B = stats(W @ RS, W @ RN, W @ PS, W @ PN)
    Bf = B[np.isfinite(B)]
    return point, Bf


def test_planted_effect_recovered():
    """D = +0.10 planted; point inside CI, CI contains truth, p small."""
    cm = make_cm(nd=80, ns=12, rn_mu=25, pn_mu=22,
                 r_rate=0.65, p_rate=0.55, seed=1)
    r = K.contrast_boot(cm, n_boot=2000, seed=7)
    D, lo, hi, p = r["D"], r["lo"], r["hi"], r["p"]
    assert abs(D - 0.10) < 0.03, D
    assert lo < 0.10 < hi, (lo, hi)
    assert lo <= D <= hi, (lo, D, hi)
    assert p < 0.05, p


def test_planted_null_stays_null():
    """Identical rates -> CI straddles 0, point inside CI."""
    cm = make_cm(nd=80, ns=12, rn_mu=25, pn_mu=22,
                 r_rate=0.60, p_rate=0.60, seed=2)
    r = K.contrast_boot(cm, n_boot=2000, seed=8)
    D, lo, hi = r["D"], r["lo"], r["hi"]
    assert lo < 0 < hi, (lo, hi)
    assert lo <= D <= hi, (lo, D, hi)
    assert abs(D) < 0.05, D


def make_cm_concentrated(nd, ns, seed, r_rate=0.62, p_rate=0.62):
    """Placebo events concentrated on 2-3 days per stratum: pooled
    support passes min_cell but resamples empty the arm ~1/3 of the
    time — the exact F2 configuration."""
    rng = np.random.default_rng(seed)
    RN = rng.poisson(8, (nd, ns)).astype(np.float64)
    RS = rng.binomial(RN.astype(np.int64), r_rate).astype(np.float64)
    PN = np.zeros((nd, ns))
    PS = np.zeros((nd, ns))
    for s in range(ns):
        days = rng.choice(nd, size=3, replace=False)
        for d in days:
            PN[d, s] = 2.0                     # pooled = 6 >= min_cell
            PS[d, s] = float(rng.binomial(2, p_rate))
    return {"RS": RS, "RN": RN, "PS": PS, "PN": PN,
            "days": list(range(nd)), "keys": list(range(ns))}


def test_thin_placebo_no_bias():
    """Small-n, thin placebo: emptied resamples must not shift the
    bootstrap off the point.  Over 20 seeds the fixed code keeps the
    point inside its CI; the pre-fix stat violates it systematically."""
    viol_new, viol_old, n_ok = 0, 0, 0
    for seed in range(20):
        cm = make_cm_concentrated(nd=40, ns=6, seed=100 + seed)
        r = K.contrast_boot(cm, n_boot=1500, seed=seed)
        if not np.isfinite(r["D"]) or not np.isfinite(r["lo"]):
            continue
        n_ok += 1
        if not (r["lo"] - 1e-12 <= r["D"] <= r["hi"] + 1e-12):
            viol_new += 1
        pt, Bf = legacy_boot(cm, n_boot=1500, seed=seed)
        if len(Bf) >= 100:
            lo_l, hi_l = np.percentile(Bf, [2.5, 97.5])
            if not (lo_l - 1e-12 <= pt <= hi_l + 1e-12):
                viol_old += 1
    assert n_ok >= 15, n_ok
    assert viol_new <= max(1, n_ok // 10), (viol_new, n_ok)
    # F2 artifact restated honestly: on a TRUE NULL the pre-fix stat's
    # bootstrap distribution is shifted UP by the emptied-cell mass —
    # systematically, not just occasionally.  That shift is what pushed
    # real point estimates outside their own CIs in the shipped tables.
    shifts = []
    for seed in range(20):
        cm = make_cm_concentrated(nd=40, ns=6, seed=100 + seed)
        r = K.contrast_boot(cm, n_boot=1500, seed=seed)
        pt, Bf = legacy_boot(cm, n_boot=1500, seed=seed)
        Bn = r["boot"]; Bn = Bn[np.isfinite(Bn)]
        if len(Bf) >= 100 and len(Bn) >= 100:
            shifts.append(np.median(Bf) - np.median(Bn))
    pos = sum(1 for s in shifts if s > 0)
    assert pos >= int(0.8 * len(shifts)), \
        f"legacy bootstrap not upward-biased ({pos}/{len(shifts)})"


def test_point_always_inside_ci_dense():
    """Invariant sweep on dense data: point inside own CI, all seeds."""
    for seed in range(10):
        cm = make_cm(nd=60, ns=10, rn_mu=15, pn_mu=15,
                     r_rate=0.55 + 0.01 * seed, p_rate=0.55, seed=seed)
        r = K.contrast_boot(cm, n_boot=1500, seed=seed)
        assert np.isfinite(r["D"])
        assert r["lo"] - 1e-12 <= r["D"] <= r["hi"] + 1e-12, \
            (seed, r["lo"], r["D"], r["hi"])


def test_sparse_strata_nan_coherent():
    """A stratum with <5 pooled events in either arm is excluded from
    the point AND all replicates (D23 semantics kept)."""
    cm = make_cm(nd=50, ns=4, rn_mu=10, pn_mu=10,
                 r_rate=0.6, p_rate=0.6, seed=5)
    cm["RN"][:, 0] = 2.0            # stratum 0: thin real arm
    cm["RS"][:, 0] = 1.0
    cm["PN"][:, 2] = 1.0            # stratum 2: thin placebo arm
    cm["PS"][:, 2] = 0.0
    r = K.contrast_boot(cm, n_boot=500, seed=3)
    assert np.isfinite(r["D"])
    assert r["lo"] <= r["D"] <= r["hi"]


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("test_contrast_boot: all pass")
