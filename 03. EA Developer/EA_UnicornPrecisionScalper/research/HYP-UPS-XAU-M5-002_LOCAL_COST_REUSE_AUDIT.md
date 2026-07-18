# Local cost-reuse audit — HYP-UPS-XAU-M5-002

## Verdict

`NO_ADMISSIBLE_LOCAL_SLIPPAGE_EVIDENCE`.

The full local AlphaFactory run history contains a useful FivePercent XAU
tester-commission clue, but it does not contain promotion-eligible independent
slippage evidence. It therefore cannot clear the frozen Model 0 cost gate.

## Inventory boundary

- `runs_db.py build`: 277 indexed runs, 53 skipped, 0 errors.
- Direct manifest/report scan: 52 XAUUSD runs.
- Report identity split: 29 `FivePercentOnline-Real (Build 5961)` / Five
  Percent Online Ltd; 23 `MetaQuotes-Demo (Build 5836)` / MetaQuotes Ltd.
- Nineteen XAU runs contain legacy PX6 execution/trade sidecars.

The direct manifest/report scan is used for the identity count because the
SQLite catalog is only an index and intentionally skips incomplete runs.

## Strongest same-broker tester clue

Source run:
`02. AlphaFactory/runs/EA_SonicR/20260705_022757`.

- Report identity: `FivePercentOnline-Real (Build 5961)`, company Five Percent
  Online Ltd, account currency USD, XAUUSD M5, Model 0.
- Entry fills: 335 = 171 BUY + 164 SELL.
- Final-close commission rows: 335 across 335 unique position IDs.
- Observed tester round-turn commission per lot: P50 `2.00`, P90 `3.25`,
  minimum `1.60`, maximum `4.40` account-currency units per lot.
- Entry request/fill differences: 335 zeros; no non-zero entry-slippage row.

Hash-bound source artifacts:

- `report.html`: `FC174B3C26847AA8EDFA912457A7AAB4AE852BCD53943141C7154D939ED8DA10`.
- `run_manifest.json`: `802CB56EB83A73EA4D76EBFC3A38462A5C5AA6FE8AB58B60785CED3099E127DE`.
- PX6 Exec CSV: `D90F3735DD725B979FF8E7C50CF20265A9C7C2AEA8034A7CA828EF9B97A15E70`.
- PX6 Trades CSV: `ADA1EFFD4A5EA8B5AF3FFF29343F8F616B707FD3F4D788F54209E66AB41855B1`.
- RunMeta JSON: `0DC1E1C285D60835F094A4AAA08F7EBA0E0AE76F54D84B88247B1681971E0506`.

## Why the clue is not VERIFIED cost provenance

1. The source is a Strategy Tester simulation, not account-history/QFSI
   execution. A tester-observed zero does not prove real slippage is zero.
2. The legacy run manifest does not bind hypothesis, preregistration, source
   SHA256, EX5 SHA256, include closure, or broker/account/data fingerprints.
3. PX6 is not the required lifecycle-v3 sidecar contract and has no
   report-bound `deal_fee`/`deal_net` lifecycle reconciliation artifact.
4. The Exec CSV has second-resolution `event_time` plus `request_price` and
   `fill_price`, but lacks `reference_time_msc`, `request_time_msc`,
   `fill_time_msc`, reference age, and an independently captured BID/ASK row.
5. A later Git source blob shows that `request_price` was refreshed BID/ASK
   immediately before `CTrade.Buy/Sell`, but that source is not snapshotted or
   hash-bound by the 20260705 run. Post-run source similarity is not run proof.

The post-run source clue is Git commit
`b709309f8aa901a6e6f06beba1acaeedb44f0e6d`, blob SHA1
`af80b7bbb9f5b735c036624fba10455c0f5dc32e`, content SHA256
`0ACFC92D93E772C54E72D93BAA1103A59D47CB99890EEE7BA33AACAA1776F0BB`.

## Remaining external input

- At least 100 XAUUSD fills with contemporaneous independent BID/ASK
  references and decision-safe timestamps, including at least 30 BUY and 30
  SELL samples.
- At least 30 XAUUSD commission lifecycles from account history/QFSI, or an
  Owner-approved explicit broker contract. The tester P90 above is a clue, not
  a silent substitute.
- Regenerate one FivePercent-bound task packet only after the evidence belongs
  to the same broker/account/data scope.

No order was sent, no Strategy Tester run was started, and no C-drive tester
cache was created by this audit.
