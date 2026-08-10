# HYP010 exact summary-BOM comparator failure

Verdict: `KILL_EXACT_ZERO_TRADE_SUMMARY_UTF8_BOM_DECODER_NO_PARITY_NO_ECONOMICS`

## What happened

The sole authorized `STBS010-COMPARATOR-001` attempt claimed its immutable evidence root, passed HYP010 authority and parent binding checks, accepted the exact structured MetaEditor result (`0 errors`, `0 warnings`, `722 ms`, CPU `X64 Regular`), and entered the unchanged HYP009 run validator.

That validator then failed at `json.loads(summary_path.read_text(encoding="utf-8"))`. The exact frozen `enhanced_summary.json` begins with bytes `EF BB BF 7B`; Python's strict `utf-8` text decoder preserves the BOM character and `json.loads` rejects it. The correct exact decoder for this already-frozen AlphaFactory artifact is `utf-8-sig`.

## Exact evidence

- HYP010 screened authority raw SHA256: `5FC3C4B315318ECB30B39DE89291A4EBDA1EE5969B35EC6E50290C35121AD289`.
- Attempt start SHA256: `595E055332AAEFFC738812F213CBDF6593FD44295548E292EEE79DAF1EAE66D6`.
- Failed terminal SHA256: `E0CD5B3DE7A2332CBD8C4BB729B23141D29DC940F3C13A8A173D0DB8A8686AE5`.
- Frozen summary SHA256: `E546E60F4587CE4572AE7526BAABC737F8A65FAF7542A96359A092E893C8DA47`.
- Attempt root contains exactly `attempt_started.json` and `attempt_terminal.json`; no comparator report or receipt exists.

## Gate boundary

Before the BOM failure, the comparator completed parent/authority/hash checks, structured compile-result validation, exact config validation, manifest identity/path/hash/sidecar/geometry checks, and the manifest data-quality/history/M5-series-proof predicate. It did not complete zero-trade summary semantics, Orders/funding checks, journal signal normalization, ST003 oracle clock/direction/geometry parity, or deterministic full replay.

No MT5 or compile process was launched by HYP010. Bound artifacts were hash-read and the summary was unsuccessfully decoded, but no Orders, trades, post-event outcomes, returns, PF, costs, optimization, validation or holdout data were semantically parsed or evaluated. This failure rejects only the exact HYP010 summary decoder; it says nothing about the EA's engineering parity or market edge.

## Next legal lane

HYP010 is consumed and must not retry. A fresh comparator-only child may retain the exact structured compile recovery and every unchanged HYP009/HYP010 gate, adding only a strict decoder for the exact hash-bound summary: require exactly one leading UTF-8 BOM and no additional/interior BOM, decode through strict `utf-8-sig`, reject invalid encoding or trailing/multiple JSON documents, require the same zero-trade summary schema/counters, and then continue all report/journal/oracle gates. It must use a fresh attempt ID, claim before bound reads, pass independent review, and keep all MT5/compile/trade/outcome/performance/economic permissions false.
