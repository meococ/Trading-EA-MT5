# HYP-ST-XAUUSD-H1-011 - exact funding-row comparator preregistration

Status: `FROZEN_PRE_AUTHORITY`

## Exact engineering revision

HYP011 is a fresh comparator-only child of terminal HYP010. HYP010 passed all
authority, provenance, claim-order, oracle-chain, non-repaint and sealed-input
checks, then failed because its inherited zero-trade validator treated the
tester-start account-funding row as a trading deal.

HYP011 changes only that local report predicate. It preserves the frozen HYP010
wrapper/engine, outer lineage through HYP009/HYP008/HYP003, the HYP009 sealed
collection, HYP008 report/source/EX5/run and all 29,460 audit/oracle rows.

Fresh outer identity is `HYP-ST-XAUUSD-H1-011`; the sole attempt is
`ST011-COMPARATOR-001` under the canonical HYP011 evidence root.

## Frozen zero-trade report contract

The report SHA256 remains
`178901C855F050FA18217762509F791870D8CB2A2903CEF08C0436E8A7EE79EB` and
the quant analyzer SHA256 remains
`A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B`.

`parse_deals_from_html_report()` must return a list of length exactly one and
that element must equal the analyzer `Deal` dataclass with every field frozen:

- `time=2005-01-01 00:00:00`, `deal_id=1`;
- `symbol=''`, `side='balance'`, `direction=''`, `comment=''`;
- `volume=0.0`, `price=0.0`, `commission=0.0`, `swap=0.0`;
- `order_id=None`, `profit=10000.0`, `balance=10000.0`.

Every deviation or extra parsed row fails. Generic parser behavior is not
changed. Separately, the exact HTML Orders section between its localized/English
heading and the Deals heading must contain exactly the 13-cell bold header row
and one empty spacer row, with no order data row.

## Comparator and authority boundary

The outer HYP011 wrapper must hash-load exact HYP010 comparator SHA256
`434D79CEE674FB19F38F9CFBCDE6E5A2EB0A63F947719B4E78F49DAB5A1C6823`,
bind terminal HYP010 row SHA256
`E46E10C7DC99508D2CFD7AA7E14FACA740C40E09172E08AB75A7F631B7314039`,
its start/terminal/failure/review artifacts, then override only
`validate_alpha_run()` with the exact funding/Orders contract above.

Claim-before-artifact-read ordering, the HYP009 historical/terminal dual
binding, disclosure binding, exact run-source snapshot path, deterministic
full-row replay and all fail-closed gates remain unchanged.

No collection, MT5, compilation, mutable FILE_COMMON/canonical-log read, trade
API, outcome, return, PF, economics, optimization, validation, holdout, paper,
promotion or live work is authorized. A parity PASS is engineering-valid only;
economic work requires a separate preregistered child.
