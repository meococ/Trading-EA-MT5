"""pick_windows.py — freeze the 8 DESIGN snapshot windows BEFORE any picture.

Rule (declared here and recorded in `research/zones/WINDOWS.json`):
- symbol EURUSD, TF M5, split DESIGN (2016-2021);
- pool = in-session M5 bars (05:00-11:00 or 11:30-17:30 UTC), non-warm-up,
  at least `window_bars` = 120 bars of history;
- one bar per DESIGN year 2016..2021 drawn uniformly from that year's pool,
  plus 2 extra bars drawn uniformly from the whole pool, without replacement;
- each window is the 120 M5 bars ENDING at the chosen decision bar;
- seed 20260920 (the program seed), `numpy.random.default_rng(20260920)`.

This script ran BEFORE any snapshot was rendered; the JSON is the record and
is never edited after the first render.  No outcomes.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA_PRO = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(PA_PRO)                       # repo root
for _p in (HERE, os.path.join(PA_PRO, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data_helpers import load_ctx  # noqa: E402
import pa_clock  # noqa: E402

SEED = 20260920
WINDOW_BARS = 120
N_WINDOWS = 8
OUT = os.path.join(PA_PRO, "research", "zones", "WINDOWS.json")


def _year(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).year


def _iso(ts):
    """True UTC from a SERVER-clock epoch (pa_clock semantics)."""
    return datetime.fromtimestamp(int(pa_clock.server_to_utc_epoch(ts)),
                                  tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _iso_srv(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")


def main():
    ctx = load_ctx("EURUSD")
    bars = ctx.bars
    t = bars["t"]
    utc_min = bars["utc_min"]
    n = len(t)
    sess = ((utc_min >= 300) & (utc_min < 660)) | ((utc_min >= 690) & (utc_min < 1050))
    years = np.asarray([_year(x) for x in t], dtype=np.int64)
    idx = np.arange(n)
    valid = sess & (idx >= WINDOW_BARS) & (~np.asarray(bars["warmup"], dtype=bool))
    rng = np.random.default_rng(SEED)
    picks = []
    for y in range(2016, 2022):
        pool_y = np.flatnonzero(valid & (years == y))
        if len(pool_y):
            picks.append(int(rng.choice(pool_y)))
    pool = np.flatnonzero(valid)
    pool = pool[~np.isin(pool, picks)]
    extra = [int(x) for x in rng.choice(pool, size=N_WINDOWS - len(picks),
                                        replace=False)]
    picks.extend(extra)
    picks.sort()
    out = {
        "task": "T-PAPRO-ZONE-1",
        "symbol": "EURUSD",
        "tf": "M5",
        "split": "DESIGN",
        "seed": SEED,
        "rng": f"numpy.random.default_rng({SEED})",
        "rule": ("1 in-session (05:00-11:00 or 11:30-17:30 UTC) non-warmup "
                 "DESIGN bar per year 2016..2021, plus 2 extra in-session bars "
                 "uniform from the same pool, without replacement; each window "
                 "= the 120 M5 bars ending at the chosen decision bar; chosen "
                 "BEFORE any snapshot was rendered"),
        "window_bars": WINDOW_BARS,
        "n_bars": int(n),
        "data_first_utc": _iso(t[0]),
        "data_last_utc": _iso(t[-1]),
        "windows": [
            {
                "window_id": i,
                "bar_idx": int(p),
                "utc_close": _iso(t[p]),
                "utc_window_start": _iso(t[p - WINDOW_BARS + 1]),
                "server_close": _iso_srv(t[p]),
                "year": _year(t[p]),
            }
            for i, p in enumerate(picks)
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"wrote {OUT}")
    for w in out["windows"]:
        print(f"  win {w['window_id']} idx={w['bar_idx']:7d} "
              f"close={w['utc_close']}  start={w['utc_window_start']}")


if __name__ == "__main__":
    main()
