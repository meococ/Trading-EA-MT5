# HYP-GC-OFI-INNOV-XAU-M5-001 — one-shot paid source acquisition

Frozen after the free metadata receipt and before any paid source request.
This plan authorizes source bytes only; XAUUSD outcomes, economics, MQL5, MT5,
optimization, validation, paper trading and live trading remain closed.

## Bound free quote

- Receipt:
  `02. AlphaFactory/data/databento/gc_order_flow_innovation/HYP-GC-OFI-INNOV-XAU-M5-001/GCOFI001-Q1-2019-SOURCE-PILOT-001/metadata_quote_receipt.json`
- Receipt SHA-256:
  `AB7E59772C92149F903092FB5C32C95E97B4F974540690B10578B499BAFD7285`
- Estimate: USD `8.955708209425`, strictly below USD 10.00.
- Estimated billable bytes: `343488960`.
- Per schema: `tbbo` USD `8.955564200878` / `343427280` bytes;
  `definition` USD `0.000063393265` / `40040` bytes; `status` USD
  `0.000080615282` / `21640` bytes.
- The receipt records zero `timeseries.get_range` and zero batch calls.

## Exact paid population

- Acquisition ID: `GCOFI001-Q1-2019-SOURCE-PILOT-001`.
- Dataset/symbol: `GLBX.MDP3 / GC.v.0`.
- `stype_in=continuous`, `stype_out=instrument_id`.
- Window: `[2019-01-01T00:00:00Z, 2019-04-01T00:00:00Z)`.
- Schemas and order: `tbbo`, then `definition`, then `status`.
- Runtime: Python 3.12.10, Databento 0.55.1, databento-dbn 0.35.0,
  DBNv3; runtime receipt SHA-256
  `E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD`.

Immediately before the first paid call, the tool repeats the same six free
metadata calls, writes a fresh immutable `acquisition_plan.json`, and stops if
the aggregate is not strictly below USD 10.00 or any schema has nonpositive
billable bytes.  It may not expand or split the window.

## One-shot/no-retry behavior

1. Write `download_manifest.json` and an exact in-flight identity before every
   paid request.
2. Call `timeseries.get_range` once for that schema and write to a `.partial`
   path.
3. Validate Zstandard magic, DBN version 3, dataset/schema identity and the
   entire record stream before atomically promoting the file.
4. Bind byte count, SHA-256, record count and response metadata in the manifest.
5. A remote, partial-file, decode, schema, empty-record or identity failure
   stops immediately.  The same hypothesis/tool makes no automatic or manual
   remote retry.  Any recovery requires a fresh successor and separate review.

Paid-call ceiling: exactly three total, one per frozen schema.  No batch order,
subscription, auto-renewal, parallel paid call or other purchase is permitted.

## Post-download boundary

A complete download still has no source verdict.  A separate fail-only source
integrity tool must verify the gates in the source-pilot plan.  No XAUUSD price,
return, forward bar, PnL or target outcome may be opened until that verdict is
written.  A source PASS permits only a fresh multi-year counts-only plan.

