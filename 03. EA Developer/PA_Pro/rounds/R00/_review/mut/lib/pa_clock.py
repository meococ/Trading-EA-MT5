"""pa_clock — server-clock <-> UTC for the PA-PRO referee (frozen semantics).

Data-plane convention
---------------------
The M1 parquet index (``ctm``) is the BROKER SERVER wall clock written as Unix
epoch seconds ("server epoch"): server = UTC + 2h (winter) / +3h (EU summer
time).  A server epoch is therefore the server wall-clock reading *as if* it
were UTC.  Everything in PA-PRO that needs a timezone conversion goes through
this module.

Frozen provenance (READ-ONLY sources, semantics copied exactly)
---------------------------------------------------------------
- ``03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60-70``
  ``eu_server_offset_hours``: offset 3 when the *server* timestamp lies in
  [last Sunday of March + 1h, last Sunday of October + 1h) of its own year,
  else 2.
- ``.../research/lab/vpa_data.py:55-61``: the mod-1440 wrap into [0, 1440)
  (server 00:30 with +2h maps to 22:30 UTC of the previous day, never to a
  negative minute).
- Weekday: ``vpa_data.py:61`` uses ``pandas.Timestamp.weekday()`` of the
  server timestamp -> Monday=0..Sunday=6.  The ``((t//86400)+4) % 7`` formula
  in ``vpa_random_baseline.py:157`` is a DIFFERENT (Sunday=0) convention and
  its ``dow == 4`` fired on Thursday; that quirk is exposed separately as
  ``legacy_server_dow`` and is NOT what ``server_dow`` returns.
"""

import numpy as np
import pandas as pd

__all__ = [
    "server_offset_hours",
    "server_to_utc_epoch",
    "utc_epoch_to_server",
    "utc_minute_of_day",
    "server_dow",
    "legacy_server_dow",
    "server_day_start_utc",
    "server_year",
]

_DAY = 86400


def _split_scalar(x):
    arr = np.asarray(x)
    if arr.ndim == 0:
        return arr.reshape(1).astype(np.int64), True
    return arr.astype(np.int64).ravel(), False


def server_offset_hours(server_epoch):
    """EU DST offset (+2/+3) for server-epoch seconds.  Exact copy of the
    frozen ``eu_server_offset_hours`` semantics (last Sunday of March /
    October + 1h, evaluated on the server wall clock)."""
    ts, scalar = _split_scalar(server_epoch)
    out = np.full(ts.shape[0], 2, dtype=np.int64)
    if ts.shape[0] == 0:
        return int(2) if scalar else out
    naive = pd.to_datetime(ts, unit="s", utc=False)
    years = np.asarray(naive.year)
    for y in np.unique(years):
        mar31 = pd.Timestamp(year=int(y), month=3, day=31)
        oct31 = pd.Timestamp(year=int(y), month=10, day=31)
        mar_last = mar31 - pd.Timedelta(days=(mar31.weekday() + 1) % 7)
        oct_last = oct31 - pd.Timedelta(days=(oct31.weekday() + 1) % 7)
        summer = (naive >= mar_last + pd.Timedelta(hours=1)) & (
            naive < oct_last + pd.Timedelta(hours=1)
        )
        out[np.asarray(years == y) & np.asarray(summer)] = 3
    return int(out[0]) if scalar else out


def server_to_utc_epoch(server_epoch):
    """UTC epoch = server epoch - offset(server epoch)."""
    ts, scalar = _split_scalar(server_epoch)
    off = np.asarray(server_offset_hours(ts), dtype=np.int64)
    out = ts - off * 3600
    return int(out[0]) if scalar else out


def utc_epoch_to_server(utc_epoch):
    """Inverse of :func:`server_to_utc_epoch`.

    Tries each candidate offset and keeps the fixed points (upset: the frozen
    convention makes the spring-forward hour ambiguous, because both the
    winter and the summer rendering of one UTC instant are consistent).  Tie
    break: the smaller (winter) server epoch.  Fallback (no fixed point, not
    observed on this data plane): offset taken at the UTC instant itself.
    """
    u, scalar = _split_scalar(utc_epoch)
    out = np.empty(u.shape[0], dtype=np.int64)
    for i in range(u.shape[0]):
        cands = []
        for o in (2, 3):
            s = int(u[i]) + o * 3600
            if int(server_offset_hours(s)) == o:
                cands.append(s)
        if cands:
            out[i] = min(cands)
        else:
            out[i] = int(u[i]) + int(server_offset_hours(int(u[i]))) * 3600
    return int(out[0]) if scalar else out


def utc_minute_of_day(server_epoch):
    """UTC minute-of-day in [0, 1440) for a server epoch (mod-1440 wrap)."""
    ts, scalar = _split_scalar(server_epoch)
    off = np.asarray(server_offset_hours(ts), dtype=np.int64)
    srv_min = (ts % _DAY) // 60
    out = (srv_min - off * 60) % 1440
    return int(out[0]) if scalar else out


def server_dow(server_epoch):
    """Correct weekday of the server day: Monday=0 .. Sunday=6.

    NOTE: this is pandas ``weekday()`` of the server timestamp (the convention
    used by ``vpa_data.load_m5_bars``), NOT the legacy ``((t//86400)+4)%7``.
    """
    ts, scalar = _split_scalar(server_epoch)
    out = ((ts // _DAY) + 3) % 7
    return int(out[0]) if scalar else out


def legacy_server_dow(server_epoch):
    """The legacy Sunday=0 convention ``((t//86400)+4)%7`` used by
    ``vpa_random_baseline.py:157`` / ``vpa_econ1_sim.py:37``, where the label
    ``dow == 4`` fired on THURSDAY.  Kept for the legacy-flats regression."""
    ts, scalar = _split_scalar(server_epoch)
    out = ((ts // _DAY) + 4) % 7
    return int(out[0]) if scalar else out


def server_day_start_utc(server_epoch):
    """UTC epoch of 00:00 server of the server day containing ``server_epoch``."""
    ts, scalar = _split_scalar(server_epoch)
    day_start = (ts // _DAY) * _DAY
    out = np.asarray(server_to_utc_epoch(day_start), dtype=np.int64)
    return int(out[0]) if scalar else out


def server_year(server_epoch):
    """Calendar year of the server wall clock (frozen loaders filter on this)."""
    ts, scalar = _split_scalar(server_epoch)
    out = np.asarray(pd.to_datetime(ts, unit="s", utc=False).year, dtype=np.int64)
    return int(out[0]) if scalar else out
