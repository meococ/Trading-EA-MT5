# Local Self-Research Probe Batch Readout — 2026-07-13 (Owner no-ChatGPT)

Status: `ALL_KILLED / NO_SURVIVOR / NO_EA / NO_COMPILE / NO_MODEL0`  
Authority: Owner override — skip ChatGPT Deep Research; local self-research only.

## Context

- Prior weekly D1 cross-sectional carry probe remains `KILL_AT_OFFLINE_PROBE`
  (do not rescue).
- G3 rates panel + FRED mirrors on disk; Demo MT5 used for falsification only.
- No threshold edits applied to any freeze after reading its own result.

## Probes run (frozen pre-result)

| ID | Mechanism | Train tpw | PF stress-A | vs control | Verdict |
|---|---|---|---|---|---|
| Weekly D1 rank (prior) | Fri cross-section carry level | 0.05 | 1.75 | beat | KILL cadence |
| Rate-change event H4 V1a | \|Δcarry\|≥5bps → H4 (overlap bug) | ~2.22 | 1.15 | beat | **DISCARDED** (integrity) |
| Rate-change event H4 V1b | same + one pos/symbol | **1.37** | 1.12 | beat | KILL cadence&lt;1.5 |
| Carry-level H4 strip | daily level sign, hold 2 | **14.8** | 0.91 | slight beat | KILL overtrade+PF |
| US–EU DGS2−DFR shock | bond/policy wedge EURUSD | 0.57 | 0.81 | **lose** | KILL |
| COT TFF AM net Δ | positioning lag H4 | 0.92 | 0.91 | slight beat | KILL cadence+PF |

Artifacts under `preflight/v8_probe/` and freezes under `preregs/20260713_H_*`.

## Research conclusions

1. **Cadence vs edge tension on rates surface:** Sparse exogenous shocks that
   beat return controls (V1b) sit near ~1.4 trades/week after no-overlap —
   below GOAL 2–5. Dense daily carry-level strips hit cadence but die after
   1.5-pip stress.
2. **Bond wedge and COT AM net** do not currently show a train edge after
   cost on this Demo H4 reconstruction.
3. **No legal survivor** → no registry append, prereg freeze for build,
   MetaEditor compile, or Model 0.
4. `EA_CarryPublicRates` scaffold (if present) remains **non-evidence**; do
   not treat compile of that scaffold as a gate pass.

## Next independent probe set (no ChatGPT)

1. **G10 daily overnight rates acquisition** (RBA AONIA / BoC CORRA / RBNZ /
   SARON official CSVs) → freeze a multi-pair MM **event** book with the same
   V1b constants (not threshold-mined) to test structural cadence ≥2/week.
2. **COT Lev_Money net-change** (distinct participant class from Asset Mgr) +
   optional release-Friday cluster entries — new freeze, not AM rescue.
3. **Menkhoff vol-innovation anti-carry** (short high-carry when global RV
   innovation spikes) — expect sparse cadence; kill fast if tpw&lt;1.2.
4. Keep QFSI Real-broker cost lane separate; Demo falsification ≠ promotion.

## Non-actions

- No ChatGPT / Browser Deep Research dependency.
- No post-hoc HOLD/MIN_DELTA edits of killed freezes.
- No git operations.
