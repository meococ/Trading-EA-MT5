# HYP-GC-OFI-INNOV-XAU-M5-002 — frozen reference-schema recovery

Status: `FREE_METADATA_QUOTE_ONLY`. This fresh successor repairs only the
missing `definition` and `status` source payloads from HYP001. It does not retry
the HYP001 continuous-symbol request, download TBBO again, transform signals or
open XAUUSD outcomes/economics.

## Inherited immutable TBBO

- Parent: `HYP-GC-OFI-INNOV-XAU-M5-001`.
- Parent acquisition ID: `GCOFI001-Q1-2019-SOURCE-PILOT-001`.
- TBBO: `107311267` bytes, `4292841` records, SHA-256
  `6E0AD7D7893A7475DECAA6C71042139474AAE136BAC77FCBF96584FEB789BAEB`.
- Parent acquisition plan SHA-256:
  `EC9A22A43EFFD58809378C6E8798C894E71759873861CA70D17438D310495231`.
- Parent stopped manifest SHA-256:
  `5919A7B2A8240EA7E755C69A16500FF9659A95C6898E6D9C9A1E58EB442EA21E`.
- Parent engineering closeout SHA-256:
  `032E2910FB9291F71DC730E32BE964DD36D04161FA72861ABEC3B52A734B11F1`.

The local DBNv3 TBBO metadata provides the outcome-blind continuous mapping:

- `32257`: `[2019-01-01, 2019-02-01)`;
- `14651`: `[2019-02-01, 2019-03-31)`;
- `142620`: `[2019-03-31, 2019-04-01)`.

These are the only allowed raw instrument IDs. No contract may be added from a
later semantic or outcome readout.

## Exact free quote

- Quote/recovery ID: `GCOFI002-Q1-2019-REF-SOURCE-001`.
- Dataset: `GLBX.MDP3`.
- Symbols: `32257`, `14651`, `142620` in that order.
- `stype_in=instrument_id`; paid output remains instrument-ID keyed.
- Window: `[2019-01-01T00:00:00Z, 2019-04-01T00:00:00Z)`.
- Schemas/order: `definition`, then `status`.
- Cost mode: `historical-streaming`.
- Runtime: hash-bound Python 3.12.10 / Databento 0.55.1 / DBN 0.35.0.

The quote tool may make exactly two `metadata.get_cost` and two
`metadata.get_billable_size` calls. It makes no timeseries/batch call. The
aggregate must remain strictly below USD 10 and every schema must have positive
billable bytes.

## Later one-shot paid boundary

A separate reviewed and hash-bound acquisition tool/receipt must be frozen
after the free quote. It may make at most two serial paid requests, one per
schema. A failure stops the successor and forbids same-ID retry. The inherited
TBBO is locally validated by exact hash and full DBNv3 stream; it is never
remotely requested.

Completion permits only the already frozen source-integrity gates from HYP001.
It is not permission to inspect XAUUSD, estimate returns, build an EA, optimize,
validate, paper trade or deploy live.
