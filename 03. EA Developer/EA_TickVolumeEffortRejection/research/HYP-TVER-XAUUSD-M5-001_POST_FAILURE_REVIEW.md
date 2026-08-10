# HYP-TVER-XAUUSD-M5-001 — Independent Post-failure Review

Date: 2026-08-09  
Reviewer: read-only sub-agent `t2_campaign_audit`  
Verdict: `PASS_PARK`

The reviewer changed no files and accessed no post-event OHLC, performance, validation or holdout data.

## Integrity

The one-shot chain reconciles:

- preregistration `047F5BD7…C04F17`;
- analyzer `DDF4EC4C…B8D6C`;
- manifest `D2F48E9C…3AD23` and declared dataset `12679E64…0D380`;
- attempt start `D3B6315D…03F46`;
- source report `F99E5441…5BCF2E`;
- candidate ledger `89822CF5…9E5D8`;
- source receipt `371B3FA8…F9F30`;
- terminal receipt `F419C8BF…2C94C`.

The terminal receipt binds the source receipt. The source receipt binds all inputs, outputs and the exact pre-run registry row SHA `67F0D6D4…DFE14`.

## Independent source-only replay

- 141 unique, time-ordered rows: 79 LONG and 62 SHORT;
- every decision timestamp equals the completed source-bar timestamp plus five minutes;
- zero threshold or allowed-field violations;
- yearly counts: 48 / 17 / 42 / 13 / 21 for 2018–2022.

Gate arithmetic matches the canonical report:

- design rows: 351,303 — pass;
- feature coverage: `350,916 / (351,303 - 15) = 0.998941` — pass;
- exact-next coverage: `349,627 / 350,915 = 0.996330` — pass;
- direction shares: 56.03% / 43.97% — pass;
- candidates: 141 versus minimum 500 — fail;
- pooled cadence: `141 / 260.8571 = 0.540526/week` versus 2–5 — fail;
- maximum year share: `48 / 141 = 34.04%` versus at most 30% — fail;
- every yearly cadence is 0.249–0.921/week versus minimum 1.25 — fail.

`PARK_SOURCE_FEASIBILITY_EXACT_TVER_MAPPING` is mandatory. This is a source-population infeasibility verdict for the exact frozen mapping, not an economic no-edge conclusion.

## Next lane recommendation

Open a fresh source-only `HYP-MFI-XAUUSD-M5-001` using the TradingView-documented MFI14 calculation and native MT5 tick volume:

- typical price `(H+L+C)/3`;
- raw flow `typical_price * tick_volume`;
- positive/negative classification solely by completed typical-price change;
- exact rolling 14-bar MFI;
- LONG only on completed-bar re-entry from `MFI <= 20` to `MFI > 20`;
- SHORT only on completed-bar re-entry from `MFI >= 80` to `MFI < 80`;
- decision at the following M5 open with timestamp-only continuity proof;
- no wick, ATR, RV, session, filter, debounce or outcome.

This is a single volume-price oscillator state transition. On XAUUSD CFD it must be described only as tick-volume-weighted MFI, not true money, exchange volume or aggressor flow.

