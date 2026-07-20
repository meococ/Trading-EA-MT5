# HYP-ICT-FVG-FID-EURUSD-M5-001 — pre-outcome amendment V2

Status: **FROZEN BEFORE ANY MODEL-0 OUTCOME READ**  
Parent plan: `HYP-ICT-FVG-FID-EURUSD-M5-001_PROBE_PLAN.md`  
Parent SHA-256: `EC8A89D5E9EB45504A716B1DA920FED43498F0AEC60DE96970971F1EDFDAEB85`

## Reason for amendment

The parent plan correctly froze historical high-impact news as `UNMET`. A
source-C, diagnostic-only calendar has now been acquired before any Model-0
result was opened. The parent file remains immutable; this V2 changes only the
news input and its binding. It does not relax costs, cadence, economics, trial
budget, holdout, signal rules, or acceptance gates.

## Frozen news contract

- Source: Forex Factory weekly calendar pages, `High Impact Expected`, EUR and
  USD, displayed in GMT+7 and converted deterministically to UTC.
- Weekly coverage: `dec30.2018` through `dec25.2022`, 209 consecutive weeks.
- In-range timed rows: 1,282 unique event IDs for local event dates
  2019-01-01 through 2022-12-31.
- Raw evidence SHA-256:
  `78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F`.
- Normalized CSV SHA-256:
  `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307`.
- Generated MQL include SHA-256:
  `248D569B981564AC0B179588C4919CD6CC196A9E7B008939A9CCDB3446F4678C`.
- Build audit SHA-256:
  `D5D38389CE72A443A79E63131719FAE42BAB4BFC552B792E130921870B0CBE2A`.
- EA behavior: `InpRequireNewsGuard=true`, symmetric blackout +/-30 minutes,
  binary search over the generated array, fail closed outside the 2019-2022
  UTC coverage contract.
- Untimed EUR/USD rows (24) and global `All` rows (63) remain in the audit but
  are excluded from timestamp blackout rows. This is a known limitation.

Source classification remains `C_DIAGNOSTIC_ONLY`; the calendar does not make
the lane promotion eligible and does not claim official completeness.

## Frozen implementation binding

- Main source SHA-256:
  `AD30CBFD4BA29A7D0A5258A2C71E66FE7B744AAF32D89447E15F4A1E8889E621`.
- Only parameter delta from the parent plan:
  `InpRequireNewsGuard=true;InpNewsBlackoutMinutes=30`.
- Control remains `SIGNAL_HIGH_RECALL_CONTROL`.
- Challenger remains `SIGNAL_REPORT_FIDELITY`.
- Trial budget remains exactly two fixed arms; no optimization.
- 2023 onward remains sealed and must not be loaded.

## Cost and authority boundary

The FivePercent 2019-2022 M1 export contains 24.5552909% zero-spread rows and
fails spread-cost provenance. Commission and direction-aware slippage evidence
also remain unavailable. Therefore:

- `promotion_eligible=false` for every run;
- fixed 1.5 / 2.25 / 3.0 pip round-trip costs remain diagnostic stress only;
- no live/paper attachment;
- no promotion or professional-performance claim is permitted;
- a Model-0 run, if accepted by AlphaFactory, may answer engineering,
  signal-cadence, and diagnostic economics only. It cannot satisfy the final
  cost gate.

## Outcome seal declaration

At freeze time the post-news source compiled with 0 errors and 0 warnings and
the static/data tests passed. No Strategy Tester report, trade ledger, PF,
expectancy, cadence, drawdown, or outcome series for either V2 arm had been
opened. A good result may not revive the killed `EA_FVGConfluence` hypothesis.
