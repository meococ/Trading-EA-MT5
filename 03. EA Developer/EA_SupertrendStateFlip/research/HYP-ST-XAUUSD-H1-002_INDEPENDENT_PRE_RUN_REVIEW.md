# HYP-ST-XAUUSD-H1-002 — Independent pre-run review

Status: `PASS`  
Scope: static review only; no source data or analyzer execution.

## Authoritative package

- Preregistration SHA-256: `FF23C8FDD5BDCD4B25AC02A46D984D2B9815A099BD92FB47E4F565DF404668D8`
- Analyzer SHA-256: `9B44FDCFEA2BC944E4CC70B3C0C9D92E0899BC6F4A9EDE1ECE4AF933F20EAF3B`
- Tests SHA-256: `D502E6E9379CA81CD56A374A77ADCA8FBDF6C31F8E4F282182EC77916A69BAD7`
- Frozen ST001 formula dependency SHA-256: `2B48F3AA01BB2B00EB66A5AE97346F810EF549CEC2626B0DC9F175EEC890211C`
- Combined ST001/ST002 test result before review: 22 passed.

## Verdict

No fatal pre-run blocker exists. The only source-contract change from terminal ST001 is finite `high >= low` with close inside the range. These inequalities force `H=L` to imply `H=L=C`. No row is skipped, changed or used to reset state.

The hash-bound dependency preserves exact TR0, SMA-seeded ATR10, Wilder RMA, initial `DOWN` without a flip, strict final-band update order, semantic state transitions and equality behavior. Tests cover flat bars at inception, in and around the seed, after the seed, recursive continuity, and deterministic all-flat zero-ATR/coincident-band handling.

The analyzer preserves design-only completed-bar `DOWN <-> UP` events, timestamp-only inspection of the immediately following row, exact `+1h` execution, raw-gap consumption, exact ledger allowlist, source/design coverage and every frozen cadence/balance/concentration gate.

The source path, H1 schema, manifest inception, hashes, sorted unique axes and UTC clarity fail closed. The PyArrow predicate materializes only `time_utc < 2023`; scoring is limited to 2018–2022. Same-frame analysis replays byte-identically.

Registry authority requires the terminal ST001 parent, exact analyzer/formula hashes, explicit prehistory and flat-bar permission, one unconsumed source-only attempt and false outcome/economic/validation/holdout/MT5/MQL5/live permissions. The durable exclusive marker is flushed and fsynced before data access. Receipt and terminal bind formula dependency, registry, report and event ledger.

ST002 is a legal engineering revision because ST001 stopped before indicator/event/economic analysis. A source pass may authorize only a separately reviewed direct MQL5 implementation; no native Supertrend handle or economic claim is implied.

## Nonfatal test debt

There is no dedicated fixture for an unequal close on an `H=L` row, design-start continuity, or the receipt's formula-dependency binding. The validator inequalities, uninterrupted dependency calculation and receipt construction make these code paths unambiguous; this debt does not block the sole source attempt.

Operational prerequisite: append a fresh reviewed ST002 probe row granting the exact one-attempt source-only authority. Until then the analyzer correctly fails closed.
