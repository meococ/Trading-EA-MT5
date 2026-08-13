# DBNV3 RECOVERY ACQUISITION PLAN - HYP-EVENT-AGGFLOW-EURUSD-TICK-005

Frozen on 2026-08-12 after HYP004 stopped on the first paid response and before
any CME trade record field or EURUSD outcome was decoded.

## Scope and unchanged Owner ceiling

This is a recovery successor, not a new data purchase thesis. It inherits the
Owner's exact approval for the 329 frozen `GLBX.MDP3` / `trades` / `6E.v.0`
DESIGN 2019-2020 windows under one aggregate ceiling of USD 1.00. It may:

1. locally decode and hash-reconcile the already-written HYP004 `EVT0001`
   partial with a reviewed DBNv3-compatible runtime;
2. copy that exact verified file into a new HYP005 evidence root without a
   second remote request;
3. resume serial `timeseries.get_range` only from the remaining nonzero-byte
   identities;
4. record the two live zero-byte identities as explicit coverage without a
   time-series call.

The full HYP004 live estimate, including the already-started EVT0001 estimate,
is USD 0.875670075414. It remains below the Owner ceiling. HYP005 may not reset
the budget, omit EVT0001 from cost accounting, requote a different population,
or retry EVT0001 remotely.

Still forbidden: VALIDATION 2021-2022, alternate data/schema/symbol/window,
batch APIs, EURUSD target prices, signed-flow transformation, economics,
charting, MQL5, MT5, optimization, paper, promotion and live trading.

## Immutable recovery basis

- Parent hypothesis: `HYP-EVENT-AGGFLOW-EURUSD-TICK-004`
- Parent acquisition ID: `EVENTAGGFLOW004-TRADES-DESIGN-SOURCE-001`
- Parent live acquisition plan SHA256:
  `9FFC85B6B0C8EE4948119C2DE1049AFAE312DE075371208D3F1E0B8D8A240BC4`
- Parent stopped manifest SHA256:
  `124DA202639066F47D75204CB85FA7AF4C8235A75E2C7DD28C890B1AA41C1619`
- Parent `EVT0001` partial SHA256:
  `186F843AE99C9202FF70059329303ACE33843C27619B2D84CD7187A801870F50`
- Parent `EVT0001` partial bytes: 9,090
- Parent `EVT0001` request:
  `[2019-01-03T15:00:00.000Z,2019-01-03T15:00:15.000Z)`
- Parent `EVT0001` live estimate: USD 0.007167220116 and 274,848 billable
  bytes.
- Frozen parent live aggregate: USD 0.875670075414 and 33,580,128 billable
  bytes for 329 identities.
- Original free quote receipt SHA256:
  `9C48C85CEC7766E83C387841CD0F8502C7CF70BEAB3F4537737DD73E4DC12C9D`

The parent manifest must still contain exactly one `in_flight` identity,
`EVT0001`, zero completed downloads and zero zero-byte coverage rows. The
partial must remain exact; any drift blocks recovery.

## Reviewed runtime contract

- Runtime receipt:
  `HYP-EVENT-AGGFLOW-EURUSD-TICK-005_DBV3_RUNTIME_RECEIPT.json`
- Runtime receipt SHA256:
  `E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD`
- Python: 3.12.10
- `databento`: 0.55.1
- `databento-dbn`: 0.35.0
- decoder/default DBN version: 3
- critical installed wheel/binary hashes are frozen in the runtime receipt;
- `pip check`: no broken requirements;
- official 0.55 release line introduced DBNv3 support.

The legacy 0.54 runtime remains untouched for historical reproducibility.

## Recovery and resume invariants

Before remote resume, the HYP005 tool must:

- bind its exact immutable file SHA256 and focused-test SHA256 through the
  latest validator-clean HYP005 registry row;
- verify this plan, a fresh HYP005 Owner-authority receipt, the runtime receipt,
  original quote, parent plan, parent manifest and partial hashes;
- prove the 329 parent live windows exactly match the original source quote
  identities and half-open timestamps;
- prove the parent aggregate estimate is finite and <= USD 1.00;
- decode the parent partial locally with zero remote calls, require DBN v3,
  schema `trades`, positive record count and exact file hash/bytes;
- create the successor plan/manifest before any remaining paid call;
- mark EVT0001 as inherited/recovered and never invoke it remotely.

Every remaining call is serial and checkpointed before invocation. An
unresolved successor `in_flight` identity freezes the campaign and is not
retried automatically. Completion requires 329/329 coverage, where every
nonzero-byte identity has a verified DBN file and every live zero-byte identity
has an explicit no-call entry.

Download completion only opens a separately reviewed, outcome-blind
source-quality successor. It does not itself evaluate signed flow or market
edge.
