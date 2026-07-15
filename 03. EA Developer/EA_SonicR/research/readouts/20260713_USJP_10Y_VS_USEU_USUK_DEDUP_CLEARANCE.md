# De-dup Clearance — US−JP 10Y JGB Diff → USDJPY — 2026-07-13

Status: `INTAKE_CLEARED / INDEPENDENT` (pre-result; does not grant survivor)

## Proposed probe

| Field | Value |
|---|---|
| Working ID | `HYP-SR-FX-USJP-10Y-DIFF-USDJPY-001` (mint only if probe survives) |
| Probe tag | `V8_USJP_10Y_DIFF_USDJPY_V1` |
| Surface | Lagged US Treasury 10Y − MoF JGB 10Y → USDJPY D1 z-gate |

## Closed families checked

| Closed / active family | Why independent |
|---|---|
| USEU 10Y → EURUSD | Different non-US curve (JGB MoF vs ECB AAA) and different FX leg (USDJPY). Not a z retune. |
| USUK 10Y → GBPUSD | Different non-US curve (JGB vs BoE GLC) and different FX leg. |
| EU curve slope | EU domestic shape only; unused here. |
| OIS SOFR−€STR | Overnight RFR money-market; this is sovereign **10Y bond** US−JP. |
| USBILL slope USD basket | US bill shape multi-pair; this is cross-market 10Y → USDJPY only. |
| Carry rank / COT / equity-bond / cadence-book | Different causal surfaces. |

## Authority

One cheap offline probe only. No registry/prereg/EA/Model 0 unless survive.
Do not overlay results onto killed USEU/USUK/OIS books.
