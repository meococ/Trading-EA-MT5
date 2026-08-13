# Sonic calendar recovery frontier and AlphaFactory input escrow

Date: 2026-08-13  
Goal status: `ACTIVE / UNMET`  
Market-run status: `NOT OPENED`

## Decision

The EA goal is not globally infeasible. Only the frozen historical SonicR replay
is unavailable under current local evidence. Its required calendar object was:

- `FILE_COMMON/SNR_FX_EVENTS.csv`;
- SHA256 `b62eab34e6630f6255f97aedc280bde438d53ef1643ef1ee29effc9f5d6634c7`;
- 34,630 bytes, 448 events;
- coverage `2019.01.04 15:30:00` through `2026.12.25 15:30:00`;
- classes `CPI,FOMC,GDP,NFP,PCE,RATE`.

The bounded verdict is `EXACT_RECOVERY_NOT_PROVEN`. This does not imply that
Sonic R, XAUUSD/Forex, or all future sources have no edge.

## Full-byte forensic boundary

The recovery pass checked exact filenames, known file sizes, renamed candidates,
task-owned artifacts, workspace roots, MetaQuotes Common Files, likely user
storage roots and Recycle Bin. No object matched the bound SHA256. Codex session
receipts show the 34,630-byte file existed through at least 2026-07-08, but their
tool output contains only file metadata and fragments, not the complete 448-row
payload. Reconstruction from fragments, using the old 342-byte fixture,
regenerating a different calendar, or disabling the news gate would create a
different tested object and is forbidden.

The Owner's FivePercent terminal PID 42864 was not interrupted or repurposed.
No compile/backtest outcome, optimization, OOS, live action, purchase or Git
operation was opened by this pass.

## Independent Grok Build decision

The first bounded call exceeded its one-turn finalization contract and was not
accepted. A finalize-only retry completed with schema-valid `end_turn`:

- verdict `EXACT_RECOVERY_NOT_PROVEN`;
- prospective verdict `NO_LAWFUL_PROSPECTIVE_CANDIDATE`;
- candidate `null`;
- response SHA256
  `B5C9C6A64C55CAF5AF162A1C817F3AFC6D603A7BC3F2BF97F189A0C00EB77E2C`;
- summary SHA256
  `4EFCFEF8828AA7C751E5F5D26369B754355AB1A0F847450AF35B0C851361DDD1`.

Accepted artifacts:

- `.context/grok-sonic-recovery-prospective-decision-20260813/run2/grok-response.json`
- `.context/grok-sonic-recovery-prospective-decision-20260813/run2/summary.json`

Lead accepts the result only within the supplied local-evidence boundary. It
forbids a reconstructed/proxy replay and another Sonic/Dragon/Trend/PVA/SMC or
sweep child mined from known outcomes. It does not authorize a global no-edge
claim.

## Root-cause correction: prospective input escrow

The historical run preserved a calendar hash in RunMeta but did not preserve
the input bytes inside the run artifact. AlphaFactory now closes that evidence
gap prospectively:

1. Task packet optionally binds `required_input_artifacts` records containing
   `source=FILE_COMMON`, a safe basename and SHA256.
2. The research loop binds the list into the execution receipt and passes it to
   `alpha.ps1`.
3. Before launch, AlphaFactory requires the exact Common Files object and hash,
   copies it to `runs/<EA>/<run_id>/inputs/<name>`, and verifies the snapshot.
4. Source and snapshot are rehashed immediately before MT5 launch and again at
   manifest completion. Path escape, missing file, hash mismatch, duplicate
   basename, source mutation or snapshot mutation fails closed.
5. The manifest records `required_input_artifacts`, `input_artifacts`, and
   `input_artifacts_sha256`. MT5 price/history `data_fingerprint` remains a
   separate identity to preserve existing semantics.

Implementation evidence at this checkpoint:

- `02. AlphaFactory/alpha.ps1` SHA256
  `523B164ACD6EB480D6268E5A0A61A7899D2D4D62CD1C0A6A94B2863BA583E75E`;
- `02. AlphaFactory/tools/research_loop_engine.ps1` SHA256
  `550C4E457B6FA397402153733C681B37EC1EA8C0792326E37FEB7D5F4BBF8A07`;
- `02. AlphaFactory/tests/test_input_artifact_escrow.py` SHA256
  `FB8C17A06783EFA7FF5CA556FFCDCF3B0D2271D9A5AE2A21B7D2DA5B5362A409`.

Verification:

- PowerShell parse: `alpha.ps1` 0 errors;
- PowerShell parse: `research_loop_engine.ps1` 0 errors;
- input escrow plus forced-no-Git tests: `8 passed`;
- legacy execution-receipt compatibility tests: `2 passed`;
- canonical active-package discovery test: `1 passed`.

## Next lawful lane

Run a metadata-only, outcome-blind inventory/de-dup of local XAU/Forex payloads
and source capabilities. If no materially new PIT/source object exists, return a
scoped `NO_CANDIDATE` and continue capability/source intake. Do not open a
baseline until a new source contract, mechanical sign, preregistration and
untouched outcome window exist.
