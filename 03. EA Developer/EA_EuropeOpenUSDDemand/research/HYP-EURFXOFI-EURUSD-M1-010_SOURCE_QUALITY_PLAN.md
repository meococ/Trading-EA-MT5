# SOURCE-QUALITY PLAN - HYP-EURFXOFI-EURUSD-M1-010

Frozen on `2026-07-30` after HYP009 failed during parent-manifest
reconciliation and before any DBN payload feature or EURUSD target return was
read.

## Fresh source-availability contract

HYP010 is not a trading-rule rescue. It corrects only the measured HYP006
source-availability cardinality:

- terminal parent manifest SHA256
  `C2FA31D39970200DD05AF35A3E23BAE3941F1083BE870D77A4A24E4A709DF820`;
- 1,359 selected dates: TRAIN 630, VALIDATION 526, HOLDOUT 203;
- 1,356 paid DBN files in the exact `source_root/raw/` directory;
- 1,338 DBNs declare positive record counts;
- 18 paid DBNs declare `source_empty=true` and zero records but remain real
  files that must be byte/hash checked and fully decoded;
- three live-quote empty dates have no paid file;
- total explicit empty dates = 21; no date may be dropped, filled or replaced.

Attempt `EURFXOFI010-SOURCE-QUALITY-001` is exactly once. Evidence and data
roots are respectively:

- `03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EURFXOFI-EURUSD-M1-010/EURFXOFI010-SOURCE-QUALITY-001/`
- `02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/HYP-EURFXOFI-EURUSD-M1-010/EURFXOFI010-SOURCE-QUALITY-001/`

Both must be absent/empty before the attempt.

## Independent verification and empty provenance

The builder must reconcile the exact request union and split counts, reject
extra/partial/missing filenames, recheck every paid file byte length and
SHA256, fully decode all 1,356 files and match every record count. Paid empty
files must decode to exactly zero; positive files must decode to their positive
manifest count. Every positive record must be TBBO trade-space data inside its
exact end-exclusive `[14:14:45,14:15:00) Europe/Berlin` window with valid trade
and top-book fields and no crossed book.

Every feature row includes `source_empty_kind`:

- `none` for a positive-record paid DBN;
- `paid_payload_empty` for one of the exact 18 zero-record paid DBNs;
- `live_quote_empty` for one of the exact three no-file dates.

Empty rows keep null features and cannot trade later.

## Frozen signed-flow transform

For positive records only, Databento initiating side `B` contributes `+size`,
`A` contributes `-size`, and `N` contributes zero/unclassified. No tick-rule
fallback or hindsight relabel is allowed. The full-window and fixed
`[0,5)`, `[5,10)`, `[10,15)` volume/imbalance fields, trade/VWAP/move,
spread/locked/crossed/top-book context, flow acceleration and late-flow share
are identical to the hash-bound HYP007 transformation foundation. 6E tick size
remains `0.00005`.

## Hard gates and outputs

- exact 1,359 rows, splits 630/526/203;
- exact 1,338 positive, 18 paid-empty and three live-empty rows;
- exact 1,356 files rehashed and fully decoded, zero partial/extra files;
- zero crossed books and zero out-of-window records;
- at least 99% of positive-record windows have classified buy/sell volume;
- at least 95% of total aggressive volume is side-classified;
- live acquisition estimate USD2.117540538299 <= Owner USD2.25 ceiling.

Mandatory artifacts remain `source_features.parquet`, source summary, artifact
manifest, English readout and five PNGs: yearly coverage, quality
distributions, signed flow by year/split, frozen within-window trajectory and
monthly missingness. Coverage charts must distinguish both empty kinds.

## Closed surfaces

The run is local-only: zero network/paid calls, zero target returns/economics,
zero MT5/MQL5/Model0 and zero trading mutation. A PASS can hand exact source
artifact hashes only to a fresh TRAIN-economic successor. Validation and
holdout outcomes remain sealed.
