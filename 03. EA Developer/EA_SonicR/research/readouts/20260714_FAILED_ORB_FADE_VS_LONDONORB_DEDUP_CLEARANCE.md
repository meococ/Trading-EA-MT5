# Dedup — Failed ORB Fade vs LondonORB / PDH / NY / LiqSweep

Date: 2026-07-14  
Verdict: `INTAKE_CLEARED / INDEPENDENT`

## Candidate

`HYP-FAILED-ORB-FADE-M15-001` / `EA_M15FailedORBFade` — London first-hour OR
`[9,10)` a priori (same freeze as parked LondonORB, **not mined from readout**).
After lock, pierce OR extreme then **close back inside** on closed M15 `bar[1]`
→ fade toward OR mid.

## Contrast table

| Family | Mechanism | Relation |
|---|---|---|
| LondonORB (parked) | Break **continuation** beyond OR | **Opposite** trade direction / trigger |
| NY Open Drive (parked) | NY ORB break | Different session object |
| PDH Break (parked) | D1 PDH/PDL continuation | Different level object |
| LiqSweep / PDLevel fade | Fade PDH/PDL without OR pierce+reclaim | Different level + trigger |
| Spark Asian | Asian range breakout | Different range + break vs fail |
| HourOpen / InsideBar / Keltner | Micro OR / compression | Different |

## Independence claim

Same OR window as LondonORB is intentional a-priori reuse of a frozen contract,
not post-hoc hour mining. Decision predicate is **failed auction** (pierce +
close inside), not break continuation. Matches the allowed PDH-break-vs-LiqSweep
opposite-side pattern.

## Banned after readout

Do not retune OR hours, mine day filters, flip back to breakout, or rescue
LondonORB from this ID.
