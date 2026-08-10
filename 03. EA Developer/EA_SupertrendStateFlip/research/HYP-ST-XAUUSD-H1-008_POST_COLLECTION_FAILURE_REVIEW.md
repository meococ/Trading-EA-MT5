# HYP-ST-XAUUSD-H1-008 - independent post-collection-failure review

Status: `PASS_KILL_HYP008`

The HYP008 MT5 run is engineering-valid through compilation, data-quality and
MQL summary generation. Its manifest-bound journal delta contains two identical
current summaries, exact counters and no current fatal. The common CSV has the
expected 29,460 rows and exact first/last/next epochs.

The consumed collector failed because it scanned the entire daily tester log,
which also contains HYP007's earlier fatal and zero-row summary. The failure
occurred before the three intended run-local writes; no collection receipt or
comparator evidence exists.

Verdict: kill only `ST008-ARTIFACT-COLLECT-001` and close HYP008. This does not
kill the completed HYP008 MT5 run, source, formula, data-quality evidence, CSV
or any economic edge. Parity remains unproven and economics remain unopened.

A fresh HYP009 artifact-recovery child is legal after HYP008 is terminal. It
must not rerun MT5/Alpha/MetaEditor. It may use one fresh collection ID and one
fresh comparator ID, bind all exact HYP008 hashes, use only the manifest-bound
run-local delta, require one or more identical exact summaries, reject any
distinct summary/current fatal, and seal mutable artifacts exclusively into a
fresh HYP009 evidence root before parity.
