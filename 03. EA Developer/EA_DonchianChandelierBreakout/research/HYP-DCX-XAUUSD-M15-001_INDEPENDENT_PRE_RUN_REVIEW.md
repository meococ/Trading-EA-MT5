# HYP-DCX-XAUUSD-M15-001 independent pre-run review

Verdict: `PASS_ONE_BASELINE`

Two independent static passes were obtained after the final execution hardening. The accepted exact source is `A4BE71F1A1F98DCDE3C181C8BDF60017CA981816F0871D5CAC281565132FB94F`.

- Donchian indexing is completed-bar causal: release bar excluded from its prior 20-bar channel, prior/current transition exact, decision at next M15 open.
- ATR22 and Chandelier22x3 use completed bars only and the stop only tightens.
- A newly crossed Chandelier level closes at market; an uncrossed broker-too-close level retains the prior protective stop.
- Position/order/property uncertainty fails closed; FOK is mandatory and only DONE is accepted.
- Compile is 0 errors / 0 warnings, the EX5 is nonempty, six source-contract tests pass, and the exact-source non-repaint audit is PASS.

Authority is limited to one untuned XAUUSD M15 Model-0 train baseline for 2010-01-04 through 2018-01-01. Validation, holdout, optimization, cost stress, paper and live remain closed.

