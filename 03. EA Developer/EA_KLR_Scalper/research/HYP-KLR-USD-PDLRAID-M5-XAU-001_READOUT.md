# Readout - HYP-KLR-USD-PDLRAID-M5-XAU-001

Verdict: **KILL_AT_OFFLINE_PROBE**. No EA source, compile or Model 0 is
authorized under this hypothesis.

## Frozen identity

- Train window: 2022-01-01 through 2024-12-31; 2025+ remained untouched.
- XAU data: portable MT5 build 6006, `data_path` on `D:`.
- External gate: Federal Reserve H.10/FRED `DTWEXBGS`, SHA-256
  `15B46514271F0E8D5D721CFEE2FA5A994DB56982E042B55F66F23750B70E8951`,
  lagged by two U.S. business days.
- Prereg SHA-256:
  `902D810DA1B0807423B3A95F797534AA844D8745BDC1BF1D84C59C6FD8119718`.
- Probe SHA-256:
  `6CB23635AF192BBC4147AE95B9EC8937F9B3CCF37F927B4B7C93D62391EAF460`.
- Result SHA-256:
  `DB2FBF482FFB723BAC8200BCD1099BD6C7C187D7DE2AA7FFC28DB43509F0745E`.

## Funnel and result

The probe read 212,590 M5 bars and 70,950 M15 bars over 932 ET dates.

| Stage | Count |
|---|---:|
| Prior-day raids matching M15 bias | 210 |
| Displacement + mechanical MSS | 42 |
| Strict three-candle FVG | 16 |
| Directional FVG retest | 3 |
| Core trades admitted | 2 |
| USD-aligned retests / challenger trades | 0 / 0 |

The ungated core produced only two trades, about 0.0128 per elapsed week, PF
0.0 and -1.5083R after the frozen 35-point cost proxy. Both represented years
were negative. The mandatory USD gate admitted no challenger trade.

Nine of eleven frozen gates failed: minimum cadence, PF at x1/x1.5/x2 cost,
positive expectancy, positive-year breadth, net not below core, PF advantage,
and core-trade retention. Only maximum cadence and the vacuous drawdown cap
passed.

## Interpretation

The KLR memo's external USD requirement is not enough to rescue the already
spent liquidity-raid -> displacement -> MSS -> FVG/retest family. The primary
failure happens before economics: the fully quantified sequence is too sparse,
and its ungated observations are already negative. Lowering displacement,
removing structure, widening sessions, relaxing FVG/retest or changing the USD
lag would be post-hoc rescue, not implementation completion.

## Storage evidence

- Portable terminal/data/tester root: `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable`.
- `FILE_COMMON` was disabled by contract because MT5 reports its shared common
  path on C even in portable mode.
- C tester, history, Tester profile, roaming Tester and Program Files Tester
  fingerprints were unchanged.
- The shared C Common fingerprint changed concurrently due files named for
  `HYP-UPS-XAU-M5-002`, not KLR. Therefore the global C comparison is marked
  `PARTIAL_CONCURRENT_CONTAMINATION`; no KLR-named C artifact was found and no
  concurrent file was deleted.

## Decision

`HYP-KLR-USD-PDLRAID-M5-XAU-001` is terminal. Do not create
`EA_KLR_Scalper.mq5`, compile, backtest, tune or open 2025+ under this ID.
