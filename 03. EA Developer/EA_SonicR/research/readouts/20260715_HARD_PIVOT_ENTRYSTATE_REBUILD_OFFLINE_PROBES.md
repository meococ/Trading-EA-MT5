# Offline probes — HARD PIVOT entry-state rebuild

Generated: 2026-07-15 ~14:26 ICT
Receipt SHA256: `202A33835FC62A307C199594AA71C7A7B1711BF5265F96EA9F0E15D65467A0E6`
Freeze SHA256: `2428F8F3447EEC6D6BEBB4CA42D15AAC0BA2A14BE6DA4DD4C77FE805548E0C27`
Book freeze SHA256: `D123520950D84C29EFFBFC6A9DAF78C134D8D158CE63C42308B33E8D7B01B4CC`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
Cost a priori: +$12/trade
QFSI parallel: QFSI 007 parallel accumulate; cost freeze still GAP (raw_deals≈11; freeze_eligible=False); login not headline

| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001` | 3205 | 1.0634 | 12.2932 | 1.0217 | 1.0016 | KILL |
| `HYP-SB-FVG-RETEST-ACCEPT-DELAY-001` | 299 | 1.2747 | 1.1468 | 1.2054 | 1.1724 | KILL |

## Fail notes
- `HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001`: pf_fail, cadence_fail, pf12_fail, stress_fail
- `HYP-SB-FVG-RETEST-ACCEPT-DELAY-001`: pf_fail, cadence_fail, pf12_fail, stress_fail

## Optional book stress
```{
  "verdict": "BOOK_STRESS_WITHHELD__NO_SLEEVE_SURVIVOR"
}```

## Model 0
AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.
