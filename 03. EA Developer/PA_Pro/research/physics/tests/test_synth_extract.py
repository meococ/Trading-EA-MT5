import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
for _p in (PHYS,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from phys_extract import extract_events  # noqa: E402
from synth import SynthSource, make_bars, flat_zone  # noqa: E402

A = 0.0010  # 10 pips


def _closes(n, base=1.0950):
    return [base] * n


def test_basic_event_from_below():
    n = 60
    closes = _closes(n)
    # entry bar 40: range touches band [1.1000, 1.1010] from below
    closes[40] = 1.1000
    bars = make_bars(closes, spread=0.0002)
    bars["h"][40] = 1.1005
    bars["l"][40] = 1.0990
    src = SynthSource(bars, [A] * n, [flat_zone(1, 1.1000, 1.1010)])
    ev, cnt = extract_events(src)
    assert cnt["events"] == 1
    e = ev[0]
    assert e["bar_idx"] == 40 and e["side"] == -1
    assert e["near"] == pytest.approx(1.1000)
    assert e["far"] == pytest.approx(1.1010)
    assert e["w"] == pytest.approx(0.0010)
    assert e["m"] == pytest.approx(A)
    assert e["close_prev"] == pytest.approx(1.0950)


def test_not_fresh_after_earlier_touch():
    n = 60
    closes = _closes(n)
    closes[30] = 1.1000
    closes[40] = 1.1000
    bars = make_bars(closes, spread=0.0002)
    bars["h"][30] = 1.1005
    bars["l"][30] = 1.0990
    bars["h"][40] = 1.1005
    bars["l"][40] = 1.0990
    src = SynthSource(bars, [A] * n, [flat_zone(1, 1.1000, 1.1010)])
    ev, cnt = extract_events(src)
    assert [e["bar_idx"] for e in ev] == [30]
    assert cnt["skip_window"] >= 1


def test_no_away_bar_rejects():
    n = 60
    closes = _closes(n)
    for i in range(16, 40):
        closes[i] = 1.0995  # d = 0.0005 < A, never away
    closes[40] = 1.1000
    bars = make_bars(closes, spread=0.00005)
    bars["h"][40] = 1.1005
    bars["l"][40] = 1.0998
    src = SynthSource(bars, [A] * n, [flat_zone(1, 1.1000, 1.1010)])
    ev, cnt = extract_events(src)
    assert ev == []
    assert cnt["skip_no_away"] >= 1


def test_warmup_bars_excluded():
    n = 40
    closes = _closes(n)
    closes[10] = 1.1000
    bars = make_bars(closes, spread=0.0002, warmup=20)
    bars["h"][10] = 1.1005
    bars["l"][10] = 1.0990
    src = SynthSource(bars, [A] * n, [flat_zone(1, 1.1000, 1.1010)])
    ev, cnt = extract_events(src)
    assert ev == []


def test_broken_zone_skipped():
    n = 60
    closes = _closes(n)
    closes[40] = 1.1000
    bars = make_bars(closes, spread=0.0002)
    bars["h"][40] = 1.1005
    bars["l"][40] = 1.0990
    z = flat_zone(1, 1.1000, 1.1010,
                  state={"broken": 35, "touches": 1, "n_respected": 0,
                         "role_flip": 0})
    src = SynthSource(bars, [A] * n, [z])
    ev, cnt = extract_events(src)
    assert ev == [] and cnt["skip_broken"] == 1


def test_created_too_recent_skipped():
    n = 60
    closes = _closes(n)
    closes[40] = 1.1000
    bars = make_bars(closes, spread=0.0002)
    bars["h"][40] = 1.1005
    bars["l"][40] = 1.0990
    src = SynthSource(bars, [A] * n, [flat_zone(1, 1.1000, 1.1010, created=30)])
    ev, cnt = extract_events(src)
    assert ev == []


def test_invalid_atr_skips():
    n = 60
    closes = _closes(n)
    closes[40] = 1.1000
    bars = make_bars(closes, spread=0.0002)
    bars["h"][40] = 1.1005
    bars["l"][40] = 1.0990
    arr = [A] * n
    arr[40] = float("nan")
    src = SynthSource(bars, arr, [flat_zone(1, 1.1000, 1.1010)])
    ev, cnt = extract_events(src)
    assert ev == []


def test_prefix_invariance():
    n = 120
    closes = _closes(n)
    for i in (40, 80):
        closes[i] = 1.1000
    bars = make_bars(closes, spread=0.0002)
    for i in (40, 80):
        bars["h"][i] = 1.1005
        bars["l"][i] = 1.0990
    z = flat_zone(1, 1.1000, 1.1010)
    full_src = SynthSource(bars, [A] * n, [z])
    ev_full, _ = extract_events(full_src)
    cut = 60
    short_bars = {k: (v[:cut] if isinstance(v, np.ndarray) and len(v) == n else v)
                  for k, v in bars.items()}
    short_src = SynthSource(short_bars, [A] * cut,
                            [flat_zone(1, 1.1000, 1.1010, end=cut - 1)])
    ev_short, _ = extract_events(short_src)
    keep = [e for e in ev_full if e["bar_idx"] < cut]
    assert [(e["bar_idx"], e["side"], e["near"]) for e in keep] == \
           [(e["bar_idx"], e["side"], e["near"]) for e in ev_short]


def test_side_above_band():
    n = 60
    closes = _closes(n, base=1.1100)
    closes[40] = 1.1010
    bars = make_bars(closes, spread=0.0002)
    bars["h"][40] = 1.1020
    bars["l"][40] = 1.1005
    src = SynthSource(bars, [A] * n, [flat_zone(1, 1.1000, 1.1010)])
    ev, _ = extract_events(src)
    assert len(ev) == 1 and ev[0]["side"] == +1
    assert ev[0]["near"] == pytest.approx(1.1010)
    assert ev[0]["far"] == pytest.approx(1.1000)
