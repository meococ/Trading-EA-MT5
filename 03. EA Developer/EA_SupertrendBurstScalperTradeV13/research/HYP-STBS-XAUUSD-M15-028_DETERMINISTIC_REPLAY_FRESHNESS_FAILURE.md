# HYP028 Deterministic Replay Freshness Failure

- Verdict: `KILL_DETERMINISTIC_REPLAY_VOLATILE_FRESHNESS_PROVENANCE_MISMATCH_NO_ECONOMIC_VERDICT`
- Attempt: `STBS028-COMPARATOR-001`
- Status: `FAILED`; same-ID retry is forbidden.

## Exact failure radius

The sole comparator-only attempt durably claimed its evidence root, verified the terminal HYP027 chain, emitted a PASS runtime non-repaint artifact, emitted a verified research-proxy cost artifact, and completed two frozen unified-validation invocations. It then failed before a comparison result or receipt because the two stable projections retained invocation-owned freshness provenance.

An independent recursive comparison found exactly 13 differences: eight `after.mtime_ns` values, two `producer_result.elapsed_s` values, and three `after.sha256` values for the generated `execution`, `monthly_fitness`, and `overnight_exposure` artifacts. Removing only those exact volatile locations makes the projections byte-semantically equal; the normalized projection SHA256 is `5C3F9B5FC7AE761441B2A754C7E64FCC21DDCBEF917883CCEE07FC6024CD0702`. Every gate status, freshness classification, producer status, return-code semantic and verdict field otherwise agrees.

No comparison result, comparison receipt or authoritative economic verdict was created. This failure therefore does not authorize an economic PASS or FAIL.

## Immutable evidence

- Authorized HYP028 raw row SHA256: `6533F2ABED6ABF392C8F5151F5105433B53D94984E142A4F19929D82EAAB848B`
- Registry snapshot at claim SHA256: `22D11CDC3B5827590B50F7082E8F423EC6C0D0977B0ADC37F8FAF3E8C284D558`
- Attempt start SHA256: `FBEB5A736AC44E1464BD7F6A8FEF71D9C858F91DE9434CEA0AE00B3B9FD43E43`
- Failed terminal SHA256: `7308F0779C3A92D296F9AA497AFC98B9CBC4035B124014934726C1A6AA9EC922`
- Unified summary A SHA256: `F9C39982431963AECB278BD02FDFFDB4D2844EBE7187BD2762B54F04E74298F2`
- Unified summary B SHA256: `86311C8F0251CD9AEDD5CA2C9ED95C14F9741C650A42828DC3B47F12E07F0BA8`
- Runtime non-repaint audit SHA256: `47F5A65BC4853D89A38DD17F6B64E9BE6E7CCFC551F8F296ACE56E26FA44CE9F`
- Verified cost artifact SHA256: `C279E47CC54E3F8D1ECAD7DC4FCFB40E6EA79D478FDC770B59221AF2F5C7C989`
- Derived sealed run manifest SHA256: `869784F02C7D697035EFAFBED7511B2A942DA12848B8399315D8FB43E2B447D3`
- Derived cost manifest SHA256: `C166DE04C6002AB9DEE2A58F145A2F36E57D64A964FF819B09814D152B4BA25F`

The failed terminal inventories 89 attempt artifacts with zero rehash mismatches and records `mt5_launched=false`, `compile_executed=false`, `source_market_data_opened=false`, `new_orders_or_fills_created=0`, `economic_verdict_created=false`, and `same_id_retry_authorized=false`.

## Opportunity-cost decision

The sealed summaries expose non-authoritative diagnostics that are far from the project target: 464 completed positions, 1.7807 trades/week, research-proxy PF x1 `0.3309`, x1.5 `0.1993`, x2 `0.1218`, x1 expectancy `-0.5895R`, every calendar year nonpositive, and Monte Carlo p95 drawdown `9.0524%`. Operational gates are also blocked or failed. These values are not promoted to a terminal economic verdict, but they make another comparator-only recovery a poor use of research time.

HYP029 is therefore not opened. The exact Supertrend-10x3 flip plus M15 ATR burst lane is abandoned without an economic claim, and the active EA goal continues with a materially new strategy mechanism.
