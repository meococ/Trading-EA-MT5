# HYP-EURFXOFI-EURUSD-M1-011 — Source quality with Databento receive-time clock

## Decision and provenance

- This is a fresh source-only successor after HYP010 stopped before any persisted feature, target outcome, chart or economic metric.
- The measured HYP010 failure was clock-contract drift: historical TBBO requests are filtered on the schema index timestamp `ts_recv`, while HYP010 incorrectly required every publisher `ts_event` to lie in the request range.
- On `ECBFX-2018-01-18`, all five `ts_recv` values were inside `[13:14:45, 13:15:00)` UTC. One publisher `ts_event` was 973,695 ns before the lower boundary. The new rule is therefore based on source/API semantics, not on PnL.
- Parent raw manifest SHA256: `C2FA31D39970200DD05AF35A3E23BAE3941F1083BE870D77A4A24E4A709DF820`.
- Frozen HYP010 terminal SHA256: `E9CE5B0E49F8F4C1B28287C2CF126A7175F4708C91402B81D609A3EE66D75A44`.

## Exact corpus

- Dataset/schema/symbol: `GLBX.MDP3` / `tbbo` / `6E.v.0` continuous.
- Requested local dates: 1,359 from 2016-01-01 through 2026-07-29.
- Splits remain sealed: TRAIN 630, VALIDATION 526, HOLDOUT 203.
- Raw payload root: HYP006 `raw/`.
- Exact availability: 1,338 positive-record DBNs, 18 paid zero-record DBNs and three live-quote no-file dates.
- All 21 empty dates must remain explicit rows. No deletion, fill, imputation or substitution is allowed.

## Frozen time and feature transform

1. `ts_recv` is the authoritative inclusive-start/exclusive-end range clock because it is the TBBO schema index timestamp used by the historical API.
2. `ts_recv` is also the stable ordering and three-bin clock: `[0,5)`, `[5,10)`, `[10,15)` seconds from the exact request start.
3. `ts_event` remains immutable diagnostic data. The extractor records event-before-start/event-after-end counts and event-to-receive latency statistics; an out-of-range `ts_event` does not delete a record whose `ts_recv` is legal.
4. Any `ts_recv` outside the frozen range is fatal. Duplicate/unknown identity, byte/hash/count mismatch, malformed TBBO, unsupported side, negative size or crossed book remains fatal.
5. Aggressor sign remains frozen: `B = +size`, `A = -size`, `N = 0`. No magnitude threshold and no target-conditioned transform.
6. Empty provenance is `none | paid_payload_empty | live_quote_empty`.

## Outputs and source gates

- `source_features.parquet`: exactly 1,359 rows and source-only fields.
- `source_quality_summary.json`: exact split/availability counts, 34,838 decoded records, source gates, clock diagnostics and zero outcome use.
- Five PNG charts: yearly coverage/provenance, classification quality, flow distribution, three-bin flow anatomy and clock/quality diagnostics.
- Artifact manifest and terminal evidence must hash-bind every output.
- PASS requires all exact cardinalities, 1,338 positive rows, 18 paid empty rows, three live empty rows, no `ts_recv` outside the frozen range, all 1,356 DBNs independently rehashed/decoded, no outcome fields and all artifacts present.

## One-shot authority and prohibitions

- Attempt ID: `EURFXOFI011-SOURCE-QUALITY-001`; one local attempt only after registry review authority and sentinel binding.
- Zero network calls and zero new paid requests. The Owner USD2.25 ceiling is not reopened.
- No EURUSD post-entry price, return, profit factor, drawdown, DSR, validation, holdout, MT5, MQL5, Model 0, optimization, paper or live trading.
- A PASS authorizes only a fresh TRAIN-economics hypothesis. It does not claim edge or permit EA implementation.

## Pre-outcome next decision

- `PASS_SOURCE_QUALITY`: freeze exact feature/summary/manifest hashes and open a fresh TRAIN-only economics ID using the already preregistered flow-reversal mechanism and controls.
- Any failure: terminalize this exact source contract, define the narrow failure radius and do not edit/retry HYP011.
