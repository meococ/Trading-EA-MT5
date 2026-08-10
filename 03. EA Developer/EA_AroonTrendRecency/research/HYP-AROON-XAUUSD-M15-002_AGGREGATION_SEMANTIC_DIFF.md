# HYP-AROON-XAUUSD-M15-002 — Aggregation Semantic Diff

Parent formula analyzer: `analyze_aroon_m15_source.py` SHA256 `6E2383CE15074890905AFC6AAF2E6D0D9893FBDE8B414850F28F12A08F100CF0`.

Revision analyzer: `analyze_aroon_m15_source_v2.py`; its final SHA256 is bound separately by the registry authority to avoid a self-hash cycle.

Allowed changes:

- replace Python iteration over each M15 group with vectorized `groupby` transforms and aggregation;
- add durable phase-only checkpoints and a caught-failure terminal;
- bind the parent terminal/failure/start evidence and frozen formula dependency.

Unchanged by dependency reuse:

- source validation and sealed predicate;
- Aroon period, length+1 window, most-recent tie rule and formula;
- polarity crossover and exact-next execution mapping;
- event ledger allowlist, design window, gate thresholds and outcome-blind prohibitions.

Equivalence and integrity proof: `22 passed`, including complete triplets, every missing offset, inception offset-zero rejection, duplicate/extra offsets, UTC gaps, invalid geometry, missing market-closure bucket, half-open design boundaries, exact formula-output bytes, a 100,000-bucket vectorized throughput fixture, and bound-input mutation failure before receipt. The legacy implementation and vectorized implementation return identical frames on every bounded comparable fixture.
