# V8 COT TFF Spec-Net Offline Probe Readout — 2026-07-13

Status: `KILL_AT_OFFLINE_PROBE`

## Authority

Owner GOAL mandate + Owner order to **skip GPT / ChatGPT Deep Research**
(2026-07-13 23:40). Self-research only. Frozen contract:
`preflight/v8_exogenous/20260713_V8_COT_TFF_PROBE_CONTRACT_V1.md`.
Tool: `02. AlphaFactory/tools/v8_cot_tff_spec_net_offline_probe.py`.
Result: `preflight/v8_probe/20260713_V8_COT_TFF_SPEC_NET_PROBE_RESULT_V1.json`.

Not Strategy Tester. Not registry/prereg/EA/Model 0 authority.

## Frozen design (pre-result)

| Item | Value |
|---|---|
| Probe ID | `V8_COT_TFF_SPEC_NET_CHG_V1` |
| Mechanism | Lagged CFTC TFF Asset Mgr + Lev Money net-position change → FX direction |
| Threshold | `\|Δspec\| / OI >= 0.015` |
| Availability | `report_date + 3 calendar days 00:00Z` |
| Symbols | EURUSD, GBPUSD, USDJPY (JPY futures sign inverted for USDJPY) |
| Control | Same calendar + threshold; direction = sign of prior 5 D1 log returns |
| Cost | Stress A 1.5 / B 3.0 pip RT |
| Train / holdout | 2022–2023 / 2024–2025 (holdout gated) |

## Train result

| Bucket | Trades | /week | PF stress A | Expectancy A |
|---|---:|---:|---:|---:|
| Candidate | 225 | **2.160** | 1.194 | +10.80 pips |
| Control | 225 | 2.160 | 1.147 | +8.19 pips |

`train_year_concentration_pos_net_a = 1.0` (all positive net-A mass in one year).

## Verdict

`KILL_AT_OFFLINE_PROBE` — sole kill reason: `year_concentration>0.55`.

Cadence and sample floors passed. Candidate beat control on PF and expectancy,
but the edge is regime-concentrated (concentration = 1.0). Holdout was **not**
opened (train fail-closed).

## Explicit non-rescues

Do **not** retune the 1.5% OI threshold, drop Asset Mgr or Lev Money only,
add price filters, or reopen holdout after this kill. Any child needs a new
independent mechanism ID and frozen contract.

## Authority after kill

| Action | Allowed? |
|---|---|
| Registry / prereg / Model 0 for this COT book | No |
| Further OI / lag mining from these 225 trades | No |
| Independent frozen exogenous probes (other surfaces) | Yes |
| GPT Deep Research | **No** — Owner abandoned GPT path 2026-07-13 23:40 |

## Broker note

MT5 server: `MetaQuotes-Demo`. Falsification only. Not FivePercentOnline-Real
cost provenance.
