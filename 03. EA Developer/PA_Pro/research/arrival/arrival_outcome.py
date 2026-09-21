"""arrival_outcome — R02 outcome resolver (FROZEN-PATH, gated by Lead).

Implements R02's outcome stage by mapping arrival events onto the R01
frozen resolver `phys_resolve.resolve_events` (imported read-only —
identical BOUNCE / BREAK / NONE / adverse-first / continuation semantics
as PHYSICS_PREREG §4, with the grid band in place of the zone).

LEAD RULING R02-B: this module may be unit-tested on SYNTHETIC data only.
It must NOT be run on real data before the R02 freeze.
"""

import numpy as np

import phys_resolve  # read-only import of the R01 frozen resolver

__all__ = ["to_resolver_rows", "resolve_arrivals"]

HORIZON = 48  # phys_common.HORIZON — declared here so tests pin it


def to_resolver_rows(events):
    """Map arrival events -> phys_resolve row dicts.

    side=-1: price below band, e_near = glo, e_far = ghi.
    side=+1: price above band, e_near = ghi, e_far = glo.
    m = 1.0 x A(t) (the event's frozen ATR).
    """
    rows = []
    for e in events:
        glo, ghi, s = float(e["glo"]), float(e["ghi"]), int(e["side"])
        rows.append({
            "bar_idx": int(e["bar_idx"]), "side": s,
            "lo": glo, "hi": ghi,
            "near": glo if s == -1 else ghi,
            "far": ghi if s == -1 else glo,
            "m": 1.0 * float(e["atr"]),
        })
    return rows


def resolve_arrivals(events, bars):
    """(rows -> phys_resolve.resolve_events).  DO NOT RUN PRE-FREEZE."""
    return phys_resolve.resolve_events(to_resolver_rows(events), bars)
