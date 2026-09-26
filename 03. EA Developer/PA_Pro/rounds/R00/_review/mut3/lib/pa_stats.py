"""pa_stats — bootstrap CIs, BH-FDR and the Deflated Sharpe Ratio.

Sources / formulas
------------------
- Bootstrap: percentile method, seeded (``numpy.random.default_rng``).
- BH-FDR: Benjamini & Hochberg (1995), step-up q-values
  ``q_(i) = min_{j>=i} p_(j) * n / j``.
- Deflated Sharpe Ratio (DSR): Bailey, D. H. & Lopez de Prado, M. (2014),
  "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest
  Overfitting, and Non-Normality", Journal of Portfolio Management 40(5).

  ``PSR(SR*) = Phi[ (SR_hat - SR*) * sqrt(T - 1)
                    / sqrt(1 - skew*SR_hat + (kurt-1)/4 * SR_hat^2) ]``

  with ``SR_hat`` non-annualised, ``skew`` = Pearson skewness and ``kurt`` =
  Pearson kurtosis (normal = 3), ``T`` = number of observations.

  ``DSR = PSR(SR0)`` where the expected maximum Sharpe under the null of N
  independent trials is

  ``SR0 = sqrt(V[SR_hat]) * ( (1 - euler) * Phi^-1(1 - 1/N)
                              + euler * Phi^-1(1 - 1/(N*e)) )``

  ``euler = 0.5772156649``, ``e = 2.718281828``.  When the caller does not
  supply ``V[SR_hat]`` the estimator variance is used:
  ``V = (1 - skew*SR_hat + (kurt-1)/4 * SR_hat^2) / (T - 1)``.  ``N < 2``
  deflates to ``SR0 = 0`` (no selection).
"""

import math

import numpy as np
from scipy.stats import norm

__all__ = [
    "bootstrap_ci_mean", "bootstrap_ci_prop", "bootstrap_diff_mean_ci",
    "bootstrap_diff_prop_ci", "bh_fdr", "sharpe_stats",
    "probabilistic_sharpe_ratio", "deflated_sharpe_ratio", "mean_t",
    "program_trial_count", "dsr_with_program_trials",
]

EULER = 0.5772156649015329
E = math.e


def _boot_means(x, n_boot, rng, chunk=256):
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    out = np.empty(n_boot, dtype=np.float64)
    done = 0
    while done < n_boot:
        m = min(chunk, n_boot - done)
        idx = rng.integers(0, n, size=(m, n))
        out[done:done + m] = x[idx].mean(axis=1)
        done += m
    return out


def bootstrap_ci_mean(x, n_boot=10000, alpha=0.05, seed=20260920):
    """Percentile bootstrap CI for the mean.  Returns (lo, hi)."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return (float("nan"), float("nan"))
    if x.size == 1:
        return (float(x[0]), float(x[0]))
    rng = np.random.default_rng(seed)
    means = _boot_means(x, int(n_boot), rng)
    lo, hi = np.percentile(means, [100.0 * alpha / 2, 100.0 * (1 - alpha / 2)])
    return float(lo), float(hi)


def bootstrap_ci_prop(wins, n, n_boot=10000, alpha=0.05, seed=20260920):
    """Percentile bootstrap CI for a proportion (Wins of n).  Returns (lo, hi)."""
    n = int(n)
    if n <= 0:
        return (float("nan"), float("nan"))
    x = np.zeros(n, dtype=np.float64)
    x[: int(wins)] = 1.0
    return bootstrap_ci_mean(x, n_boot=n_boot, alpha=alpha, seed=seed)


def bootstrap_diff_mean_ci(a, b, n_boot=10000, alpha=0.05, seed=20260920):
    """Percentile bootstrap CI for mean(a) - mean(b), independent resampling."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.size == 0 or b.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    da = _boot_means(a, int(n_boot), rng)
    db = _boot_means(b, int(n_boot), rng, chunk=256)
    d = da - db
    lo, hi = np.percentile(d, [100.0 * alpha / 2, 100.0 * (1 - alpha / 2)])
    return float(lo), float(hi)


def bootstrap_diff_prop_ci(k1, n1, k2, n2, n_boot=10000, alpha=0.05,
                           seed=20260920):
    """Percentile bootstrap CI for p1 - p2 (proportions)."""
    n1, n2 = int(n1), int(n2)
    if n1 <= 0 or n2 <= 0:
        return (float("nan"), float("nan"))
    a = np.zeros(n1, dtype=np.float64)
    a[: int(k1)] = 1.0
    b = np.zeros(n2, dtype=np.float64)
    b[: int(k2)] = 1.0
    return bootstrap_diff_mean_ci(a, b, n_boot=n_boot, alpha=alpha, seed=seed)


def bh_fdr(pvalues, q=0.10):
    """Benjamini-Hochberg step-up.  Returns dict with qvalues/rejected."""
    p = np.asarray(pvalues, dtype=np.float64)
    n = p.shape[0]
    if n == 0:
        return {"qvalues": p, "rejected": np.zeros(0, dtype=bool), "q": q, "n": 0}
    order = np.argsort(p, kind="stable")
    ranked = p[order]
    qv = ranked * n / (np.arange(n) + 1)
    qv = np.minimum.accumulate(qv[::-1])[::-1]
    qv = np.clip(qv, 0.0, 1.0)
    out = np.empty(n, dtype=np.float64)
    out[order] = qv
    return {"qvalues": out, "rejected": out <= q, "q": float(q), "n": int(n)}


def mean_t(x):
    """(mean, t) of the sample mean; t=None when undefined (n<2 or zero sd)."""
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    if n == 0:
        return float("nan"), None
    m = float(x.mean())
    if n < 2:
        return m, None
    sd = float(x.std(ddof=1))
    if sd == 0.0 or not np.isfinite(sd):
        return m, None
    return m, float(m / (sd / math.sqrt(n)))


def sharpe_stats(r):
    """(SR, T, skew, kurt) of a return series; SR non-annualised, kurt Pearson."""
    r = np.asarray(r, dtype=np.float64)
    T = r.shape[0]
    if T < 2:
        return float("nan"), T, float("nan"), float("nan")
    sd = r.std(ddof=1)
    if sd == 0:
        return float("nan"), T, float("nan"), float("nan")
    sr = float(r.mean() / sd)
    z = (r - r.mean()) / sd
    skew = float((z ** 3).mean())
    kurt = float((z ** 4).mean())
    return sr, T, skew, kurt


def probabilistic_sharpe_ratio(sr, T, skew, kurt, sr_star=0.0):
    """PSR(SR*) per Bailey & Lopez de Prado (2014), eq. for non-normal returns."""
    if T is None or T < 2 or sr is None or not np.isfinite(sr):
        return float("nan")
    var_term = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if var_term <= 0 or not np.isfinite(var_term):
        return float("nan")
    z = (sr - sr_star) * math.sqrt(T - 1) / math.sqrt(var_term)
    return float(norm.cdf(z))


def deflated_sharpe_ratio(sr, T, skew, kurt, n_trials, sr_var=None):
    """DSR = PSR(SR0) with SR0 the expected max Sharpe over ``n_trials``."""
    if T is None or T < 2 or sr is None or not np.isfinite(sr):
        return float("nan")
    n = int(n_trials)
    if n < 2:
        sr0 = 0.0
    else:
        if sr_var is None:
            v = (1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr) / (T - 1.0)
        else:
            v = float(sr_var)
        v = max(v, 0.0)
        z1 = norm.ppf(1.0 - 1.0 / n)
        z2 = norm.ppf(1.0 - 1.0 / (n * E))
        sr0 = math.sqrt(v) * ((1.0 - EULER) * z1 + EULER * z2)
    return probabilistic_sharpe_ratio(sr, T, skew, kurt, sr_star=sr0)


def program_trial_count(kind="eval", include_error=False):
    """Program-level trial count read from the append-only ledger."""
    import pa_ledger

    return pa_ledger.count_trials(kind=kind, include_error=include_error)


def dsr_with_program_trials(sr, T, skew, kurt, kind="eval", sr_var=None):
    """DSR deflated by the program trial count currently in the ledger."""
    return deflated_sharpe_ratio(sr, T, skew, kurt,
                                 program_trial_count(kind=kind), sr_var=sr_var)
