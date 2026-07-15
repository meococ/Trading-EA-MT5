# Session Anchor

Updated: 2026-05-01

Read this first, then `04. Project Control/hot.md`.

## Active frontier

- Active research lane is `EA_SonicR` only.
- All other EA projects are archived or parked and must not be treated as active unless ngài explicitly reopens them.
- New Sonic R tests use MetaQuotes-Demo symbols such as `XAUUSD`, `EURUSD`, and `GBPUSD`; E8 plus-suffix runs are historical context for this branch.
- Current Sonic R evidence is research-only. Do not promote to demo, prop, or live from PF alone.

## Active EA

- `EA_SonicR` | source: `03. EA Developer/EA_SonicR/EA_SonicR.mq5`
- Includes: `03. EA Developer/EA_SonicR/Include/SNR_*.mqh`
- Research notes: `03. EA Developer/EA_SonicR/research/`
- Retired/legacy EA source and runtime EA caches belong under `00. Old File/EA_Archive/`.

## Current Sonic R evidence

- Longer-horizon XAUUSD M5 research candidate: `20260501_000718`, Model 0, 282 trades, PF about `1.32`, but `validate-full` remained `REVIEW 0/5`.
- Engineering smoke after cleanup/hardening: `20260501_012639`, telemetry-on, Model 1, 10 trades. This proves sidecar/risk plumbing, not strategy edge.
- Latest hardening note: `03. EA Developer/EA_SonicR/research/20260501_SONICR_ENGINEERING_HARDENING_SMOKE.md`.
- Invalid run to exclude: `20260501_221111`, compiled from archived `00. Old File/EA_Archive/EA_SonicR` instead of canonical source.
- Latest diagnostic: `20260501_230200`, XAUUSD M5 Model 0 with S1 execution off, 87 trades, PF `1.4496`, net `$79.43`, but lower net/cadence than `20260501_000718` and still `validate-full REVIEW 0/5`.
- Current S1 decision: keep `XAU_S1_SWEEP_RECLAIM` as scanner/casebook material only; current executable S1 evidence is noisy and cost-fragile.

## Durable rules

- AlphaFactory is the canonical compile/backtest/analyze lane: `02. AlphaFactory/alpha.ps1`.
- Confirm `run_manifest.json` `main_file` points to `03. EA Developer/EA_SonicR/EA_SonicR.mq5` before citing a run.
- Use `validate-full` as the deployment-readiness gate; PF is only a research signal.
- Keep closed-bar discipline: no bar-zero price/buffer decision logic.
- Telemetry-on Sonic R runs need a non-empty `InpVariantTag` or sidecar hygiene will fail.
- After meaningful backtest batches, run archive-first cleanup for stale `Terminal/Common/Files` telemetry and old run artifacts. Preserve cited evidence and manifests.
- `EA_SonicR` is reconstructed Sonic R/PVSRA parity research, not proven original-source parity.

## Memory fragments

- `04. Project Control/memory/2026-04-10.md` - historical portfolio memory only; not current Sonic R routing truth.
