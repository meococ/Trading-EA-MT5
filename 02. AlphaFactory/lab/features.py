"""Vectorized feature/event library.

Every function maps a symbol DataFrame -> mask (bool array, len=df) or a
float Series aligned to df.index. Signal bar t is the LAST CLOSED bar the
EA could see; entries happen at t+1 open by labels.sim_path.
"""
import numpy as np
import pandas as pd


def ret_k(df, k):
    """k-bar close-to-close log-style return in raw price units."""
    return df["c"] - df["c"].shift(k)


def impulse_mask(df, k, thresh_pips, pip):
    """k-bar move magnitude >= thresh. +1/-1 direction array via impulse_dir."""
    r = ret_k(df, k) / pip
    return (np.abs(r) >= thresh_pips).fillna(False).to_numpy()


def impulse_dir(df, k, pip):
    """Sign of k-bar move (+1 up, -1 down)."""
    return np.sign(ret_k(df, k) / pip)


def breakout_mask(df, k, side, pip, min_move_pips=0.0):
    """Close breaks the prior k-bar extreme (strictly prior bars only)."""
    c = df["c"]
    if side > 0:
        ext = df["h"].shift(1).rolling(k).max()
        move = (c - ext) / pip
    else:
        ext = df["l"].shift(1).rolling(k).min()
        move = (ext - c) / pip
    return (move > min_move_pips).fillna(False).to_numpy()


def vol_z(df, k, lookback=2400):
    """Z-score of rolling k-bar realized vol vs its own history.
    NB: computed on 1e4-scaled diffs — pandas rolling.std underflows to NaN
    on raw ~1e-5 diffs; z-score is scale-invariant so this is exact."""
    rv = (df["c"].diff().abs() * 1e4).rolling(k).mean()
    mu = rv.rolling(lookback, min_periods=lookback // 2).mean()
    sd = rv.rolling(lookback, min_periods=lookback // 2).std()
    return (rv - mu) / sd


def range_mask(df, k, thresh_pips, pip):
    """k-bar high-low range >= thresh (volatility burst, e.g. news)."""
    rng = (df["h"] - df["l"]).rolling(k).sum() / pip
    return (rng >= thresh_pips).fillna(False).to_numpy()


def hour_mask(df, h0, h1):
    """Server hour-of-day in [h0, h1)."""
    m = df["mod"] // 60
    return ((m >= h0) & (m < h1)).to_numpy()


def mow_mask(df, mow0, mow1):
    """Minute-of-week in [mow0, mow1)."""
    return ((df["mow"] >= mow0) & (df["mow"] < mow1)).to_numpy()


def session_mask(df, name):
    """Named sessions on server clock (server ~= UTC+2/+3 DST hybrid)."""
    table = {
        "asia": (0, 7),       # 00:00-07:00 post-roll Asian session
        "london": (9, 12),    # London morning
        "ny_am": (15, 18),    # NY morning
        "quiet": (20, 23),    # late NY -> pre-roll
    }
    h0, h1 = table[name]
    return hour_mask(df, h0, h1)


def day_open_gap(df, pip, max_prev_gap_s=3600):
    """Gap = day-first-bar open - previous bar close (prev bar within
    max_prev_gap_s, so weekends/holidays/data-holes excluded).
    Returns Series aligned to index (NaN elsewhere)."""
    ctm = df.index.to_numpy()
    o = df["o"].to_numpy()
    c = df["c"].to_numpy()
    day = df["day"].to_numpy()
    is_first = np.r_[True, day[1:] != day[:-1]]
    gap = np.full(len(df), np.nan)
    idx = np.flatnonzero(is_first)
    prev = idx - 1
    ok = prev >= 0
    idx, prev = idx[ok], prev[ok]
    dt = ctm[idx] - ctm[prev]
    good = dt <= max_prev_gap_s
    gap[idx[good]] = (o[idx[good]] - c[prev[good]]) / pip
    return pd.Series(gap, index=df.index)


def consec_bars(df, k):
    """k consecutive same-sign closes -> direction array (+1/-1/0)."""
    sgn = np.sign(df["c"] - df["o"])
    up = (sgn > 0).rolling(k).sum() == k
    dn = (sgn < 0).rolling(k).sum() == k
    return up.astype(np.int8) - dn.astype(np.int8)


def pullback_mask(df, k_trend, k_pull, pip, min_trend=2.0):
    """With-trend pullback: strong k_trend move, then k_pull counter-move
    that does NOT retrace >60% of the trend leg. Returns dir array."""
    tr = ret_k(df, k_trend) / pip
    pb = ret_k(df, k_pull) / pip
    up = (tr >= min_trend) & (pb < 0) & (pb > -0.6 * tr)
    dn = (tr <= -min_trend) & (pb > 0) & (pb < 0.6 * -tr)
    return up.astype(np.int8) - dn.astype(np.int8)
