"""Statistical gates for the lab: Welch-t, BH-FDR, split-half, per-year."""
import numpy as np
import pandas as pd


def welch_t(x):
    """One-sample Welch t-stat and two-sided p-value (normal approx, df-robust
    enough at our sample sizes)."""
    x = np.asarray(x, dtype=np.float64)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 30:
        return np.nan, np.nan
    m = x.mean()
    s = x.std(ddof=1)
    if s <= 0:
        return np.nan, np.nan
    t = m / (s / np.sqrt(n))
    # two-sided normal p-value (n>=30 -> fine)
    from math import erfc, sqrt
    p = erfc(abs(t) / sqrt(2))
    return t, p


def bh_fdr(pvals):
    """Benjamini-Hochberg q-values, same order as input."""
    p = np.asarray(pvals, dtype=np.float64)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    pv = p[ok]
    m = len(pv)
    if m == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order]
    adj = ranked * m / (np.arange(m) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    out = np.empty(m)
    out[order] = adj
    q[ok] = out
    return q


def split_half(returns, ctms):
    """Same-sign + comparable-magnitude check on first vs second half by time."""
    r = np.asarray(returns, dtype=np.float64)
    t = np.asarray(ctms, dtype=np.int64)
    order = np.argsort(t)
    r = r[order]
    mid = len(r) // 2
    if mid < 15:
        return np.nan, np.nan, np.nan
    a, b = r[:mid], r[mid:]
    ta, _ = welch_t(a)
    tb, _ = welch_t(b)
    return a.mean(), b.mean(), min(ta if not np.isnan(ta) else 0,
                                 tb if not np.isnan(tb) else 0)


def per_year(returns, ctms):
    """Mean return and sign per calendar year."""
    r = np.asarray(returns, dtype=np.float64)
    years = pd.to_datetime(np.asarray(ctms), unit="s", utc=True).year
    out = {}
    for y in sorted(set(years)):
        sel = r[years == y]
        if len(sel):
            out[int(y)] = (round(float(sel.mean()), 3), int(len(sel)))
    return out


def stability_ok(peryear, min_pos_frac=0.7):
    """Fraction of years with positive mean >= threshold."""
    means = [v[0] for v in peryear.values() if v[1] >= 10]
    if len(means) < 4:
        return np.nan
    return sum(1 for m in means if m > 0) / len(means) >= min_pos_frac
