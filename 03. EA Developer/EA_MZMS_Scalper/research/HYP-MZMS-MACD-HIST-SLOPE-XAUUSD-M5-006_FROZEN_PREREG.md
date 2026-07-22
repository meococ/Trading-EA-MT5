# HYP-006 Frozen XAUUSD M5 Transfer Diagnostic

Frozen at `2026-07-21T11:48:00Z`, before changing the canonical source identity
or reading any MZMS XAUUSD outcome.

## Authority and epistemic boundary

The Owner explicitly requests an XAUUSD backtest comparable to the completed
EURUSD HYP-005 diagnostic. This opens one post-outcome cross-symbol transfer
diagnostic; it does not rescue HYP-003/HYP-005 and is not an independent edge
hypothesis. Run exactly one matched Model-0 pair: `InpSignalMode=0` control,
then `InpSignalMode=1` MZMS challenger. No third run, threshold change,
subgroup veto, symbol fallback, BE/intrabar arm, optimization, paper, promotion,
or live execution is authorized.

## Frozen identity and test window

- EA/hypothesis: `EA_MZMS_Scalper` /
  `HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006`
- Broker/test lane: FivePercent portable MT5 on D:
- Symbol/timeframe/model: `XAUUSD`, `M5`, Model `0`
- Window: `2018.01.01` through `2026.07.21`
- Deposit/leverage: USD 100,000 / 1:100
- Risk: 0.01% of current equity per accepted entry
- Tester spread: `current` / Model-0 tick spread
- Cost provenance: tester-reported only; no independent slippage or live-fill
  proof, therefore diagnostic-only

## Frozen XAU geometry adaptation

The prior FivePercent XAUUSD Model-0 manifest at
`02. AlphaFactory/runs/EA_UnicornPrecisionScalperRR15/20260716_144508/run_manifest.json`
(SHA256 `204AE22A34B65228BF39FEA759D6A38B57CD6E538150731F6D9EB268F803A372`)
binds two digits, point `0.01`, and EA `PipSize()` `0.01` for XAUUSD.

The EURUSD values 0.8/0.5 pip are not copied numerically into a two-digit gold
contract. Freeze the existing workspace FivePercent XAU M5 execution geometry
before outcome access:

- `InpMaxSpreadPips=35.00`, equal to 35 XAU points / USD 0.35 maximum spread.
- `InpStopBufferPips=40.00`, equal to 40 XAU points / USD 0.40 structure buffer.
- `InpMagic=5600722` for XAU transfer identity isolation.

These are symbol-unit adaptations only. They are not selected from an MZMS
XAU result and may not be changed after either arm starts.

The RunMeta pre-run data-contract marker is SHA256
`BC45C0CC644CE8BE67FF61245F20F8063BE2BAE99FEFF77D25556CC1F955B563`
over the exact text
`XAUUSD|M5|MODEL0|2018.01.01|2026.07.21|POSTRUN_MANIFEST_DATA_FINGERPRINT_REQUIRED`.
It is a contract marker, not a claim that the future tester data is already
hashed. Each valid run must bind the actual post-run AlphaFactory data
fingerprint and report hash in its run manifest.

## Frozen strategy contract

- 100% closed-bar decisions; no intrabar indicator evaluation.
- MACD 12/26/9 histogram local extremum on shifts 1/2/3.
- Minimum normalized histogram delta `abs(hist1-hist2)/ATR(14) >= 0.01`.
- EMA200 close bias, RSI14 42--58 and directional, ADX14 >=18.
- Five-M5-bar cooldown and one owned position maximum.
- 08:00--17:00 UTC using the existing FivePercent EU-DST clock contract.
- Farther of five-bar structural stop plus the frozen XAU buffer and 1.5 ATR.
- Target 1.6R; maximum hold 15 M5 bars; hard flatten 18:15 UTC.
- Break-even OFF; no trailing; max five entries per UTC day.
- Daily loss guard 1.5%; account drawdown guard 8%.

The embedded news file is an EUR/USD 2019--2022 calendar and is neither XAU
complete nor full-window PIT evidence. Freeze `InpRequireNewsGuard=false`
uniformly for both XAU arms. This limitation forbids promotion; it is not a
post-outcome toggle.

## Acceptance and terminal contract

Inherited research gates are context, not rescue authority:

- PF >=1.35.
- 2--5 trades per elapsed calendar week.
- Max DD <=6%.
- Cost-stress PF x1.5 >=1.25 and x2 >=1.00 only when verified cost inputs exist.
- Monte Carlo P95 DD <=6%.

A valid run must cover the requested window, materially exceed 125 bars, report
at least 99% history quality, bind source/EX5/config/report hashes, emit exactly
one RunMeta and one LifecycleTrades file, reconcile lifecycle positions and net
P/L to the report, and leave MT5 stopped.

Report control/challenger trades, elapsed-week cadence, PF, net profit,
expectancy, drawdown, sessions, directions, calendar years, WFA, robustness,
Monte Carlo, equity audit, and chart artifacts. Terminal outcome is
`DIAGNOSTIC_COMPLETE_NO_PROMOTION`, `KILL_DIAGNOSTIC_XAU_TRANSFER_NO_EDGE`, or
`INVALID_ENGINEERING_RUN`. No result authorizes parameter rescue or another
symbol.
