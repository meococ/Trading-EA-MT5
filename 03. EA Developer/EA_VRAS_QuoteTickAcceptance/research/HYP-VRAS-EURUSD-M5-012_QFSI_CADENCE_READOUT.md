# HYP-012 QFSI quote-cadence readout (schema-only prior)

Source: `20260715_QFSI_REAL_007_LONG_ACCUMULATE/EURUSD_quote_ticks.csv`,
bound by capture manifest SHA256
`3BEE05599A97BD812CDCC895EC84D6D8E3BE62D15D8A6D3C5A66505C463A2D03`
and CSV SHA256
`B5418CCE08D3BAFE8AA747553C571955A76991FADE246F896E4B8C696CC4624E`.

This corpus is used only as a broker-feed schema and cadence prior. It is not
joined to HYP-008 trades or any future return/outcome and cannot establish an
edge or authorize threshold changes.

| Descriptive field | Value |
|---|---:|
| Unique chronological EURUSD quote rows | 11,834 |
| Median interquote gap | 1,340 ms |
| P95 interquote gap | 5,146 ms |
| P99 interquote gap | 8,375 ms |
| Gaps above 15,000 ms | 4 (0.034%) |
| Rolling 120-second quote count, P10 | 52 |
| Rolling 120-second quote count, median | 66 |
| Rolling 120-second quote count, P90 | 83 |

The frozen HYP-012 minimum of 20 quote updates is below the old feed's P10
120-second count, while the 15-second stale gate lies beyond its P99 gap. That
supports engineering feasibility only. The authoritative AlphaFactory bundle
validator still returns `STOP_DATA_FRONTIER`: quote history is partial and far
below the 90 elapsed-day research gate.

