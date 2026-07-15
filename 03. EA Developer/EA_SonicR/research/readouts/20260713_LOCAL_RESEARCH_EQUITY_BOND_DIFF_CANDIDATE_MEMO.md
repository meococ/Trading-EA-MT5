# Local Research Memo — Equity–Bond Differential (B4) — 2026-07-13

Status: `NO_LEGAL_CANDIDATE / KILL_AT_OFFLINE_PROBE`

Authority: Owner skip-GPT self-research; coordinator merge next action
`NEXT_ACQUIRE_EQUITY_BOND_PANEL` executed.

## Acquisition

Hash-bound panel under `preflight/v8_exogenous/raw/equity_bond/`
(manifest `manifests/20260713_V8_EQUITY_BOND_PANEL_ACQUISITION_V1.json`):
US Treasury YC 2018–2026, ECB AAA 2Y/10Y, FRED SP500 + VIX, DGS10/DGS2 mirrors.
Lag/join frozen in
`preflight/v8_exogenous/20260713_V8_EQUITY_BOND_DIFF_JOIN_CONTRACT_V1.md`.

## Probe

| Field | Value |
|---|---|
| Probe ID | `V8_EQUITY_BOND_DIFF_V1` |
| Working ID (not minted) | `HYP-SR-FX-EQUITY-BOND-DIFF-001` |
| Tool | `02. AlphaFactory/tools/v8_equity_bond_diff_offline_probe.py` |
| Result | `preflight/v8_probe/20260713_V8_EQUITY_BOND_DIFF_PROBE_RESULT_V1.json` |
| Status | `KILL_AT_OFFLINE_PROBE` |

### Train (2019–2022)

| Book | Trades | /week | PF-A | Exp-A |
|---|---:|---:|---:|---:|
| Candidate (eq−bond diff) | 282 | 1.35 | **1.004** | +0.08 |
| Equity-only control | 277 | 1.33 | 0.858 | −3.48 |
| Bond-only control (diag) | 309 | 1.48 | 1.131 | +2.64 |

Kill reason: `train_pf_stress_a<1.10`. Holdout gated shut.
Year concentration OK (0.35). Cadence above probe floor 0.5 but below GOAL 2–5.

## De-dup (honored; not the kill cause)

Independent of USD-factor M15 architecture, V8 carry/COT/carry×vol, S619, S682
hour drift. VIX/ECB archived but unused in frozen signal.

## Interpretation (no rescue)

Differential beat equity-only but failed absolute PF-A gate. Bond-only looked
stronger than the candidate — that is **diagnostic only**. Do **not** mint a
bond-only rescue from this readout (overlaps rates/bill surfaces; post-hoc).

## Registry / prereg / Model 0

**None.** Working ID not minted.

## QFSI side check (same session)

`probe-mt5` V2: `observed_server=MetaQuotes-Demo`, `server_match=false`.
Branch B still `STOP_DATA_FRONTIER`.
