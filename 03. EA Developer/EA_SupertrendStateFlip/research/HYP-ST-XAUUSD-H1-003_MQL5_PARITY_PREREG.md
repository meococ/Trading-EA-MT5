# HYP-ST-XAUUSD-H1-003 — Frozen direct-MQL5 implementation/oracle preregistration

Status: `FROZEN_PRE_IMPLEMENTATION_CORRECTNESS_ONLY`  
Parent: `HYP-ST-XAUUSD-H1-002` (`PASS_SOURCE_FEASIBILITY`, terminal handoff; no economics)  
Candidate EA: `EA_SupertrendStateFlip`

## Objective and authority

Build and compile a direct MQL5 implementation of the exact source-passed Supertrend 10/3 state machine and seal its deterministic source oracle. This ID authorizes one oracle-build attempt plus static audit/compile only. It does not authorize opening MT5 Strategy Tester.

The sole MT5 audit and final comparator verdict require a fresh child, `HYP-ST-XAUUSD-H1-004`, whose preregistration and registry authority must bind the sealed HYP003 oracle/report/receipt/terminal, reviewed MQL source, comparator/tests, non-repaint audit, compiled binary/log and exact AlphaFactory receipt. No order API, trade, return, cost, PnL, PF, drawdown, validation, holdout, optimization, paper or live operation is authorized by HYP003.

## Frozen source identity

- Symbol/timeframe: FivePercentOnline-Real `XAUUSD`, native H1 Bid bars.
- Canonical server source start: `2004-06-11 07:00:00` (UTC `2004-06-11T04:00:00Z`).
- Design/parity UTC window: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`.
- Manifest SHA-256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- Native H1 SHA-256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`.
- Frozen Python formula dependency SHA-256: `2B48F3AA01BB2B00EB66A5AE97346F810EF549CEC2626B0DC9F175EEC890211C`.
- Source-pass ledger SHA-256: `6689F69B1EB28A6617F4555656C2237669B4A9B0FF0D886D84234AD4427FC666`.
- Canonical server-clock model: `02. AlphaFactory/tools/research/fivepercent_server_clock.py`, SHA-256 `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.

`source_epoch` is the primary parity join key. UTC is independently checked with the frozen server-clock model; no inferred constant offset is permitted.

## Exact direct formula

No `iATR`, `iCustom`, native/third-party Supertrend handle, rounding, epsilon or price normalization is allowed.

- Work oldest to newest on fully closed native H1 bars.
- Accept finite `high >= low` with close inside the range; retain `H=L=C` bars without skip/reset.
- `TR[0]=high-low`; thereafter standard maximum of high-low and both prior-close gaps.
- `ATR10[9]=mean(TR[0..9])`; thereafter evaluate exactly `(9*prior_atr + current_tr)/10` in that operation order.
- At index 9 initialize final bands from `hl2 +/- 3*ATR`, semantic state `DOWN`, line=upper, and emit no flip.
- Preserve the exact strict final-band/state update order frozen in ST002.
- When prior upper and lower coincide with the prior line, test upper identity first.
- Do not clamp, reorder or repair crossed final bands. A source-valid case has final upper below final lower.
- Carry recursion across all closures/gaps without synthetic bars.

## EA audit contract

Canonical source: `03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.mq5`.

- `OnInit` must fail unless `_Symbol==XAUUSD`, `_Period==PERIOD_H1`, `InpAuditOnly==true`, and exact prehistory beginning at server `2004-06-11 07:00:00` is available.
- `OnInit` rebuilds the frozen state through the latest closed H1 bar without emitting historical parity rows.
- On each new H1 bar, process every newly closed native bar exactly once in chronological order. Backlog processing is allowed; state never resets.
- A raw flip on closed bar `t` is executable only when the immediately following observed native bar has server epoch `t+3600`. A non-exact-next flip is recorded as raw but consumed, never queued.
- No open/forming-bar OHLC may enter the formula. Current open timestamp may be used only as the next-row timestamp for the just-closed bar.
- The EA must contain no order/trade API call. `OnTester` returns a constant non-economic value.

The audit file is written to `FILE_COMMON` under the frozen input name `ST003_MQL5_PARITY_001.csv` and then copied into the package evidence directory. Exact columns:

`schema_version,hypothesis_id,audit_run_id,source_epoch,time_server,atr10,final_upper,final_lower,supertrend,prior_state,state,raw_event,next_source_epoch,exact_next,executable_event,direction`

It contains one row for every closed H1 bar processed by the test in the design window. Numeric indicator values are serialized with 17 significant digits. No open/high/low/close, future price, position, order, return or PnL field is emitted.

## Deterministic source oracle

`build_st003_parity_oracle.py` may execute once after static review/registry authority. It reads only the frozen source columns through `<2023`, recomputes the exact hash-bound formula and persists design rows for which an immediately following source row is available inside the sealed materialization. It emits the same state/event fields plus `time_utc`, but no OHLC, return or outcome. It binds prereg/analyzer/formula/manifest/data/clock hashes, replays byte-identically and writes a receipt/terminal.

Expected invariants from the source-passed parent are frozen, not rediscovered thresholds:

- 29,461 design bars and full feature coverage;
- 690 raw flips, 683 executable flips, seven consumed next gaps;
- 339 executable LONG and 344 executable SHORT events.

## Frozen contract for the future HYP004 MT5 audit child

- Runner: `02. AlphaFactory/alpha.ps1` only.
- EA/Symbol/Period: `EA_SupertrendStateFlip`, `XAUUSD`, `H1`.
- Test window: `2018.01.01` to `2023.01.01`.
- Model: 4 (open prices only), because the EA processes completed H1 bars and places no orders.
- Execution mode/fixed delay: `0 / 0`.
- Run role/telemetry: `control / off`.
- Frozen overrides: `InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpEnableTelemetry=false;InpParityFileName=ST003_MQL5_PARITY_001.csv`.
- Exactly one reviewed MT5 parity attempt under fresh HYP004 authority after HYP003 is terminally closed and its compile/non-repaint/oracle artifacts are sealed.

Model 4 is a scheduling mechanism only; the H1 OHLC history consumed by `CopyRates` must reconcile with the canonical source through indicator parity. No tester performance metric is admissible.

## Parity comparator and pass gates

`compare_st003_mql5_parity.py` joins the MQL audit rows to the sealed oracle by exact integer `source_epoch`, verifies the UTC mapping, and fails closed on any duplicate, missing, extra, unordered or schema-invalid row.

All gates must pass:

1. MQL5 compile: zero errors and zero warnings through AlphaFactory.
2. Static non-repaint/order audit: closed-bar only; no forbidden order API; no native Supertrend/iATR dependency.
3. Exact source inception and chronological row processing.
4. Exact row coverage for every oracle-comparable design bar; no missing/extra row.
5. Exact equality for source/next epochs, prior/current state, raw/exact-next/executable flags and direction.
6. For ATR10/final upper/final lower/Supertrend, absolute error must be `<= max(1e-10, 1e-12*abs(expected))` on every row.
7. Oracle and MQL executable event counts/directions must both equal 683 / 339 LONG / 344 SHORT; raw count 690 and consumed gaps seven.
8. Byte-identical comparator replay and hash-bound receipt.
9. No orders/trades/outcome fields/performance metrics and zero access to validation/holdout.

Any failure gives an engineering/parity failure limited to this exact implementation/run. Same-ID repair after viewing the sole HYP004 MT5 parity result is forbidden; a code defect requires a fresh revision ID. All pass gives `ENGINEERING_VALID_DIRECT_MQL5_PARITY_PASS_ECONOMIC_CHILD_AUTHORIZED` and permits only a separately preregistered economic child.
