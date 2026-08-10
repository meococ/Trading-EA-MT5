# HYP-ST-XAUUSD-H1-012 - exact Orders-shape comparator preregistration

Status: `FROZEN_PRE_AUTHORITY`

HYP012 is a fresh comparator-only child of terminal HYP011. It preserves the
entire frozen HYP011/HYP010/HYP009/HYP008/HYP003 chain and changes only the
empty-Orders HTML predicate that confused physical cells with logical columns.

Fresh identity: `HYP-ST-XAUUSD-H1-012`; sole comparator attempt:
`ST012-COMPARATOR-001` under the canonical HYP012 evidence root.

The exact report/analyzer hashes and exact sole funding `Deal` dataclass remain
unchanged. The Orders section locator remains localized `Các lệnh đặt` or
English `Orders`, terminated by the `Deals` heading.

The section must have exactly two `<tr>` rows. The first must have exactly 11
physical `<td>` cells, each containing one bold header value. The parser must
retain td attributes, accept zero or one `colspan` attribute per cell, default
missing colspan to 1, and require the exact vector
`[1,1,1,1,2,1,1,1,2,1,1]` with sum 13. The second row must have exactly one td,
default colspan 1, with empty text. Any malformed/duplicate/nonpositive colspan,
extra/missing cell, non-bold header, nonempty spacer or extra row fails.

The wrapper must hash-load exact HYP011 comparator SHA256
`1782402317C28CDA45ED5F1B4B10E571E361F26A3B025C38CEC1E0E059FFA48C`,
bind terminal HYP011 row SHA256
`8B6A6F8EAD19C653DE4CD1FCC360639FF9B473DE336DE78320865014311BEE39`
and its start/terminal/failure/review files, then override only
`orders_section_is_empty()`.

Claim ordering, historical/terminal HYP009 lineage, disclosure, exact run-source
path, exact funding/report/analyzer contract, deterministic full-row replay and
all zero-authority gates remain frozen. No collection, MT5, compilation, mutable
source, trading, outcomes, PF, economics, optimization, validation, holdout,
paper, promotion or live work is authorized.
