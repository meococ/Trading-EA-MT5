# HYP-STBS-XAUUSD-M15-005 — Exact Orders-heading comparator revision

Preregistered at: `2026-08-09T06:20:00Z`

## Question and legal scope

Can a fresh comparator-only revision validate the exact completed HYP003 Model-0 audit run after replacing only HYP004's mojibaked Orders-heading predicate with exact English/NFC-Vietnamese recognition?

HYP005 is a fresh engineering child of terminal `HYP-STBS-XAUUSD-M15-004`. It performs no AlphaFactory invocation, compile, MT5 launch, source-data acquisition, order, outcome, performance or economic analysis. It must replay the entire unchanged HYP004 comparator over the same frozen HYP003 inputs. Same-ID retry is forbidden.

## Frozen identities

- Hypothesis: `HYP-STBS-XAUUSD-M15-005`.
- Attempt: `STBS005-COMPARATOR-001`, limit one.
- Parent indicator-parity object: `HYP-ST-XAUUSD-H1-012`.
- Terminal HYP004 raw registry row SHA256: `74C14309567C96AC54A0DEACE93B08B7487D016752EF262D52830476C9DCF252`.
- Frozen HYP004 comparator: `03. EA Developer/EA_SupertrendBurstScalper/research/compare_stbs004_existing_run.py`, SHA256 `00D140BEBAB567678F96E4C581C6871D410C18C488BF1330FDEFC2EBEC44677B`.
- HYP004 authority raw SHA256: `CE2558662D065F01C6CD926EBE380252D023096020E431E7D42A0E650DA7F85B`.
- HYP004 attempt start: `03. EA Developer/EA_SupertrendBurstScalper/research/evidence/HYP-STBS-XAUUSD-M15-004/STBS004-COMPARATOR-001/attempt_started.json`, SHA256 `50D5C69C6DB4A5D60180C7ACB56A6901AC679B12FDE5A924164561553148534F`.
- HYP004 failed terminal: `03. EA Developer/EA_SupertrendBurstScalper/research/evidence/HYP-STBS-XAUUSD-M15-004/STBS004-COMPARATOR-001/attempt_terminal.json`, SHA256 `905A1C5C899F52B3EF879A95563C462A250E6D73CC810F39CEB40536B93CA16D`.
- HYP004 failure document: `03. EA Developer/EA_SupertrendBurstScalper/research/HYP-STBS-XAUUSD-M15-004_COMPARATOR_FAILURE.md`, SHA256 `E4EC24C6A60BD0BF5985FCB2EA89318987F3454D324308FD0C1782C402F00837`.
- HYP004 independent post-failure review: `03. EA Developer/EA_SupertrendBurstScalper/research/HYP-STBS-XAUUSD-M15-004_POST_FAILURE_REVIEW.md`, SHA256 `FD2C41DD682CC48A71400438C5CF5996346AADA35DA0C2F9678E7F89F4BE185A`.
- HYP003 terminal raw registry row SHA256: `F7813C1663BA9E14C28CB90227422A612A776743F1634DC1D25C0FE00F97D593`.
- HYP003 run/oracle/artifact path and SHA contract: inherited byte-for-byte from the frozen HYP004 comparator and HYP004 preregistration SHA256 `6DC4A6E70E33C330C735B3995D3212C204F498AC4840DC50498A2A53AC384CD3`.

The HYP005 wrapper must capture the exact frozen HYP004 comparator bytes once, verify their hash, and compile/execute only that same in-memory buffer. The receipt binds that same buffer without reopening the base path. Every inherited static evidence path is opened once after the durable HYP005 claim; hashing and parsing reuse the same captured bytes. HYP004 terminal/failure artifacts and the HYP005 preregistration, tests and independent review are separately hash-verified after the claim.

## Only permitted semantic change

- Extract all case-insensitive `<b>...</b>` elements without Unicode repair or normalization.
- Strip only surrounding whitespace from the inner text.
- Require exactly one supported Orders heading in the complete report: exact English `Orders` or exact NFC Vietnamese expressed in source with Unicode escapes as `C\u00e1c l\u1ec7nh \u0111\u1eb7t`.
- Require exactly one later bold heading whose stripped inner text is exact `Deals`.
- Mojibake, NFD/decomposed Unicode, misspellings, duplicate supported Orders headings, missing or duplicate following Deals headings fail closed.
- Between those exact headings, retain the unchanged HYP004 empty-section contract: exactly two rows; 11 bold header cells; colspan vector `[1,1,1,1,2,1,1,1,2,1,1]` with logical sum 13; exactly one default-span empty spacer cell; malformed, duplicate or nonpositive colspan fails.

All BOM, duplicate-key, manifest, DQ, series-proof, zero-trade summary, journal multiplicity, dual UTC/server-clock, referenced-next-row, signal identity, exact-next, gap, direction, exact 1-ATR/1.5R geometry, volume-readiness-only and deterministic replay rules remain unchanged.

The inherited analyzer must first return exact schema `stbs004_existing_run_comparator_report.v1`. HYP005 then creates a fresh final report with schema `stbs005_exact_orders_heading_comparator_report.v1` and field `heading_revision=EXACT_ENGLISH_OR_NFC_VIETNAMESE_NO_NORMALIZATION`. Deterministic replay compares the complete transformed HYP005 report bytes, not the inherited HYP004 dictionary.

## Verdict boundary

PASS may state only `ENGINEERING_VALID_STBS_MODEL0_SIGNAL_ATR_GEOMETRY_AUDIT_PASS`. Exact position sizing remains unproven and only positive volume readiness is checked. No zero-warning compile claim is permitted. Profitability, PF, expectancy, costs, robustness, optimization, OOS/holdout and deployment remain unauthorized.
