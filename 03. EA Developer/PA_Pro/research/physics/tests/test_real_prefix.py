import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)

import phys_common as pc  # noqa: E402
from phys_source import GenSource  # noqa: E402
from phys_extract import extract_events  # noqa: E402


def _load(name, max_bars):
    from data_helpers import load_ctx
    import registry

    ctx = load_ctx("EURUSD", max_bars=max_bars)
    cls = registry.get(name)
    return GenSource(name, cls, ctx).run()


def test_prefix_invariance_real_data():
    full_n = 14000
    short_n = 10000
    src_full = _load("line1_cluster", full_n)
    src_short = _load("line1_cluster", short_n)
    ev_full, _ = extract_events(src_full)
    ev_short, _ = extract_events(src_short)
    keep = [e for e in ev_full if e["bar_idx"] < short_n]
    key = lambda e: (e["bar_idx"], e["zid"], e["side"], round(e["near"], 9),
                     round(e["far"], 9), round(e["strength"], 9))
    assert [key(e) for e in keep] == [key(e) for e in ev_short]
    assert len(ev_short) > 0
