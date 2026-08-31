"""Mechanism-neutral negative-control generators.

These produce ENTRY TIMESTAMPS only; the lane simulates them with its own
frozen exit engine so control and challenger share identical mechanics.
Seeds are caller-supplied and must be declared in the frozen plan.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def matched_random_entries(bar_times: pd.Series, n: int, seed: int,
                           mask: pd.Series | None = None) -> pd.Series:
    """Sample n entry bar-times uniformly from eligible bars (matched cadence).

    `mask` restricts eligibility (e.g. same session hours as the challenger)
    so the control matches the challenger's opportunity set, not its signal.
    """
    t = pd.Series(pd.to_datetime(bar_times)).reset_index(drop=True)
    if mask is not None:
        elig = t[np.asarray(mask, dtype=bool)]
    else:
        elig = t
    if len(elig) == 0:
        raise ValueError("no eligible bars for control sampling")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(elig), size=min(n, len(elig)), replace=False)
    return elig.iloc[np.sort(idx)].reset_index(drop=True)


def time_shift_entries(entry_times: pd.Series, bar_times: pd.Series,
                       shift_bars: int) -> pd.Series:
    """Shift each entry by `shift_bars` bars along the actual bar index.

    Placebo control: same count/spacing, decoupled from the signal. Entries
    shifted past the end are dropped.
    """
    t = pd.Series(pd.to_datetime(bar_times)).reset_index(drop=True)
    pos = {ts: i for i, ts in enumerate(t)}
    out = []
    for e in pd.to_datetime(entry_times):
        i = pos.get(pd.Timestamp(e))
        if i is None:
            continue
        j = i + shift_bars
        if 0 <= j < len(t):
            out.append(t.iloc[j])
    return pd.Series(out)
