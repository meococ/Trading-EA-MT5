"""registry.py - the frozen config table (17 <= 22 per symbol).

Every entry lists its params and a `tag` provenance string
(source-primary / community / reconstructed). NOTHING here may change
after PREREG is hashed.
"""
from __future__ import annotations

_J = dict(swing="fractal2", session="london_j", w2=None, w3=False,
          w4_atr=0.0, sl="leg0", tp="j", pv=False, offset_pips=3.0,
          ttl=4, weekly_cap=5, reentry=False, lookback=40)


def _c(cfg_id, family, **kw):
    c = dict(_J)
    c.update(kw)
    c["id"] = cfg_id
    c["family"] = family
    return c


CONFIGS = [
    _c("F0_J", "F0", tag="source-primary:16/08 packet s6"),
    # ---- F1 ladder: J + ONE element ----------------------------------
    _c("F1_W2whq", "F1", w2="whq",
       tag="source-primary:packet W2 WHQ-proximity"),
    _c("F1_W2swing", "F1", w2="swing",
       tag="community:swing-zone variant of W2"),
    _c("F1_W3", "F1", w3=True, tag="source-primary:packet W3"),
    _c("F1_W4a", "F1", w4_atr=0.05, tag="reconstructed:angle proxy"),
    _c("F1_W4b", "F1", w4_atr=0.10, tag="reconstructed:angle proxy"),
    _c("F1_R1b", "F1", sl="bigswing", tag="reconstructed:big swing stop"),
    _c("F1_R2a", "F1", tp="zone", tag="reconstructed:zone target"),
    _c("F1_R2b", "F1", tp="whq", tag="source-primary:WHQ runway"),
    _c("F1_PV", "F1", pv=True, tag="reconstructed:pvsra regime"),
    _c("F1_FULL", "F1", w2="swing", w3=True, w4_atr=0.05, sl="bigswing",
       tp="zone", pv=True, tag="composite:most source-faithful each"),
    _c("F1_FULL_RE", "F1", w2="swing", w3=True, w4_atr=0.05,
       sl="bigswing", tp="zone", pv=True, reentry=True,
       tag="composite+reentry S3.2"),
    # ---- F2 Nhat Hoai -------------------------------------------------
    _c("F2_NH_a", "F2", session="london_ext", w2=None, sl="pullback",
       tp="zone", offset_pips=2.0, weekly_cap=0,
       tag="source-primary:atlas S6 fam2 SL-pullback"),
    _c("F2_NH_b", "F2", session="london_ext", w2=None, sl="bigswing",
       tp="zone", offset_pips=2.0, weekly_cap=0,
       tag="source-primary:atlas S6 fam2 SL-swing"),
    # ---- F3 Lucy ------------------------------------------------------
    _c("F3_LUCY_a", "F3", offset_pips=2.0, ttl=6, weekly_cap=0,
       tp="r15", tag="source-primary:atlas fam3 TP1.5R"),
    _c("F3_LUCY_b", "F3", offset_pips=2.0, ttl=6, weekly_cap=0,
       tp="zone", tag="source-primary:atlas fam3 TPzone"),
    # ---- F4 Bai 14 ----------------------------------------------------
    _c("F4_BAI14", "F4", session="london_ext", w2=None, tp="r2",
       offset_pips=2.0, weekly_cap=0,
       tag="community:atlas fam4"),
]

assert len(CONFIGS) <= 22

# NOTE on F0_J: the 16/08 code treats S/R proximity as telemetry
# (sr.blocked never gates), so J runs w2=None. PARITY_J tests whether
# N~307/PF~0.94 reproduces; if N overshoots, the w2='whq' variant is the
# documented alternative interpretation, not a new config.
