# HYP-ST-XAUUSD-H1-002 — Source-feasibility result

## Verdict

`SCREENED_SOURCE_PASS_MQL5_DIRECT_SUPERTREND_BUILD_AUTHORIZED`

The sole outcome-blind source attempt completed durably and passed every preregistered gate. This authorizes only direct MQL5 formula implementation and MT5-native correctness/parity work. It does not authorize orders, outcome analysis or an economic claim.

## Funnel and gates

- Source rows from manifest inception through 2022: 107,679
- Design rows / feature-usable design rows: 29,461 / 29,461 (100%)
- Raw / executable / exact-next-gap-consumed flips: 690 / 683 / 7
- LONG / SHORT: 339 / 344 (49.63% / 50.37%)
- Pooled cadence: 2.618291 per elapsed week
- Exact-next coverage: 98.9855%
- Maximum year share: 21.5227%
- Annual events: 147 / 140 / 109 / 144 / 143 for 2018–2022
- Annual cadence: 2.8192 / 2.6849 / 2.0847 / 2.7616 / 2.7425 per week
- Direction conflicts: zero
- Every frozen gate: pass

## Evidence

- Attempt start SHA-256: `EEFDBE05A2AD48F8A804481A96ABA2C26DD0801220D29221574A387C8DF33CA5`
- Report SHA-256: `ED232FD4CB6761A727D93FC03E6CC5BD8B7C2D275A0B93A0984F5AEFA1DA2B2F`
- Event ledger SHA-256: `6689F69B1EB28A6617F4555656C2237669B4A9B0FF0D886D84234AD4427FC666`
- Receipt SHA-256: `2AA9EBF1BF6765AE9D7AE9F0136515ABD965C7CD43463C7432055023C8C8BCA6`
- Attempt terminal SHA-256: `8FB31CB5777B0C183DAF17CBBDC18B72FF038D5F539EABA5167A9FD698A8EEF1`

The receipt binds the preregistration, analyzer, frozen ST001 formula dependency, manifest, H1 dataset, exact pre-run registry snapshot, report, ledger and attempt marker. Same-frame replay was byte-identical. All outcome counters are zero.

## Independent reconciliation

Independent ledger audit reconciled all 683 unique ordered events, the exact 11-field source-only schema, every `+1h` decision timestamp, LONG/SHORT semantic transitions, strict active-band crossings, line identity, yearly counts and report arithmetic. The event-only ledger cannot independently recreate the entire recursive bar path, but the exact formula dependency is hash-bound and rechecked at execution, and deterministic replay matched.

## Build boundary

The MQL5 implementation must rebuild from the exact 2004 source inception, calculate oldest-to-newest, implement TR and the SMA-seeded Wilder RMA directly, preserve strict operation order/full double precision, accept flat bars and ATR zero, use upper identity first for coincident bands, never reorder crossed bands, carry state across closures, and consume non-exact-next flips. Broker server timestamps must be mapped to the frozen UTC source axis using the canonical FivePercent clock model. Parity must cover every bar's ATR/bands/state plus event identity, not just the 683 flips.

No native Supertrend handle exists in the frozen contract. No trade, return, PnL, PF, cost, validation, holdout, optimization, promotion, paper or live conclusion is authorized.
