"""Mechanism-neutral metrics over per-trade R series.

Inputs are plain arrays of per-trade net R (any strategy, any cost tier).
Gate thresholds are lane parameters — none live here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def profit_factor(vals) -> float | None:
    v = np.asarray(vals, dtype=float)
    wins = float(v[v > 0].sum())
    losses = float(-v[v < 0].sum())
    if losses == 0.0:
        return None if wins == 0.0 else float("inf")
    return wins / losses


def expectancy(vals) -> float:
    v = np.asarray(vals, dtype=float)
    return float(v.mean()) if len(v) else float("nan")


def max_dd_r(vals) -> float:
    v = np.asarray(vals, dtype=float)
    cum = np.cumsum(v)
    peak = np.maximum.accumulate(np.r_[0.0, cum])[1:]
    return float(np.max(peak - cum)) if len(v) else 0.0


def max_dd_pct(vals, risk_pct: float) -> float:
    """Compounding equity DD%% when each trade risks `risk_pct` percent."""
    eq, peak, dd = 1.0, 1.0, 0.0
    for v in np.asarray(vals, dtype=float):
        eq *= 1.0 + (risk_pct / 100.0) * v
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak)
    return 100.0 * dd


def by_year_net(vals, years) -> dict[str, float]:
    out: dict[str, float] = {}
    for v, y in zip(np.asarray(vals, dtype=float), years):
        out[str(int(y))] = out.get(str(int(y)), 0.0) + float(v)
    return {k: round(v, 4) for k, v in sorted(out.items())}


def positive_year_stats(year_net: dict[str, float]) -> tuple[int, float | None]:
    """(count of positive years, max positive-year share of positive sum)."""
    pos = {y: v for y, v in year_net.items() if v > 0}
    if not pos:
        return 0, None
    return len(pos), max(pos.values()) / sum(pos.values())


def sr_skew_kurt(vals) -> tuple[float | None, float | None, float | None]:
    """Per-trade Sharpe, skew, NON-excess kurtosis — DSR inputs."""
    v = pd.Series(np.asarray(vals, dtype=float))
    if len(v) <= 3 or v.std(ddof=1) == 0:
        return None, None, None
    return (float(v.mean() / v.std(ddof=1)),
            float(v.skew()),
            float(v.kurt() + 3.0))


def top1_win_share(vals) -> float | None:
    v = np.asarray(vals, dtype=float)
    pos = v[v > 0]
    return float(pos.max() / pos.sum()) if len(pos) else None


def loo_pf(vals) -> float | None:
    """Profit factor after removing the single largest winner."""
    v = np.asarray(vals, dtype=float)
    if len(v) < 2:
        return None
    return profit_factor(np.delete(v, int(np.argmax(v))))
