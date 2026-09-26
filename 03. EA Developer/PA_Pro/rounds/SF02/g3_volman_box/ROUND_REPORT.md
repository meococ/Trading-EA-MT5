# G3 — Volman build-up break at a salient zone — DEAD (cadence)

Spec v2 prereg T000283 (sha cbd7011f); v1 (T000280) superseded
pre-outcome after census showed same-bar compression+break is a
near-nonexistent joint event (~0.05 sig/wk). v2 = episode model:
contiguous compressed bars (12-bar range <= rolling pct_max percentile
over 576 bars, mean body <= 0.5*ATR_M5, CMAX=24) form the box; a salient
zone near the relevant edge arms the episode (expires E=6 bars);
trigger = close beyond the box edge aligned with s_tr_h4.

## Census (DESIGN, 20 cells)

Total across grid: **342 signals / 6 years / 4 symbols**.

| best cells | N |
|---|---|
| S14 line1 pct20 | 69 |
| S18 line1 pct20 | 68 |
| S24 line1 pct20 | 35 |
| S18 line1 pct10 | 28 |
| S18 sd_base pct20 | 25 |

Every cell is 4-15x below the n>=300 screen gate. The tightness of the
Volman compression condition AND the salient-zone press AND h4 trend
alignment AND the cost guard is a quadruple coincidence the data does
not produce at screening cadence.

## Governed probe

The densest cell (S14/line1/pct20) was screened once for a data point:
N=68, PF_x1=0.925, t=-0.29, lift -2.55pp CI [-13.3,+10.0] — no edge in
the little that exists (SCREEN.json, 1-cell probe; referee-native
matched randoms, stop orders).

## Verdict

**DEAD** — cadence-fail at every cell; the one governed probe shows the
signals that do exist carry no lift. A cadence-rescuing revision (wider
box percentile, lower salience, longer expiry) would need ~5x more
signals and would abandon the "compressed box pressing a salient level"
definition that is the family's thesis. No third revision spent.
