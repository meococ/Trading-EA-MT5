# EA_ProspectiveDOMTape v1.0 stopped smoke receipt

Date: 2026-08-13

Verdict: `FAIL_ENGINEERING_IO_AND_CROSS_FILE_INTEGRITY`

## Runtime boundary

- Terminal: current `FivePercentOnline-Real` MT5, build 6090.
- Collector was attached with terminal Algo Trading permission unchecked.
- Frozen symbols: `XAUUSD`, `EURUSD`, `GBPUSD`, `USDJPY`.
- The active chart was closed and file growth was rechecked over two seconds:
  zero additional bytes, followed by a `SHUTDOWN` receipt with reason 4.
- This was a source-capability smoke only; no orders, outcomes, chart bars or
  backtest economics were accessed.

## Positive source evidence

- All four symbols produced nonempty DOM snapshots.
- Stopped state: 4,221 events, 4,183 accepted snapshots, 33 duplicate payloads,
  zero empty books and zero `MarketBookGet` API errors.
- This confirms that the broker currently exposes a changing terminal-observed
  book for the four symbols. It does not establish firm exchange L2, causality
  or an edge.

## Engineering failures

The independent runtime auditor returned `FAIL`:

- five state-level I/O errors and two surviving `IO_ERROR` JSON receipts;
- no surviving `INIT` or `SUBSCRIBE` receipts;
- 199 CSV snapshot keys without their corresponding JSON snapshot;
- two reused global snapshot IDs at 3443 and additional JSON/CSV mismatches;
- output pressure was amplified by opening/closing both files and atomically
  replacing durable state after every changed book at thousands of events per
  minute.

The v1.0 files are frozen as failed evidence and are not repaired in place.
Revision 1.1 uses new filenames, a single exclusive persistent writer and
reserved durable sequence blocks.

## Artifact identities

- `dom_tape_v1.jsonl` SHA-256:
  `BD61CE1F515131B293FD41AEFF00681ABDA7908348DD4993965188C7044C7C09`
- `dom_levels_v1.csv` SHA-256:
  `37F3D659F608F734CD2E88EC370960E8D5F326ED7544D9EFA79C1F4992C0A0C7`
- `dom_state_v1.txt` SHA-256:
  `7DEB45A62A96A9668E422426990EE79B4F2DD0ED8DF5817D0EB0FA204682AA75`
- Machine-readable audit:
  `research/DOM_SMOKE_V1_0_AUDIT.json`

## Authority boundary

`SOURCE_CAPABILITY_PASS` is not granted to v1.0. No hypothesis, EA signal,
economic validation or promotion may cite this failed tape.
