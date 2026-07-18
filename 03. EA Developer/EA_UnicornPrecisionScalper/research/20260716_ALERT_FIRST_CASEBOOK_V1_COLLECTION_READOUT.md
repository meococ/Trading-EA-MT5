# ALERT_FIRST_CASEBOOK_V1 collection readout

Date: 2026-07-16  
Verdict: `PRESERVED_DIAGNOSTIC / SUPERSEDED_FOR_LABELING_BY_V1.3 / GOAL_UNMET`  
Authority: no trading hypothesis, no Model-0 performance claim, no outcome join

## What ran

- Canonical source v1.22 SHA256
  `A1AD68BC668C277D5EF85E54F61C28F0688D6FF9AC037A43368CECF45383B003`.
- Package contract tests: 44/44 PASS; collection-validator tests: 2/2 PASS;
  AlphaFactory storage tests: 4/4 PASS.
- MetaEditor: 0 errors, 0 warnings.
- Frozen receipt SHA256
  `08368C558658819BC1F775BAC7A55C9F562E5B5CEBF2CD0911A7C9BE4ACE574B`.
- Authoritative AlphaFactory run: `20260716_153059`, XAUUSD M5,
  2024-01-01 through 2025-12-25, Model 0 tester model used only as a data
  collector.

The exact overrides kept both mutation switches false, enabled only the
bounded casebook and kept lifecycle telemetry off. The run manifest proves
portable D-drive data/tester roots and `common_files_allowed=false`.

## Result

The Strategy Tester report contains exactly zero trades. AlphaFactory's
zero-trade acquisition branch therefore skipped economic analysis and emitted
an explicit `performance_metrics_authorized=false` summary.

- Detector rows: 200/200.
- Unique event IDs: 200.
- Nonblank human-label/outcome cells: 0.
- Casebook SHA256:
  `D96F556493DE008C0280907386488411D557451D8C507E1D46B6A05CB48A091E`.
- Metadata SHA256:
  `69411C34B82C80A7CEA14BB4DDC658BEADB7ACE0958E452E7256F3C7C0C966B8`.
- Run manifest SHA256:
  `FF46E443AF43F72911DE79D254F33071FFE61DC30A2D1D243C7AF14052DFC637`.
- Validator artifact SHA256:
  `59A955983A8FBCB291C40E79A266DD98C4565B30870B949835E415FD8F403956`.

The earlier run `20260716_152855` produced the same bounded sidecars but failed
after collection because the economic analyzer rejects a zero-trade report.
That exposed a harness gap. AlphaFactory now collects receipt-bound custom
sidecars, permits telemetry-off lifecycle packages without demanding lifecycle
trade logs, and accepts the special data-acquisition authority only when the
report itself proves exactly zero trades. The repaired run above is the sole
authoritative collection.

## Storage proof

All four protected C-drive roots are identical before and after by file count,
bytes and metadata SHA256:

| Root | Files | Bytes | Metadata SHA256 |
|---|---:|---:|---|
| Terminal Common Files | 137 | 20,008,308 | `B4C0D81C...E63DC` |
| Named terminal Tester | 120 | 1,260,063,754 | `774D3CEB...D5A3C` |
| Roaming MetaQuotes Tester | 882 | 6,847,158,854 | `E970F243...C63B` |
| ProgramData Tester | 0 | 0 | `E3B0C442...B855` |

Before snapshot SHA256:
`A3B3BB8A6BF24AD4CCD34B533D28201A4ABE48CD84E5C3A14C330933EBE9B4CA`.
After snapshot SHA256:
`3F4EF7B28537A179E523B8DCC4023D7045F21095D3D66BFB7B2760A2D55F71B9`.
The snapshot files differ only in generation time; every protected-root record
is identical. MT5 is stopped and no global backtest lock remains.

## Decision

The acquisition gate passes, but the economic research gate does not open.
These are detector alerts, not 200 profitable trades and not 200 labels. The
next Unicorn gate still requires at least 100 independently reviewed labels,
predeclared agreement analysis, and a separately sealed outcome-analysis plan.
No MSS/BOS/FVG/retest feature, threshold, session or RR change is authorized.

Workspace `GOAL.md` remains unmet. This collection cannot be included in PF,
cadence, cost stress, exposure, Monte Carlo, train/holdout or promotion claims.

## V1.3 supersession

This V1.2 run remains valid evidence that the detector can collect 200 bounded
zero-trade alerts on portable D storage. It is no longer valid input to the
human-label gate because the rows and metadata do not bind the source SHA256
and the schema omits the true-breaker validity label required by the fidelity
audit. It was not deleted or rewritten. The authoritative labeling corpus is
now the V1.3 collection described in
`20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_READOUT.md`.
