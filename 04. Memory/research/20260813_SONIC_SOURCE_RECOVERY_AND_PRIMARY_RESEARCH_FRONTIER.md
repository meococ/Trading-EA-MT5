# Sonic source recovery and primary-research frontier

Date: 2026-08-13  
Scope: XAUUSD/Forex only; MT5/MQL5 only; no Git; no purchase; no new market
outcomes  
Goal status: `ACTIVE / UNMET`

## Executive verdict

This wave does **not** prove that a profitable EA is impossible. The initial
archive/workspace/public-source pass found no editable source, but a deeper
task-artifact recovery found the real `.mq5` package. The source is now restored
and compile-valid. The earlier move to block the full goal was therefore too
broad and the initial missing-source statement is superseded below.

No new economic hypothesis, source scanner, MT5 backtest, validation/holdout
readout, live collector/trader, data download or purchase was opened in this
wave. Source recovery and compile evidence were opened.

## 1. Local SonicR recovery

- Canonical and archived EA shelves initially contained no `EA_SonicR.mq5`;
  the archived EX5 is SHA256
  `B9CF2CE8D351EDE658A88907A28C4AAF1A7DCDBC4C5C3C56CCA63ABB92320C0A`.
- A deeper exact-string scan found task-owned artifact
  `sonicr_legacy_source_b709309.zip`, SHA256
  `9F61C13CA24145A138C8997FC37ACCC9275789DA40007DA702822C3DC394B27E`.
  It contains `EA_SonicR.mq5` plus seven local includes. Main source SHA256 is
  `BCE6ABCF55DDFD503651482ED6FA1643A0302098D7FA3D559B538743A745893D`.
- Those eight files were restored byte-for-byte into canonical
  `03. EA Developer/EA_SonicR/`. The ZIP's old research registry/templates were
  not imported. No decompilation or public binary was used.
- AlphaFactory compile produced a fresh 432,574-byte EX5, SHA256
  `A75D552FE7E814C8C8EE7DB61ECD8463E08F7F3C21A1198C728B2362FA6FC1BD`;
  the fresh log proves `0 errors, 0 warnings`.
- Static safety review found no DLL/network/process/destructive-file API. All
  decision series reads start at shift 1; bar 0 is used only as the new-bar
  clock. This is preliminary engineering/non-repaint evidence, not economics.
- Catalog evidence for the meaningful rows is:

| Run | Window | Model | Trades | PF | Net USD |
|---|---:|---:|---:|---:|---:|
| `20260701_132349` | 2024-2025 | 1 | 127 | 1.41 | 803 |
| `20260701_134204` | 2024-2025 | 0 | 127 | 1.40 | 773 |
| `20260705_015521` | 2021-2025 | 1 | 335 | 1.16 | 539 |
| `20260705_022757` | 2021-2025 | 0 | 335 | 1.15 | 517 |

All four use `InpUseAutoSleeveConfig=true`. The longer history loses much of
the headline strength and has no robustness/OOS promotion receipt. These runs
remain historical discovery evidence, not a current-source edge claim.

`EA_HybridICT_Sonic.mq5` is available, but its Hybrid ICT/Sonic signal lineage
is terminal. Reusable material is neutral engineering plumbing only: closed-bar
buffer/rate reads, handle lifecycle, exact magic/ticket ownership, lot/risk and
daily-loss shells, and diagnostic counters.

A second read-only recovery pass searched the user's Desktop, Documents,
Downloads, OneDrive, MetaQuotes profile, `D:\Downloads` and the other trading
workspace for the exact filename and unique `InpUseAutoSleeveConfig` string;
those roots had no source. The later task-artifact scan is what recovered it.
Public web searches returned only unrelated paid products with different
inputs/timeframes. No demo, public binary or purchase was downloaded.

Canonical recovery/compile receipt:
`03. EA Developer/EA_SonicR/research/20260813_SOURCE_RECOVERY_AND_COMPILE_RECEIPT.md`.

### Reproduction-contract audit and preflight

Grok Build completed a bounded read-only source review with
`PASS_TO_REPRODUCTION_CONTRACT`, `MEDIUM` source-identity confidence, static
non-repaint `PASS` and telemetry-off signal equivalence. The medium confidence
is appropriate: the recovered input/source surface matches the July run, but
the newly compiled EX5 is not byte-identical to the archived executable.

The subsequent local preflight found a narrower blocker, not global
infeasibility. Historical run `20260701_134204` hash-binds
`SNR_FX_EVENTS.csv` to SHA256
`b62eab34e6630f6255f97aedc280bde438d53ef1643ef1ee29effc9f5d6634c7`,
448 events, 2019-2026 coverage and classes `CPI,FOMC,GDP,NFP,PCE,RATE`.
That file and its legacy fallback are currently absent from both relevant
Common Files roots. A renamed-file scan of the task artifacts, user document
roots, MetaQuotes profile, workspace and `D:\Downloads` also found no CSV at
either recorded historical file size. The source fails closed without it. A
tiny prior engineering fixture, a regenerated calendar with a different hash,
disabling the news filter, or substituting another calendar would all change
the tested object and are forbidden.

The Owner's existing FivePercent terminal is also running on `EURUSD,M5` and
was left untouched. A later bounded exact-name/hash/size/renamed-file forensic
pass found only session receipts proving the file once existed, not a complete
recoverable object. The exact recovery verdict is therefore
`EXACT_RECOVERY_NOT_PROVEN`; the frozen reproduction is unavailable unless the
same hash-bound bytes reappear. No MT5 outcome was opened. Accepted initial
Grok artifacts are:

- `.context/grok-sonic-source-recovery-review-20260813/run2/summary.json`
- `.context/grok-sonic-source-recovery-review-20260813/run2/grok-response.json`

## 2. Outcome-blind Sonic mechanism review

Draft `SONIC-TREND-FAIL-M15-XAU-001` used an established Dragon/Trend regime,
an EMA89 break and a failed Dragon retest, then proposed trading away from the
old trend. No target outcomes were opened.

Grok Build independently returned:

- `verdict=NO_CANDIDATE`
- `materially_distinct=false`
- `mechanical_sign_valid=false`
- `alternative_candidate=null`

Lead accepts the rejection. The draft uses the same EMA34 Dragon,
EMA89/144/169 Trend, ATR and closed-M15 clock as terminal Sonic/ITSM/classic
families. It changes thresholds, timing and polarity, but adds no new
information object. OHLC/EMA geometry cannot distinguish liquidation
continuation from a stop-run/fade interpretation, so the sign is not unique
enough to authorize even a counts-only gate.

Accepted Grok artifacts:

- `.context/grok-sonic-trend-failure-frontier-20260813/run1/summary.json`
- `.context/grok-sonic-trend-failure-frontier-20260813/run1/grok-response.json`

The run passed its structured schema and ended normally. Provider-reported
usage was USD `0.2776656` on `grok-4.5-build`.

## 3. Real-yield and primary-paper frontier

The independent real-yield direction idea was already consumed by
`HYP-GMP-XAU-M15-REALYIELD-001`: 270 observations, `1.726/week`, cost-proxy PF
`0.683924752`, `-63.09798R`, DD `16.87097%`, and `0/3` positive years. It may
not be revived by timing or filter changes.

Grok Build then searched a bounded 2024-2026 primary-source frontier. The
research run completed but its first response envelope contained multiple JSON
instances, so it was rejected as a runner result even though the backend
ended normally:

- `.context/grok-sonic-primary-research-frontier-20260813/run1/summary.json`
- failure: `schema_validation_failed`
- provider-reported usage: USD `3.170672` on `grok-4.6-build`

The exact session was resumed for envelope repair only; no new research was
allowed. The repair passed its schema and returned `NO_CANDIDATE`:

- `.context/grok-sonic-primary-research-frontier-20260813/run2/summary.json`
- `.context/grok-sonic-primary-research-frontier-20260813/run2/grok-response.json`
- provider-reported usage: USD `0.323482` on `grok-4.6-build`

Total provider-reported Grok usage in this wave was USD `3.7718196`. This was
Grok Build compute requested for the collaboration, not a data purchase. No
market-data subscription or paid source was acquired.

Lead checked the primary sources rather than accepting the Grok summary alone:

1. Iacoviello and Tong's 2026 AI-GPR paper discusses equities, oil and trade,
   but supplies no frozen XAU/G10 FX direction rule or execution horizon.
2. BIS Bulletin 105 explains the April-May 2025 dollar slide partly through FX
   hedging. It is an episode explanation, not a repeatable point-in-time signal;
   the Asian-hours observation is not an independent information object.
3. The December 2025 BIS FX review describes turnover, internalisation and
   hedging based on the 2025 Triennial Survey. It supplies no mechanical
   direction/clock and no live-identical signal feed.

Primary URLs:

- <https://www.matteoiacoviello.com/research_files/AI_GPR_PAPER.pdf>
- <https://www.bis.org/publ/bisbull105.htm>
- <https://www.bis.org/publ/qtrpdf/r_qt2512b.htm>

## 4. Fresh OIS-slope idea: source route unavailable

Iinuma and Nakazono's 2026 paper, *Exchange Rate Predictability from Monetary
Policy Path Expectations: Evidence from OIS Slopes*, reports that a steeper US
one-month-versus-12-month OIS path predicts subsequent USD appreciation in a
weekly 2008-2025 study, with weaker predictability in FOMC weeks. This is a
genuinely fresher directional idea than the consumed real-yield mapping:

- <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6834679>

It nevertheless fails the current source gate before hypothesis creation:

- there is no local OIS curve history;
- the free NY Fed 30/90/180-day SOFR averages are backward-looking compounded
  rates, not a one-month/12-month forward OIS slope;
- CME Term SOFR offers tenors but is a different licensed benchmark and the
  official documentation applies fees from 2026;
- DTCC SDR prints cannot be silently converted into an identical historical
  par-OIS curve without a separately specified and validated construction.

Relevant official source pages:

- <https://www.newyorkfed.org/markets/reference-rates/sofr-averages-and-index>
- <https://www.cmegroup.com/market-data/market-data-api/cme-term-sofr-api.html>
- <https://www.cmegroup.com/market-data/files/term-sofr-data-license-faq.pdf>
- <https://www.cmegroup.com/market-data/files/cme-term-sofr-data-licensing-fees-january-2026.pdf>

Verdict: `NO_CANDIDATE_SOURCE_ROUTE_UNAVAILABLE`. Do not proxy the paper with
SOFR averages or CME Term SOFR, and do not purchase access without Owner
authorization.

## 5. Registry descendant audit

Several latest parent rows looked active until their descendants were traced.
They are not forgotten survivors:

| Apparent parent | Terminal descendant | Final evidence |
|---|---|---|
| `HYP-ROUND-CASCADE-EURUSD-M5-008/010` | `...-011` | PF 0.6762 at 1.5 pips; 0 positive years; 10/11 gates failed |
| `HYP-G10-XMOM-W1-001` | `...-002` | PF 0.814/x1, 0.753/x1.5, 0.697/x2; negative expectancy; MC P95 DD 11.95% |
| `HYP-TRILAG-EURJPY-M1-001` | `...-002` | 58 events/260.565 weeks = 0.2226/week; structural gate failed |
| `HYP-JCDR-EURUSD-M5-002` | `...-006` | Model-0 PF 0.763972; price-only PF 0.851207; net -7888.77; DD 8.02% |
| `HYP-GC-OFI-INNOV-XAU-M5-002` | `...-003` | duplicate keys, bad flags, A/B volume coverage and definition conflicts |

Registry status must therefore be read lineage-first, not row-by-row.

## Boundary and next direction

This receipt closes only the exact routes above. It does not close the goal,
all XAU/Forex mechanisms, future free sources, or prospective evidence
engineering. Goal stays active. In the recovered Sonic lane, the frozen lineage
replay is unavailable unless the exact calendar bytes reappear. New market
research must add a genuinely new information object/source identity or a
candidate-agnostic forward evidence capability; it must not revive the same
Sonic fields, real-yield rule, OIS proxies or terminal registry parents. The
subsequent forensic and input-escrow receipt is
`04. Memory/research/20260813_SONIC_CALENDAR_RECOVERY_FRONTIER_AND_INPUT_ESCROW.md`.
