# V8 COT TFF Spec-Net Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner unlimited-GOAL + Owner order to **skip GPT Deep Research** and
self-research from workspace truth. Frozen contract:
`preflight/v8_exogenous/20260713_V8_COT_TFF_PROBE_CONTRACT_V1.md`.

Independent of killed carry weekly/daily/rate-event probes. Not Strategy
Tester. Not Model 0 / EA / promotion authority.

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_COT_TFF_SPEC_NET_CHG_V1` |
| Mechanism | Lagged CFTC TFF Asset Mgr + Lev Money net change ≥ 1.5% of OI |
| Symbols | EURUSD, GBPUSD, USDJPY (JPY futures sign inverted for USDJPY) |
| Lag | `available_at = report_date + 3d` |
| Control | Same calendar; direction = sign of prior 5D FX log return |
| Cost | Stress A 1.5 / B 3.0 pip RT |
| Train / holdout | 2022–2023 / 2024–2025 (holdout gated) |

Tool: `02. AlphaFactory/tools/v8_cot_tff_offline_probe.py`  
Result: `preflight/v8_probe/20260713_V8_COT_TFF_PROBE_RESULT_V1.json`  
Panel: `preflight/v8_probe/20260713_V8_COT_TFF_PANEL_V1.csv` (209 rows/symbol)

## Train result (authoritative JSON run)

Source: `preflight/v8_probe/20260713_V8_COT_TFF_PROBE_RESULT_V1.json`
(SHA256 `39e5b90c4576acdbcbccfc5f0042fe19c87b8b0d8597680ea3a1845fab56fa15`)

| Book | Trades | TPW | PF stress-A | Exp stress-A |
|---|---:|---:|---:|---:|
| Candidate | 203 | **1.95** | 1.062 | +3.90 pips |
| Control | 203 | 1.95 | **1.125** | **+7.19 pips** |

Cadence and sample floors **pass**. Candidate **fails** to beat the matched
price-path control on PF and expectancy (`fail_beat_control_pf_and_expectancy`).
A parallel local implementation
(`20260713_V8_COT_TFF_SPEC_NET_PROBE_RESULT_V1.json`) also killed on
year-concentration = 1.0 after beating control — both fail-closed.

Holdout not opened (train fail-closed).

## Verdict

`KILL_AT_OFFLINE_PROBE`.

COT TFF speculative-net change on retail D1 FX does not isolate a positioning
edge beyond ordinary return continuation under this frozen design. Cadence is
not the blocker — mechanism isolation / concentration is.

## Explicit non-rescues

Do **not** post-hoc:

- retune the 1.5% OI threshold;
- drop Asset Mgr or Lev Money only after seeing this readout;
- add carry/vol/session filters mined from these 203 trades;
- promote `EA_CarryPublicRates` or any new EA from this kill.

## Authority after this kill

| Action | Allowed? |
|---|---|
| Registry / prereg / EA / compile / Model 0 for this design | No |
| New independent exogenous probe with new frozen ID | Yes (self-research) |
| GPT Deep Research | **No** — Owner waived for this lane |
