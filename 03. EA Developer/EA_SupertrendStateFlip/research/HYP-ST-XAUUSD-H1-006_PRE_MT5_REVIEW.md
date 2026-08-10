# HYP-ST-XAUUSD-H1-006 — pre-MT5 review packet

Status: `PASS_PRE_MT5`

Independent reviewer verdict: no fatal blocker. The reviewer independently
reconciled the HYP005 terminal parent, all 24 receipt bindings, HYP006 packet and
snapshot, live Git-status hash, absent FILE_COMMON/attempt root, exact empty
launcher token versus semantic `current`, fresh one-shot IDs, source/EX5/oracle
bindings and the zero-outcome/no-economics boundary.

## Exact revision

The only executable difference from consumed HYP005 is the launcher adapter:
`build_alpha_command()` passes an empty value immediately after `-Spread`.
AlphaFactory normalizes that request to semantic `spread=current`, which remains
frozen in the HYP006 task packet, receipt and expected run manifest. The source,
EX5, formula, oracle, Model 4, window, overrides, gates and zero-trade boundary
are unchanged. HYP005 is terminal and cannot be retried.

## Static evidence

- prereg: `FC230B9DB60427180A321C009EC8BF7014E717C26FBF887C013C6887A182DC79`
- packet / receipt / registry snapshot:
  `9A33AD1044729CD655701CF08EBA04951D5D1D6842CEDFDE1A8DCEBC679B937A` /
  `BE63DD424127AF9EE28D627C01DC32AE2BD7D9C65720B3E515DCAEF4D2E74173` /
  `56FCB1E2FC00DCC8DD247E30BAC0C5ACB4219586939557C588BEB833CB2130B7`.
- builder / launcher / collector / comparator:
  `5DD823B1E6D8C926212F17497F2B5DF829A8FA9DDFF4A56633994A846FB2C1D4` /
  `5E819D9BC7F743AB8ABAB1E89D3C776310E8F6E2608BB2A9F66F8CED139CFF9C` /
  `B14CDF7AFA706F356010F69B798A69C66E37C0741B5775285B6BFC9ECCF724BC` /
  `5A4E2780BB30DFBF793618066A1A8C8B6C38FE9123C87E54F3D95CC304A7A9D0`.
- HYP006 / HYP003 tests:
  `8DABB6BA171F5D05223FB3FCA2A0A9EF0D8EB0A7E7218B45B61658CE96A139B0` /
  `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590`;
  focused run: `27 passed`.
- non-repaint manifest / audit:
  `16514A08EB02652E2C1D2069E0B985EA477AFB72CDF5820A07875BD643455F93` /
  `A062527152762373F5975CF8FD80CEF0BCF97470FF59F741575DD07845CC0BB0`;
  audit status PASS, collection authority verified, no findings, exactly one
  allowed read-only `CopyTime` provenance record at archived source line 86.
- cost manifest / `.gitignore`:
  `7096D1AFFC3F7FD1D218663839952D36CC08B433CFD814EC44DE557BCE8F6EDE` /
  `855207E43A54522688385164E0BFA987D4AFF2EB48B5770A3DA6368AC9FDAB71`.

No HYP006 attempt directory or common CSV exists. No compile, MT5, collection,
comparator, order, outcome or economic attempt has been executed under HYP006.

Nonfatal debt accepted for this frozen attempt: historical tool filenames still
contain `st004`, and some producer/consumer schema labels retain `st005`; the
actual payload/authority identities are consistently HYP006/ST006 and the
paired tests enforce them. Renaming those labels now would enlarge the revision
without improving this one-shot correctness claim.
