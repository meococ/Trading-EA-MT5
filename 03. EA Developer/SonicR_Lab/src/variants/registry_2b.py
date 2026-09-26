"""registry_2b.py - ROUND 2B config table (8 configs, LEAD_NOTE_4).

Frozen by PREREG_V2.md (separate hash); does NOT touch the round-2
CONFIGS table. Base = F0_J generator with new one-element gates or the
F5 confluence score. F5 exits = R1b (big-swing SL) + R2a (zone target).
"""
from __future__ import annotations

from .registry import _c

CONFIGS_2B = [
    _c("F1_W4c", "F1B", w4c=True,
       tag="2B:dragon pointing the trade way over wave (mid[t]-mid[t-20])"),
    _c("F1_W4d", "F1B", w4d=True,
       tag="2B:dir*angle20 >= median Q of F0_J signals (census-frozen)"),
    _c("F1_PV2a", "F1B", pv2a=True,
       tag="2B:volume rising/climax at the turn [leg2-1,leg2+1]"),
    _c("F1_PV2b", "F1B", pv2b=True,
       tag="2B:volume rising/climax at the breakout bar"),
    _c("F5_S2", "F5", score_min=2, sl="bigswing", tp="zone",
       tag="2B:confluence S>=2, exits R1b+R2a"),
    _c("F5_S3", "F5", score_min=3, sl="bigswing", tp="zone",
       tag="2B:confluence S>=3, exits R1b+R2a"),
    _c("F5_S2_EXT", "F5", score_min=2, sl="bigswing", tp="zone",
       session="london_ext", tag="2B:confluence S>=2, london_ext"),
    _c("F5_S3_EXT", "F5", score_min=3, sl="bigswing", tp="zone",
       session="london_ext", tag="2B:confluence S>=3, london_ext"),
]
