# HYP-ST-XAUUSD-H1-011 - Orders header-shape failure

Status: `KILL_EXACT_PHYSICAL_CELL_COUNT`

Timestamp: `2026-08-09T01:00:22Z`

The sole ST011 comparator claimed and passed all inherited provenance, exact
funding-row and run checks, then failed before full oracle/audit row comparison
because its empty-Orders predicate required 13 physical `<td>` cells.

The exact MT5 Orders header has 11 physical cells. Two cells use `colspan="2"`
(Volume and Time), giving 13 logical columns. The section contains exactly two
rows: that 11-cell bold header with logical colspans
`[1,1,1,1,2,1,1,1,2,1,1]`, followed by one empty spacer row. There is no order
data row. The exact exception was
`ValueError: HYP008 report Orders section is not exactly empty`.

Evidence:

- ST011 start SHA256:
  `4A5D28D2103898C74FC06148B984DE1F02CD5D12A4FC3F167D676B10FA40B82F`;
- ST011 failed terminal SHA256:
  `912130D0E3C5789EFFFB8AE58ABEC4F0032EF1A3ACEAD81B5E17CD9B23F4F45B`;
- no parity report/receipt, no full-row comparison and no economics;
- no collection, MT5 or compilation repeated.

Same-ID retry is forbidden. A fresh comparator-only HYP012 may change only the
Orders header predicate to require the exact 11 physical / 13 logical structure
above while preserving the exact funding Deal, report hash, analyzer hash,
claim ordering, sealed inputs and zero-economic gates.
