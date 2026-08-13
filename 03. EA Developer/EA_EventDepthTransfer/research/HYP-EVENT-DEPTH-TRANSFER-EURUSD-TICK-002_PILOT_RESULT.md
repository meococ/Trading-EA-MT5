# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-002 — pilot result

Verdict: `PASS_DEPTH_SEMANTICS` (source-only).

- Paid cost: USD 0.013034924865, below the frozen USD 0.02 ceiling.
- API calls: one cost quote, one billable-size query, one paid
  `timeseries.get_range`, zero batch calls, zero retries.
- Raw: 380,175 bytes, SHA-256
  `6E883C88321ED06DD5F4A2C223ED7D5D68A537021F43E4ED979B7F770BECF134`.
- Records: 12,862; one instrument ID; zero containment/clock violations; zero
  malformed snapshots; 100% `[T+15,T+60)` coverage; zero locked/crossed records.
- Initial 15 seconds: buyer-aggressor volume 769 versus seller-aggressor volume 484.
- Baseline: `Dbid0=373`, `Dask0=374`; weighted post-wave means:
  `Dbid1=558.7501884224222`, `Dask1=505.8153099288222`.
- Frozen score: `0.14554242854249555`; classification `CONTINUATION`, direction long.

This proves only that the corrected level-2-to-10 feature can be computed
deterministically from the contracted source. It does not test a EURUSD return,
expectancy, or market edge. No EA or MT5 authority follows from this receipt.

The raw filename retains the parent's `...150200...` label even though the DBN metadata
and receipts correctly bind the child end time to 15:01:00Z. This is a naming-only
engine defect and must be corrected in a future acquisition engine; no artifact is
renamed after hashing.

