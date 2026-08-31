# Grok SonicR v10 original-evidence recovery review

Date: 2026-08-13 (Asia/Saigon)

## Decision

`REJECT_GROK_SONICR_V10_AS_ECONOMIC_CANDIDATE`

The recovery improves provenance but does not reopen the strategy. The exact
2026-08-04 walk-forward assignments and the per-fold OOS trade ledgers do not
exist in the recovered workspace. The available source also confirms that the
object is the already-seen Dragon breakout/pullback family with symbol-specific
filters and selected parameters, not a materially new preregistrable mechanism.

The project goal remains `ACTIVE / UNMET`. No hypothesis ID, compile, MT5 run,
price outcome, purchase, trial, contact or promotion authority was opened.

## Frozen intake identity

- Local package:
  `.context/external/grok_sonicr_v10/SonicR_MT5_QUALITY_v10.zip`
- SHA256:
  `77709C82212FACD6DF4F74C31A6EBD1581DEB033DECF60C03EC5C3494EA921DA`
- Size: `158707` bytes; ZIP entries: `76`.
- The local package still contains `0/9` named freeze artifacts checked in this
  review. The recovered objects remain separate from that original package.

## Grok Build recovery receipt

Grok Build was constrained to original-byte discovery only: no regeneration,
web research, result production, backtest or modification of the recovered
evidence bytes.

Grok returned:

`ORIGINAL_EVIDENCE_INCOMPLETE: walk-forward fold assignments`

The rendered manifest was copied byte-for-byte into:

`.context/external/grok_sonicr_v10/recovery/ORIGINAL_EVIDENCE_RECOVERY_MANIFEST.json`

- Local size: `12482` bytes.
- Local SHA256:
  `2C51A59F4421FCAAD9345096118BF2E00777F939214784378F2440CDA2738F18`.
- Named freeze artifacts found: `9/9`.
- Reproducibility objects found: `1/3`.
- First missing object: exact walk-forward fold assignments.
- Second missing object: per-fold OOS trade ledgers.

The separately generated Grok workspace ZIP is labelled
`SonicR_v10_ORIGINAL_EVIDENCE_INCOMPLETE.zip`. It is not treated as locally
verified evidence in this receipt because its bytes were not acquired into the
local quarantine. Only the rendered manifest and source/result views described
below were used.

## Direct source inspection

The following source/result objects were inspected in Grok's file view, not
accepted from the chat summary alone.

### Mechanism identity

`engine_enhanced.py` implements the familiar Sonic/Dragon family:

- breakout: prior close inside the Dragon channel and current close beyond the
  upper/lower band;
- optional pullback: a prior beyond-band state followed by a Dragon-mid or
  band retest;
- filters: Dragon slope, higher-timeframe EMA slope, close-vs-mid bias,
  candle direction/body, ADX, volatility percentile, session/hour blocks and
  ATR chase distance;
- fill model: next-bar open plus/minus a fixed spread proxy, with ATR SL/TP,
  partial exit, break-even and trail logic.

This is not a new information object relative to the closed Sonic/Dragon
breakout and pullback family.

### Outcome-conditioned configuration

`pair_configs.py` includes outcome comments in the source and separate recipes
per symbol. The XAUUSD recipe alone selects Dragon 13, SL 1.5 ATR, TP 2.1 ATR,
ADX 15, session 06-17, HTF/body filters, 0.25 ATR minimum body, chase cap,
cooldown and partial-exit settings. Other pairs change sessions, blocked hours,
SL/TP, ADX, direction/context filters and cooldowns. Its exposed parameter grid
also spans ADX, SL, partial-R and partial fraction.

Those choices cannot be presented as a fresh, outcome-blind preregistration
after the source comments and external result tables have already been seen.
Project rules also forbid rescuing a failed family by post-readout sessions,
direction, SL/TP, sizing or threshold selection.

### Walk-forward evidence gap

`walk_forward.py` can calculate folds and returns in-memory fold rows plus OOS
trades. `run_all.py` calls it with `force_fixed=True`, but serializes only fold
number, selected parameters, aggregate fold PF and trade count. It omits the
exact train/test bar or timestamp bounds and omits the per-fold trades.

`walkforward_XAUUSD.json` contains seven aggregate fold rows, including one
fold below PF 1, but no assignment bounds and no ledgers. Re-running
`make_folds()` now would create a new reconstruction after outcomes were seen;
it would not prove the bytes used for the 2026-08-04 table.

### Data-contract mismatch

`data_loader.py` is a yfinance loader. Its XAUUSD fallback order starts with
`GC=F`, then `XAUUSD=X`, then `GLD`. The recovered XAU cache is therefore not a
hash-bound broker-native MT5 XAUUSD Bid/Ask/tick contract. The fixed
`spread_pts` model does not establish commission or dynamic slippage for the
Owner's broker.

## Engineering status

The previous local MQL5 review remains controlling. The package has a bar-zero
HTF read that fails open, a Dragon buffer out-of-bounds access under the shipped
slope setting, double cooldown decrement, current-bar ATR exit updates and an
unscoped trade-transaction handler.

Therefore:

- `engineering-valid`: **NO**;
- `economic-valid`: **NO**;
- `promotion-ready`: **NO**.

The code may be used only as a reviewed implementation-shell reference for a
future materially new, independently preregistered mechanism. It is not an
authorized baseline and must not be compiled or backtested as a revival.

## Next admissible actions

1. Keep the SonicR v10 family terminal; do not reconstruct folds or repair the
   EA into a hidden new economic object.
2. Continue outcome-blind discovery for a materially distinct XAU/FX mechanism
   not already terminal in the lineage audit.
3. The prepared CLS FX Spot Flow inquiry remains the highest-information
   external source-contract step, but sending it still requires the Owner's
   explicit authorization: `Cho phép gửi inquiry CLS R2`.

## Concurrent registry note

Final validation detected a concurrent registry identity replacement. The
lineage guard correctly failed closed and was not rebound. This does not change
the SonicR v10 rejection, which is supported by the recovered source and
evidence gaps independently of the registry. Before any later
registry-authoritative candidate decision, use:
`04. Memory/research/20260813_CANDIDATE_REGISTRY_CONCURRENT_DRIFT_HOLD.md`.
