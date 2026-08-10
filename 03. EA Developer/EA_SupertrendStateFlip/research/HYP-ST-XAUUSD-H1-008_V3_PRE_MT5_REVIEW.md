# HYP-ST-XAUUSD-H1-008 V3 - pre-MT5 review packet

Status: `PASS_PRE_MT5`

V3 replaces the unused V2 before authority. It removes the contradictory
`00:00` narrative, freezes the exact server design window
`[2018.01.01 02:00, 2023.01.01 02:00)`, describes every audit-hardening source
change, labels the zero-trade cost manifest as Model 0, and removes any need to
pre-bind an unknown EX5 or compile-log hash.

The comparator now accepts only the canonical run-local EX5 snapshot and
run-local MetaEditor log. The run manifest, collector receipt and canonical
paths/hashes must reconcile. No cross-compile EX5 equality is used.

Frozen hashes:

- source / AlphaFactory: `580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF` / `68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8`
- prereg V3 / cost V3: `35CC4CA7A30BB83FDBC7CCD53E7702E88DF7A98DD425C2C6C238F23DB0517A7F` / `A734B983227B902062A59D28E97BFFAEBE33AA4E98A1E1FEDF0B99A438B86735`
- builder: `4EADBDBA66C6A5C6AA44495E3DF8D11F9FA4AF33A8B23CD2A5F11F6800048D12`
- packet / receipt / registry snapshot: `68E2D8D4EEB8226C27E7E78F2717F1B8028E0DEAB15DDC27C5CE3B12765BC1FD` / `3E3C4E913BFB991E883B5F64011FA494CF386D9EA560132B81956427D35C47D1` / `E24EC8A8E9D34A6AADD22CCF35D87D4935DB8C5BAC5DE21658B8A47C551AFAD7`
- launcher / collector / comparator: `97CA475DC4BE73A515C159C44B7D5B979CA5D75165DFBFC460DCDDB1560044AD` / `9B406B3A964623C6C3C108A29EDC256AAC9D87087B3462D85AD38E2358C8BDFD` / `0DA75EED50E420209A0A70E48E21FE46D93F21B17D100CA27BF9F0D7DA9BD367`
- HYP008 tests / HYP003 tests / DQ tests: `63B999F5B625E345441629529C362F9591C2C5D9EEC12425DE3B519249F94CAF` / `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590` / `22A66AA21857C1D2B661D8DDDDE730EFB5956B6478C7E8886A3C4EA76009A008`
- non-repaint manifest / audit: `BF404645B3A687DC48512C14DE12A19C2DB8036C8165A89DE389C218547D48F1` / `AF9DD56E5C108FB174DE31232D0976B253A38A23275A9ADCC238D6E4488C4623`
- gitignore / frozen live status: `B362B1E3CB837B53776D3FC891BB2AA68702580762CE71D09C698B78CD9BF1DC` / `9421FDB8A6FBBF1DEC2F28947313ADAA498919538415BC4FF83A85E50C748DCF`

Verification: focused comparator/collector/launcher/DQ suite `50 passed`;
candidate registry `800 rows / 310 hypotheses` PASS; Python compilation PASS;
non-repaint PASS with one exact allowed provenance-only CopyTime and no
findings.

ST008 attempt root and `ST003_MQL5_PARITY_001.csv` are absent. No HYP008 MT5,
order, outcome, return, PF, optimization, validation, holdout, paper or live
evidence exists. Reviewer must not run MT5 or open sealed market data.

## Independent verdict

`PASS_PRE_MT5`: V3 closes all three V2 blockers. Model 0 is authorized only for
zero-trade data acquisition/correctness; the exact run-local EX5 and compile log
will be bound after the sole AlphaFactory run. The authority row must not carry
an economic acceptance contract or any pre-run EX5/log hash. Every performance,
outcome, optimization, validation, holdout, paper and live permission remains
false.

Nonfatal disclosure: the builder docstring and one `.gitignore` comment retain
legacy phase names. Their executable bindings are V3/ST008 and correct; they are
left unchanged to preserve the sealed V3 receipt.
