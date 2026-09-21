"""phys_common — constants, paths and hashing for the R01 level-physics harness.

Authority: `PA_PRO_CHARTER.md` section 4, `docs/CHARTER_ADDENDUM_1.md` (zone
generator bake-off), `rounds/R01/PHYSICS_PREREG_DRAFT.md` (the draft this
harness implements).  NO OUTCOMES live anywhere in `research/physics/`.

Everything in this package is OUTCOME-BLIND by construction: the extractor and
the control sampler read only prices up to and including the event bar; the
resolver (`phys_resolve.py`) is the only module that reads forward bars and it
is never run before `rounds/R01/FREEZE.json` exists.
"""

import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA_PRO = os.path.dirname(os.path.dirname(HERE))
ZONES_DIR = os.path.join(PA_PRO, "struct", "zones")
LIB_DIR = os.path.join(PA_PRO, "lib")
for _p in (LIB_DIR, ZONES_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

__all__ = [
    "HERE", "PA_PRO", "ZONES_DIR", "LIB_DIR",
    "CORE_SYMBOLS", "EXTENDED_SYMBOLS", "ALL_SYMBOLS", "SYMBOL_ORD",
    "SEED", "K_CTRL", "HORIZON", "FRESH_BARS", "AWAY_ATR",
    "CTRL_SEARCH", "CTRL_REDRAWS", "STRATA_SESSIONS",
    "sha256_file", "dir_code_sha256", "utc_now",
]

CORE_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
EXTENDED_SYMBOLS = ["USDCAD", "USDCHF", "NZDUSD"]
ALL_SYMBOLS = CORE_SYMBOLS + EXTENDED_SYMBOLS
SYMBOL_ORD = {s: i + 1 for i, s in enumerate(ALL_SYMBOLS)}

SEED = 20260920
K_CTRL = 5
HORIZON = 48                 # outcome window in M5 bars
FRESH_BARS = 24              # freshness scan depth
AWAY_ATR = 1.0               # away-bar distance in ATR14(H1)
CTRL_SEARCH = 1440           # fake-event search window (5 days of M5 bars)
CTRL_REDRAWS = 20            # redraws per control slot

# Stratum windows (draft section 6, `vpa_random_baseline.py:50-53`), UTC minutes.
STRATA_SESSIONS = [
    ("asia", 0, 300),
    ("london", 300, 660),
    ("ny", 690, 1050),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_scratch(name):
    """Audit scratch (R02-D): never part of a frozen code bundle.  Covers
    ``_scratch/``, ``_diag*``, ``_review*``; ``__init__.py`` stays."""
    return name.startswith("_") and name != "__init__.py"


def dir_code_sha256(directory, suffix=".py"):
    """SHA256 over sorted `suffix` files (names + bytes), `pa_ledger.code_sha256` style.

    Names starting with `_` are excluded so audit scratch can never change a
    frozen hash again (R02-D; the R01 `_diag_dist.py` mismatch).
    """
    h = hashlib.sha256()
    if os.path.isdir(directory):
        for name in sorted(os.listdir(directory)):
            if name.endswith(suffix) and not _is_scratch(name):
                h.update(name.encode("utf-8"))
                with open(os.path.join(directory, name), "rb") as f:
                    h.update(f.read())
    return h.hexdigest()


def utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_of(utc_min):
    """Stratum session name for a UTC minute-of-day (draft section 6)."""
    m = int(utc_min) % 1440
    for name, lo, hi in STRATA_SESSIONS:
        if lo <= m < hi:
            return name
    return "off"


def year_of(epoch_server):
    """Server-clock year of a bar close (pa_clock semantics, UTC+2/+3)."""
    import pa_clock

    t_close = int(epoch_server) + 300
    return int(pa_clock.server_year(t_close))


def wilson_ci(k, n, z=1.959963984540054):
    """Wilson score interval for a binomial proportion; returns (lo, hi)."""
    k = float(k)
    n = float(n)
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))
