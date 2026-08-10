# HYP-ST-XAUUSD-H1-002 — Independent post-source review

Status: `PASS_BUILD`  
Scope: read-only artifact and ledger audit; no outcome access.

## Artifact integrity

- Attempt start: `EEFDBE05A2AD48F8A804481A96ABA2C26DD0801220D29221574A387C8DF33CA5`
- Attempt terminal: `8FB31CB5777B0C183DAF17CBBDC18B72FF038D5F539EABA5167A9FD698A8EEF1`
- Source receipt: `2AA9EBF1BF6765AE9D7AE9F0136515ABD965C7CD43463C7432055023C8C8BCA6`
- Event ledger: `6689F69B1EB28A6617F4555656C2237669B4A9B0FF0D886D84234AD4427FC666`
- Source report: `ED232FD4CB6761A727D93FC03E6CC5BD8B7C2D275A0B93A0984F5AEFA1DA2B2F`
- Preregistration: `FF23C8FDD5BDCD4B25AC02A46D984D2B9815A099BD92FB47E4F565DF404668D8`
- Analyzer: `9B44FDCFEA2BC944E4CC70B3C0C9D92E0899BC6F4A9EDE1ECE4AF933F20EAF3B`
- Tests: `D502E6E9379CA81CD56A374A77ADCA8FBDF6C31F8E4F282182EC77916A69BAD7`
- Frozen formula dependency: `2B48F3AA01BB2B00EB66A5AE97346F810EF549CEC2626B0DC9F175EEC890211C`

Receipt and terminal bindings reconcile. The receipt binds the exact pre-run registry snapshot and ST002 authority row, every package/source/output artifact, and hard-zero outcome counters. Terminal verdict and timestamps agree with the receipt.

## Independent ledger audit

The ledger contains 683 unique strictly ordered design events under the exact 11-field allowlist: 339 LONG and 344 SHORT, with annual counts 147/140/109/144/143. Every decision is exactly one hour after the source timestamp. Every numeric field is finite, ATR is nonnegative, semantic transition and direction agree, source close strictly crosses the current active flip band, and the Supertrend line has the correct state identity. No equality or duplicate event exists.

Report arithmetic reconciles: 100% design feature coverage, 683/690 exact-next coverage, seven consumed gaps, 2.618291 events/week, direction shares, yearly shares/cadence and every gate. The seven intentionally non-persisted raw gap events cannot be audited row-by-row, but the coverage gate passes and deterministic hash-bound analysis supports the count.

## Mandatory MQL5 parity hazards

1. Rebuild full native H1 chronology from exact manifest inception `2004-06-11T04:00:00Z`; fail if unavailable and never seed at tester start/2018.
2. Implement exact TR, SMA10 seed and `(9*prior+TR)/10` directly. Do not assume `iATR` seed parity.
3. Calculate oldest-to-newest despite MQL5 series conventions; use only completed bars; initialize `DOWN` without emitting a flip.
4. Preserve operation/update order, prior-close references, strict comparisons and raw double precision. Do not normalize, round, epsilon-adjust or algebraically reorder the RMA.
5. Accept `H=L=C`, retain state through flat bars, allow ATR zero/coincident bands, and resolve prior line identity with the upper branch first.
6. Never clamp/reorder bands. At least one valid ledger flip has final upper below final lower (`2019-06-30T22:00:00Z`).
7. Carry state across normal closures/gaps without synthetic bars. Consume a non-exact-next flip rather than queueing it.
8. Map broker/server time to the frozen UTC source axis exactly.
9. Parity must compare every bar's ATR, bands and state plus every flip timestamp/direction, not only event totals.
10. Make no native `iSuperTrend` claim.

## Authority boundary

After terminal registry authorization, a separately reviewed direct MQL5 implementation and MT5-native correctness/parity harness may proceed. No orders, costs, returns, PF, validation, holdout, optimization, paper/live or economic claim is authorized.
