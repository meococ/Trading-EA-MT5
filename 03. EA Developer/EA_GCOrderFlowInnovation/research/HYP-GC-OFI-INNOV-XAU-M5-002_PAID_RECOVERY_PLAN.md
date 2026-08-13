# HYP-GC-OFI-INNOV-XAU-M5-002 — one-shot paid reference recovery

Frozen after the free raw-instrument quote and before any HYP002 paid request.
This plan authorizes missing source bytes only. It does not authorize a TBBO
remote call, source transform, XAUUSD outcomes, economics, MQL5, MT5,
optimization, validation, paper or live trading.

## Bound inputs

- Source recovery plan SHA-256:
  `2A769D9A36CD0EAB10F6B64D1020514CA3D02F0F0E8BA03C1CD85A94A45273DD`.
- Free quote receipt SHA-256:
  `7422D510B2A483EC16C5E35776020E2175CC7438CE754964FFF5AE95DADCD9EB`.
- Quote: USD `0.000400014222`, `172560` billable bytes.
- Inherited TBBO SHA-256:
  `6E0AD7D7893A7475DECAA6C71042139474AAE136BAC77FCBF96584FEB789BAEB`.
- HYP001 closeout SHA-256:
  `032E2910FB9291F71DC730E32BE964DD36D04161FA72861ABEC3B52A734B11F1`.
- Runtime receipt SHA-256:
  `E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD`.

## Exact remote population

- Recovery ID: `GCOFI002-Q1-2019-REF-SOURCE-001`.
- Dataset: `GLBX.MDP3`.
- Symbols/order: `32257`, `14651`, `142620`.
- `stype_in=instrument_id`, `stype_out=instrument_id`.
- Window: `[2019-01-01T00:00:00Z, 2019-04-01T00:00:00Z)`.
- Schemas/order: `definition`, then `status`.
- Definition quote: USD `0.000179477036`, `113360` billable bytes.
- Status quote: USD `0.000220537186`, `59200` billable bytes.
- Cost mode: `historical-streaming`.

Immediately before the first paid call, the tool repeats exactly two free cost
and two free billable-size calls. It stops if the aggregate is not strictly
below USD 10 or any schema is nonpositive.

## One-shot behavior

The tool first full-stream-validates the inherited TBBO by exact hash, DBNv3,
dataset/schema and record count. It then writes plan/manifest state before each
of at most two serial paid calls. Each payload must have Zstandard magic,
DBNv3, dataset/schema identity, a nonzero full record stream, and only the
frozen instrument IDs. A remote, partial, decode, schema, empty-record or
identity failure stops immediately. Same-ID retry is forbidden.

Completion permits a separate frozen source-integrity analyzer over the three
hash-bound source payloads. It is not an edge verdict or permission to open
target outcomes.
