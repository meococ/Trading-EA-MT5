"""Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) — dependency-free.

Lane-local copy; canonical: `02. AlphaFactory/tools/research/dsr.py`.

Per-trade Sharpe convention: SR = mean(net_R)/std(net_R) over n trades.
PSR(SR*) = Phi( (SR - SR*) * sqrt(n-1) / sqrt(1 - skew*SR + (kurt-1)/4 * SR^2) )
DSR = PSR evaluated at SR* = E[max SR over N trials]
E[max SR] = sqrt(V[{SR}]) * ((1-gamma)*ppf(1-1/N) + gamma*ppf(1-1/(N*e)))
with gamma = Euler-Mascheroni. Self-test: N=1000, V=1 -> E[max SR] ~ 3.2554.
"""

from __future__ import annotations

import math

EULER_GAMMA = 0.5772156649015329


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Acklam's rational approximation (|error| < 1.15e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def expected_max_sharpe(var_sr_trials: float, n_trials: int) -> float:
    if n_trials < 2 or var_sr_trials <= 0:
        return 0.0
    return math.sqrt(var_sr_trials) * (
        (1 - EULER_GAMMA) * norm_ppf(1 - 1.0 / n_trials)
        + EULER_GAMMA * norm_ppf(1 - 1.0 / (n_trials * math.e))
    )


def psr(sr: float, sr_star: float, n_obs: int, skew: float, kurt: float) -> float:
    """Probabilistic Sharpe Ratio; kurt is NON-excess (normal = 3)."""
    if n_obs < 3:
        return 0.0
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 0:
        return 0.0
    return norm_cdf((sr - sr_star) * math.sqrt(n_obs - 1.0) / math.sqrt(denom))


def dsr(sr: float, n_obs: int, skew: float, kurt: float,
        var_sr_trials: float, n_trials: int) -> float:
    return psr(sr, expected_max_sharpe(var_sr_trials, n_trials), n_obs, skew, kurt)


if __name__ == "__main__":
    em = expected_max_sharpe(1.0, 1000)
    assert abs(em - 3.2554) < 0.01, em
    assert abs(norm_cdf(0.0) - 0.5) < 1e-12
    assert abs(norm_ppf(0.975) - 1.959964) < 1e-5
    print(f"SELF-TEST PASS  E[maxSR|N=1000,V=1]={em:.4f}")
