"""Statistics: bootstrap determinism, BH-FDR step-up, DSR falls with trials."""

import numpy as np

import pa_ledger
import pa_stats


def test_bootstrap_ci_deterministic_and_covers_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(0.1, 1.0, size=400)
    a = pa_stats.bootstrap_ci_mean(x, n_boot=2000, seed=7)
    b = pa_stats.bootstrap_ci_mean(x, n_boot=2000, seed=7)
    assert a == b
    lo, hi = a
    assert lo < x.mean() < hi
    c = pa_stats.bootstrap_ci_mean(x, n_boot=2000, seed=8)
    assert c != a                       # seed matters

    p1 = pa_stats.bootstrap_ci_prop(70, 200, n_boot=2000, seed=3)
    assert p1[0] < 0.35 < p1[1]

    d = pa_stats.bootstrap_diff_mean_ci(x, x + 0.5, n_boot=1000, seed=5)
    assert d[1] < -0.2                  # shifted distribution is clearly lower


def test_bh_fdr_stepup():
    p = np.array([0.001, 0.02, 0.04, 0.2, 0.9])
    out = pa_stats.bh_fdr(p, q=0.10)
    q = out["qvalues"]
    assert np.all(q <= 1.0) and np.all(q >= p - 1e-12)
    order = np.argsort(p)
    assert np.all(np.diff(q[order]) >= -1e-12)     # monotone step-up
    assert out["rejected"][0] and not out["rejected"][-1]
    empty = pa_stats.bh_fdr([], q=0.1)
    assert empty["n"] == 0


def test_dsr_falls_as_trial_count_rises():
    rng = np.random.default_rng(11)
    r = rng.normal(0.06, 1.0, size=600)
    sr, T, skew, kurt = pa_stats.sharpe_stats(r)
    assert T == 600 and np.isfinite(sr)
    d2 = pa_stats.deflated_sharpe_ratio(sr, T, skew, kurt, 2)
    d10 = pa_stats.deflated_sharpe_ratio(sr, T, skew, kurt, 10)
    d100 = pa_stats.deflated_sharpe_ratio(sr, T, skew, kurt, 100)
    d10000 = pa_stats.deflated_sharpe_ratio(sr, T, skew, kurt, 10_000)
    assert d2 > d10 > d100 > d10000
    psr0 = pa_stats.probabilistic_sharpe_ratio(sr, T, skew, kurt, 0.0)
    assert d10000 < psr0
    # one trial means no deflation
    assert abs(pa_stats.deflated_sharpe_ratio(sr, T, skew, kurt, 1) - psr0) < 1e-12


def test_dsr_reads_program_trial_count_from_ledger():
    assert pa_stats.program_trial_count(kind="eval") == 0
    for i in range(3):
        pa_ledger.append({"family": "T", "split": "DESIGN", "n": i})
    assert pa_stats.program_trial_count(kind="eval") == 3
    rng = np.random.default_rng(2)
    r = rng.normal(0.05, 1.0, 300)
    sr, T, skew, kurt = pa_stats.sharpe_stats(r)
    assert pa_stats.dsr_with_program_trials(sr, T, skew, kurt) == \
        pa_stats.deflated_sharpe_ratio(sr, T, skew, kurt, 3)
