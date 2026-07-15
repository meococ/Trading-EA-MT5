# De-dup Clearance — OIS/RFR SOFR−€STR → EURUSD — 2026-07-13

Status: `INTAKE_CLEARED / INDEPENDENT` (pre-result; does not grant survivor)

## Proposed probe

| Field | Value |
|---|---|
| Working ID | `HYP-SR-FX-OIS-SOFR-ESTR-DIFF-EURUSD-001` (mint only if probe survives) |
| Probe tag | `V8_OIS_SOFR_ESTR_DIFF_EURUSD_V1` |
| Surface | Lagged overnight RFR differential SOFR − €STR → EURUSD D1 z-gate |

## Closed families checked

| Closed / active family | Why independent |
|---|---|
| V8 carry weekly / daily rank / rate-event ≥5bp | Cross-sectional **rank / long-max / deadband** on G3 policy+short rates. This is **single-pair z-score** of overnight RFR differential (€STR market rate, not ECB DFR policy). |
| DGS2−ECB DFR shock EURUSD | 2Y Treasury vs **policy** deposit facility. This uses **SOFR vs €STR** overnight RFRs only. |
| USEU / USUK 10Y / EU curve slope | Sovereign **bond** curves. This is overnight **money-market RFR**, not 10Y. |
| USBILL slope → USD basket | US bill **curve shape** multi-pair. This is **cross-currency overnight spread** → EURUSD only. |
| Equity−bond SPX−DGS10 | Equity risk premium wedge. Unused here. |
| COT TFF / carry×vol | Positioning / vol regime. Unused here. |
| Cadence-book M15 | Price open-break. Unused here. |
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | FX-return factor + pullback. No overlap. |

## Explicit non-claims

- Not true FX forward points (vendor).
- Not multi-tenor OIS swap curve.
- Not a post-hoc rescue of killed carry books (no deadband mining; no rank).

## Authority

Clearance authorizes **one** cheap offline probe only. Registry/prereg/EA/Model 0
remain closed unless the probe survives doctrine floors.
