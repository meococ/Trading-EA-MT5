# HYP010 independent post-failure review

Verdict: `PASS_KILL`

The sole `STBS010-COMPARATOR-001` attempt is irrevocably consumed. Its evidence root contains exactly the start and failed terminal:

- start SHA256 `595E055332AAEFFC738812F213CBDF6593FD44295548E292EEE79DAF1EAE66D6`;
- terminal SHA256 `E0CD5B3DE7A2332CBD8C4BB729B23141D29DC940F3C13A8A173D0DB8A8686AE5`.

The terminal binds the start, records `status=FAILED`, forbids same-ID retry and reports the exact `JSONDecodeError`. The frozen zero-trade summary SHA256 is `E546E60F4587CE4572AE7526BAABC737F8A65FAF7542A96359A092E893C8DA47`; its prefix is exactly `EF BB BF 7B`. The frozen HYP009 validator failed at strict `utf-8` summary reading before zero-trade summary semantics.

Completed gates were authority/parent/hash binding, exact structured compile result, snapshot/live config, manifest identity/path/hash/sidecar/geometry, and history-quality/M5-series proof. Summary semantics, Orders/funding, journal/ST003 parity, second replay, final rehash, report and receipt did not complete. No MT5/compile was launched by HYP010 and no market/economic conclusion follows.

The exact terminal verdict is `KILL_EXACT_ZERO_TRADE_SUMMARY_UTF8_BOM_DECODER_NO_PARITY_NO_ECONOMICS`.

A fresh HYP011 comparator-only child is legal if it claims a new root before bound reads, binds terminal HYP010 and all frozen dependencies, requires exactly one leading BOM only on the exact hash-bound summary, performs strict UTF-8/single-document JSON parsing, retains every other HYP010/HYP009 gate, runs deterministic dual replay/final rehash, and keeps all MT5/compile/trade/outcome/performance/economic/optimization/validation/holdout permissions false.
