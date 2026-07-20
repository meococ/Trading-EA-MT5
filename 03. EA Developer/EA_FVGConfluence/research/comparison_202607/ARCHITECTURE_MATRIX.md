# Architecture and Fidelity Matrix

Evidence states are limited to `verified_exact`, `verified_proxy`, `claimed`,
and `missing_or_unknown`. Public-product marketing can never exceed `claimed`.

| Dimension | Report requirement | Current source | State | Evidence / consequence |
|---|---|---|---|---|
| FVG | Closed three-candle imbalance | Closed bars, newest scanned shift >=2 | verified_exact | Source uses no bar 0 and source-bound non-repaint audit passes. |
| Displacement | Body >1.5x average body of prior 20 | Body >=0.8 ATR or body/range >=0.55 | verified_proxy | Different statistic and permissive OR gate. |
| Sequence | sweep -> displacement -> M15 MSS -> fresh OB/FVG -> retest | Independent score >=3/5 | missing_or_unknown | Report requires all gates; source has no ordered FSM. |
| MSS/BOS | M15 break after sweep | H1/H4 soft bias/BOS | verified_proxy | Timeframe and event ordering differ. |
| Order block | Fresh, unmitigated last opposite candle | Nearby opposite candle within ATR distance | verified_proxy | No freshness, mitigation, overlap, or state lifetime. |
| Liquidity sweep | Wick beyond swing/equal/session extreme then reclaim | Recent confirmed pivot sweep | verified_proxy | No equal-high/low or session-extreme taxonomy; not forced before FVG. |
| Entry | OB/FVG overlap limit or OTE 62-79% | Market after rejection or close depth 40-60% | verified_proxy | Different entry geometry and fill physics. |
| Stop | OB origin or sweep invalidation | FVG edge plus four-pip buffer | verified_proxy | Can materially change R and lot sizing. |
| Exit | 2R/liquidity target, lock +0.5R at +1R, ATR/swing trail | 2R, partial at 1R, BE to entry, fixed 0.8R trail | verified_proxy | Management is not report-faithful. |
| Regime | ADX(14)>25 or frozen VR arm | None | missing_or_unknown | No regime gate. |
| News | Calendar blackout +/-30 minutes | Manual-window stub disabled by default | missing_or_unknown | No historical calendar provenance or fail-closed behavior. |
| Session | London 07-11 and NY 13-17 UTC | Server-time 08-12 and 13-17, static offset | verified_proxy | Not UTC/DST safe. |
| Spread | EURUSD <1.5 pip at entry/fill | <=2.5 pip pre-send | verified_proxy | Historical spread cannot be used as verified cost. |
| Prop daily risk | Stop at -1.5%, persistent | -2.0%, RAM-only state | verified_proxy | Restart can reset equity baseline and trade count. |
| Cool-off/flat | Two losses -> 2h/end-day; flat before 22 UTC | Missing | missing_or_unknown | No max-hold, end-day, or weekend flat rule. |
| Sizing/execution | Actual SL/fill/cost reconciliation | Tick-value sizing before stop-level widening | verified_proxy | Stop can widen after lot sizing; actual risk may exceed target. |
| Non-repaint | Closed-bar/as-of only | Closed-bar signal path | verified_exact | Audit is engineering-only, not edge evidence. |
| Telemetry | Auditable decisions/trades/state | Print log only | missing_or_unknown | No immutable snapshot-casebook/lifecycle telemetry contract. |

## Fixed interpretation

The current EA is a compile-valid, closed-bar research scaffold. It is not a
faithful implementation of the report's sequential setup, and neither compile
success nor architecture richness establishes economic edge. A report-faithful
FSM would be a different specimen and requires a new preregistration; it is not
silently substituted into this benchmark.

