# HYP-STBS-XAUUSD-M15-004 — Independent post-failure review

Status: `PASS_KILL_EXACT_ORDERS_HEADING_ENCODING_PREDICATE`

## Evidence reviewed

- Screened authority raw SHA256: `CE2558662D065F01C6CD926EBE380252D023096020E431E7D42A0E650DA7F85B`.
- Comparator SHA256: `00D140BEBAB567678F96E4C581C6871D410C18C488BF1330FDEFC2EBEC44677B`.
- Attempt start SHA256: `50D5C69C6DB4A5D60180C7ACB56A6901AC679B12FDE5A924164561553148534F`.
- Failed terminal SHA256: `905A1C5C899F52B3EF879A95563C462A250E6D73CC810F39CEB40536B93CA16D`.
- The attempt root contains only those two artifacts; no comparator report or success receipt exists.

## Independent verdict

The exact kill is warranted. The sole HYP004 attempt passed its frozen input-hash, manifest/data-quality and zero-trade-summary gates, then deterministically failed while locating the locale Orders heading. The exact report uses `Các lệnh đặt`; the frozen HYP004 regex literal is mojibaked and cannot match it.

HYP004 did not reach Orders structural validation or the journal/oracle/geometry comparison. Those contracts remain unadjudicated by this attempt. No AlphaFactory call, compile, MT5 launch, source acquisition, order, outcome, performance or economics occurred.

## Legal next revision

A fresh comparator-only HYP005 is legal only after HYP004 is terminal. It must use a fresh evidence root and one-shot attempt, bind the HYP004 terminal row and failure chain, and replay the entire unchanged comparator over the same HYP003 inputs.

The only permitted semantic change is exact Orders-heading recognition. Supported headings must be defined with Unicode escapes and compared exactly after extracting bold-tag inner text: English `Orders` and NFC Vietnamese `C\u00e1c l\u1ec7nh \u0111\u1eb7t`. Mojibake, decomposed Unicode, misspellings, duplicate headings, missing or duplicate following `Deals`, and every existing colspan/spacer mutation must fail closed. Unicode repair or normalization is forbidden.
