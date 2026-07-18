# KLR storage reconciliation

Status: `PARTIAL_CONCURRENT_CONTAMINATION`, not a KLR storage failure.

- Before snapshot SHA-256:
  `A83E7DBC31AE84CA20F8FD97E01F4A52D66C5440E4285E1B5F327ED2F7FFB692`.
- After snapshot SHA-256:
  `E4986970C6A38FC50DC9D6ECE07D571D7078E54CD3DFE59A1EFA444E014B03AC`.
- Raw comparison receipt SHA-256:
  `FEA53CD7946EF8423CD284E3529CED47A10B906A3DDCF98F3F0FCE583559765B`.
- Unchanged C roots: terminal `Tester`, terminal `bases`,
  `MQL5/Profiles/Tester`, roaming `MetaQuotes/Tester`, and Program Files
  `Tester`.
- Changed shared root: `MetaQuotes/Terminal/Common`.

Files written after the before-snapshot cutoff were named for the concurrent
Unicorn hypothesis, not KLR:

- `XAUUSD_LifecycleTrades_HYP-UPS-XAU-M5-002_54728593.csv`, SHA-256
  `E8D63E91C845A057E60CD7BD2357D9AA4D66D143B40623A1BDE99AD48B8E3D0D`.
- `XAUUSD_RunMeta_HYP-UPS-XAU-M5-002_54728593.json`, SHA-256
  `57FDA2B7030C493AE27C4E157B434E798B48B00C28B10878111E0A78F8BF8F65`.

The KLR probe used Python bar reads and wrote only its D-side evidence file. It
did not use `FILE_COMMON`. Concurrent artifacts are preserved untouched.
