# DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002

Status: `FROZEN_PRE_OUTCOME_ENGINEERING_SUCCESSOR`

## 1. Failure radius and purpose

This is a fresh engineering source-contract successor to
`DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-001`. Parent hypothesis HYP-003
consumed its one allowed attempt and parked with
`PARK_ENGINEERING_INVALID_FOOTER_DIGEST_CONTRACT_MISMATCH_NO_MARKET_VERDICT`.
The generic custodian opened the raw source once but stopped before Parquet row
decode. Whole-file SHA, bytes, root manifest, collection plan and clock matched;
only the frozen footer digest did not match the exact runtime byte-range
definition. No strategy row, outcome, PnL or performance metric was opened.

HYP-003 packet, marker, terminal, empty custody stage and failure manifest are
immutable failure evidence and forbidden inputs to this successor.

## 2. Immutable raw source and corrected footer contract

Source:

- path: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`;
- bytes: `104965845`;
- whole-file SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`;
- root manifest SHA256:
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`;
- clock tool SHA256:
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.

The exact Parquet footer digest algorithm is frozen as follows:

1. require first four and final four bytes equal ASCII `PAR1`;
2. read unsigned little-endian `footer_length` from bytes `[-8:-4]`;
3. require `footer_start = file_bytes - 8 - footer_length >= 4`;
4. hash the exact byte range `payload[footer_start:file_bytes]`, which includes
   serialized footer metadata, the four footer-length bytes and final `PAR1`;
5. require `footer_length=10121`, `footer_start=104955716`, and SHA256
   `691BE204EBC508FD61C925972F91482854AED46625EF7B05F330B7FDFBC9970F`.

The prior value `92E8403266EF971ED2F4C05523ECB6C10AE5B5723F0F7504E09694663A779727`
is explicitly rejected as a different, undefined byte-range contract. This
correction is engineering metadata learned from a failed pre-decode attempt;
it is not a market rule or outcome-based rescue.

## 3. Mechanism-free custody split

The custodian may stable-read the raw source exactly once after a reviewed
one-shot packet and durable fresh-attempt marker. It must validate whole SHA,
bytes, corrected footer, schema, strictly increasing unique minute-aligned UTC
rows, server/UTC clock round-trip, finite positive OHLC and OHLC geometry.
Global one-minute adjacency is not required across ordinary FX calendar gaps.

Physical split boundaries are unchanged:

- `PRE_DESIGN`: UTC `< 2016-01-04`;
- `DESIGN`: `2016-01-04 <= UTC < 2021-01-01`;
- `VALIDATION`: `2021-01-01 <= UTC < 2023-01-01`;
- `HOLDOUT`: UTC `>= 2023-01-01`.

The public capability exposes only physical DESIGN bytes plus public DESIGN
manifest/receipt. VALIDATION, HOLDOUT and private custody artifacts remain
sealed. No strategy identity, direction, ATR, trade, cost or outcome enters the
custodian.

## 4. Fresh one-shot authority and outputs

Only a create-new HYP-004 packet may authorize one exact source attempt. It
must bind this plan, HYP-004 preregistration, active registry row/hash, source
identity, corrected footer contract, final reviewed tools/tests, exact attempt
ID, durable evidence root, deterministic custody/DESIGN stage paths, and
create-new outputs:

- `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002`;
- `02. AlphaFactory/data/fivepercent/EURUSD/trendstack_004_design_m1`.

First durable marker creation conservatively consumes the attempt. Any crash,
hash/footer/schema/identity/capability/path/output/validation failure parks
HYP-004 with no same-ID retry, fill, repair, resume, delete or reuse. The failed
stage remains evidence. Source acceptance grants only a separate DESIGN
economic packet; economics, MT5, Model 0, validation outcomes, holdout,
promotion, paper, live and deployment remain false.
