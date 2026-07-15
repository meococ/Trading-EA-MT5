# Session closeout — London–NY overlap EUR/GBP

Date: 2026-07-15
Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / `OFFLINE_ALL_KILL / NO_MODEL0`
Lane: single checkout; no-Git; no Real stall

## Board

| ID | N | PF | tpw | stress x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001` | 109 | 0.9636 | 0.4181 | **0.8896** | **KILL** |
| `HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001` | 308 | 1.0278 | 1.1814 | **0.929** | **KILL** |
| `HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001` | 30 | 0.769 | 0.1151 | **0.7267** | **KILL** |

Receipt: `EEF617F060532C4095FDBC38548690B0C72CF88C2D949077B24CC1F941FD9E27`
Design: `readouts/20260715_LNY_OVERLAP_EURGBP_DESIGN_MEMO.md`
De-dup: `readouts/20260715_LNY_OVERLAP_EURGBP_DEDUP_CLEARANCE.md`
Probes: `preflight/20260715_LNY_OVERLAP_EURGBP_OFFLINE_PROBES.json`

## Model 0

Withheld (zero PROBE_SURVIVOR).

## Decisions

1. Keep **`EXO_FRED_DISPLACE_SPAM_PAUSED`** — no new FRED series.
2. Do **not** densify MULTISYM EUR 07–10 / GBP NY-impulse / Asia coil / RR2 exit.
3. Do **not** invent cost freeze; do **not** densify MaxKZ/RR / IB/ORB/Spark/ITSM.
4. Best shelf unchanged: RR2 `194548`. GOAL unmet.

## Next autonomous EV (non-login-only)

1. New independent object class outside LNY fade/coil/catch-up densify — or wait research-grade cost then microstructure.
2. Keep QFSI 006 accumulating; rebind harness `--execute` only on gate GO.
3. Owner PIT/vendor tape still required for multi-month session×hour cost freeze.
