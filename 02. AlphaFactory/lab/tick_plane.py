"""Tick-plane reader for Dukascopy AFDTICK1 binaries.

Record: <q (int64 epoch ms) <d ask <d bid. 16-byte header <QQ: magic,count.
No suspect bars exist on this plane — ticks are raw feed quotes. Spread is
real (ask-bid), so cost accounting is exact.
"""
import os
import struct
from datetime import date, timedelta

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "external", "dukascopy_pilot")
MAGIC = 0x4146445449434B31
REC = np.dtype([("ms", "<q"), ("ask", "<d"), ("bid", "<d")])


def day_path(sym, d):
    return os.path.join(ROOT, sym, "decoded", f"{d:%Y}", f"{d:%m}",
                        f"{d:%Y-%m-%d}.afdticks")


def load_day(sym, d):
    p = day_path(sym, d)
    if not os.path.exists(p):
        return None
    raw = open(p, "rb").read()
    magic, cnt = struct.unpack("<QQ", raw[:16])
    if magic != MAGIC:
        raise ValueError(f"bad magic {p}")
    r = np.frombuffer(raw[16:], dtype=REC)
    assert len(r) == cnt
    return r


def load_range(sym, d0, d1):
    """d0,d1: date; inclusive-exclusive. Returns concatenated record array."""
    out = []
    d = d0
    while d < d1:
        r = load_day(sym, d)
        if r is not None:
            out.append(r)
        d += timedelta(days=1)
    if not out:
        return np.empty(0, dtype=REC)
    return np.concatenate(out)


def mid(rec):
    # NOTE: source writer stores the lower quote in field "ask" and higher in
    # "bid" (empirically ask<bid in every record). Treat them as lo/hi.
    return (rec["ask"] + rec["bid"]) * 0.5


def resample(rec, sec):
    """Resample ticks to fixed-second bars. Returns (t_sec, o,h,l,c, n_ticks, med_spread)."""
    if len(rec) == 0:
        return None
    m = mid(rec)
    sp = np.abs(rec["bid"] - rec["ask"])
    bucket = rec["ms"] // (sec * 1000)
    ub, first, counts = np.unique(bucket, return_index=True, return_counts=True)
    order = np.argsort(first)
    ub, counts = ub[order], counts[order]
    first = np.sort(first)
    last = np.minimum(first + counts, len(m))
    o = m[first]
    c = m[last - 1]
    hh = np.empty(len(ub)); ll = np.empty(len(ub)); msp = np.empty(len(ub))
    s = 0
    for k in range(len(ub)):
        seg = m[first[k]:last[k]]
        sseg = sp[first[k]:last[k]]
        hh[k] = seg.max(); ll[k] = seg.min(); msp[k] = np.median(sseg)
    return ub * sec, o, hh, ll, c, counts, msp
