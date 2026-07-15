# NO-GIT provenance for AlphaFactory Get-GitSnapshot

Updated: 2026-07-13

## Why

Root `d:\Trading EA MT5` is intentionally **not** a Git work tree (empty `.git` placeholder). Prior `Get-GitSnapshot` called `git rev-parse HEAD` and threw, which blocked `Assert-ContractReceipt` and therefore Model 0 backtest.

## Fix (fail-closed, not weakened)

In `02. AlphaFactory/alpha.ps1` (mirrored in `tools/sonic_research_loop.ps1`):

1. Detect NO-GIT: `rev-parse --is-inside-work-tree` is not `true`, or `.git` is an empty placeholder.
2. Return deterministic snapshot:
   - `Commit = "NOGIT-" + SHA256(UTF8 of relativePath TAB fileSha256 lines)`
   - Provenance files (required): `AGENTS.md`, `01. GOAL/GOAL.md`
   - Plus active-lane EA when present: `03. EA Developer/EA_CarryPublicRates/EA_CarryPublicRates.mq5`
   - `Status = ["nogit=true","dirty=true","provenance_sha256=..."]`
   - `StatusSha256 = SHA256 of Status lines joined by LF`
3. **Unchanged**: `HypothesisId`, `ContractReceipt` path/SHA256, evidence hash binding, and all other receipt checks remain mandatory.

## Receipt template

`03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/contracts/20260713_HYP_CARRY_PUBLIC_RATES_D1_001_CONTRACT_RECEIPT.json`

Verified (2026-07-13): `MATCH_COMMIT=True`, `MATCH_STATUS=True` via `_verify_nogit_snapshot.ps1`.

Current receipt SHA256 (rebuild after any EA/provenance edit):

`B1F929BA47660B12975012575C0EC11DAE64C89AC74D4871F15D0665ACA94427`

Rebuild stubs + print SHA256:

```powershell
python "03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/contracts/build_contract_receipt_template.py"
powershell -NoProfile -File "03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/contracts/_verify_nogit_snapshot.ps1"
```

## Tests note

No dedicated Pester/unit test file existed solely for `Get-GitSnapshot`. This readout is the focused contract note until a small fixture test is added under `tests/`.
