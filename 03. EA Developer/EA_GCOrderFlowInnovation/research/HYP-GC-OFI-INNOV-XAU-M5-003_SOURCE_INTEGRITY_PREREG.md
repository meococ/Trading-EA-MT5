# HYP-GC-OFI-INNOV-XAU-M5-003 — frozen Q1 source-integrity readout

Status: `SOURCE_FIELDS_ONLY`. This is the first step allowed to read aggregate
TBBO source fields. It may not evaluate the three-sigma event predicate, report
candidate/event cadence, inspect XAUUSD, calculate PnL, build MQL5 or run MT5.

## Immutable inputs

- TBBO SHA-256:
  `6E0AD7D7893A7475DECAA6C71042139474AAE136BAC77FCBF96584FEB789BAEB`.
- Definition SHA-256:
  `F3D611000866D8ACB45CB9636307410F91674EDB1B1609B9F4BB867CE5E144CB`.
- Status SHA-256:
  `B20CE73170247CADF96179137D9729EBBC771B3DD831019CFFA2E0951B6D59BE`.
- Official condition receipt SHA-256:
  `03675D70570B3A2429AD259D00C0CFE79FB7E79A82FB8E4143075BA790632972`.
- Grok v3 review SHA-256:
  `158568A54B176029A0B6DA1F83451E73B717BDA83C6E9D7F49004E4DBBA4FC09`.
- Estimator reference SHA-256:
  `48D4ABC930329803AD03587B8EA5C6814A06B89BE7B7AE8CE39CAA444FB29FE2`.
- Estimator tests SHA-256:
  `33FE9648545B71CC955C3750E5C6C4A0D03B6B79EBC7339339BA3ED99513725E`.

Official condition tape: `74 available`, `4 degraded`. Degraded UTC dates are
exactly `2019-01-15`, `2019-02-22`, `2019-03-13`, `2019-03-26`.

## Clock and condition policy

- Provider daily condition and continuous mapping use the DBN index clock,
  `ts_recv` UTC date.
- Five-minute bins and within-contract event order use `ts_event`.
- Every UTC date containing a TBBO row must have one official condition row.
- Only `available` dates enter any side, BBO, transition or replay aggregate.
- Degraded dates are skipped before field inspection and hard-reset every
  instrument on entry and exit. No status/session/transition/sigma/bin state may
  bridge them. They remain in later full-calendar cadence denominators.

## Exact source gates

1. All three DBN files must be v3, `GLBX.MDP3`, exact schema/window, and fully
   replay to nonzero records with only IDs `32257`, `14651`, `142620`.
2. TBBO metadata mappings must equal:
   - `32257 [2019-01-01,2019-02-01)`;
   - `14651 [2019-02-01,2019-03-31)`;
   - `142620 [2019-03-31,2019-04-01)`.
   Every eligible TBBO row must match its `ts_recv`-date mapping.
3. Definition must identify each ID as an outright GC future (`FUT`, asset
   `GC`, class `F`, USD, positive `0.1` price increment) before its first
   eligible trade. Any conflicting definition is fatal.
4. Available-date TBBO must have globally nondecreasing `ts_recv` and strictly
   increasing `(ts_event,sequence)` within each raw instrument. Any duplicate
   `(instrument_id,ts_event,sequence)` is fatal; nothing is dropped. Action must
   be `T`, size/price positive, and flags `F_BAD_TS_RECV (8)` or
   `F_MAYBE_BAD_BOOK (4)` must both be absent.
5. Status updates are replayed causally by `ts_recv`; `~` retains the prior
   field. A session is open only when both `is_trading=Y` and `is_quoting=Y`.
   False-to-true, official `ChangeTradingSession`, roll, and degraded-date
   boundaries hard-reset previous sign. Every eligible signed trade must have a
   known open status and one session identity; required coverage is 100%.
6. `side=B` is +1, `A` is -1, `N` is excluded and counted. Pooled A/B share
   must be at least 99% of both eligible trade count and eligible contract
   volume. Per-date/session/contract shares are reported but have no new
   threshold.
7. Completed nonoverlapping UTC five-minute bins are keyed by raw instrument
   and open session. A bin crossing any reset is unavailable. A bin containing
   the first signed trade after reset is unavailable. First/last signed-trade
   pre-trade BBOs must be positive finite `bid < ask`; otherwise that bin is
   unavailable. `R` uses last-pretrade minus first-pretrade midpoint divided by
   the definition tick; no post-trade BBO is inferred.
8. Deterministic replay is bounded before readout to the first 25 complete
   eligible sessions per instrument in chronological identity order. It
   compares the independent incremental Markov/U/X/R implementation against
   the frozen reference wherever the 10,000-transition and 1,000-bin floors are
   available, and repeats the replay twice. Values and signatures must match
   exactly within `1e-12`. The tail predicate is never evaluated and no event
   count is emitted.

Any failed gate returns `KILL_SOURCE_INTEGRITY_HYP003` and stops before cadence.
A full PASS authorizes only a separately frozen multi-year counts-only quote and
cadence plan; it is not economic evidence.
