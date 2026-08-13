# HYP-XJRR-XAUUSD-M5-001 — economic failure

Verdict: `KILL_BASE_PF_EXPECTANCY_CADENCE_AND_YEAR_CONCENTRATION_FAIL`

Sole admissible baseline: AlphaFactory run `20260811_113423`.

## Engineering validity

- FivePercent XAUUSD M5, Model 0, 2018–2022, current spread, USD100,000,
  leverage 1:100; compile `0 errors / 0 warnings`.
- HQ `99%`, full fixed-window DQ, 351,303 XAU bars / 135,208,676 ticks,
  non-truncated journal and two identical XJRR summaries.
- `runtime_failed=false`, invalid inputs `0`; report trades `124` equal EA
  entries `124` and all positions were closed by EA exit or broker stop.
- Source opportunity reconciliation is exact:
  `1290 = 124 entries + 5 geometry/order-plan rejects + 7 stale attach/gap
  classifications + 1154 frozen risk-lock suppressions`.
- Source sides remained `614 LONG / 676 SHORT`; runtime code did not change the
  288-window beta, z threshold, daily quota or 12-bar lockout.

## Economic result after tester spread and commission

- Completed trades: `124` (`56 LONG / 68 SHORT`).
- PF: `0.3785071919`; net: `-$7,989.52`; expectancy: `-$64.4316/trade`.
- Win rate: `37.9032%`; relative DD: `7.7451%`.
- Commission: `-$1,141.57`; swap: `$0`. Tester spread semantics: `current`.
- Completed cadence: `124 / (1826/7) = 0.475356/week`, below `2/week`.
- All completed trades occurred in 2018 before the frozen 8% peak-equity latch;
  max-year share is `100%`, above `30%`.

The risk latch behaved exactly as preregistered; removing or relaxing it would
be a post-outcome risk rescue. Favorable Friday or other session/weekday slices
in the generic analyzer are diagnostics only and cannot create a successor.
PF, expectancy, cadence and year concentration fail before slippage stress, so
x1.5/x2 costs, optimization, validation, OOS and holdout remain closed.

## Evidence

- manifest: `638BF0BE7E264B7708F4F5D74DB0077F8923020DAB3F5249A405EAEE100EDBEB`
- report: `E971A9DB556F7978C42378BE69427EF4D612C8A3EF43317B3B68306B8888313E`
- journal: `6144F40F341E4E6DB80767BED20436172B7E47797F1C91540E670661B4C39B2A`
- enhanced summary: `D3D345DFE080184101BE47D5DF42C4FD55D06DA51A0772C40567F130EE621D89`
- executed source: `FAF3F3643303DE5A8998A52E0E6F554EB175238335E9CC77EE981B49A4D5EC99`
- run EX5: `AE560984CA662F31C7A2028C0E25FD863FE0BC579BFCDE3214F07302EB3BA457`

Failure radius: this exact XAUUSD/USDJPY M5 residual re-entry, beta288,
two-sigma re-entry, daily first-event quota, 12-bar lock, ATR1.25 stop,
residual-zero/12-bar exit and 0.25% risk mapping. No threshold, window, symbol,
weekday/session/direction, quota, stop/exit/hold/risk or timeframe rescue.
