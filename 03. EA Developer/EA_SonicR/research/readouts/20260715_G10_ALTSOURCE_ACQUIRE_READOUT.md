# G10 overnight alt-source acquire readout

Generated: 2026-07-15T01:45:10.287963Z
Status: **PARTIAL_SERIES_NO_JOINT_PANEL**
Manifest SHA: `145EBE40EDE3C9BA0C5A83F1E8B19331CFA2A525695A9A9262E697F02AC89036`

## Attempts

| Note | Result | Bytes |
|---|---|---|
| BoC Valet CORRA AVG.INTWO csv | OK | 49202 |
| BoC Valet CORRA AVG.INTWO json | OK | 262162 |
| BoC target overnight V39079 | OK | 46643 |
| BIS WS_CBPOL daily G10 | HTTP_500 | — |
| BIS WS_CBPOL alt csvdata | HTTP_500 | — |
| RBA F1 hist xls retry | HTTP_404 | — |
| RBA F1 xls-hist mirror | HTTP_404 | — |
| RBA F1d hist xls | HTTP_404 | — |
| RBA data API f1 | ERROR | — |
| FRED CORRA | HTTP_404 | — |
| FRED IRSTCI01AUM156N | OK | 12086 |
| FRED IRSTCI01CAM156N | OK | 18022 |
| FRED RBATCTR | HTTP_404 | — |
| OECD MEI AU/CA short rates | HTTP_422 | — |

## Series retained

```json
{
  "CAD_CORRA": 2128,
  "CAD_TARGET": 2212
}
```

Panel rows: 0
Panel: `None`
Panel SHA: `None`

## Authority

BIS policy rates are target/policy (step) series, not always CORRA/AONIA MM. BoC AVG.INTWO is CORRA overnight. Use +1 business-day lag for available-at (publication lag conservative). Monthly OECD/SNB ≠ daily event book alone.

## Follow-on (same session)

- CAD+USD overnight panel built from CORRA + G3 USD:
  `panels/cad_usd_corra_overnight_d1_v1.csv` (2124 rows) — see
  `manifests/20260715_CAD_USD_CORRA_PANEL_V1.json`.
- Child probe `HYP-USDCAD-CORRA-USD-DIFF-EXPAND-H4-001` →
  **KILLED_AT_OFFLINE_PROBE** (cadence). AUD still blocked.
- Session VN: `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`.

