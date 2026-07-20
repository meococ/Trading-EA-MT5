# HYP-LSS-OB-REPL-EURUSD-M15-001 - Fidelity/Cadence Readout

Verdict: `TERMINAL_STOP_FIDELITY_CADENCE_NO_BUILD_NO_MODEL0`

This readout contains no trade outcome, forward return, PnL, MFE, MAE,
stop/target result, profit factor, expectancy, Sharpe, drawdown, WFA, Monte
Carlo, FTMO pass simulation, or 2023+ bar. It answers only whether the frozen
LSS-OB M15 detector has enough faithful setup density to justify an EA build.

## Frozen identity

- Hypothesis: `HYP-LSS-OB-REPL-EURUSD-M15-001`.
- Report SHA256:
  `8F3EE339C52B7271CC9382DE21379E8C35C0D1646CEF133D1050D083FEC19223`.
- PROBE_PLAN SHA256:
  `7F051DE01B89E6A41A01B0C7EC023ED7435AF74420EA2E6D89AB9348279C26BD`.
- Frozen requirement matrix SHA256:
  `7C23A0E336E49D3A73BCC5A9B6ED3A575C9080518EB02BE7425D1491A9D30F33`.
- M1 SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- News CSV SHA256:
  `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307`.
- 2019-01-03 through 2022-12-31 only; `holdout_bars_loaded=0`.

Governance limitation: the requirement matrix existed unchanged before the
probe but its SHA was omitted from the pre-run registry row. The terminal row
late-binds the unchanged file. This is recorded as
`PARTIAL_PREBIND_MATRIX`; it cannot upgrade evidence, and the conservative
terminal stop does not depend on an economic outcome.

## Mechanical verification

- Contract tests: 12 passed.
- Candidate registry before execution: PASS (`rows=79`, `hypotheses=31`).
- No-outcome schema: PASS.
- Repeatability: the density JSON SHA was identical across two consecutive
  runs over identical inputs.
- Density JSON SHA256:
  `70447FB1D97AFDF4EDBCF8E630D334A51D3655AE9124D7BE4CC58D315390963D`.
- Event CSV SHA256:
  `6C98AB2B5D0DD4D1983798FA2303F029255D0E3A44869BA57D9E25DFD53C0699`.
- Native MT5 parity SHA256:
  `4E916DE8AE800262CFF9C98D0DF38030D786D7BE9B929BAFE6E34A5397054694`.

Native parity is PASS for the frozen UTC clock contract: a fresh read-only
FivePercent M1 pull, converted by the canonical server-clock model and replayed
into UTC M15/H1/H4, matched the sealed M1-derived bars, event identities, and
all funnel counts exactly. Direct broker-native M15 and H1 also match after
clock conversion. Direct broker-native H4 is intentionally non-canonical and
does not match because MT5 anchors H4 to server time; the frozen plan anchors
H4 to UTC.

## No-outcome funnel

| Stage | Count |
|---|---:|
| Closed M15 bars | 99,467 |
| Eligible session bars | 24,901 |
| Context-aligned sweeps | 383 |
| Displacement + strict FVG within three bars | 0 |
| Valid OB/FVG body overlap | 0 |
| Control-ready events | 0 |
| Challenger-ready events | 0 |

The pooled inclusive denominator is 1,459 calendar days = 208.428571 weeks.
The frozen 2.0/week floor requires at least 417 pooled challenger events. Only
383 upstream sweeps exist before displacement, OB/FVG overlap, confirmation,
news, ADX, and 8-12 pip geometry can reject anything. Therefore the full
challenger cannot mathematically reach the cadence floor. The exact frozen
detector produces zero events in pooled, Train, and Internal Validation.

## Decision

- Do not create `EA_LSSOBPropScalper.mq5`.
- Do not create `ALPHAFACTORY_EA_CONTRACT.json`.
- Do not compile, run Model 0, cost stress, WFA, Monte Carlo, or FTMO
  simulation for this hypothesis.
- Do not alter displacement, session, direction, stop band, timeframe, asset,
  RR, or confirmation to rescue this result.
- Any materially different geometry is a new hypothesis with a new de-dup and
  pre-outcome contract; it does not reopen this record.

The DOCX remains a discretionary strategy brief, not an implementable
positive-expectancy claim. This exact EURUSD M15 replication is terminal at the
fidelity/cadence frontier before economic testing.
