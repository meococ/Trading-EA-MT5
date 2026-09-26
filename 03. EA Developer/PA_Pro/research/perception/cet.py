"""cet.py — CET/CEST wall clock for the perception lane.

Volman's casebook charts are Central European local time (CET = UTC+1,
CEST = UTC+2).  The EU switch happens at 01:00 UTC on the last Sunday of
March (01:00 UTC -> offset 1->2) and the last Sunday of October
(01:00 UTC -> offset 2->1).

Relationship to the feed (verified P1.3, Ruling 1 / D3): in the BOOK
window the feed's server clock IS the Europe/Berlin wall clock (UTC+1
winter / UTC+2 summer, EU switch dates) — i.e. ``server = CET`` and the
book's chart axis matches both.  Evidence: the NFP spike prints at
server 14:30 on every 2012 NFP Friday (Mar = UTC+1, Jun-Aug = UTC+2);
an EET feed would show 15:30/16:30, a fixed-UTC+1 feed 13:30 in summer.
NOTE: this differs from the DESIGN feed (2016-2021), where the Lead
verified server = EET/EEST (NFP at 15:31).  ``pa_clock`` therefore
describes the DESIGN feed, NOT the BOOK feed — do not use it to convert
BOOK timestamps.

Scalar and array entry points mirror ``pa_clock``.  No lib imports here:
this module must also be safe to load in processes where ``pa_clock`` is
not on ``sys.path``.
"""

import numpy as np
import pandas as pd

__all__ = [
    "cet_offset_hours", "utc_to_cet_epoch", "cet_to_utc_epoch",
    "server_to_cet_epoch", "cet_to_server_epoch", "cet_minute_of_day",
    "cet_dow", "cet_day_start_utc", "last_sunday",
]

_DAY = 86400


def _split_scalar(x):
    arr = np.asarray(x)
    if arr.ndim == 0:
        return arr.reshape(1).astype(np.int64), True
    return arr.astype(np.int64).ravel(), False


def last_sunday(year, month):
    """UTC epoch of 00:00 UTC on the last Sunday of ``month``."""
    if month == 3:
        d = pd.Timestamp(year=int(year), month=3, day=31)
    elif month == 10:
        d = pd.Timestamp(year=int(year), month=10, day=31)
    else:
        raise ValueError("EU DST switches only in March and October")
    last = d - pd.Timedelta(days=(d.weekday() + 1) % 7)
    return int(last.timestamp())


def cet_offset_hours(utc_epoch):
    """CET offset in hours (+1 winter / +2 summer) for UTC-epoch seconds."""
    ts, scalar = _split_scalar(utc_epoch)
    out = np.full(ts.shape[0], 1, dtype=np.int64)
    if ts.shape[0] == 0:
        return int(1) if scalar else out
    naive = pd.to_datetime(ts, unit="s", utc=True)
    years = np.asarray(naive.year)
    for y in np.unique(years):
        mar = last_sunday(int(y), 3) + 3600      # 01:00 UTC
        oct_ = last_sunday(int(y), 10) + 3600    # 01:00 UTC
        summer = (ts >= mar) & (ts < oct_)
        out[np.asarray(years == y) & np.asarray(summer)] = 2
    return int(out[0]) if scalar else out


def utc_to_cet_epoch(utc_epoch):
    """CET wall-clock epoch (CET reading as if UTC) = utc + offset."""
    ts, scalar = _split_scalar(utc_epoch)
    off = np.asarray(cet_offset_hours(ts), dtype=np.int64)
    out = ts + off * 3600
    return int(out[0]) if scalar else out


def cet_to_utc_epoch(cet_epoch):
    """Inverse of :func:`utc_to_cet_epoch`.

    Fixed-point search over both candidate offsets (the autumn fold makes
    02:00–02:59 CET ambiguous for one hour; the earlier, summer-side
    mapping is chosen — unreachable for bar data because markets are shut
    at the Sunday 02:00 CET fold).
    """
    u, scalar = _split_scalar(cet_epoch)
    out = np.empty(u.shape[0], dtype=np.int64)
    for i in range(u.shape[0]):
        cands = []
        for o in (1, 2):
            c = int(u[i]) - o * 3600
            if int(cet_offset_hours(c)) == o:
                cands.append(c)
        if cands:
            out[i] = min(cands)
        else:
            out[i] = int(u[i]) - int(cet_offset_hours(int(u[i]))) * 3600
    return int(out[0]) if scalar else out


def server_to_cet_epoch(server_epoch):
    """CET wall epoch for a BOOK-feed (server-epoch) timestamp.

    The 2012 BOOK feed's server clock is the Europe/Berlin wall clock, so
    the mapping is the identity (server epoch already reads as CET wall
    time).  Verified by NFP bars at server 14:30 in both winter and
    summer 2012 (D3).  Do NOT route through pa_clock — it encodes the
    DESIGN feed's EET/EEST server clock.
    """
    ts, scalar = _split_scalar(server_epoch)
    return int(ts[0]) if scalar else ts


def cet_to_server_epoch(cet_epoch):
    """Inverse of :func:`server_to_cet_epoch` — identity on the BOOK feed."""
    u, scalar = _split_scalar(cet_epoch)
    return int(u[0]) if scalar else u


def cet_minute_of_day(server_epoch):
    """CET minute-of-day in [0,1440) for a server epoch."""
    ts, scalar = _split_scalar(server_epoch)
    cet = np.asarray(server_to_cet_epoch(ts), dtype=np.int64)
    out = (cet % _DAY) // 60
    return int(out[0]) if scalar else out


def cet_dow(server_epoch):
    """Weekday of the CET day containing the bar: Monday=0 .. Sunday=6."""
    ts, scalar = _split_scalar(server_epoch)
    cet = np.asarray(server_to_cet_epoch(ts), dtype=np.int64)
    out = ((cet // _DAY) + 3) % 7
    return int(out[0]) if scalar else out


def cet_day_start_utc(server_epoch):
    """UTC epoch of 00:00 CET of the CET day containing ``server_epoch``."""
    ts, scalar = _split_scalar(server_epoch)
    cet = np.asarray(server_to_cet_epoch(ts), dtype=np.int64)
    day0 = (cet // _DAY) * _DAY
    out = np.asarray(cet_to_utc_epoch(day0), dtype=np.int64)
    return int(out[0]) if scalar else out
